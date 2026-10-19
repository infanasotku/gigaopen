# Gigaopen

Gigaopen bridges shared [OpenSpec](https://github.com/Fission-AI/OpenSpec)
requirements to an optional [Superpowers](https://github.com/obra/superpowers)
implementation workflow. Each developer explicitly opts in; teammates keep their
own agents and skills. Detailed plans and session state stay private.

The source-tree prototype provides personal setup, an explicit-only bridge skill,
and a Python CLI. Full conflict diagnostics and upstream upgrade tooling remain
planned.

## Usage

With Git and Python 3.12 installed:

```sh
wget -qO- https://raw.githubusercontent.com/infanasotku/gigaopen/main/setup.sh | bash
```

The bootstrap installs a stable checkout and venv under
`~/.local/share/gigaopen/source`. For an existing development checkout, use
`venv/bin/python -m pip install -r requirements.txt`, then
`venv/bin/python -m gigaopen setup` instead.

Setup fetches the exact Superpowers commit in
[`upstream.lock.yaml`](upstream.lock.yaml) into a private cache and links only the
bridge into `~/.agents/skills/`. Keep this checkout and its venv in place.
Then explicitly ask your agent:

> Use $gigaopen-superpowers to implement OpenSpec change `add-greeting` in this repository.

The bridge uses private cache/state defaults, so you no longer need to supply
those paths. For manual use from any directory:

```sh
bash ~/.agents/skills/gigaopen-superpowers/scripts/gigaopen prepare \
  --repo /path/to/project --change add-greeting
```

`--upstream` and `--state-root` override the defaults. Normal commands stay offline.
The launcher's `uninstall` command removes only its checkout's registration;
private plans and caches remain.

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
