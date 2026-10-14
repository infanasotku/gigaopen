import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from test_bridge import git, init_repo

from gigaopen.bridge import EXECUTION_SKILLS, Bridge, BridgeError
from gigaopen.personal import PersonalSetup

BUNDLE = Path(__file__).resolve().parents[1]


@pytest.fixture
def personal(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    upstream = tmp_path / "source"
    init_repo(upstream)
    for name in EXECUTION_SKILLS:
        folder = upstream / "skills" / name
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(f"# {name}\n")
    refs = upstream / "skills/using-superpowers/references"
    refs.mkdir(parents=True)
    (refs / "codex-tools.md").write_text("# Tools\n")
    git(upstream, "add", ".")
    git(upstream, "commit", "-qm", "Fixture")
    lock = tmp_path / "lock.yaml"
    lock.write_text(
        yaml.safe_dump(
            {
                "lock_version": 1,
                "dependencies": {
                    "superpowers": {
                        "commit": git(upstream, "rev-parse", "HEAD"),
                        "repository": str(upstream),
                    }
                },
            }
        )
    )
    return PersonalSetup(Bridge(lock), BUNDLE), upstream


def test_setup_provisions_exact_pin_and_registers_only_bridge(personal):
    manager, upstream = personal
    result = manager.setup()
    assert Path(result["upstream"]) == manager.upstream
    assert git(manager.upstream, "rev-parse", "HEAD") == git(
        upstream, "rev-parse", "HEAD"
    )
    assert git(manager.upstream, "status", "--porcelain", "--ignored") == ""
    assert manager.registration.is_symlink()
    assert manager.registration.resolve() == BUNDLE / "skills/gigaopen-superpowers"
    assert list(manager.registration.parent.iterdir()) == [manager.registration]
    metadata = yaml.safe_load((manager.registration / "agents/openai.yaml").read_text())
    assert metadata["policy"]["allow_implicit_invocation"] is False
    assert manager.upstream.name == manager.bridge.commit


def test_repeat_setup_is_offline_and_uninstall_preserves_state(personal, monkeypatch):
    manager, _ = personal
    manager.setup()
    manager.state.mkdir(parents=True)
    plan = manager.state / "plan.md"
    plan.write_text("Existing plan")
    monkeypatch.setattr(
        manager, "_provision", lambda *args: pytest.fail("must reuse cache")
    )
    assert manager.setup()["registration_status"] == "already_registered"
    assert manager.uninstall()["registration_status"] == "removed"
    assert not manager.registration.is_symlink()
    assert manager.upstream.is_dir()
    assert plan.read_text() == "Existing plan"
    assert manager.uninstall()["registration_status"] == "not_registered"


@pytest.mark.parametrize("collision", ["directory", "symlink", "broken_symlink"])
def test_setup_and_uninstall_preserve_unrelated_registration(
    personal, tmp_path, collision
):
    manager, _ = personal
    manager.registration.parent.mkdir(parents=True)
    other = tmp_path / "other"
    if collision == "directory":
        manager.registration.mkdir()
        (manager.registration / "keep").write_text("Mine")
    else:
        if collision == "symlink":
            other.mkdir()
        manager.registration.symlink_to(other)
    with pytest.raises(BridgeError, match="registration"):
        manager.setup()
    with pytest.raises(BridgeError, match="registration"):
        manager.uninstall()
    assert (
        manager.registration.is_symlink()
        or (manager.registration / "keep").read_text() == "Mine"
    )
    assert not manager.upstream.exists()


def test_dirty_cache_is_preserved_and_not_registered(personal):
    manager, _ = personal
    manager.setup()
    manager.uninstall()
    marker = manager.upstream / "keep.txt"
    marker.write_text("Local edits")
    with pytest.raises(BridgeError, match="pristine"):
        manager.setup()
    assert marker.read_text() == "Local edits"
    assert not manager.registration.exists()


def test_failed_fetch_leaves_no_registration_or_partial_cache(personal, tmp_path):
    manager, _ = personal
    manager.bridge.repository = str(tmp_path / "missing-remote")
    with pytest.raises(BridgeError, match="Git"):
        manager.setup()
    assert not manager.upstream.exists()
    assert not manager.registration.exists()


def test_verified_existing_checkout_can_seed_cache(personal):
    manager, upstream = personal
    manager.bridge.repository = None
    manager.setup(upstream=upstream)
    assert manager.upstream != upstream
    assert git(manager.upstream, "rev-parse", "HEAD") == manager.bridge.commit
    assert git(upstream, "status", "--porcelain", "--ignored") == ""


def test_wrong_seed_pin_is_rejected_without_registration(personal):
    manager, upstream = personal
    (upstream / "change").write_text("Another commit")
    git(upstream, "add", ".")
    git(upstream, "commit", "-qm", "Wrong revision")
    with pytest.raises(BridgeError, match="HEAD differs"):
        manager.setup(upstream=upstream)
    assert not manager.upstream.exists()
    assert not manager.registration.exists()


def test_xdg_defaults_and_relative_paths_rejected(personal, tmp_path, monkeypatch):
    manager, _ = personal
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    changed = PersonalSetup(manager.bridge, BUNDLE)
    assert (
        changed.upstream
        == tmp_path / "cache/gigaopen/upstream/superpowers" / manager.bridge.commit
    )
    assert changed.state == tmp_path / "state/gigaopen"
    monkeypatch.setenv("XDG_CACHE_HOME", "relative")
    with pytest.raises(BridgeError, match="absolute"):
        PersonalSetup(manager.bridge, BUNDLE)


def test_launcher_runs_from_registered_symlink_and_other_cwd(personal, tmp_path):
    manager, _ = personal
    manager.setup()
    result = subprocess.run(
        ["bash", str(manager.registration / "scripts/gigaopen"), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "prepare" in result.stdout
    assert "setup" in result.stdout


def test_cli_default_prepare_is_offline_and_explicit_overrides_work(personal, tmp_path):
    manager, upstream = personal
    manager.setup()
    repo = tmp_path / "project"
    init_repo(repo)
    (repo / "README").write_text("Fixture")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Fixture")
    env = dict(
        os.environ,
        XDG_CACHE_HOME=str(manager.home / ".cache"),
        XDG_STATE_HOME=str(manager.home / ".local/state"),
    )
    command = [
        sys.executable,
        "-m",
        "gigaopen",
        "--lock",
        str(manager.bridge.lock_path),
        "prepare",
        "--repo",
        str(repo),
        "--change",
        "new-feature",
    ]
    result = subprocess.run(
        command, env=env, cwd=BUNDLE, capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout)["route"] == "openspec"
    change = repo / "openspec/changes/new-feature"
    (change / "specs/greeting").mkdir(parents=True)
    (change / "proposal.md").write_text("Add greeting")
    (change / "tasks.md").write_text("- [ ] 1.1 Greet")
    (change / "specs/greeting/spec.md").write_text("Greet the caller")
    result = subprocess.run(
        command, env=env, cwd=BUNDLE, capture_output=True, text=True, check=True
    )
    handoff = json.loads(result.stdout)
    assert handoff["route"] == "superpowers"
    assert Path(handoff["session"]).is_relative_to(manager.state)
    env["XDG_CACHE_HOME"] = str(tmp_path / "absent-cache")
    result = subprocess.run(
        command, env=env, cwd=BUNDLE, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "setup" in json.loads(result.stderr)["error"]
    assert not Path(env["XDG_CACHE_HOME"]).exists()
    result = subprocess.run(
        command
        + ["--upstream", str(upstream), "--state-root", str(tmp_path / "custom-state")],
        env=env,
        cwd=BUNDLE,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["route"] == "superpowers"


def test_launcher_preserves_relative_target_and_avoids_cwd_module_shadow(
    personal, tmp_path
):
    manager, upstream = personal
    manager.setup()
    repo = tmp_path / "project with spaces"
    init_repo(repo)
    (tmp_path / "gigaopen.py").write_text("raise RuntimeError('Wrong module')")
    result = subprocess.run(
        [
            "bash",
            str(manager.registration / "scripts/gigaopen"),
            "--lock",
            str(manager.bridge.lock_path),
            "prepare",
            "--repo",
            repo.name,
            "--change",
            "new-feature",
            "--upstream",
            str(upstream),
            "--state-root",
            str(tmp_path / "private state"),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(result.stdout)["route"] == "openspec"


@pytest.mark.parametrize("layout", ["discovery", "overlap"])
def test_setup_rejects_unsafe_private_layout(personal, monkeypatch, layout):
    manager, _ = personal
    if layout == "discovery":
        monkeypatch.setenv("XDG_CACHE_HOME", str(manager.home / ".agents/skills/cache"))
    else:
        monkeypatch.setenv("XDG_STATE_HOME", str(manager.home / ".cache"))
    changed = PersonalSetup(manager.bridge, BUNDLE)
    with pytest.raises(BridgeError):
        changed.setup()
    assert not changed.registration.exists()
    assert not changed.upstream.exists()


def test_existing_unowned_cache_directory_is_not_replaced(personal):
    manager, _ = personal
    manager.upstream.mkdir(parents=True)
    keep = manager.upstream / "keep"
    keep.write_text("Unrelated files")
    with pytest.raises(BridgeError):
        manager.setup()
    assert keep.read_text() == "Unrelated files"
    assert not manager.registration.exists()
