# Hive Context

Use this skill when a Codex agent needs Hive Synapse workspace context, validation, imports, jobs, or stale-context checks.

## Canonical Commands

- `hive context status <target> --workspace <workspace>` before shared writes.
- `hive context compile <target> --workspace <workspace>` to refresh a context pack.
- `hive validate <workspace>` before and after mutating workflows.
- `hive mcp call get_context_pack --workspace <workspace> --args-json ''{"target":"departments/engineering"}''` for adapter-safe context retrieval.

Do not duplicate memory semantics in Codex prompts. Call the Hive CLI or MCP surface.
