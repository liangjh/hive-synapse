# MCP and Adapter Surface

Hive Synapse exposes a dependency-free MCP-compatible JSON-line tool surface for early integration.

```bash
hive mcp tools --json
hive mcp call get_context_pack --workspace /tmp/hive-demo --args-json ''{"target":"departments/engineering"}''
printf ''{"method":"tools/list"}
'' | hive mcp serve
```

Tools currently include context pack retrieval, validation, context status, import add, job enqueue, memory search, and graph impact. This surface intentionally wraps canonical runtime functions; it does not own memory semantics.
