# Explicit Superpowers bridge prototype

The prototype consists of an explicit-only skill, a Python helper, and personal
source-tree setup. It supports conventional OpenSpec artifact paths. Custom schema
layouts and full agent-runtime conflict detection remain outside its scope.

## Bootstrap installation

With Git and Python 3.12 available:

```sh
wget -qO- https://raw.githubusercontent.com/infanasotku/gigaopen/main/setup.sh | bash
```

Alternatively download setup.sh and run `bash setup.sh`. The script installs
Gigaopen into `${XDG_DATA_HOME:-~/.local/share}/gigaopen/source`, creates its venv,
installs requirements.txt there, then calls the Python `setup` command below.
It uses an existing project venv first, otherwise `python3.12` or `--python`.
It does not install system packages or edit shell profiles.

Options can be passed through the pipe with `bash -s --`:

```sh
wget -qO- https://raw.githubusercontent.com/infanasotku/gigaopen/main/setup.sh |
  bash -s -- --dir /absolute/path/to/gigaopen --python /path/to/python3.12
```

`--ref TAG_OR_COMMIT` selects the Gigaopen source revision on first installation.
For a reproducible source selection, use the same release tag or commit in both
the download URL and `--ref`. Python dependency versions still follow requirements.txt.
`--upstream CHECKOUT` passes a verified existing Superpowers checkout to setup.

Repeated runs reuse the current clean source revision without fetching updates;
an explicit different `--ref` is rejected. Modified checkouts, unrelated destination
folders, and redirected venv folders are preserved and rejected. A failed initial
fetch leaves its newly created directory for inspection. Dependency installation
may still need network access. Registration failures preserve other installations;
if moving from a development checkout, uninstall its registration explicitly first.
The bootstrap does not migrate old plans or replace an existing registration.

The success message reports the installed commit, skill invocation, and registration
removal command. Keep the installation directory and venv while using the bridge.

## Local setup

Create a Python 3.12 virtual environment at `venv/`. From the Gigaopen source root:

```sh
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m gigaopen setup
```

Setup fetches the exact Superpowers commit from `upstream.lock.yaml`, verifies the
pristine checkout, and registers a symlink at `~/.agents/skills/gigaopen-superpowers`.
Only the bridge is registered; its metadata disables implicit invocation. This is
an editable source-tree installation: retain the Gigaopen checkout and its venv.
Changes to the bridge in that checkout become visible through the symlink.

Default locations:

| Resource | Default |
| --- | --- |
| Upstream checkout | `~/.cache/gigaopen/upstream/superpowers/<full-commit>/` |
| Private state | `~/.local/state/gigaopen/` |
| Bridge registration | `~/.agents/skills/gigaopen-superpowers` |

Absolute `XDG_CACHE_HOME` and `XDG_STATE_HOME` override the cache/state base folders.
State retains the existing repository/worktree/change separation. Existing sessions
are not moved or automatically rediscovered under the new defaults.

To seed the default cache without a network fetch, supply an existing pristine
checkout at the exact locked commit:

```sh
venv/bin/python -m gigaopen setup --upstream /absolute/path/to/private/superpowers
```

Repeated setup reuses a valid cache and the same registration. It refuses unrelated
files, directories, or symlinks at the registration path and never resets an existing
cache. A failed fetch removes only the new checkout created by that invocation;
interrupted or modified caches require inspection, not automatic replacement.
Source-tree setup requires Git, Bash and the project interpreter. It does not
install OpenSpec or change the lock, shell PATH, agent/model preferences, or project
files. [Codex supports personal symlinked skills and explicit invocation](https://learn.chatgpt.com/docs/build-skills).

Remove this checkout's registration with:

```sh
venv/bin/python -m gigaopen uninstall
```

Uninstall preserves the source checkout, all upstream caches and private plans. A
registration pointing somewhere else is left intact. To move the Gigaopen checkout,
uninstall before moving it and run setup from the new location.

## Try a handoff

After setup, explicitly select `$gigaopen-superpowers` for a repository and change.
The skill's `scripts/gigaopen` launcher works through the registration symlink from
any working directory. Without registration, the source skill remains usable by
absolute path. For a manual helper check, run from Gigaopen's source root:

```sh
venv/bin/python -m gigaopen prepare \
  --repo /absolute/path/to/project \
  --change add-greeting
```

`--upstream` and `--state-root` remain optional explicit overrides. No normal
command fetches code or registers skills; a missing cache reports an actionable
setup error. An existing session retains its recorded upstream and state paths.

Missing change artifacts produce `route: openspec` and no local session. Complete
artifacts produce `route: superpowers`, absolute input paths, a local plan path,
and a session JSON path. This is a handoff, not an autonomous execution engine.
Read the shared artifacts and create the plan with the bridge's instructions.

```sh
venv/bin/python -m gigaopen resolve \
  --session /absolute/path/from/prepare/session.json \
  --skill superpowers:executing-plans

venv/bin/python -m gigaopen resolve \
  --session /absolute/path/from/prepare/session.json \
  --skill requesting-code-review --resource code-reviewer.md

venv/bin/python -m gigaopen brief \
  --session /absolute/path/from/prepare/session.json --task 1
```

The last command runs the real upstream task extraction helper from the target
repository. It requires an existing local plan with a `### Task 1: ...` heading.
It creates ignored scratch under `.superpowers/sdd/` without modifying tracked
project files. Other upstream scripts must likewise run from the returned target
`execution_cwd`, using their absolute paths.

## State and failure behavior

State is scoped by the canonical Git common directory, worktree path, and change.
Re-preparing the same unchanged change preserves the existing plan and session.
Switching worktrees requires a separately prepared session.

The fingerprint includes living specs, change specs, proposal, optional design,
and task text. Task checkbox changes are treated as progress, not new requirements.
Changed or missing inputs prevent execution handoff and task extraction:
`prepare` refuses stale sessions (or routes missing artifacts back to OpenSpec),
and `brief` refuses to run the upstream helper. For this prototype, explicitly
replan using a fresh state root; existing plans and evidence are left intact.

`resolve` is a read-only lookup, so pinned skills and review templates remain
accessible after completion edits or requirement changes. Its JSON includes
`read_only: true` and `inputs_status: current` or `stale`; stale results also
include a warning against executing the old plan. It does not update the stored
fingerprint, rewrite documents, or certify completion. For example, after editing
the design, resolving a reviewer template returns fields like:

```json
{
  "path": "/private/superpowers/skills/subagent-driven-development/re-review-prompt.md",
  "execution_cwd": "/project",
  "read_only": true,
  "inputs_status": "stale",
  "warning": "OpenSpec inputs changed. Resource lookup is read-only; do not execute the stale plan or its helpers. Replan in a fresh state root before continuing execution; old state is preserved."
}
```

Keep final documents in place while reading review guidance. Before resuming
implementation or running resolved helpers directly, revalidate with `prepare`.
The CLI cannot prevent commands run outside it; the bridge skill carries this
execution rule. Invalid pins, dirty upstream trees, session identity errors,
unsafe paths, and forbidden skills still fail resolution. Version changes also
remain blocking for every command.
There is no automatic migration, task-completion update, merge, push, or archive.

An independently installed Superpowers plugin can still influence the session.
The skill explains the conflict, but automatic detection belongs to the future
`doctor` command. Current session instructions always take precedence over
upstream tool mappings and model-selection advice.

## Verification

```sh
venv/bin/python -m pytest -v
GIGAOPEN_TEST_UPSTREAM=/absolute/path/to/private/superpowers \
  venv/bin/python -m pytest -v
venv/bin/python -m ruff check --fix .
venv/bin/python -m ruff format .
```

Unit checks cover pin enforcement, artifact routing, private paths, resume and
invalidation, reference restrictions, and distinct worktree state. The optional
pinned-source check runs upstream task extraction and resolves a reviewer template.

The metadata disables implicit invocation, and the cache is not registered for
discovery. These structural properties are tested; they are not proof of model
behavior. A completed user task has exercised explicit planning, subagent execution,
review, scope changes and replanning. Broader host compatibility and ordinary-session
nonactivation remain unverified; the lock's compatibility status stays `untested`.
