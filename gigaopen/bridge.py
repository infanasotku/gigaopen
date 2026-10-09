"""Pinned source resolution and private state for an explicitly selected change."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

from gigaopen import __version__

EXECUTION_SKILLS = frozenset(
    {
        "writing-plans",
        "executing-plans",
        "subagent-driven-development",
        "using-git-worktrees",
        "test-driven-development",
        "systematic-debugging",
        "requesting-code-review",
        "receiving-code-review",
        "verification-before-completion",
        "finishing-a-development-branch",
    }
)


class BridgeError(Exception):
    """An actionable validation error, before loading or running upstream content."""


class UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise BridgeError(f"Duplicate lock key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise BridgeError(f"Git check failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _private_path(path):
    # Check spelling AND resolved location: a discoverable symlink is still exposed.
    for candidate in (path.absolute(), path.resolve()):
        pairs = zip(candidate.parts, candidate.parts[1:])
        if any(a in {".agents", ".codex"} and b == "skills" for a, b in pairs):
            raise BridgeError(
                "Use a private path outside agent skill-discovery folders."
            )


def _inside(path, root):
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise BridgeError(f"Path escapes its expected root: {path}")
    return resolved


def _artifacts(repo, change):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", change):
        raise BridgeError("Change must be a kebab-case name, not a path.")
    change_dir = _inside(repo / "openspec/changes" / change, repo)
    files = {}
    missing = []
    for name in ("proposal.md", "tasks.md"):
        path = _inside(change_dir / name, repo)
        if not path.is_file() or not path.read_text().strip():
            missing.append(name)
        else:
            files[str(path.relative_to(repo))] = path
    for relative in (
        Path("openspec/specs"),
        Path("openspec/changes") / change / "specs",
    ):
        directory = _inside(repo / relative, repo)
        for path in sorted(directory.rglob("*.md")):
            _inside(path, repo)
            files[str(path.relative_to(repo))] = path
    delta_prefix = f"openspec/changes/{change}/specs/"
    if not any(
        key.startswith(delta_prefix) and path.read_text().strip()
        for key, path in files.items()
    ):
        missing.append("specs/*.md")
    design = _inside(change_dir / "design.md", repo)
    if design.is_file():
        files[str(design.relative_to(repo))] = design
    hashes = {}
    for name, path in files.items():
        text = path.read_text()
        if name.endswith("/tasks.md"):
            # Progress is allowed to change without invalidating the implementation plan.
            text = re.sub(r"(?m)^(\s*- )\[[xX ]\]", r"\1[ ]", text)
        hashes[name] = _digest(text)
    return files, missing, _digest(json.dumps(hashes, sort_keys=True))


class Bridge:
    def __init__(self, lock_path):
        self.lock_path = Path(lock_path).resolve()
        lock = yaml.load(self.lock_path.read_text(), Loader=UniqueLoader)
        try:
            if lock["lock_version"] != 1:
                raise BridgeError("Unsupported lock version.")
            self.commit = lock["dependencies"]["superpowers"]["commit"]
        except (KeyError, TypeError) as exc:
            raise BridgeError("Lock must define the Superpowers commit.") from exc
        if not isinstance(self.commit, str) or not re.fullmatch(
            r"[0-9a-f]{40}", self.commit
        ):
            raise BridgeError("Superpowers must be pinned to a full commit SHA.")

    def upstream(self, path):
        path = Path(path).absolute()
        _private_path(path)
        root = path.resolve(strict=True)
        if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root:
            raise BridgeError("Upstream must be the root of its private Git checkout.")
        if _git(root, "rev-parse", "HEAD") != self.commit:
            raise BridgeError("Upstream HEAD differs from upstream.lock.yaml.")
        if _git(root, "status", "--porcelain", "--untracked-files=all", "--ignored"):
            raise BridgeError(
                "Upstream cache must be pristine, including ignored files."
            )
        for name in EXECUTION_SKILLS:
            self._resource(root, name, "SKILL.md")
        self._platform(root)
        return root

    def _resource(self, upstream, skill, resource):
        name = skill.removeprefix("superpowers:")
        if name not in EXECUTION_SKILLS:
            raise BridgeError(f"Skill is outside this adapter's execution set: {skill}")
        if Path(resource).is_absolute() or ".." in Path(resource).parts:
            raise BridgeError("Resource must stay within the selected skill.")
        directory = _inside(upstream / "skills" / name, upstream)
        path = _inside(directory / resource, directory)
        if not path.is_file():
            raise BridgeError(f"Missing upstream resource: {path}")
        return path

    def _platform(self, upstream):
        path = _inside(
            upstream / "skills/using-superpowers/references/codex-tools.md", upstream
        )
        if not path.is_file():
            raise BridgeError("Missing Codex platform reference.")
        return path

    def prepare(self, repo, change, upstream, state_root):
        requested_repo = Path(repo).resolve(strict=True)
        repo = Path(_git(requested_repo, "rev-parse", "--show-toplevel")).resolve()
        upstream = self.upstream(upstream)
        if upstream.is_relative_to(repo):
            raise BridgeError("Keep the upstream cache outside the target repository.")
        state_root = Path(state_root).absolute()
        _private_path(state_root)
        state_root = state_root.resolve()
        if state_root.is_relative_to(repo) or state_root.is_relative_to(upstream):
            raise BridgeError(
                "State root must be outside the target and upstream checkouts."
            )
        files, missing, fingerprint = _artifacts(repo, change)
        if missing:
            return {
                "route": "openspec",
                "missing": missing,
                "message": "Explore or complete the OpenSpec change first; no Superpowers skill loaded.",
            }
        common = str(
            Path(
                _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
            ).resolve()
        )
        identity = _digest(json.dumps([common, str(repo)]))[:24]
        directory = _inside(state_root / identity / change, state_root)
        plan = directory / "plan.md"
        session_path = directory / "session.json"
        session = {
            "schema_version": 1,
            "bridge_version": __version__,
            "repo": str(repo),
            "git_common_dir": common,
            "change": change,
            "upstream": str(upstream),
            "upstream_commit": self.commit,
            "spec_fingerprint": fingerprint,
            "artifacts": {name: str(path) for name, path in sorted(files.items())},
            "plan": str(plan),
        }
        if session_path.exists():
            self._session(session_path)
            if json.loads(session_path.read_text()) != session:
                raise BridgeError(
                    "Session identity changed; use a fresh state root for an explicit migration."
                )
        else:
            if directory.exists() and any(directory.iterdir()):
                raise BridgeError(
                    "Unowned local state exists; select a fresh state root."
                )
            directory.mkdir(parents=True, exist_ok=True)
            with session_path.open("x") as stream:
                stream.write(json.dumps(session, indent=2) + "\n")
        return {
            "route": "superpowers",
            "session": str(session_path),
            "plan": str(plan),
            "artifacts": session["artifacts"],
            "planning_skill": str(
                self._resource(upstream, "writing-plans", "SKILL.md")
            ),
            "platform_reference": str(self._platform(upstream)),
            "execution_cwd": str(repo),
            "resume": plan.exists(),
        }

    def _session(self, path):
        path = Path(path).resolve(strict=True)
        session = json.loads(path.read_text())
        if (
            session.get("schema_version") != 1
            or session.get("bridge_version") != __version__
        ):
            raise BridgeError(
                "Session version changed; explicitly migrate or use fresh local state."
            )
        if session["upstream_commit"] != self.commit:
            raise BridgeError(
                "Session upstream pin changed; explicitly migrate or use fresh local state."
            )
        repo = Path(session["repo"]).resolve(strict=True)
        if path.is_relative_to(repo):
            raise BridgeError("Session must stay outside the target repository.")
        common = Path(
            _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
        ).resolve()
        if str(common) != session["git_common_dir"]:
            raise BridgeError("Target repository identity changed.")
        expected_plan = path.parent / "plan.md"
        if Path(session["plan"]) != expected_plan or expected_plan.is_symlink():
            raise BridgeError("Plan must be an ordinary file beside its session.")
        self.upstream(session["upstream"])
        _, missing, fingerprint = _artifacts(repo, session["change"])
        if missing or fingerprint != session["spec_fingerprint"]:
            raise BridgeError(
                "OpenSpec inputs changed. Replan in a fresh state root; old state is preserved."
            )
        return session

    def resolve(self, session_path, skill, resource="SKILL.md"):
        session = self._session(session_path)
        path = self._resource(Path(session["upstream"]), skill, resource)
        return {"path": str(path), "execution_cwd": session["repo"]}

    def brief(self, session_path, task):
        if task < 1:
            raise BridgeError("Task number must be positive.")
        session = self._session(session_path)
        plan = Path(session["plan"])
        if not plan.is_file():
            raise BridgeError(
                "Write the local implementation plan before extracting a brief."
            )
        helper = self._resource(
            Path(session["upstream"]),
            "subagent-driven-development",
            "scripts/task-brief",
        )
        result = subprocess.run(
            ["bash", str(helper), str(plan), str(task)],
            cwd=session["repo"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise BridgeError(f"Upstream task-brief failed: {result.stderr.strip()}")
        return {"output": result.stdout.strip(), "execution_cwd": session["repo"]}
