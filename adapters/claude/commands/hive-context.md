---
description: Load or refresh Hive Synapse context
allowed-tools: Bash(hive context:*), Bash(hive mcp:*)
---

Run `hive context status "$ARGUMENTS" --workspace "$HIVE_WORKSPACE"`. If stale, run `hive context compile "$ARGUMENTS" --workspace "$HIVE_WORKSPACE"` and report the generated pack path.
