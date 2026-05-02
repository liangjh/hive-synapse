# hive-synapse

Hierarchical memory and context management for organization-based AI agents.

Hive Synapse is a filesystem-first memory framework for teams of humans and AI agents. It keeps organizational context in Markdown/YAML, compiles bounded context packs for agents, and enforces promotion, validation, invalidation, rollback, and upgrade safety through deterministic CLI/MCP operations.

## Current Build Status

Implementation has started with a dependency-free Python CLI/runtime scaffold. The current focus is the Markdown/Obsidian-compatible MVP:

```text
hive init -> hive validate -> hive context compile, with repository safety, backups, and rollback preview
```

## Quick Start

```bash
uv run hive --help
uv run hive init /tmp/hive-demo --fixture basic-org
uv run hive validate /tmp/hive-demo
uv run hive context compile departments/engineering --workspace /tmp/hive-demo
uv run hive backup create /tmp/hive-demo
printf "# Launch Notes\n\nCurrent project practice." > /tmp/launch-notes.md
uv run hive import add departments/engineering /tmp/launch-notes.md --workspace /tmp/hive-demo
uv run hive promote sweep --workspace /tmp/hive-demo --create-proposals
uv run hive job watchdog --workspace /tmp/hive-demo
uv run hive upgrade doctor --workspace /tmp/hive-demo
```

See [`docs/getting-started.md`](docs/getting-started.md) for the detailed guide.

## Design and Build Plans

- [`docs/implementation-backlog.md`](docs/implementation-backlog.md): task-by-task implementation backlog.
- [`docs/implementation-test-plan.md`](docs/implementation-test-plan.md): task-mapped test plan.
- [`docs/implementation-decisions.md`](docs/implementation-decisions.md): confirmed implementation defaults.
- [`docs/concurrency-sync.md`](docs/concurrency-sync.md): Markdown/Obsidian concurrency strategy.
- [`docs/distribution-upgrade.md`](docs/distribution-upgrade.md): runtime/workspace separation and non-clobbering upgrades.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
