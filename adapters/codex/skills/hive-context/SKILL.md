---
name: hive-context
description: Use when a Codex agent needs general Hive Synapse workspace context, validation, imports, jobs, stale-context checks, or guidance choosing a more specific Hive skill.
---

# Hive Context

This is the general Hive Synapse skill. Prefer narrower skills when the user intent is clear:

- `hive-context-sync` for agent sign-in, scoped hydration, context packs, and refresh.
- `hive-ingest-summarize` for adding notes, documents, URLs, Notion/GDrive links, and import summaries.
- `hive-compaction-rollups` for node/edge compaction and generated briefs.
- `hive-scheduler-jobs` for cron/launchd templates, job queues, watchdogs, and audits.
- `hive-governance-promotion` for promotion, review, policy, and rollback.

## Canonical Commands

- `hive validate <workspace>` before and after mutating workflows.
- `hive actor signin <actor> --workspace <workspace> --json` to hydrate an agent.
- `hive context status <target> --workspace <workspace>` before shared writes.
- `hive context compile <target> --workspace <workspace>` to refresh a context pack.
- `hive mcp call get_context_pack --workspace <workspace> --args-json '{"target":"departments/engineering"}'` for adapter-safe context retrieval.

Do not duplicate memory semantics in prompts. Call the Hive CLI or MCP surface.
