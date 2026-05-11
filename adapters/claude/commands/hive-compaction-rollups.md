---
description: Compact Hive Synapse node or edge memory into generated briefs
allowed-tools: Bash(hive node:*), Bash(hive edge:*), Bash(hive job:*), Bash(hive context:*), Bash(hive validate:*)
---

Interpret `$ARGUMENTS` as a compaction, summarization, pruning, or rollup request.

Common mappings:
- compact node/team/department: `hive node compact <node-id> --workspace "$HIVE_WORKSPACE" --json`
- compact edge/collaboration: `hive edge compact <edge-id> --workspace "$HIVE_WORKSPACE" --json`
- schedule node compaction: `hive job enqueue node_compact <node-id> --workspace "$HIVE_WORKSPACE" --reason "scheduled rollup" --json`
- schedule edge compaction: `hive job enqueue edge_compact <edge-id> --workspace "$HIVE_WORKSPACE" --reason "scheduled rollup" --json`
- refresh context after compaction: `hive context compile <node-id> --workspace "$HIVE_WORKSPACE" --json`

Never hand-edit generated `BRIEF.md`; update `CURRENT.md` or `CHARTER.md`, then compact.
