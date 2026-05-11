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

The current CLI supports workspace initialization, validation, charters, context compilation/invalidation, imports, promotion review, jobs, node/edge lifecycle and compaction, actor assignment/sign-in/refresh, skills, archives, scheduler templates, operation audit, backups, upgrades, operation policy inspection, connector registries, persistence registries, and the MCP-compatible tool surface. See `docs/command-reference.md` for the full command list.

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

Inspect automation defaults:

```bash
./bin/hive policy show --workspace /tmp/hive-demo
```

Fresh workspaces start with low-noise operation policy in `policies/operations.yaml`: automatic context invalidation is observed but does not create new dirty markers, promotion sweeps are manual, watchdogs report only, and import sync is manual.

## 4. Validate the Workspace

```bash
./bin/hive validate /tmp/hive-demo
```

Validation checks required directories, graph records, memory records, source references, and duplicate IDs.

## 5. Sign In an Agent and Compile Context

The fixture includes `agent:codex-engineering-001` assigned to `departments/engineering`. Sign it in to generate scoped startup context:

```bash
./bin/hive actor signin agent:codex-engineering-001 \
  --workspace /tmp/hive-demo \
  --require-assignment \
  --json
```

The response includes a `context_pack` path under:

```text
memory/generated/context-packs/nodes/departments/engineering/
```

You can also compile the pack directly:

```bash
./bin/hive context compile departments/engineering --workspace /tmp/hive-demo
```

The context pack is generated. Do not hand-edit it as source of truth.

## 6. Create a Backup and Preview Rollback

```bash
./bin/hive backup create /tmp/hive-demo
./bin/hive rollback preview <operation-id> --workspace /tmp/hive-demo
```

Backups live inside the organization workspace under `memory/backups/`. Rollback preview is intentionally read-only in this stage; rollback apply requires a later guarded implementation.


## 7. Import a Local Note

```bash
printf "# Launch Notes\n\nCurrent project practice." > /tmp/launch-notes.md
./bin/hive import add departments/engineering /tmp/launch-notes.md --workspace /tmp/hive-demo --json
./bin/hive import classify <import-id> --workspace /tmp/hive-demo
./bin/hive import compact <import-id> --workspace /tmp/hive-demo
./bin/hive import propose <import-id> --workspace /tmp/hive-demo
```

Imports preserve raw source material under `memory/raw/` and create candidate memory only. They do not publish shared memory directly.

## 8. Invalidate and Inspect Context Impact

```bash
./bin/hive context impacted departments/engineering --workspace /tmp/hive-demo
./bin/hive context invalidate departments/engineering --workspace /tmp/hive-demo --reason "practice update"
./bin/hive context status departments/engineering --workspace /tmp/hive-demo
```

Dirty markers persist for dormant agents and should be checked at sign-in or before shared writes.

Manual `hive context invalidate` writes a dirty marker. Add `--respect-policy` when you want the command to follow the same automatic policy used by lifecycle and promotion operations.


## 9. Review, Promote, and Automate

```bash
./bin/hive promote sweep --workspace /tmp/hive-demo --create-proposals --json
./bin/hive promote review <proposal-id> --workspace /tmp/hive-demo --decision approved --actor steward:engineering --rationale "source-backed reusable practice"
./bin/hive promote apply <proposal-id> --workspace /tmp/hive-demo --actor steward:engineering
./bin/hive job enqueue context_rebuild departments/engineering --workspace /tmp/hive-demo --reason "refresh after promotion"
./bin/hive job run --workspace /tmp/hive-demo
./bin/hive job watchdog --workspace /tmp/hive-demo --enqueue
```

Promotion is conservative by default. Sweeps can create proposals, but publishing requires an approved proposal and an authorized actor.

Automatic side effects are policy-driven. With the default policy, applying a promotion updates memory and records an invalidation observation without creating a new dirty marker. Set `context_invalidation.mode: strict` in `policies/operations.yaml` when promotion and lifecycle changes should dirty affected context automatically.


## 10. Lifecycle, Compaction, Skills, and Upgrades

```bash
./bin/hive node create departments/research --workspace /tmp/hive-demo --kind department --title "Research" --parent org --actor human:admin
./bin/hive actor assign agent:research-001 --workspace /tmp/hive-demo --home-node departments/research --role contributor --actor human:admin
./bin/hive actor signin agent:research-001 --workspace /tmp/hive-demo --require-assignment --json
./bin/hive node compact departments/research --workspace /tmp/hive-demo --actor steward:research
./bin/hive edge list --workspace /tmp/hive-demo
./bin/hive skill register literature-review --workspace /tmp/hive-demo --title "Literature Review" --scope departments/research --trigger "research synthesis" --actor steward:research
./bin/hive archive sweep --workspace /tmp/hive-demo
./bin/hive scheduler install cron --workspace /tmp/hive-demo --interval-minutes 15
./bin/hive upgrade doctor --workspace /tmp/hive-demo
./bin/hive upgrade migration-dry-run 001_runtime_markers --workspace /tmp/hive-demo
./bin/hive upgrade template-diff --workspace /tmp/hive-demo
```

Runtime upgrade operations are designed to be non-clobbering. Template diffing reports differences first; template apply only creates missing files. Scheduler install writes templates under `local-overrides/schedulers/`; review them before installing into the OS.

## 11. Connector and Persistence Registries

```bash
./bin/hive connector list --json
./bin/hive persistence list --json
./bin/hive import fetch departments/engineering https://github.com/example/repo --connector github --workspace /tmp/hive-demo
```

Filesystem Markdown remains canonical in the MVP. Vector, relational, and temporal graph stores are modeled as future projections from canonical records.

## 12. Install Agent Skills

Hive ships portable skills under `skills/hive/` plus adapter packages for Codex and Claude.

```bash
scripts/install-agent-skills.py codex
scripts/install-agent-skills.py claude
scripts/install-agent-skills.py generic --target ./agent-skills
scripts/install-agent-skills.py all --dry-run
```

Use the generic target for Hermes, OpenClaw, or other harnesses that can consume Markdown `SKILL.md` style instructions. See `docs/agent-interoperability.md` and `docs/agent-skills.md`.

## 13. Known MVP Limits

- Notion and Google Drive connectors preserve external references only; authenticated fetch/watch is not implemented yet.
- Markdown/YAML is the canonical persistence layer; vector and relational backends are not active stores yet.
- Rollback preview exists; rollback apply is not implemented.
- Agent sign-in provides partial context hydration; per-agent filesystem projection and hard write-scope enforcement are future work.
