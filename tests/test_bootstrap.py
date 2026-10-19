"""Exercise the Bash bootstrap with real Git and a recording Python substitute."""

import os
import subprocess
from pathlib import Path

import pytest
from test_bridge import git, init_repo

SCRIPT = Path(__file__).resolve().parents[1] / "setup.sh"


@pytest.fixture
def bootstrap(tmp_path):
    source = tmp_path / "origin"
    init_repo(source)
    (source / ".gitignore").write_text("/venv/\n")
    (source / "requirements.txt").write_text("-e .\n")
    (source / "gigaopen").mkdir()
    (source / "gigaopen/personal.py").write_text("# Fixture\n")
    launcher = source / "skills/gigaopen-superpowers/scripts/gigaopen"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("# Fixture\n")
    git(source, "add", ".")
    git(source, "commit", "-qm", "Bootstrap fixture")
    git(source, "branch", "-M", "main")
    git(source, "tag", "v-test")
    configuration = tmp_path / "gitconfig"
    configuration.write_text(
        f'[url "{source}"]\n    insteadOf = https://github.com/infanasotku/gigaopen.git\n'
    )
    recorder = tmp_path / "python 3.12"
    recorder.write_text("""#!/bin/bash
set -eu
if [[ "$1" == -c ]]; then exit "${BOOTSTRAP_VERSION_EXIT:-0}"; fi
if [[ "$1" == -m && "$2" == venv ]]; then
  mkdir -p "$3/bin"
  cp "$0" "$3/bin/python"
  exit 0
fi
echo "$PWD|$*" >> "$BOOTSTRAP_LOG"
if [[ "$2" == pip ]]; then exit "${BOOTSTRAP_PIP_EXIT:-0}"; fi
""")
    recorder.chmod(0o755)
    log = tmp_path / "calls.log"
    env = dict(
        os.environ,
        GIT_CONFIG_GLOBAL=str(configuration),
        GIT_CONFIG_NOSYSTEM="1",
        BOOTSTRAP_LOG=str(log),
        XDG_DATA_HOME=str(tmp_path / "data with spaces"),
    )
    install = Path(env["XDG_DATA_HOME"]) / "gigaopen/source"

    def run(*args, piped=False):
        command = ["bash", "-s", "--"] if piped else ["bash", str(SCRIPT)]
        return subprocess.run(
            command + ["--python", str(recorder), *args],
            input=SCRIPT.read_text() if piped else None,
            text=True,
            capture_output=True,
            env=env,
            cwd=tmp_path,
        )

    return run, install, source, log, env


def test_piped_install_pins_revision_and_delegates_from_install_root(bootstrap):
    run, install, source, log, _ = bootstrap
    result = run("--ref", "v-test", "--upstream", "/private/pinned", piped=True)
    assert result.returncode == 0, result.stderr
    assert git(install, "rev-parse", "HEAD") == git(source, "rev-parse", "v-test")
    assert (install / "venv/bin/python").is_file()
    calls = log.read_text().splitlines()
    assert calls == [
        f"{install}|-m pip install --disable-pip-version-check -r requirements.txt",
        f"{install}|-m gigaopen setup --upstream /private/pinned",
    ]
    assert "$gigaopen-superpowers" in result.stdout
    assert "uninstall" in result.stdout


def test_repeat_reuses_revision_without_fetching_updates(bootstrap):
    run, install, source, _, _ = bootstrap
    assert run().returncode == 0
    previous = git(install, "rev-parse", "HEAD")
    (source / "next").write_text("New upstream revision")
    git(source, "add", ".")
    git(source, "commit", "-qm", "New revision")
    # Remove the remote source entirely from its configured location.
    source.rename(source.with_name("offline-origin"))
    result = run()
    assert result.returncode == 0, result.stderr
    assert git(install, "rev-parse", "HEAD") == previous
    assert "no fetch or checkout" in result.stdout
    assert run("--ref", "another-ref").returncode != 0
    assert git(install, "rev-parse", "HEAD") == previous


@pytest.mark.parametrize("kind", ["untracked", "tracked"])
def test_local_changes_are_preserved_and_no_python_install_runs(bootstrap, kind):
    run, install, _, log, _ = bootstrap
    assert run().returncode == 0
    marker = install / ("local-note" if kind == "untracked" else "requirements.txt")
    marker.write_text("User changes")
    before = log.read_text()
    result = run()
    assert result.returncode != 0
    assert "local changes" in result.stderr
    assert marker.read_text() == "User changes"
    assert log.read_text() == before


def test_unrelated_destination_is_untouched(bootstrap):
    run, install, _, log, _ = bootstrap
    install.mkdir(parents=True)
    marker = install / "keep"
    marker.write_text("User files")
    result = run()
    assert result.returncode != 0
    assert marker.read_text() == "User files"
    assert not log.exists()


def test_wrong_python_fails_before_download(bootstrap):
    run, install, _, log, env = bootstrap
    env["BOOTSTRAP_VERSION_EXIT"] = "1"
    result = run()
    assert result.returncode != 0
    assert "Python must be version 3.12" in result.stderr
    assert not install.exists()
    assert not log.exists()


def test_pip_failure_does_not_register_or_report_success(bootstrap):
    run, _, _, log, env = bootstrap
    env["BOOTSTRAP_PIP_EXIT"] = "1"
    result = run()
    assert result.returncode != 0
    assert "gigaopen setup" not in log.read_text()
    assert "Installed Gigaopen revision" not in result.stdout


def test_malformed_options_do_not_modify_destination(bootstrap):
    run, install, _, _, _ = bootstrap
    assert run("--unknown").returncode != 0
    assert run("--dir").returncode != 0
    assert run("--dir", "relative").returncode != 0
    assert not install.exists()


def test_installation_and_venv_symlinks_are_not_followed(bootstrap, tmp_path):
    run, install, _, log, _ = bootstrap
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    install.parent.mkdir(parents=True)
    install.symlink_to(elsewhere)
    assert run().returncode != 0
    assert not list(elsewhere.iterdir())
    assert not log.exists()
    install.unlink()
    assert run().returncode == 0
    venv = install / "venv"
    venv.rename(install / "venv-old")
    # Keep the saved environment ignored for this test of venv redirection.
    git(install, "config", "status.showUntrackedFiles", "no")
    venv.symlink_to(elsewhere)
    result = run()
    assert result.returncode != 0
    assert "another environment" in result.stderr
    assert not list(elsewhere.iterdir())


def test_failed_ref_fetch_preserves_partial_directory_for_inspection(bootstrap):
    run, install, _, log, _ = bootstrap
    result = run("--ref", "missing-ref")
    assert result.returncode != 0
    assert (install / ".git").is_dir()
    assert not log.exists()
    assert "Installed Gigaopen revision" not in result.stdout
