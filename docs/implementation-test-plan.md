# Implementation Test Plan

Updated: 2026-05-02

## Purpose

This document is the test companion to [Implementation Backlog](implementation-backlog.md). It lets a dedicated test agent work in parallel once interfaces are agreed.

The test agent should validate behavior through public interfaces first, then add unit tests for stable internal modules.

## Test Strategy

Use a layered test suite:

| Layer | Purpose | Examples |
|---|---|---|
| Unit tests | Validate pure functions and models | schema parsing, path resolution, graph traversal |
| Contract tests | Validate stable module interfaces | repository, validator, compiler, connector adapters |
| CLI tests | Validate user/agent-facing behavior | `hive init`, `hive validate`, `hive context compile` |
| Fixture tests | Validate realistic workspaces | `fixtures/workspaces/basic-org/` |
| E2E tests | Validate full workflows | import → candidate → proposal → context invalidation |
| Regression tests | Lock critical guardrails | no parent direct writes, stale context blocks shared write |

Default test tooling for Python:

```text
pytest
pytest-cov
ruff
mypy or pyright
freezegun or deterministic clock helper
tmp_path fixture for workspace tests
```

## Test Agent Rules

The test agent should:

- Prefer black-box CLI tests for user-facing behavior.
- Use fixture workspaces copied into temporary directories.
- Never mutate committed fixtures directly during tests.
- Mock network connectors by default.
- Assert operation records for all mutating commands.
- Assert generated artifacts are rebuildable and not hand-edited.
- Add failing tests before implementation when interface is agreed.
- Avoid testing private implementation details until interfaces stabilize.

## Interface Agreement Gate

Before the test agent writes tests for a task, the implementation agent and test agent should agree on:

- command name and flags
- input file paths and formats
- output JSON shape
- error codes
- operation record fields
- fixture names
- deterministic clock/ID strategy

If this is not agreed, the test agent should write pending contract tests or a test TODO rather than guessing.

## Test Data Rules

Use these fixture categories:

```text
fixtures/workspaces/basic-org/
fixtures/workspaces/invalid/
fixtures/imports/
fixtures/connectors/
fixtures/templates/
```

Every fixture should include:

- expected validation result
- expected command output where applicable
- source refs for durable memory
- stable IDs
- no secrets

## Phase 0: Final Decisions and Scaffold

### T00: Confirm Implementation Defaults

Tests:

- Documentation test confirms `docs/implementation-decisions.md` exists and includes confirmed runtime defaults.
- Static check confirms `docs/implementation-backlog.md` references the confirmed defaults.

Success criteria:

- Test fails if defaults are contradictory across docs.

### T01: Scaffold Runtime Package

Tests:

- `hive --help` or `uv run hive --help` exits successfully.
- `pytest` runs from clean checkout.
- Package metadata includes CLI entry point.
- Runtime package excludes organization-owned workspace data.

Success criteria:

- A fresh clone can install dependencies and run help/tests.

### T02: Define Runtime/Workspace Paths

Tests:

- Unit tests for resolving runtime-owned roots and workspace-owned roots.
- CLI test for failing writes outside workspace root.
- Template-copy test proves runtime templates are copied only by explicit command.

Success criteria:

- Path traversal and accidental external writes are rejected.

## Phase 1: Schema and Fixtures

### T03: Convert Schema Drafts to Enforceable Models

Tests:

- Every schema draft has a corresponding runtime model.
- Valid fixture objects parse successfully.
- Invalid fixture objects fail with actionable error messages.
- JSON Schema export exists if supported.

Success criteria:

- Schema test coverage includes records, graph, jobs, imports, operations, invalidations, dirty markers, assignments, archives, skills, workspace config, and migrations.

### T04: Create Filesystem Workspace Fixtures

Tests:

- Fixture inventory test confirms required sample files exist.
- Fixture validation test passes for `basic-org`.
- Invalid fixture test suite fails for expected reasons.

Success criteria:

- Fixture can be copied to a temp directory and used by downstream CLI tests.

### T05: Implement Workspace Initialization

Tests:

- `hive init <tmp>` creates required directories and `hive.config.yaml`.
- `hive init --fixture basic-org <tmp>` creates sample org.
- Re-running init does not overwrite local files.
- `--force` requires backup or explicit confirmation behavior.

Success criteria:

- Init is idempotent and non-clobbering.

## Phase 2: Filesystem Repository and Validation

### T06: Implement Filesystem Repository

Tests:

- Load all fixture records.
- Write deterministic Markdown/YAML paths.
- Atomic write leaves no partial file on simulated failure.
- Stale content-hash precondition fails.
- Raw source overwrite/delete is rejected.

Success criteria:

- Repository operations are safe under temporary workspace tests.

### T07: Implement Validator Engine

Tests:

- `hive validate` passes for valid fixture.
- Broken node/edge/actor/record refs fail.
- Missing source refs fail for durable shared memory.
- Generated file hand-edit marker fails.
- Imported records bypassing candidate stage fail.

Success criteria:

- Validation emits machine-readable error codes and human-readable messages.

### T08: Implement Guardrail Policy Checks

Tests:

- Each non-negotiable invariant from `docs/guardrails.md` has at least one test.
- Direct child write to parent published memory fails.
- Shared write with stale context fails.
- Archive without final compaction or deferral fails.
- Controlled write without lease/hash precondition fails.

Success criteria:

- Guardrail tests block unsafe workflows before implementation can mark tasks complete.

## Phase 3: CLI Command Surface

### T09: Implement CLI Framework

Tests:

- `hive --help` lists all top-level command groups.
- `--json` emits valid JSON for supported commands.
- Invalid flags fail with non-zero exit and useful error.
- Dry-run/proposal-only/apply flags parse consistently.

Success criteria:

- CLI is stable enough for test agent and future MCP wrapper to call.

### T10: Implement Operation Log

Tests:

- Every mutating command under test writes an operation record.
- Failed mutating command writes failed operation where required.
- Operation record includes actor, command, mode, target, status, changed files, rollback metadata.
- Operation records are append-only.

Success criteria:

- Mutating command without operation record fails test.

### T11: Implement Backup and Rollback Preview

Tests:

- `hive backup create` writes manifest with file hashes.
- Backup excludes runtime-owned files unless configured.
- `hive rollback preview <operation-id>` reports affected files, records, generated artifacts.
- Preview does not mutate workspace.

Success criteria:

- Rollback apply cannot be implemented without preview coverage.

## Phase 4: Import Workspace

### T12: Implement Import Add and Fetch

Tests:

- Local Markdown import creates raw source and import item.
- Folder import creates one import item per expected source or a collection item by design.
- URL import records external ref and fetched/stubbed metadata.
- Obsidian folder import preserves relative paths.
- Git/GitHub import uses connector abstraction and no hard-coded credentials.

Success criteria:

- Imported material remains evidence/candidate only.

### T13: Implement Import Classification

Tests:

- Deterministic fixture imports classify target, topics, sensitivity, current/historical/mixed.
- Unknown sensitivity blocks shared proposal.
- Manual override updates classification with operation record.

Success criteria:

- Classification is deterministic and auditable.

### T14: Implement Import Compaction Stub

Tests:

- Compaction stub creates source-linked import summary.
- Candidate records include source refs.
- No direct published memory is written.
- Conflicting claim creates conflict record or conflict candidate.
- Empty/noisy import creates `no_changes` result.

Success criteria:

- Import pipeline works without real LLM calls.

### T15: Implement Import Proposals

Tests:

- Import-created candidate can become promotion proposal.
- Proposal routes to node, edge, parent, or org according to classification.
- Proposal apply is blocked without authority.
- Markdown and JSON proposal reports are generated.

Success criteria:

- Import proposal flow is reviewable and non-publishing by default.

## Phase 5: Context Compiler and Refresh

### T16: Implement Graph Traversal

Tests:

- Parent chain traversal.
- Descendant traversal.
- Connected edge traversal.
- Assigned actor lookup.
- Archived/inactive nodes excluded by default.
- Traversal explanation path is deterministic.

Success criteria:

- Impact analysis and context compiler can share traversal results.

### T17: Implement Context Pack Compiler

Tests:

- Compile department context pack.
- Project pack includes relevant edge memory.
- Private partner memory excluded.
- Historical memory excluded by default.
- Manifest includes runtime/schema/policy/command/skill versions.
- Generated pack is reproducible from source records.

Success criteria:

- Context pack is bounded, source-linked, and manifest-backed.

### T18: Implement Context Budgeting

Tests:

- Token estimator returns deterministic values for fixture pack.
- Over-budget pack fails or creates pruning/compaction job per policy.
- Layer budget report emitted.
- Stable-prefix ordering is deterministic.

Success criteria:

- Budget behavior is predictable and guardrailed.

### T19: Implement Context Invalidation and Dirty Markers

Tests:

- Parent update dirties descendants.
- Edge update dirties connected node packs.
- Runtime/schema/policy version change dirties referencing packs.
- Dormant agent sees dirty marker on next context status check.
- Stale sign-in cannot perform shared write.

Success criteria:

- Dirty context cannot be silently ignored.

## Phase 6: Promotion, Review, and Shared Memory

### T20: Implement Promotion Proposal Flow

Tests:

- Candidate can be proposed to department.
- Steward role can apply proposal.
- Unauthorized actor cannot apply proposal.
- Apply updates current memory and invalidates impacted packs.
- Rejection remains auditable.

Success criteria:

- Shared memory changes are gated and auditable.

### T21: Implement Conflict and Drift Records

Tests:

- Conflicting import creates conflict record.
- Conflict resolution supports expected outcomes.
- Resolution preserves old memory as history/superseded.
- Drift record can create promotion proposal or policy review.

Success criteria:

- Contradictions are visible and reviewable.

### T22: Implement Promotability Sweep

Tests:

- Sweep produces promotable, not_promotable, needs_more_evidence, conflicts_detected.
- Sweep can create proposals.
- Sweep never publishes directly.
- No qualifying items creates `no_changes`.

Success criteria:

- Sweep is conservative and proposal-only.

## Phase 7: Job Runner and Automation

### T23: Implement Filesystem Job Queue

Tests:

- Atomic job claim allows one runner.
- Expired lease requeues.
- Completed job writes result.
- Failed job writes reason.
- Overlapping controlled-writer leases are detected.

Success criteria:

- Job runner is safe under concurrent test processes where practical.

### T24: Implement Built-In Job Handlers

Tests:

- Import compact job runs.
- Node compact job runs.
- Edge compact job runs.
- Context rebuild job runs.
- Promotion sweep job runs.
- Failed handler remains retryable.

Success criteria:

- Built-in job handlers are deterministic under fixture tests.

### T25: Implement Watchdogs

Tests:

- Detect dirty node without job.
- Detect stale context pack.
- Detect unprocessed import.
- Detect invalidated sign-in.
- Detect sync conflict file.
- Detect duplicate logical ID.
- Report can enqueue remediation job.

Success criteria:

- Watchdogs surface unsafe states without silently mutating memory.

## Phase 8: Lifecycle, Skills, and Archives

### T26: Implement Node Lifecycle Commands

Tests:

- Node create creates graph record, folders, current/history files, import workspace, policy defaults.
- Node move updates parent chain and invalidates impacted packs.
- Node archive requires final compaction or deferral.
- Node restore preserves history.

Success criteria:

- Graph lifecycle commands are safe and explainable.

### T27: Implement Actor Assignment Commands

Tests:

- Actor assignment grants expected inherited context.
- Actor move invalidates old and new node context.
- Actor archive removes active ownership but preserves history.
- Sign-in references assignment.

Success criteria:

- Durable assignment and run-level sign-in remain distinct.

### T28: Implement Shared Skill Registry

Tests:

- Department skill visible to eligible department agents.
- Org skill visible where allowed.
- Deprecated/archived skill excluded by default.
- Script/tool skill requires safety review metadata.
- Context pack manifest includes relevant skill registry version.

Success criteria:

- Skills are governed shared assets.

### T29: Implement Archive Sweep

Tests:

- Sweep identifies inactive agent/node/edge/skill.
- Archive preview lists affected files, records, packs.
- Archive apply excludes target from startup context.
- Historical retrieval references remain.

Success criteria:

- Archive removes noise without deleting history.

## Phase 9: Distribution, Upgrade, and Migration

### T30: Implement Workspace Doctor

Tests:

- Clean fixture passes.
- Schema mismatch detected.
- Missing generated pack detected.
- Runtime/workspace version mismatch detected.

Success criteria:

- Doctor gives actionable remediation.

### T31: Implement Migration Framework

Tests:

- Migration list shows available migrations.
- Dry-run reports changes without writing.
- Apply requires backup when policy says so.
- Apply writes migration record and operation record.
- Failed migration leaves workspace recoverable.

Success criteria:

- Migrations are non-clobbering and auditable.

### T32: Implement Template Diffing

Tests:

- Runtime template update does not overwrite local file.
- Diff report generated.
- Explicit approved apply writes operation record.
- Generated artifacts can be rebuilt after template change.

Success criteria:

- Runtime upgrades never silently clobber workspace context.

## Phase 10: MCP and Harness Adapters

### T33: Implement MCP Server

Tests:

- MCP server exposes expected tools/resources.
- `get_context_pack` returns fixture pack.
- Import item can be created through MCP.
- Publish/apply fails without authority.

Success criteria:

- MCP wraps canonical runtime semantics without duplicating policy logic.

### T34: Implement Codex Adapter

Tests:

- Skill wrapper calls canonical CLI/MCP command.
- Hook example blocks stale shared write.
- `codex exec` job example emits structured result.

Success criteria:

- Codex adapter is thin and does not own memory semantics.

### T35: Implement Claude Adapter

Tests:

- Slash command wrapper calls canonical CLI/MCP command.
- Skill wrapper calls canonical CLI/MCP command.
- Hook example blocks stale shared write.
- Headless job example emits structured result.

Success criteria:

- Claude adapter is thin and does not own memory semantics.

## Phase 11: Packaging, Docs, and Release

### T36: Add End-to-End Test Suite

Tests:

- Init → validate → import → compact → propose → review → context compile.
- Context invalidate → dirty marker → refresh.
- Archive preview/apply.
- Rollback preview.
- Migration dry-run.
- Failure path for each critical guardrail.

Success criteria:

- E2E suite runs in temporary workspaces and does not mutate committed fixtures.

### T37: Add User Documentation

Tests:

- Documentation smoke test follows quickstart in temp workspace.
- Command reference includes all public command groups.
- Upgrade guide states runtime/workspace separation.

Success criteria:

- New user can complete first workflow from docs.

### T38: Add Release Packaging

Tests:

- Clean install exposes `hive --help`.
- Package excludes organization workspace memory.
- Release archive includes schemas, templates, migrations, skills.
- Release notes include migration guidance.

Success criteria:

- Package is installable and does not include local org data.

## Cross-Cutting Test Gates

Before any phase is considered done:

- `pytest` passes.
- `hive validate fixtures/workspaces/basic-org` passes.
- `git diff --check` passes.
- Mutating CLI commands emit operation records.
- Workspace-owned data is not overwritten by runtime-owned templates.
- Generated artifacts are reproducible or explicitly marked non-deterministic.

## Test Agent Execution Plan

### Wave 1

Write tests for T00-T05 once CLI scaffold and schema interface are agreed.

### Wave 2

Write tests for T06-T11 once repository, validator, and operation log interfaces are agreed.

### Wave 3

Write tests for T12-T19 once import and context compiler command outputs are agreed.

### Wave 4

Write tests for T20-T25 once promotion, conflict, job, and watchdog outputs are agreed.

### Wave 5

Write tests for T26-T32 once lifecycle and migration command contracts are agreed.

### Wave 6

Write tests for T33-T38 once CLI behavior is stable enough for adapter and packaging tests.
