#!/usr/bin/env bash
# Keep execution inside main so a piped download is parsed before installation starts.
set -euo pipefail

fail() { echo "gigaopen setup: $*" >&2; exit 1; }
run_git() { git -c core.hooksPath=/dev/null -c init.templateDir= "$@"; }

main() {
  local repository='https://github.com/infanasotku/gigaopen.git'
  local install_dir="${XDG_DATA_HOME:-$HOME/.local/share}/gigaopen/source"
  local requested_ref='main' explicit_ref=false interpreter='' upstream=''
  local source_head current_ref recorded_ref recorded_commit checkout_root
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dir|--ref|--python|--upstream)
        [[ $# -ge 2 && -n "$2" ]] || fail "$1 requires a value"
        case "$1" in
          --dir) install_dir=$2 ;;
          --ref) requested_ref=$2; explicit_ref=true ;;
          --python) interpreter=$2 ;;
          --upstream) upstream=$2 ;;
        esac
        shift 2 ;;
      -h|--help)
        cat <<'HELP'
Usage: bash setup.sh [--dir ABSOLUTE_PATH] [--ref REF] [--python PYTHON_3_12] [--upstream CHECKOUT]

Installs Gigaopen into ${XDG_DATA_HOME:-~/.local/share}/gigaopen/source,
creates its Python 3.12 venv, and registers the explicit-only personal bridge.
--ref selects a branch, tag, or commit for a NEW installation (default: main).
Existing clean installations are reused without fetching or changing revisions.
--upstream seeds the private Superpowers cache from an existing pinned checkout.
HELP
        return ;;
      *) fail "Unknown option: $1 (see --help)" ;;
    esac
  done
  [[ "$install_dir" == /* && "$install_dir" != / ]] || fail '--dir / XDG_DATA_HOME must yield an absolute non-root path'
  [[ -n "$requested_ref" && "$requested_ref" != -* ]] || fail 'Invalid --ref'
  [[ ! -L "$install_dir" ]] || fail 'Installation directory must not be a symlink'
  command -v git >/dev/null || fail 'Git is required'
  if [[ -n "$upstream" && "$upstream" != /* ]]; then upstream="$PWD/$upstream"; fi
  [[ ! -L "$install_dir/venv" ]] || fail 'Project venv must not redirect to another environment'

  if [[ -e "$install_dir" ]]; then
    [[ -d "$install_dir" && -e "$install_dir/.git" ]] || fail "Destination already exists and is not a Gigaopen checkout: $install_dir"
    checkout_root=$(run_git -C "$install_dir" rev-parse --show-toplevel) || fail 'Cannot inspect checkout'
    [[ "$(cd "$install_dir" && pwd -P)" == "$(cd "$checkout_root" && pwd -P)" ]] || fail 'Destination must be the checkout root'
    case "$(run_git -C "$install_dir" config --get remote.origin.url)" in
      "$repository"|https://github.com/infanasotku/gigaopen|git@github.com:infanasotku/gigaopen.git|ssh://git@github.com/infanasotku/gigaopen.git) ;;
      *) fail 'Destination belongs to a different repository; nothing changed' ;;
    esac
    [[ -z "$(run_git -C "$install_dir" status --porcelain --untracked-files=all)" ]] || fail 'Checkout has local changes; nothing overwritten'
    source_head=$(run_git -C "$install_dir" rev-parse HEAD)
    if [[ "$explicit_ref" == true ]]; then
      recorded_ref=$(run_git -C "$install_dir" config --get gigaopen.bootstrapRef || true)
      recorded_commit=$(run_git -C "$install_dir" config --get gigaopen.bootstrapCommit || true)
      current_ref=$(run_git -C "$install_dir" rev-parse --verify --end-of-options "$requested_ref^{commit}" 2>/dev/null || true)
      [[ "$current_ref" == "$source_head" || ( "$recorded_ref" == "$requested_ref" && "$recorded_commit" == "$source_head" ) ]] || fail 'Requested ref differs from the installed revision; updates must be performed explicitly'
    fi
    echo "Reusing Gigaopen at $source_head (no fetch or checkout)"
  fi

  if [[ -e "$install_dir/venv" || -L "$install_dir/venv" ]]; then
    [[ -x "$install_dir/venv/bin/python" ]] || fail 'Existing venv is incomplete; inspect it before retrying'
    interpreter="$install_dir/venv/bin/python"
  else
    echo 'No project venv found; creating one with Python 3.12.'
    if [[ -z "$interpreter" ]]; then
      interpreter=$(command -v python3.12) || fail 'Python 3.12 is required; install it or pass --python /path/to/python3.12'
    elif [[ "$interpreter" != */* ]]; then
      interpreter=$(command -v "$interpreter") || fail 'Requested Python interpreter was not found'
    elif [[ "$interpreter" != /* ]]; then
      interpreter="$PWD/$interpreter"
    fi
  fi
  "$interpreter" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))' || fail 'Python must be version 3.12; existing environments are never replaced'

  if [[ ! -e "$install_dir" ]]; then
    mkdir -p -- "$(dirname -- "$install_dir")"
    mkdir -- "$install_dir" || fail 'Destination was created concurrently; inspect it before retrying'
    # Failed downloads leave their new directory for inspection, never delete user data.
    run_git -C "$install_dir" init -q
    run_git -C "$install_dir" remote add origin "$repository"
    GIT_TERMINAL_PROMPT=0 run_git -C "$install_dir" fetch --depth=1 origin "$requested_ref"
    run_git -C "$install_dir" checkout --detach FETCH_HEAD
    source_head=$(run_git -C "$install_dir" rev-parse HEAD)
    run_git -C "$install_dir" config gigaopen.bootstrapRef "$requested_ref"
    run_git -C "$install_dir" config gigaopen.bootstrapCommit "$source_head"
  fi
  [[ -f "$install_dir/requirements.txt" && -f "$install_dir/gigaopen/personal.py" && -f "$install_dir/skills/gigaopen-superpowers/scripts/gigaopen" ]] || fail 'Selected revision does not support personal setup'
  if [[ ! -x "$install_dir/venv/bin/python" ]]; then
    "$interpreter" -m venv "$install_dir/venv"
  fi
  "$install_dir/venv/bin/python" -c 'import sys; from pathlib import Path; raise SystemExit(sys.version_info[:2] != (3, 12) or Path(sys.prefix).resolve() != Path(sys.argv[1]).resolve())' "$install_dir/venv" || fail 'Interpreter is not the installation Python 3.12 venv'
  (
    cd -- "$install_dir"
    venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
    if [[ -n "$upstream" ]]; then
      venv/bin/python -m gigaopen setup --upstream "$upstream"
    else
      venv/bin/python -m gigaopen setup
    fi
  )
  echo "Installed Gigaopen revision $source_head in $install_dir"
  echo 'Invoke: Use $gigaopen-superpowers to implement change <name> in this repository.'
  echo 'Uninstall registration (keeps source, caches and plans):'
  echo "  bash \"$install_dir/skills/gigaopen-superpowers/scripts/gigaopen\" uninstall"
}

main "$@" </dev/null
