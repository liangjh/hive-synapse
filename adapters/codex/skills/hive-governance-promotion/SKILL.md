---
name: hive-governance-promotion
description: Use when a user asks to promote candidate memory to shared team, department, organization, or edge context; review or reject proposals; inspect policies; or roll back Hive Synapse operations.
---

# Hive Governance + Promotion

Use promotion workflows for shared memory. Agents should not directly mutate parent department or org memory.

## Intent Mapping

- "make this shared/team knowledge" → create/review/apply a promotion proposal
- "approve this memory" → `hive promote review --decision approved`, then `hive promote apply`
- "reject this candidate" → `hive promote reject`
- "what are the rules?" → `hive policy show`
- "what changed?" → `hive operation list|show`
- "undo/inspect rollback" → `hive rollback preview`

## Commands

```bash
hive promote list --workspace <workspace> --json
hive promote sweep --workspace <workspace> --create-proposals --actor <actor> --json
hive promote review <proposal-id> --workspace <workspace> --decision approved --actor <actor> --rationale "..." --json
hive promote apply <proposal-id> --workspace <workspace> --actor <actor> --json
hive promote reject <proposal-id> --workspace <workspace> --actor <actor> --rationale "..." --json
hive policy show --workspace <workspace> --target <node-id> --json
hive rollback preview <operation-id> --workspace <workspace> --json
```

## Rules

- Source-backed memories are safer to promote.
- Parent/org memory should be conservative and high signal.
- Use edge memory for scoped cross-team collaboration.
- Validate after applying promotions.
