# Upgrade Guide

Hive Synapse separates runtime upgrades from organization workspace context. Pulling a newer runtime repository should not overwrite workspace memory.

Recommended flow:

```bash
hive upgrade doctor --workspace <workspace>
hive upgrade migration-list --workspace <workspace>
hive upgrade migration-dry-run 001_runtime_markers --workspace <workspace>
hive backup create <workspace>
hive upgrade migration-apply 001_runtime_markers --workspace <workspace>
hive upgrade template-diff --workspace <workspace>
hive upgrade template-apply-new --workspace <workspace>
```

Template apply only creates missing files. It does not overwrite local context.
