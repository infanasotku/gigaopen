# Gigaopen

Gigaopen bridges shared [OpenSpec](https://github.com/Fission-AI/OpenSpec)
requirements to an optional [Superpowers](https://github.com/obra/superpowers)
implementation workflow. Each developer explicitly opts in; teammates keep their
own agents and skills. Detailed plans and session state stay private.

The current prototype provides a bridge skill and Python CLI. Personal
installation, conflict detection, and end-to-end agent validation are still pending.

## Usage

Use a Python 3.12 virtual environment at `venv/`. From the Gigaopen source root:

```sh
venv/bin/python -m pip install -r requirements.txt
```

Provide a pristine Superpowers checkout at the commit in
[`upstream.lock.yaml`](upstream.lock.yaml). Keep that checkout and the state
directory outside the target repository and agent skill-discovery folders.

Ask your agent to read [the bridge skill](skills/gigaopen-superpowers/SKILL.md):

> Use Gigaopen's Superpowers bridge for `add-greeting` in `/path/to/project`,
> with upstream `/path/to/private/superpowers` and state `/path/to/private/state`.

The agent prepares the handoff with:

```sh
venv/bin/python -m gigaopen prepare \
  --repo /path/to/project \
  --change add-greeting \
  --upstream /path/to/private/superpowers \
  --state-root /path/to/private/state
```

## Flow

1. **Specify:** OpenSpec holds the shared proposal, requirement deltas, optional
   design, and tasks. Missing artifacts return `route: openspec`.
2. **Prepare:** Gigaopen checks the Superpowers pin and artifacts, then returns
   `route: superpowers`, input paths, and private session and plan locations.
3. **Implement:** The agent writes the plan and uses pinned Superpowers skills
   for execution and review. The CLI resolves resources and extracts task briefs;
   it does not implement the feature itself.
4. **Verify:** Run project checks before updating shared tasks and review evidence.
   Resume preserves the local plan; changed requirements require replanning.

See the [prototype guide](docs/prototype.md) for commands, tests, and limitations,
and the [integration contract](docs/integration-contract.md) for ownership and
upstream-update rules.

## Contributor

[infanasotku](https://github.com/infanasotku)
