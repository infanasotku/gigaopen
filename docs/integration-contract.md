# Integration contract

### Ownership and developer choice

| Owner | Responsibility |
| --- | --- |
| Target project | Shared OpenSpec artifacts, architectural decisions, high-level tasks, acceptance criteria, required checks, and archive policy |
| Developer | Agent, model, skills, implementation method, detailed planning, and local execution state |
| Gigaopen | Optional adapters, artifact handoffs, task traceability, supported upstream versions, and compatibility checks |

Developers can use Superpowers, other skills, or manual implementation against
the same change. All implementations must satisfy the project's requirements
and required checks, regardless of execution method.

Shared schemas and repository instructions must remain executor-neutral. They
must not require Superpowers skills, its execution sequence, or its private
receipts. Project rules can define acceptance and verification requirements
without prescribing a developer's agent behavior.

OpenSpec's living specs describe the current system. An active change's delta
specs define intended additions, modifications, and removals; its design records
architectural decisions. Execution plans derive from these artifacts and cannot
silently redefine them. Resolve contradictory requirements or design before
implementing affected work.

### Opt-in and entry routing

A developer explicitly selects Gigaopen and an adapter for their work. Merely
opening an OpenSpec repository or finding a change directory does not activate
the adapter. Shared repository instructions must not force that selection.

On entry, an adapter must:

1. Resolve the target repository and change. Ask which change to use when the
   request is ambiguous.
2. For new work, use OpenSpec exploration and establish the shared change
   artifacts before implementation planning. This routing must work before a
   change directory exists.
3. For existing work, read the shared artifacts and completion evidence, then
   reconcile any local execution state with their current revision.

The Superpowers adapter uses OpenSpec for exploration and design, bypassing
Superpowers' brainstorming route within the opted-in workflow. Prefer explicit
personal instructions and adapter handoffs over edits to upstream skills. Track
any necessary upstream patch against its source revision.

The pinned Superpowers Codex manifest disables hooks, but its broad skill
descriptions can still affect automatic selection. An explicitly invoked bridge
does not neutralize independently installed entry skills or other plugin hooks.
Detect and report conflicting routing;
verify startup behavior before claiming session isolation. Do not silently
rewrite the developer's existing skills or global configuration.

### Shared artifacts and local state

The shared workflow is:

```text
OpenSpec exploration
  -> proposal + delta specs + design when needed + tasks
  -> developer-selected implementation workflow
  -> project checks + verification against acceptance criteria
  -> OpenSpec archive
```

These artifact paths are relative to the target repository:

| Path | Purpose |
| --- | --- |
| `openspec/specs/` | Living specifications |
| `openspec/changes/<change>/proposal.md` | Motivation and scope |
| `openspec/changes/<change>/specs/` | Requirement deltas and acceptance scenarios |
| `openspec/changes/<change>/design.md` | Architectural decisions, when needed |
| `openspec/changes/<change>/tasks.md` | Authoritative high-level completion checklist |

Verification evidence belongs in the project's agreed review or verification
record, which may be `verify.md` in the change directory. It must be readable
without Gigaopen or Superpowers. A custom receipt format is not a prerequisite
for another developer to complete or archive the change.

Detailed execution plans, micro-step checkboxes, adapter versions, and session
state remain local by default, outside tracked project artifacts. Local state
must distinguish the repository, change, and checkout/worktree. Its storage
layout in the prototype is scoped by repository identity, worktree path, and
change under an explicitly supplied private state root.

The Superpowers adapter passes the proposal, specs, tasks, and available design
to `writing-plans`, explicitly redirecting its output to local state. Developers
may choose to share a useful plan, but it is advisory and not a required shared
schema stage. Another developer must be able to continue from the shared
artifacts without obtaining the original developer's private plan.

Map local implementation tasks back to OpenSpec task identifiers. Update the
shared checklist only when the corresponding deliverable and required checks
succeed; local micro-step completion alone is insufficient.

### Changes, verification, and completion

When requirements or design change, reconcile affected work and invalidate stale
local planning and verification evidence. Record the specification revision,
code revision, verification commands, outcomes, and unresolved findings in the
shared verification record. File existence alone does not prove completion.

Archive follows the project's acceptance and verification requirements. Failed
checks or unresolved blocking findings keep the change open. Git finalization
and remote actions follow project policy and user authorization; archive does
not authorize merging or publishing code.

### Personal installation and upstream updates

The first installation target is a developer's personal agent environment,
with explicit adapter opt-in. Installation must not add Superpowers skills,
bootstrap instructions, or adapter requirements to the target project's tracked
files. A private project overlay or dedicated execution environment may be added
later; neither is currently implemented or verified.

`upstream.lock.yaml` belongs to Gigaopen's distribution. It pins the upstream
baseline supported by the optional Superpowers adapter, not a dependency every
target repository or developer must adopt. Installation must disclose the
selected versions and avoid overwriting independently managed installations.

Record the selected adapter version in local execution state. Resume with that
version or explicitly migrate and revalidate affected local state. Other
developers may use different executors or versions while satisfying the same
shared requirements.

Upstream updates are candidate changes: review upstream differences, run
structural and behavioral compatibility checks, then accept new pins. Preserve
the previous tested baseline for rollback. Installation and normal execution
must not advance pins automatically.
