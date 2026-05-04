# Operation Policy

Hive Synapse keeps automation defaults in `policies/operations.yaml`. The file is organization/workspace-owned, so each deployed client can tune maintenance behavior without changing runtime code.

Policy precedence is:

1. runtime defaults
2. workspace policy at `policies/operations.yaml`
3. target overrides at `policies/nodes/<target>.yaml`
4. explicit command flags

## Default Modes

Fresh workspaces use low-noise defaults:

- `context_invalidation`: `observe`, with `emit_dirty_markers: false`
- `compaction`: `threshold`, with over-budget packs creating `node_compact` jobs
- `promotion`: `manual`, with proposal creation only when policy or `--create-proposals` requests it
- `watchdog`: `report_only`, with remediation jobs only when policy or `--enqueue` requests them
- `import_sync`: `manual`
- `archive`: `manual`

This means automatic lifecycle and promotion changes are recorded as observations by default, but they do not create new dirty markers until policy is tightened. Manual `hive context invalidate` still writes a dirty marker; add `--respect-policy` to test the effective policy instead.

## Target Overrides

Organizations, departments, projects, and agents are graph nodes. They share the same policy structure. A target-specific file can override only the settings it needs:

```yaml
id: policy_departments_engineering
target: departments/engineering
operation_policies:
  context_invalidation:
    mode: strict
  watchdog:
    enqueue_remediation: true
```

Agents are not a separate policy mechanism. They are graph nodes with assignment records under `org/assignments/` and personal memory under `memory/records/agents/`.

## Inspecting Policy

```bash
./bin/hive policy show --workspace /tmp/hive-demo
./bin/hive policy show --workspace /tmp/hive-demo --target departments/engineering --json
```

Current Notion and Google Drive connector entries persist import references, not background watches. `import_sync` stores the intended sync posture; periodic pulls still require an explicit command, job runner, or future daemon.
