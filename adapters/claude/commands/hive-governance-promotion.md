---
description: Review, promote, reject, audit, or roll back Hive Synapse shared memory changes
allowed-tools: Bash(hive promote:*), Bash(hive policy:*), Bash(hive operation:*), Bash(hive rollback:*), Bash(hive validate:*)
---

Interpret `$ARGUMENTS` as a shared-memory governance request.

Common mappings:
- list proposals: `hive promote list --workspace "$HIVE_WORKSPACE" --json`
- create proposals: `hive promote sweep --workspace "$HIVE_WORKSPACE" --create-proposals --json`
- approve: `hive promote review <proposal-id> --workspace "$HIVE_WORKSPACE" --decision approved --actor <actor> --rationale "..." --json`
- apply: `hive promote apply <proposal-id> --workspace "$HIVE_WORKSPACE" --actor <actor> --json`
- reject: `hive promote reject <proposal-id> --workspace "$HIVE_WORKSPACE" --actor <actor> --rationale "..." --json`
- inspect policy: `hive policy show --workspace "$HIVE_WORKSPACE" --target <node-id> --json`
- rollback preview: `hive rollback preview <operation-id> --workspace "$HIVE_WORKSPACE" --json`

Parent/org memory should be conservative and source-backed. Use edge memory for scoped cross-team sharing.
