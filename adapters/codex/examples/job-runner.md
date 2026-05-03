# Codex Job Runner Example

```bash
codex exec --json "Run hive job run --workspace $HIVE_WORKSPACE and summarize the operation record."
```

The job runner should invoke canonical `hive job run`, not reimplement compaction or promotion behavior.
