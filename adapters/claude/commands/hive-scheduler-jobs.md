---
description: Create scheduler templates and operate Hive Synapse jobs/watchdogs
allowed-tools: Bash(hive scheduler:*), Bash(hive job:*), Bash(hive operation:*), Bash(hive validate:*)
---

Interpret `$ARGUMENTS` as a scheduling, cron, launchd, job queue, watchdog, or audit request.

Common mappings:
- cron template: `hive scheduler install cron --workspace "$HIVE_WORKSPACE" --interval-minutes <n> --json`
- launchd template: `hive scheduler install launchd --workspace "$HIVE_WORKSPACE" --interval-minutes <n> --json`
- run watchdog: `hive job watchdog --workspace "$HIVE_WORKSPACE" --enqueue --json`
- run next job: `hive job run --workspace "$HIVE_WORKSPACE" --runner runner:scheduler --json`
- list jobs: `hive job list --workspace "$HIVE_WORKSPACE" --json`
- audit operations: `hive operation list --workspace "$HIVE_WORKSPACE" --json`

Review generated scheduler templates under `local-overrides/schedulers/` before OS installation.
