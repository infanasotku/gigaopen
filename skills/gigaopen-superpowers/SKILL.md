---
name: gigaopen-superpowers
description: Explicitly opt into implementing an OpenSpec change with the pinned Superpowers workflow through Gigaopen. Use only when the developer selects this bridge, never merely because a repository contains OpenSpec.
---

# Gigaopen Superpowers bridge

This source-tree prototype connects an explicitly selected OpenSpec change to
private Superpowers resources. It does not install or globally activate them.
The companion CLI and lock live at the bundle root, two directories above this
skill's directory. Run its CLI from that root using `venv/bin/python -m gigaopen`.

## Prepare the handoff

Resolve the target repository, change name, private pinned Superpowers checkout,
and local state root with the developer. Reuse supplied choices; ask only for
missing or ambiguous inputs. The cache and state must be outside target projects
and agent discovery folders. Do not install the upstream plugin or link its skill
tree into a discovery directory as part of this workflow.

Run `prepare --repo TARGET --change CHANGE --upstream CACHE --state-root STATE`.
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
to that skill's folder. Load sibling skills through the resolver rather than
assuming a marketplace skill of the same name is the pinned version. Retain the
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
The helper rejects changed inputs or pins while preserving old state. Replanning
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
