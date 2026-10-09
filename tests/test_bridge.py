import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gigaopen.bridge import EXECUTION_SKILLS, Bridge, BridgeError


def git(repo, *args):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], env=env, text=True, stderr=subprocess.PIPE
    ).strip()


def init_repo(path):
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.name", "Gigaopen test")
    git(path, "config", "user.email", "fixture@example.invalid")


class TestBridge:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path.resolve()
        self.repo = self.root / "project"
        init_repo(self.repo)
        self.change = "add-greeting"
        self.artifact_dir = self.repo / "openspec/changes" / self.change
        self.artifact_dir.mkdir(parents=True)
        (self.artifact_dir / "proposal.md").write_text("# Why\nAdd a greeting.\n")
        (self.artifact_dir / "tasks.md").write_text("- [ ] 1.1 Implement greeting\n")
        specs = self.artifact_dir / "specs/greeting"
        specs.mkdir(parents=True)
        (specs / "spec.md").write_text("# Requirement\nGreet the caller.\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "Fixture")
        self.upstream = self.root / "upstream"
        init_repo(self.upstream)
        for name in EXECUTION_SKILLS:
            directory = self.upstream / "skills" / name
            directory.mkdir(parents=True)
            (directory / "SKILL.md").write_text(f"# {name}\n")
        refs = self.upstream / "skills/using-superpowers/references"
        refs.mkdir(parents=True)
        (refs / "codex-tools.md").write_text("# Platform guidance\n")
        git(self.upstream, "add", ".")
        git(self.upstream, "commit", "-qm", "Fixture skills")
        self.lock = self.root / "lock.yaml"
        self.lock.write_text(
            yaml.safe_dump(
                {
                    "lock_version": 1,
                    "dependencies": {
                        "superpowers": {
                            "commit": git(self.upstream, "rev-parse", "HEAD")
                        }
                    },
                }
            )
        )
        self.bridge = Bridge(self.lock)
        self.state = self.root / "state"

    def prepare(self, **kwargs):
        return self.bridge.prepare(
            kwargs.get("repo", self.repo),
            kwargs.get("change", self.change),
            kwargs.get("upstream", self.upstream),
            kwargs.get("state_root", self.state),
        )

    def test_prepare_keeps_target_clean_and_resumes_existing_plan(self):
        before = git(self.repo, "status", "--porcelain", "--untracked-files=all")
        result = self.prepare()
        assert result["route"] == "superpowers"
        plan = Path(result["plan"])
        assert not plan.is_relative_to(self.repo)
        plan.write_text("# Existing plan\n")
        assert self.prepare()["resume"]
        assert plan.read_text() == "# Existing plan\n"
        assert (
            git(self.repo, "status", "--porcelain", "--untracked-files=all") == before
        )

    def test_new_change_routes_to_openspec_without_creating_state(self):
        result = self.prepare(change="new-feature")
        assert result["route"] == "openspec"
        assert not self.state.exists()

    def test_missing_required_artifact_does_not_enter_execution(self):
        (self.artifact_dir / "tasks.md").unlink()
        result = self.prepare()
        assert result["route"] == "openspec"
        assert "tasks.md" in result["missing"]

    def test_reference_resolution_preserves_sibling_layout_and_blocks_entry_skills(
        self,
    ):
        session = self.prepare()["session"]
        result = self.bridge.resolve(session, "superpowers:executing-plans")
        assert Path(result["path"]) == self.upstream / "skills/executing-plans/SKILL.md"
        for skill in ["brainstorming", "using-superpowers", "../using-superpowers"]:
            with pytest.raises(BridgeError):
                self.bridge.resolve(session, skill)
        with pytest.raises(BridgeError):
            self.bridge.resolve(
                session, "writing-plans", "../using-superpowers/SKILL.md"
            )

    def test_changed_specs_reject_stale_session_and_preserve_plan(self):
        result = self.prepare()
        Path(result["plan"]).write_text("# Preserve this plan\n")
        (self.artifact_dir / "specs/greeting/spec.md").write_text(
            "Changed requirement\n"
        )
        with pytest.raises(BridgeError, match="inputs changed"):
            self.bridge.resolve(result["session"], "writing-plans")
        with pytest.raises(BridgeError):
            self.prepare()
        assert Path(result["plan"]).read_text() == "# Preserve this plan\n"
        fresh = self.prepare(state_root=self.root / "replanned")
        assert not Path(fresh["plan"]).exists()

    def test_task_progress_does_not_invalidate_plan_but_task_text_does(self):
        session = self.prepare()["session"]
        (self.artifact_dir / "tasks.md").write_text("- [x] 1.1 Implement greeting\n")
        self.bridge.resolve(session, "writing-plans")
        (self.artifact_dir / "tasks.md").write_text("- [x] 1.1 Implement farewell\n")
        with pytest.raises(BridgeError):
            self.bridge.resolve(session, "writing-plans")

    def test_pin_and_dirty_cache_rejected_before_state_creation(self):
        (self.upstream / "skills/writing-plans/SKILL.md").write_text("Changed")
        with pytest.raises(BridgeError, match="pristine"):
            self.prepare()
        git(self.upstream, "add", ".")
        git(self.upstream, "commit", "-qm", "Another revision")
        with pytest.raises(BridgeError, match="HEAD differs"):
            self.prepare()
        assert not self.state.exists()

    def test_private_paths_and_change_traversal(self):
        for state in [self.repo / "state", self.root / ".agents/skills/state"]:
            with pytest.raises(BridgeError):
                self.prepare(state_root=state)
        for change in ["../escape", "/tmp/escape", "a/b"]:
            with pytest.raises(BridgeError):
                self.prepare(change=change)

    def test_symlinked_artifact_outside_project_rejected(self):
        external = self.root / "external.md"
        external.write_text("External requirements")
        proposal = self.artifact_dir / "proposal.md"
        proposal.unlink()
        proposal.symlink_to(external)
        with pytest.raises(BridgeError, match="escapes"):
            self.prepare()

    def test_worktrees_have_distinct_sessions(self):
        worktree = self.root / "worktree"
        git(self.repo, "worktree", "add", "--detach", str(worktree), "HEAD")
        first = self.prepare()
        second = self.prepare(repo=worktree)
        assert first["session"] != second["session"]
        assert second["execution_cwd"] == str(worktree)

    def test_duplicate_lock_keys_rejected(self):
        self.lock.write_text("lock_version: 1\nlock_version: 2\n")
        with pytest.raises(BridgeError, match="Duplicate"):
            Bridge(self.lock)

    def test_tampered_plan_path_rejected(self):
        result = self.prepare()
        path = Path(result["session"])
        session = json.loads(path.read_text())
        session["plan"] = str(self.repo / "plan.md")
        path.write_text(json.dumps(session))
        with pytest.raises(BridgeError, match="beside its session"):
            self.bridge.resolve(path, "writing-plans")

    def test_explicit_discovery_policy_and_no_automatic_installation(self):
        bundle = Path(__file__).resolve().parents[1]
        skills = list((bundle / "skills").glob("*/SKILL.md"))
        assert len(skills) == 1
        metadata = yaml.safe_load((skills[0].parent / "agents/openai.yaml").read_text())
        assert metadata["policy"]["allow_implicit_invocation"] is False
        self.prepare()
        assert not (self.repo / ".agents").exists()
        assert not (self.repo / ".codex").exists()

    def test_cli_emits_handoff_json_and_actionable_error(self):
        command = [sys.executable, "-m", "gigaopen", "--lock", str(self.lock)]
        result = subprocess.run(
            command
            + [
                "prepare",
                "--repo",
                str(self.repo),
                "--change",
                self.change,
                "--upstream",
                str(self.upstream),
                "--state-root",
                str(self.state),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        handoff = json.loads(result.stdout)
        assert handoff["route"] == "superpowers"
        rejected = subprocess.run(
            command
            + ["resolve", "--session", handoff["session"], "--skill", "brainstorming"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert rejected.returncode == 1
        assert "execution set" in json.loads(rejected.stderr)["error"]

    @pytest.mark.skipif(
        not os.environ.get("GIGAOPEN_TEST_UPSTREAM"),
        reason="Set GIGAOPEN_TEST_UPSTREAM for the pinned-source smoke test",
    )
    def test_real_helper_uses_target_cwd_and_ignored_scratch(self):
        bundle = Path(__file__).resolve().parents[1]
        self.bridge = Bridge(bundle / "upstream.lock.yaml")
        upstream = Path(os.environ["GIGAOPEN_TEST_UPSTREAM"])
        result = self.prepare(upstream=upstream)
        Path(result["plan"]).write_text(
            "# Fixture implementation plan\n\n### Task 1: Greeting\n- [ ] Write a greeting test\n"
        )
        brief = self.bridge.brief(result["session"], 1)
        assert brief["execution_cwd"] == str(self.repo)
        extracted = list((self.repo / ".superpowers/sdd").glob("*/task-1-brief.md"))
        assert len(extracted) == 1
        assert "Greeting" in extracted[0].read_text()
        assert git(self.repo, "status", "--porcelain", "--untracked-files=all") == ""
        assert not (self.repo / ".gitignore").exists()
        template = self.bridge.resolve(
            result["session"], "requesting-code-review", "code-reviewer.md"
        )
        assert Path(template["path"]).is_file()
