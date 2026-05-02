# Concurrency and Sync Strategy

Updated: 2026-05-02

## Objective

The Markdown/Obsidian-first MVP must tolerate multiple humans and agents working in the same synced workspace without corrupting shared memory.

The main risks are:

- multiple agents editing the same parent summary
- Obsidian or sync-provider conflict files
- stale context packs used for shared writes
- job runners double-processing the same work
- parent memory accepting noisy child updates too eagerly

## Core Principle

```text
Children propose.
Parents pull.
Shared published memory has controlled writers.
```

Agents and child nodes should not directly edit parent published memory. They create candidates, proposals, jobs, and child summaries. Parent compaction and rollup jobs pull from immediate children, edges, and proposals to update parent context through a controlled operation.

This reduces race conditions because many writers can append candidates, while only a bounded rollup operation writes the parent current memory.

## Write Model

### Append-Friendly Paths

Many agents can write unique files under:

```text
memory/records/**/candidates/
memory/proposals/
memory/jobs/pending/
memory/imports/**/inbox/
memory/operations/
memory/audit/
```

Writers must use stable unique IDs and atomic write-then-rename.

### Controlled-Writer Paths

Only authorized commands should write:

```text
memory/records/**/published/
memory/records/**/CURRENT.md
memory/records/**/HISTORY.md
memory/graph/
memory/generated/
org/assignments/
policies/
```

Controlled writes require:

- fresh context check
- role/policy validation
- content hash precondition
- operation record
- invalidation event
- rollback metadata

## Parent Pull-Up Rollups

Parent context should be built by pulling from immediate children rather than letting every descendant write upward.

```text
agent/session memory
  -> agent candidate
  -> department child summary
  -> department rollup job
  -> department candidate/published current memory
  -> parent/org rollup job
```

Rules:

- Children may propose upward.
- Parents decide what to accept.
- Rollups summarize deltas since last watermark.
- Parent rollups read immediate children and relevant edges, not every raw descendant transcript.
- Company/org memory should be updated by org rollup jobs or curators, not child agents.

## Leases and Atomic Writes

Filesystem MVP uses lease files:

```text
memory/state/leases/<target>.lease.yaml
```

Lease fields:

```yaml
id: lease_departments_engineering_20260502_001
target: departments/engineering
holder: agent:codex-001
operation: op_20260502_001
created_at: 2026-05-02T10:00:00-05:00
expires_at: 2026-05-02T10:10:00-05:00
precondition_hashes:
  - path: memory/records/nodes/departments/engineering/CURRENT.md
    sha256: abc123
```

Writes should use:

1. Read current file and hash.
2. Acquire lease for target.
3. Re-read and verify hash.
4. Write temporary file.
5. Atomic rename.
6. Write operation record.
7. Release lease.

If the hash changed, abort and create a conflict/retry job.

## Sync Conflict Detection

Obsidian/sync providers may create conflict files or duplicate files.

Watchdogs should detect:

- filenames containing conflict markers
- duplicate IDs
- files with same logical ID and different hashes
- operation records with overlapping target and time window
- generated files with stale source watermark

Default response:

```text
detect conflict
  -> block affected shared writes
  -> create conflict record
  -> mark affected context dirty
  -> require human or steward resolution if automatic merge is unsafe
```

## Optimistic Concurrency

Every mutating command should include expected versions or hashes for files it changes.

Example:

```yaml
target: departments/engineering
expected:
  context_pack_version: 17
  current_memory_hash: abc123
  graph_version: 5
```

If expectations fail, the command should not write. It should refresh, rebase, or create a retry job.

## Job Runner Concurrency

Jobs move through:

```text
pending -> claimed -> completed
pending -> claimed -> failed
claimed -> pending when lease expires
```

Claiming a job must be atomic. A runner that cannot atomically claim a job must not execute it.

## MVP Requirements

- Unique append-only candidate/proposal/job files.
- Atomic write helper.
- Lease files for controlled-writer targets.
- Content hash preconditions for shared writes.
- Conflict detection watchdog.
- Parent pull-up rollup behavior.
- Dirty markers for affected context.

## Later Enhancements

- SQLite/Postgres locks.
- CRDT-style merge for selected append-only logs.
- Branch/PR workflow for high-risk shared memory changes.
- Remote coordination service for distributed agents.
