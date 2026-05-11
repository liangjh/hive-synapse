---
name: hive-compaction-rollups
description: Use when a user asks to summarize, compact, roll up, brief, prune, or refresh memory at an agent, node, team, department, organization, or edge/collaboration level in Hive Synapse.
---

# Hive Compaction + Rollups

Use Hive compaction commands to create generated `BRIEF.md` files and scheduled rollups. Prefer commands over hand edits.

## Intent Mapping

- "summarize this team/department" → `hive node compact <node>`
- "summarize this collaboration/project edge" → `hive edge compact <edge>`
- "schedule regular compaction" → enqueue `node_compact` or `edge_compact` jobs and install scheduler
- "refresh agent startup context after compaction" → compact, then `hive context compile <node>` or `hive actor refresh <signin-id>`

## Commands

Immediate compaction:

```bash
hive node compact <node-id> --workspace <workspace> --actor <actor> --json
hive edge compact <edge-id> --workspace <workspace> --actor <actor> --json
```

Queued compaction:

```bash
hive job enqueue node_compact <node-id> --workspace <workspace> --reason "scheduled rollup" --actor <actor> --json
hive job enqueue edge_compact <edge-id> --workspace <workspace> --reason "scheduled rollup" --actor <actor> --json
hive job run --workspace <workspace> --runner runner:scheduler --json
```

## Operating Rules

- `BRIEF.md` is generated; do not hand-edit it.
- Hand-edit `CURRENT.md` or `CHARTER.md`, then compact.
- Parent/org updates should happen through promotion or controlled compaction, not direct agent writes.
- After compaction, compile or refresh context packs for affected actors.

## Validation

Run:

```bash
hive validate <workspace>
hive operation list --workspace <workspace> --type node_compact --json
```
