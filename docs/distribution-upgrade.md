# Distribution and Upgrade Boundary

Updated: 2026-05-02

## Objective

Hive Memory must be upgradeable without clobbering the organization, department, project, agent, or import context it operates on.

Users should be able to pull or install new product capabilities from GitHub or a package registry while keeping their local organizational memory, policies, artifacts, and generated context safe.

## Core Principle

```text
Product runtime is replaceable.
Organization memory is owned by the environment.
Generated artifacts are rebuildable.
```

The operating model should be distributed as versioned code, schemas, templates, docs, skills, MCP tools, validators, and migrations. The organization workspace should contain local context, records, imports, jobs, proposals, policies, and generated artifacts.

## Separation Model

### Product Runtime

Owned by the Hive Memory release.

```text
hive-memory/
  cli/
  mcp/
  schemas/
  validators/
  compilers/
  schedulers/
  migrations/
  adapters/
  skills/
  templates/
  docs/
```

The runtime can be updated by:

- `git pull`
- package manager upgrade
- pinned GitHub release
- container image update
- plugin/skill marketplace update

### Organization Workspace

Owned by the user or organization.

```text
org-workspace/
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

The product runtime must not overwrite this workspace during upgrade.

## Config Boundary

Use a small workspace config to bind runtime version to local data:

```yaml
hive_workspace:
  schema_version: 0.1.0
  runtime_version: 0.4.0
  runtime_ref: github.com/org/hive-memory@v0.4.0
  workspace_id: acme-prod-memory
  data_root: memory/
  policy_root: policies/
  local_overrides_root: local-overrides/
  generated_root: memory/generated/
  upgrade_policy:
    require_dry_run: true
    backup_before_migration: true
    never_overwrite_local_context: true
```

The runtime reads local config. Local config does not live inside the runtime package.

## Upgrade Contract

Upgrades may:

- add new commands
- add new schemas
- add new validators
- add new context compiler behavior
- add new templates
- add new skills
- add migrations
- rebuild generated artifacts

Upgrades must not:

- overwrite `memory/raw/`
- overwrite `memory/records/`
- overwrite `memory/graph/`
- overwrite `memory/imports/`
- overwrite `memory/operations/`
- overwrite `memory/audit/`
- silently modify local policies
- silently publish memory
- silently delete generated or canonical context

Any migration that mutates organization-owned data must be explicit, dry-runnable, backed up, audited, and rollback-capable.

## Recommended Install Modes

### Mode 1: External Runtime

Best default.

```text
~/.hive/runtime/<version>/
org-workspace/
```

The workspace references the installed runtime version. Upgrading runtime code does not modify org data until `hive migrate` or `hive doctor --fix` is explicitly run.

### Mode 2: Git Submodule or Subtree

Useful for transparent source review.

```text
org-workspace/
  vendor/hive-memory/
  hive.config.yaml
  memory/
```

The vendor directory is product-owned. The memory directory is organization-owned.

### Mode 3: Monorepo Package

Useful for companies integrating Hive into an internal platform.

```text
repo/
  packages/hive-memory/
  workspaces/acme-memory/
```

Package build outputs should not write into workspaces unless commands are explicitly invoked.

## Upgrade Workflow

```text
hive upgrade check
hive upgrade plan --from <version> --to <version>
hive upgrade dry-run
hive backup create
hive migrate apply
hive validate
hive context rebuild --affected
hive upgrade record
```

Every upgrade should produce:

- upgrade plan
- compatibility report
- migration operation records
- affected generated artifacts
- rollback instructions
- validation report

## Schema Migrations

Schema migrations should be versioned and idempotent.

```text
migrations/
  0001_init_workspace/
  0002_add_import_workspaces/
  0003_add_actor_assignments/
```

Migration rules:

- dry-run first
- backup before write
- write operation records
- never mutate raw evidence
- prefer additive migrations
- preserve old fields until explicitly deprecated
- emit invalidation events when context semantics change

## Templates vs Local Files

Runtime templates are defaults. Local files are owned by the workspace.

```text
runtime/templates/node/CURRENT.md
  -> copied once during creation
workspace/memory/records/nodes/departments/engineering/CURRENT.md
  -> local owned file
```

After creation, upgrades can suggest template diffs but cannot overwrite local files.

## Agent Boot Contract

Agents should receive:

- runtime protocol version
- workspace schema version
- context pack version
- policy version
- command/tool versions

Agents should not infer rules from stale copied docs when the runtime exposes newer policy through MCP/CLI. The context compiler should include the active runtime/workspace versions in the boot manifest.

Runtime or schema upgrades should also emit context invalidation events for every context pack whose manifest references changed runtime, schema, validator, command, template, policy, or skill versions. Dormant agents pick this up on next sign-in through the dirty context registry.

## Local Overrides

Organizations can tune defaults without forking the runtime:

```text
policies/
  promotion.yaml
  summarization.yaml
  context-budget.yaml
  retention.yaml
local-overrides/
  skills/
  prompts/
  templates/
```

Override precedence:

```text
runtime defaults < organization policy < node policy < explicit command flags
```

Policy changes are organization-owned data changes and should create operation records when they affect shared behavior.

## Required Commands

```text
hive init
hive doctor
hive upgrade check
hive upgrade plan
hive upgrade dry-run
hive upgrade apply
hive migrate list
hive migrate dry-run
hive migrate apply
hive backup create
hive backup restore
hive validate
hive context rebuild --affected
```

## Non-Clobbering Guarantee

The product should guarantee:

- no upgrade writes organization-owned files without explicit command execution
- no migration applies without dry-run output when policy requires dry-run
- every mutating migration writes an operation record
- every migration can be rolled back or has explicit irreversible warnings
- generated artifacts can be deleted and rebuilt
- canonical memory and raw sources are never overwritten by templates
