---
description: Sign in or refresh a Hive Synapse actor with scoped context
allowed-tools: Bash(hive actor:*), Bash(hive context:*), Bash(hive validate:*)
---

Interpret `$ARGUMENTS` as a natural-language request for Hive actor sign-in, context hydration, context status, or refresh.

Use `$HIVE_WORKSPACE` as the workspace unless the user provides another path.

Common mappings:
- start/sign in actor: `hive actor signin <actor-id> --workspace "$HIVE_WORKSPACE" --require-assignment --json`
- ad hoc sign-in: `hive actor signin <actor-id> --workspace "$HIVE_WORKSPACE" --home-node <node> --role <role> --json`
- refresh running actor: `hive actor refresh <signin-id> --workspace "$HIVE_WORKSPACE" --json`
- check staleness: `hive context status <node> --workspace "$HIVE_WORKSPACE" --json`
- rebuild pack: `hive context compile <node> --workspace "$HIVE_WORKSPACE" --json`

Report only the context pack path, manifest path, stale warnings, and next action.
