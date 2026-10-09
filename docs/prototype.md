# Explicit Superpowers bridge prototype

The prototype consists of one explicit-only skill and a Python helper. Nothing
is installed into personal or target-project skill registries automatically.
It currently supports conventional OpenSpec artifact paths; custom schema
layouts and agent-runtime discovery are not validated by the helper.

## Local setup

From the Gigaopen source root, use its Python 3.12+ virtual environment:

```sh
venv/bin/python -m pip install -r requirements.txt
```

Supply a separate, pristine Git checkout of Superpowers at the exact commit in
`upstream.lock.yaml`. Keep it outside skill-discovery directories and target
projects. The helper checks its HEAD and working tree on every operation. It
does not fetch code, register skills, install plugins, or update upstream pins.

## Try a handoff

Explicitly ask your agent to read and use
`skills/gigaopen-superpowers/SKILL.md` for a specified repository and change.
For a manual helper check, run from Gigaopen's source root:

```sh
venv/bin/python -m gigaopen prepare \
  --repo /absolute/path/to/project \
  --change add-greeting \
  --upstream /absolute/path/to/private/superpowers \
  --state-root /absolute/path/to/private/gigaopen-state
```

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
Changed inputs or versions stop the handoff. For this prototype, explicitly
replan using a fresh state root; existing plans and evidence are left intact.
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
behavior. A real agent session still needs to demonstrate ordinary work without
activation, explicit planning and execution, cross-skill loading, and resume.
The lock's integration compatibility remains `untested` until that is done.
