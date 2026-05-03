# Getting Started

This guide sets up a local Hive Synapse workspace for a team of agents.

## 1. Install Runtime Dependencies

Hive Synapse is Python-first.

Source checkout runner:

```bash
./bin/hive --help
```

Installed package entry point:

```bash
hive --help
```

The MVP runtime has no required third-party dependencies. If you do not use `uv`, install the package in editable mode with your Python environment manager of choice.

## 2. Inspect the CLI

```bash
./bin/hive --help
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
./bin/hive init /tmp/hive-demo --fixture basic-org
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
./bin/hive validate /tmp/hive-demo
```

Validation checks required directories, graph records, memory records, source references, and duplicate IDs.

## 5. Compile a Context Pack

```bash
./bin/hive context compile departments/engineering --workspace /tmp/hive-demo
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
./bin/hive backup create /tmp/hive-demo
./bin/hive rollback preview <operation-id> --workspace /tmp/hive-demo
```

Backups live inside the organization workspace under `memory/backups/`. Rollback preview is intentionally read-only in this stage; rollback apply requires a later guarded implementation.


## 8. Import a Local Note

```bash
printf "# Launch Notes\n\nCurrent project practice." > /tmp/launch-notes.md
./bin/hive import add departments/engineering /tmp/launch-notes.md --workspace /tmp/hive-demo --json
./bin/hive import classify <import-id> --workspace /tmp/hive-demo
./bin/hive import compact <import-id> --workspace /tmp/hive-demo
./bin/hive import propose <import-id> --workspace /tmp/hive-demo
```

Imports preserve raw source material under `memory/raw/` and create candidate memory only. They do not publish shared memory directly.

## 9. Invalidate and Inspect Context Impact

```bash
./bin/hive context impacted departments/engineering --workspace /tmp/hive-demo
./bin/hive context invalidate departments/engineering --workspace /tmp/hive-demo --reason "practice update"
./bin/hive context status departments/engineering --workspace /tmp/hive-demo
```

Dirty markers persist for dormant agents and should be checked at sign-in or before shared writes.


## 10. Review, Promote, and Automate

```bash
./bin/hive promote sweep --workspace /tmp/hive-demo --create-proposals --json
./bin/hive promote review <proposal-id> --workspace /tmp/hive-demo --decision approved --actor steward:engineering --rationale "source-backed reusable practice"
./bin/hive promote apply <proposal-id> --workspace /tmp/hive-demo --actor steward:engineering
./bin/hive job enqueue context_rebuild departments/engineering --workspace /tmp/hive-demo --reason "refresh after promotion"
./bin/hive job run --workspace /tmp/hive-demo
./bin/hive job watchdog --workspace /tmp/hive-demo --enqueue
```

Promotion is conservative by default. Sweeps can create proposals, but publishing requires an approved proposal and an authorized actor.


## 11. Lifecycle, Skills, and Upgrades

```bash
./bin/hive node create departments/research --workspace /tmp/hive-demo --kind department --title "Research" --parent org --actor human:admin
./bin/hive actor assign agent:research-001 --workspace /tmp/hive-demo --home-node departments/research --role contributor --actor human:admin
./bin/hive skill register literature-review --workspace /tmp/hive-demo --title "Literature Review" --scope departments/research --trigger "research synthesis" --actor steward:research
./bin/hive archive sweep --workspace /tmp/hive-demo
./bin/hive upgrade doctor --workspace /tmp/hive-demo
./bin/hive upgrade migration-dry-run 001_runtime_markers --workspace /tmp/hive-demo
./bin/hive upgrade template-diff --workspace /tmp/hive-demo
```

Runtime upgrade operations are designed to be non-clobbering. Template diffing reports differences first; template apply only creates missing files.

## 12. Connector and Persistence Registries

```bash
./bin/hive connector list --json
./bin/hive persistence list --json
./bin/hive import fetch departments/engineering https://github.com/example/repo --connector github --workspace /tmp/hive-demo
```

Filesystem Markdown remains canonical in the MVP. Vector, relational, and temporal graph stores are modeled as future projections from canonical records.
