# Troubleshooting

- Validation fails with `workspace.sync_conflict`: resolve cloud/Obsidian conflicted-copy files before shared writes.
- Context status is stale: run `hive context compile <target> --workspace <workspace>` or enqueue a context rebuild job.
- Promotion apply fails: ensure proposal is approved and actor is a steward, admin, or system actor.
- Import proposal has unknown sensitivity: run `hive import classify` with explicit sensitivity before promotion.
- Migration apply fails: run backup and dry-run first; inspect `memory/backups/` and `memory/operations/`.
