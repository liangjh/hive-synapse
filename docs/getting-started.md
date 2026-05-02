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
hive context status
hive backup create
hive rollback preview
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


## 7. Create a Backup and Preview Rollback

```bash
uv run hive backup create /tmp/hive-demo
uv run hive rollback preview <operation-id> --workspace /tmp/hive-demo
```

Backups live inside the organization workspace under `memory/backups/`. Rollback preview is intentionally read-only in this stage; rollback apply requires a later guarded implementation.


## 8. Import a Local Note

```bash
printf "# Launch Notes\n\nCurrent project practice." > /tmp/launch-notes.md
uv run hive import add departments/engineering /tmp/launch-notes.md --workspace /tmp/hive-demo --json
uv run hive import classify <import-id> --workspace /tmp/hive-demo
uv run hive import compact <import-id> --workspace /tmp/hive-demo
uv run hive import propose <import-id> --workspace /tmp/hive-demo
```

Imports preserve raw source material under `memory/raw/` and create candidate memory only. They do not publish shared memory directly.

## 9. Invalidate and Inspect Context Impact

```bash
uv run hive context impacted departments/engineering --workspace /tmp/hive-demo
uv run hive context invalidate departments/engineering --workspace /tmp/hive-demo --reason "practice update"
uv run hive context status departments/engineering --workspace /tmp/hive-demo
```

Dirty markers persist for dormant agents and should be checked at sign-in or before shared writes.
