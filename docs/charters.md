# Node Charters

Charters are editable mission, goals, tone, soul, principles, and notes records for each organization graph node.

They are intended for high-level organizational articulation that humans and agents can jointly maintain:

- company or initiative mission
- division, department, team, or project goals
- tone and communication style
- cultural soul, values, and operating principles
- agent-facing notes that should be inherited by descendants

## Storage

Each node charter lives beside the node's current and historical memory:

```text
memory/records/nodes/<node>/CHARTER.md
memory/records/nodes/<node>/CHARTER_HISTORY.md
```

`CHARTER.md` is part of the canonical knowledge base. It is hand-editable Markdown with YAML frontmatter and validates as a memory record. `CHARTER_HISTORY.md` keeps append-only update notes from CLI-driven updates.

## Commands

```bash
./bin/hive charter init departments/engineering --workspace /tmp/hive-demo --actor steward:engineering
./bin/hive charter show departments/engineering --workspace /tmp/hive-demo
./bin/hive charter update departments/engineering \
  --workspace /tmp/hive-demo \
  --section goals \
  --text "- Ship reliable agent memory primitives." \
  --actor steward:engineering \
  --source-ref manual:planning-session
./bin/hive charter list --workspace /tmp/hive-demo
```

Supported sections are `mission`, `goals`, `tone`, `soul`, `principles`, and `notes`.

## Context Inheritance

Context packs include parent charters before parent current memory, then the target charter before target current memory. This means an agent mounted at a department inherits organization-level mission/tone/soul and then receives local team goals.

Charter updates emit operation records and dirty context markers so agents can refresh context before acting on stale mission/goals/tone.
