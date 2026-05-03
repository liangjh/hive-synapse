# Workspace Layout

Runtime code lives in the Hive Synapse repository. Organization-owned memory lives in a separate workspace.

Important roots:

- `memory/graph/` stores node and edge records.
- `memory/records/` stores current, historical, candidate, reviewed, and published memory.
- `memory/imports/` stages raw imports and import items.
- `memory/raw/` preserves raw evidence as append-only artifacts.
- `memory/proposals/` stores promotion proposals.
- `memory/jobs/` stores pending, claimed, completed, and failed jobs.
- `memory/state/context-dirty/` stores invalidations that force refresh.
- `memory/generated/` stores rebuildable context packs and indexes.
- `org/assignments/` maps actors to home nodes and roles.
- `policies/` stores tunable operating policy.

Generated artifacts are rebuildable and should not be treated as source of truth.
