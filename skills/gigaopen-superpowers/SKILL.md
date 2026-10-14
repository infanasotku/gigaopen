---
name: gigaopen-superpowers
description: Explicitly opt into implementing an OpenSpec change with the pinned Superpowers workflow through Gigaopen. Use only when the developer selects this bridge, never merely because a repository contains OpenSpec.
---

# Gigaopen Superpowers bridge

This source-tree bridge connects an explicitly selected OpenSpec change to private
Superpowers resources. Personal setup registers only this bridge; opening a project
never activates it. Run the CLI through the launcher beside this skill:

```sh
bash /absolute/path/to/gigaopen-superpowers/scripts/gigaopen prepare \
  --repo /absolute/path/to/project --change CHANGE
```

Use the actual installed skill path to locate `scripts/gigaopen`. It resolves its
source checkout through the registration symlink and uses that checkout's
`venv/bin/python`, preserving the caller's working directory. No global Python or
shell PATH configuration is needed. A missing interpreter requires creating the
source checkout's Python 3.12 venv and installing its requirements.txt.

## Prepare the handoff

Resolve the target repository and change from the request/current project. Ask
only if they remain ambiguous. Reuse explicit upstream/state choices; otherwise
omit those options to use the CLI defaults. The cache defaults to
`~/.cache/gigaopen/upstream/superpowers/<locked-commit>/` and state to
`~/.local/state/gigaopen/` (respecting XDG_CACHE_HOME/XDG_STATE_HOME). Existing
sessions keep their recorded paths; defaults do not migrate old plans.

Preparation stays offline. If the pinned cache is missing, report the setup
command; run setup only when the developer authorizes personal installation.
Setup can seed its cache with `setup --upstream EXISTING_CHECKOUT`; normal handoffs
never install the upstream plugin, register its skill tree, or advance pins.

Run `prepare --repo TARGET --change CHANGE`, optionally with `--upstream CACHE`
and `--state-root STATE`. Keep cache/state outside target projects and discovery.
This verifies the upstream commit and its clean tree, fingerprints OpenSpec
inputs, and produces JSON. If the route is `openspec`, explore or complete the
missing shared artifacts using the project's OpenSpec workflow before preparing
again. Never fall back to Superpowers brainstorming. Shared schemas stay neutral.

For route `superpowers`, read the returned artifacts, platform reference, and
planning skill as needed. The platform reference is tool-mapping guidance, not
authority to change the developer's model, global configuration, or permissions;
the current host's actual tool contract takes precedence over upstream examples.
Do not load `using-superpowers/SKILL.md`.

## Load upstream resources on demand

Resolve `superpowers:<name>` through
`resolve --session SESSION --skill superpowers:NAME`, then read the returned file.
Resolve templates or scripts with `--resource RELATIVE_PATH`. Paths are relative
to that skill's folder. Resolution is read-only: inspect `inputs_status` in the
result. If it is `stale`, you may read pinned guidance and review templates, but
must not resume the old plan or run resolved helpers. Keep current OpenSpec
edits intact; never revert them just to obtain a resource. Replan in a fresh
state root before further implementation. A returned path or `execution_cwd`
is not authorization to execute; validate the session with `prepare` before
resuming implementation or running upstream helpers.

Load sibling skills through the resolver rather than assuming a marketplace skill of the same name is the pinned version. Retain the
upstream tree's relative layout. The resolver deliberately rejects brainstorming,
using-superpowers, and unrelated utility skills; unsupported branches return to
OpenSpec or the developer's chosen workflow instead of widening the adapter.

If an independently installed Superpowers entry or plugin is active, disclose
the potential conflict. Do not claim isolation or disable it without the
developer choosing how to proceed. Explicit invocation limits discovery; it
does not erase instructions already loaded into the current conversation.

## Planning and execution

Pass the returned proposal, delta and living specs, tasks, and optional design to
writing-plans. Override its output path with the returned private `plan` path.
Include a Spec pointer and a mapping from each plan task to OpenSpec task IDs.
Keep the shared requirements authoritative. Return conflicting requirements to
OpenSpec rather than silently deciding new product behavior.

If `resume` is true, inspect the existing plan and ledger; do not overwrite them.
Preparation and task extraction reject stale inputs; read-only resolution
reports them without blocking access to guidance. Pin/version checks remain
mandatory for every command, and old state is preserved. Replanning
currently requires a new state root and review of prior progress; do not copy
old completion or verification claims into the new plan without checking them.

Preserve the developer's execution choice and existing authorization. Select
executing-plans or subagent-driven-development only when supported and authorized
in this session. Follow the chosen skill's plan-review handoff. This prototype
does not dispatch agents or implement the feature by running `prepare`.

Run upstream helpers by their resolved absolute paths with the returned
`execution_cwd`, not from the cached skill folder. `brief --session SESSION
--task N` does this for task extraction. Upstream helpers write ignored scratch
under the target checkout's `.superpowers/sdd/`; the plan and session stay outside
the checkout. If using a different worktree, prepare a separate session targeting
that worktree before execution and transfer/review the plan explicitly.

Only mark shared OpenSpec tasks complete after corresponding deliverables and
required checks succeed. Put readable evidence in the project's agreed review
record. Branch finalization and archive follow project policy and user scope;
the adapter does not automatically merge, push, publish, or archive.
