# Command Reference

Primary commands:

- `hive init <path> [--fixture basic-org]`
- `hive validate <workspace>`
- `hive context compile|status|impacted|invalidate`
- `hive import add|fetch|classify|compact|propose`
- `hive connector list`
- `hive persistence list`
- `hive policy show`
- `hive promote list|review|apply|reject|sweep`
- `hive job enqueue|list|claim|complete|fail|run|watchdog`
- `hive node create|move|archive|restore`
- `hive actor assign|archive`
- `hive skill register|list|status`
- `hive archive sweep`
- `hive backup create`
- `hive rollback preview`
- `hive upgrade doctor|migration-list|migration-dry-run|migration-apply|template-diff|template-apply-new`
- `hive mcp tools|call|serve`

Use `--help` on any command group or subcommand to inspect supported options. Use `--json` for agent harness calls where supported. Mutating commands append operation records under `memory/operations/`.

Operation policy lives in `policies/operations.yaml`. `hive policy show --target <node>` shows the effective workspace policy merged with a target override from `policies/nodes/` when one exists.
