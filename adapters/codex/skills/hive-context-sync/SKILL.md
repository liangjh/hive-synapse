---
name: hive-context-sync
description: Use when a user asks to sign in an agent, hydrate only relevant context, refresh context, check stale context, sync top-down organizational memory, or determine what context an agent should load in Hive Synapse.
---

# Hive Context Sync

Use sign-in and context-pack commands. Agents should load scoped context packs, not the full workspace.

## Intent Mapping

- "start this agent in research" → `hive actor signin <actor> --home-node <node>`
- "refresh this running agent" → `hive actor refresh <signin-id>`
- "what should this agent load?" → sign in or inspect `org/signins/<signin-id>.yaml`
- "is context stale?" → `hive context status <target>`
- "who is impacted by this change?" → `hive context impacted <target>`
- "rebuild context" → `hive context compile <target>`

## Commands

```bash
hive actor signin <actor-id> --workspace <workspace> --require-assignment --json
hive actor signin <actor-id> --workspace <workspace> --home-node <node-id> --role <role> --json
hive actor refresh <signin-id> --workspace <workspace> --json
hive context status <node-id> --workspace <workspace> --json
hive context impacted <node-id> --workspace <workspace> --json
hive context compile <node-id> --workspace <workspace> --json
```

## Scope Rules

- Load parent hierarchy, effective node, and explicit edge context only.
- Do not load sibling departments, unrelated peer agents, raw imports, or historical archives unless explicitly requested.
- Do not copy parent/org memory into an agent folder.
- Treat agent-private memory as local working state and Hive context packs as shared organizational context.

## After Shared Updates

If a parent node, assigned node, or connected edge changed:

1. Run `hive context impacted <target>`.
2. Compact changed nodes/edges if needed.
3. Run `hive actor refresh <signin-id>` for long-running agents.
