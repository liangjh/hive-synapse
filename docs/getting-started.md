# Getting Started

This guide sets up a local Hive Synapse workspace for a team of agents.

## 1. Install Runtime Dependencies

Hive Synapse is Python-first.

```bash
uv run hive --help
```

The MVP runtime has no required third-party dependencies. If you do not use `uv`, install the package in editable mode with your Python environment manager of choice.

## 2. Inspect the CLI

```bash
uv run hive --help
```

The first stable slice supports:

```text
hive init
hive validate
hive context compile
```

Other command groups are reserved and will be implemented according to the backlog.

## 3. Create a Demo Workspace

```bash
uv run hive init /tmp/hive-demo --fixture basic-org
```

This creates a Markdown/YAML workspace:

```text
hive.config.yaml
memory/
  imports/
  raw/
  records/
  graph/
  jobs/
  state/
  proposals/
  operations/
  generated/
  audit/
org/
  members/
  roles/
  assignments/
  signins/
personas/
policies/
local-overrides/
```

Runtime-owned code and templates stay in this repository. The workspace owns local organization context.

## 4. Validate the Workspace

```bash
uv run hive validate /tmp/hive-demo
```

Validation checks required directories, graph records, memory records, source references, and duplicate IDs.

## 5. Compile a Context Pack

```bash
uv run hive context compile departments/engineering --workspace /tmp/hive-demo
```

The compiled pack is written under:

```text
memory/generated/context-packs/nodes/departments/engineering/
```

The context pack is generated. Do not hand-edit it as source of truth.

## 6. Next Capabilities

Implementation proceeds according to [`implementation-backlog.md`](implementation-backlog.md): imports, promotion, invalidation, job runner, lifecycle, archive, migrations, MCP, and harness adapters.
