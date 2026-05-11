# Command Reference

Use `--help` on any command group or subcommand to inspect exact options. Use `--json` for agent harness calls where supported. Mutating commands append operation records under `memory/operations/`.

## Workspace

- `hive init <path> [--fixture basic-org] [--force]`
- `hive validate <workspace> [--json]`

## LLM Configuration

- `hive llm init --workspace <workspace>`
- `hive llm providers`
- `hive llm config --workspace <workspace>`
- `hive llm credential add|assign ...`
- `hive llm profile add|assign ...`

LLM use is optional. Deterministic fallback remains available. Provider secrets should be stored in environment variables, not memory files.

## Charters

- `hive charter init <target>`
- `hive charter show <target>`
- `hive charter list`
- `hive charter update <target> --section mission|goals|tone|soul|principles|notes --text <text>`

Charters capture node mission, goals, tone, soul, principles, and notes.

## Context Packs

- `hive context compile <target>`
- `hive context status <target>`
- `hive context impacted <target>`
- `hive context invalidate <target> --reason <reason>`

Generated packs live under `memory/generated/context-packs/`.

## Imports and Summarization

- `hive import add <target> <source>`
- `hive import fetch <target> <url> [--connector local|obsidian|url|git|github|notion|gdrive]`
- `hive import classify <import-id>`
- `hive import compact <import-id>`
- `hive import propose <import-id>`

Notion and Google Drive currently preserve references only; authenticated fetch/watch is not implemented yet.

## Promotion

- `hive promote list [--status <status>]`
- `hive promote sweep [--create-proposals]`
- `hive promote review <proposal-id> --decision approved|rejected --actor <actor> --rationale <text>`
- `hive promote apply <proposal-id> --actor <actor>`
- `hive promote reject <proposal-id> --actor <actor> --rationale <text>`

## Jobs, Watchdogs, and Scheduling

- `hive job enqueue <type> <target> --reason <reason>`
- `hive job list [--status pending|claimed|completed|failed]`
- `hive job claim`
- `hive job complete <job-id>`
- `hive job fail <job-id> --reason <reason>`
- `hive job run`
- `hive job watchdog [--enqueue]`
- `hive scheduler install cron|launchd [--interval-minutes <n>]`

Implemented job handlers include `import_compact`, `context_rebuild`, `promotion_sweep`, `node_compact`, and `edge_compact`. Other job types may be report-only/no-op until implemented.

## Nodes, Edges, Actors

- `hive node create|move|archive|restore|compact ...`
- `hive edge create|list|archive|restore|compact ...`
- `hive actor assign|archive|signin|refresh ...`

Use `actor signin` to produce scoped context packs for deployed agents.

## Skills and Agent Adapters

- `hive skill register|list|status ...`
- `scripts/install-agent-skills.py codex|claude|generic|all [--dry-run]`

Canonical portable skills live under `skills/hive/`. Adapter-specific packages live under `adapters/`.

## Policy, Audit, Backup, Rollback

- `hive policy show [--target <node>]`
- `hive operation list|show ...`
- `hive backup create <workspace>`
- `hive rollback preview <operation-id>`

Rollback preview is read-only. Rollback apply is not implemented yet.

## Connectors and Persistence Registries

- `hive connector list`
- `hive persistence list`

Markdown filesystem storage is canonical today. Other persistence backends are planned projections.

## Upgrade and MCP

- `hive upgrade doctor|migration-list|migration-dry-run|migration-apply|template-diff|template-apply-new`
- `hive mcp tools|call|serve`

Operation policy lives in `policies/operations.yaml`. `hive policy show --target <node>` shows the effective workspace policy merged with a target override from `policies/nodes/` when one exists.
