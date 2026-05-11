---
name: hive-scheduler-jobs
description: Use when a user asks to schedule Hive Synapse jobs, create cron or launchd templates, run periodic summarization, run watchdogs, enqueue jobs, or inspect scheduled/audit operations.
---

# Hive Scheduler + Jobs

Hive does not run a daemon by default. It writes scheduler templates and uses the filesystem job queue.

## Intent Mapping

- "run this every 15 minutes" → `hive scheduler install cron|launchd --interval-minutes 15`
- "nightly compaction" → enqueue node/edge compaction jobs from cron/launchd or an external scheduler
- "process queued work" → `hive job run`
- "watch for stale context/conflicts" → `hive job watchdog --enqueue`
- "show what happened" → `hive operation list|show`

## Scheduler Commands

```bash
hive scheduler install cron --workspace <workspace> --interval-minutes <n> --json
hive scheduler install launchd --workspace <workspace> --interval-minutes <n> --json
```

Review generated files under `local-overrides/schedulers/` before installing with the OS.

## Job Commands

```bash
hive job enqueue node_compact <node-id> --workspace <workspace> --reason "scheduled compaction" --json
hive job enqueue edge_compact <edge-id> --workspace <workspace> --reason "scheduled compaction" --json
hive job list --workspace <workspace> --json
hive job run --workspace <workspace> --runner runner:scheduler --json
hive job watchdog --workspace <workspace> --enqueue --json
```

## Audit Commands

```bash
hive operation list --workspace <workspace> --json
hive operation show <operation-id> --workspace <workspace> --json
```

## External Schedulers

For GitHub Actions, Buildkite, cron, launchd, systemd, or other automation, run the same CLI commands. Keep credentials in environment variables; do not write secrets into Hive memory.
