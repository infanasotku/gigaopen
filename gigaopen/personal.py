"""Personal registration and explicit provisioning of the pinned source cache."""

import os
import shutil
import subprocess
from pathlib import Path

import yaml

from gigaopen.bridge import BridgeError, _private_path


def _base(variable, fallback):
    value = os.environ.get(variable)
    path = Path(value).expanduser() if value else fallback
    if not path.is_absolute():
        raise BridgeError(f"{variable} must be an absolute path.")
    return path


def _exists(path):
    return path.exists() or path.is_symlink()


class PersonalSetup:
    def __init__(self, bridge, bundle=None):
        self.bridge = bridge
        self.bundle = Path(bundle or Path(__file__).resolve().parents[1]).resolve()
        self.home = Path.home()
        self.source = self.bundle / "skills/gigaopen-superpowers"
        self.registration = self.home / ".agents/skills/gigaopen-superpowers"
        self.upstream = (
            _base("XDG_CACHE_HOME", self.home / ".cache")
            / "gigaopen/upstream/superpowers"
            / bridge.commit
        )
        self.state = _base("XDG_STATE_HOME", self.home / ".local/state") / "gigaopen"

    def _owned_registration(self):
        return (
            self.registration.is_symlink()
            and self.registration.resolve() == self.source
        )

    def _check_registration(self):
        if _exists(self.registration) and not self._owned_registration():
            raise BridgeError(
                f"Unrelated registration exists at {self.registration}; nothing overwritten."
            )

    def _validate_layout(self):
        for path in (self.upstream, self.state):
            _private_path(path)
            if path.resolve().is_relative_to(self.bundle):
                raise BridgeError(
                    "Keep personal cache and state outside the Gigaopen checkout."
                )
        cache, state = self.upstream.resolve(), self.state.resolve()
        if state.is_relative_to(cache) or cache.is_relative_to(state):
            raise BridgeError("Keep personal state and upstream cache separate.")

    def _git(self, repo, *args):
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "init.templateDir=",
                "-C",
                str(repo),
                *args,
            ],
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise BridgeError(f"Git provisioning failed: {result.stderr.strip()}")

    def _provision(self, repository):
        self.upstream.parent.mkdir(parents=True, exist_ok=True)
        # Claim an absent destination atomically. Never reset or delete existing caches.
        self.upstream.mkdir()
        try:
            self._git(self.upstream, "init", "-q")
            self._git(self.upstream, "remote", "add", "origin", str(repository))
            self._git(self.upstream, "fetch", "--depth=1", "origin", self.bridge.commit)
            self._git(self.upstream, "checkout", "--detach", self.bridge.commit)
            self.bridge.upstream(self.upstream)
        except Exception:
            # Only this invocation's newly created checkout is eligible for cleanup.
            shutil.rmtree(self.upstream)
            raise

    def setup(self, upstream=None):
        self._check_registration()
        self._validate_layout()
        if (
            not (self.source / "SKILL.md").is_file()
            or not (self.source / "scripts/gigaopen").is_file()
        ):
            raise BridgeError("Setup requires a complete Gigaopen source checkout.")
        interpreter = self.bundle / "venv/bin/python"
        if not interpreter.is_file() or not os.access(interpreter, os.X_OK):
            raise BridgeError(
                "Missing project interpreter: create venv/ with Python 3.12 and install requirements.txt first."
            )
        metadata = yaml.safe_load((self.source / "agents/openai.yaml").read_text())
        if metadata.get("policy", {}).get("allow_implicit_invocation") is not False:
            raise BridgeError(
                "The bridge must retain explicit-only invocation metadata."
            )
        repository = self.bridge.repository
        if upstream is not None:
            repository = self.bridge.upstream(Path(upstream).expanduser())
        cache_status = "reused"
        if _exists(self.upstream):
            self.bridge.upstream(self.upstream)
        else:
            if not isinstance(repository, (str, Path)) or not str(repository).strip():
                raise BridgeError(
                    "Lock must define the Superpowers repository, or supply setup --upstream CHECKOUT."
                )
            self._provision(repository)
            cache_status = "created"
        registration_status = "already_registered"
        if not self._owned_registration():
            self.registration.parent.mkdir(parents=True, exist_ok=True)
            self.registration.symlink_to(self.source, target_is_directory=True)
            registration_status = "registered"
        return {
            "registration": str(self.registration),
            "registration_status": registration_status,
            "upstream": str(self.upstream),
            "upstream_commit": self.bridge.commit,
            "cache_status": cache_status,
            "state_root": str(self.state),
            "launcher": str(self.registration / "scripts/gigaopen"),
        }

    def uninstall(self):
        self._check_registration()
        status = "not_registered"
        if self._owned_registration():
            self.registration.unlink()
            status = "removed"
        return {
            "registration": str(self.registration),
            "registration_status": status,
            "message": "Upstream caches, private state, and source checkout are preserved.",
        }

    def prepare(self, repo, change, upstream=None, state_root=None):
        selected = (
            Path(upstream).expanduser() if upstream is not None else self.upstream
        )
        state = Path(state_root).expanduser() if state_root is not None else self.state
        if not _exists(selected):
            raise BridgeError(
                f"Missing pinned Superpowers checkout: {selected}. Run Gigaopen setup "
                "explicitly, or supply --upstream CHECKOUT; prepare never downloads code."
            )
        return self.bridge.prepare(Path(repo).expanduser(), change, selected, state)
