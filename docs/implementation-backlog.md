# Implementation Backlog

Updated: 2026-05-02

## Purpose

This is the executable build plan for the first implementation of Hive Memory.

The goal is to let fresh agents start from this document and build the framework without needing chat history. Tasks are sequenced for a Markdown/filesystem-first MVP using Obsidian-compatible files. Additional persistence layers can be added after the core contracts are working.

Use [Implementation Test Plan](implementation-test-plan.md) as the parallel validation plan for these tasks.

## MVP Assumptions

These defaults should be treated as implementation assumptions unless a human overrides them before coding.

| Area | Default |
|---|---|
| Canonical storage | Markdown files with YAML frontmatter |
| Sync target | Obsidian-compatible folder synced externally |
| Runtime/workspace split | Runtime package separate from organization workspace |
| First database | None required for MVP; JSON indexes generated from files |
| First vector store | Defer until filesystem MVP is complete |
| First UI | CLI and generated Markdown reports |
| First harness adapters | CLI-first, then MCP, then Codex/Claude wrappers |
| Promotion authority | Local role files and validators |
| Scheduling | Manual CLI plus filesystem job runner; cron/launchd later |
| LLM execution | Adapter interface with dry-run/stub support first |
| Runtime language | Python 3.11+ |
| Package manager | `uv` preferred, `pipx` install supported |
| Repository | Dedicated repo; use relative paths until location is provided |

## Glaring Gaps and Defaults

These are the main gaps to resolve or explicitly defer.

| Gap | Risk | MVP Default |
|---|---|---|
| Formal schema format not finalized | YAML shape drafts are not directly enforceable | Convert drafts to Pydantic models and export JSON Schema |
| Filesystem locking under sync conflicts | Obsidian/iCloud/Dropbox can create duplicate writes | Use operation IDs, atomic writes, content hashes, lease files, parent pull-up, and conflict reports |
| LLM provider abstraction | Codex/Claude execution differs | Define provider interface and start with command templates/stubs |
| Permission enforcement depth | File permissions alone are weak | Enforce through CLI validators first; OS-level/path allowlists later |
| Human review UX | Review queues can be awkward in raw files | Generate Markdown review reports and CLI apply/reject commands |
| Remote import connectors | Notion/GDrive/GitHub APIs add auth complexity | Build connector interfaces early; local/URL/Git first, Notion/GDrive with stubbed or env-based auth |
| Secrets management | Remote sync needs credentials | Defer to environment variables or external secret store; do not write secrets to memory |
| Token estimation accuracy | Markdown token counts are approximate | Use approximate tokenizer initially; pluggable model profiles later |
| Multi-agent concurrency | Parallel agents can race | Children write candidates/jobs only; parent rollups pull child summaries; filesystem leases and optimistic hashes guard shared files |

None of these block starting. They should become explicit issues or tasks before the relevant phase begins.

## Build Strategy

Build in vertical slices, not isolated abstractions.

First working slice:

```text
hive init
  -> creates workspace
  -> writes sample graph and records
  -> validates records
  -> compiles one context pack
  -> writes operation/audit records
```

Second working slice:

```text
hive import add
  -> stages a local file
  -> preserves raw source
  -> creates candidate memory
  -> validates candidate
  -> proposes promotion
```

Third working slice:

```text
hive context invalidate
  -> computes impacted descendants/edges/agents
  -> writes dirty markers
  -> rebuilds affected context pack
  -> forces next-run refresh
```

## Agent Work Packages

For two implementation agents, split work this way after scaffold tasks are complete.

### Agent A: Runtime Core

Owns:

- package scaffold
- schema conversion
- filesystem repository
- CLI shell
- validator engine
- operation log
- backup and migration foundations

Avoid editing:

- prompt templates owned by Agent B
- context compiler behavior owned by Agent B
- MCP adapter until shared interfaces stabilize

### Agent B: Memory Workflows

Owns:

- workspace fixtures
- graph traversal
- import workspace workflows
- context compiler
- dirty marker/invalidation behavior
- promotion/review markdown reports
- job runner prompts and templates

Avoid editing:

- schema model definitions unless coordinated
- low-level filesystem repository internals
- package/build config

## Task Status Vocabulary

Use these status labels when implementing:

```text
todo
in_progress
blocked
review
done
deferred
```

Every task should update this document or an implementation tracker with status, changed files, and validation commands.

## Phase 0: Final Decisions and Scaffold

### T00: Confirm Implementation Defaults

Requirements:

- Confirm final dedicated repository or workspace location.
- Confirm CLI binary name.
- Confirm whether external dependencies are allowed in MVP.
- Confirm connector auth depth for Notion/GDrive/GitHub.

Default if unanswered:

```text
Python 3.11+ with uv
CLI binary: hive
Build in a dedicated repo; use relative paths until location is provided
Allow small, well-maintained dependencies
Real connector interfaces with stubbed or env-based auth for early MVP
```

Success criteria:

- Decisions are recorded in `docs/implementation-decisions.md`.
- `README.md` points to the current build plan.

Dependencies: none.

### T01: Scaffold Runtime Package

Requirements:

- Create product runtime package separate from workspace data.
- Add package scripts for build, test, lint, format, and CLI execution.
- Add `src/` for runtime code.
- Add `fixtures/` for test workspaces.
- Add `templates/` for runtime-owned templates.

Success criteria:

- `hive --help` runs locally.
- Test runner executes an empty test.
- Generated artifacts and fixture workspaces are not confused with runtime templates.
- `uv run hive --help` or equivalent works from a clean checkout.

Dependencies: T00.

### T02: Define Runtime/Workspace Paths

Requirements:

- Implement path resolution from `hive.config.yaml`.
- Enforce organization-owned roots vs runtime-owned roots.
- Prevent commands from writing outside workspace roots unless explicitly allowed.
- Define append-friendly vs controlled-writer paths.

Success criteria:

- Unit tests prove canonical roots resolve correctly.
- Attempted writes outside the workspace fail.
- Runtime templates are copied only by explicit commands.
- Controlled-writer paths are identified for lease enforcement.

Dependencies: T01.

## Phase 1: Schema and Fixtures

### T03: Convert Schema Drafts to Enforceable Models

Requirements:

- Convert YAML schema drafts into enforceable runtime models.
- Include memory records, nodes, edges, jobs, sign-ins, assignments, operations, imports, invalidations, dirty markers, skills, archive records, workspace config, and migrations.
- Preserve exportable JSON Schema or equivalent.

Success criteria:

- All schema drafts have runtime validators.
- Runtime models are Pydantic or equivalent Python typed models.
- Fixtures can be parsed into typed objects.
- Invalid fixtures fail with actionable errors.

Dependencies: T01.

### T04: Create Filesystem Workspace Fixtures

Requirements:

- Create one complete sample workspace under `fixtures/workspaces/basic-org/`.
- Include org, engineering, marketing, project, edge, agent, import workspace, import item, sign-in, actor assignment, candidate memory, promotion proposal, job, operation record, invalidation, dirty marker, archive record, and context pack manifest.

Success criteria:

- Fixture validates without errors.
- Fixture includes both current and history memory files.
- Fixture can be copied into a new workspace by `hive init --fixture basic-org`.

Dependencies: T03 can run in parallel, but final validation depends on T03.

### T05: Implement Workspace Initialization

Requirements:

- `hive init <path>` creates folder structure.
- Supports empty workspace and fixture workspace.
- Writes `hive.config.yaml`.
- Never overwrites existing context without `--force` and backup.

Success criteria:

- Empty init creates required directories.
- Fixture init creates sample org.
- Re-running init is idempotent and non-destructive.

Dependencies: T02, T04.

## Phase 2: Filesystem Repository and Validation

### T06: Implement Filesystem Repository

Requirements:

- Read/write canonical Markdown/YAML records.
- Read/write JSON/YAML operational records.
- Use atomic writes.
- Support content-hash preconditions.
- Preserve raw files append-only.
- Create stable IDs.

Success criteria:

- Repository can load all fixture records.
- Writes create deterministic paths.
- Atomic write tests pass.
- Stale hash write attempts fail safely.
- Raw store refuses overwrite/delete through normal APIs.

Dependencies: T03, T05.

### T07: Implement Validator Engine

Requirements:

- Validate schema fields.
- Resolve node/edge/actor/record references.
- Validate source refs.
- Validate authority transitions.
- Validate generated files were not hand-edited.
- Validate imported records do not bypass candidate/promotion workflow.

Success criteria:

- `hive validate` passes on valid fixture.
- Broken references fail.
- Missing source refs fail for durable shared memory.
- Direct published-memory writes fail unless created through authorized operation.

Dependencies: T06.

### T08: Implement Guardrail Policy Checks

Requirements:

- Encode non-negotiable invariants from `docs/guardrails.md`.
- Implement path allowlists by actor role.
- Enforce fresh context before shared writes.
- Enforce no archive without final compaction or deferral.
- Enforce child-to-parent updates through candidates/proposals/jobs rather than direct parent published-memory writes.
- Enforce leases and hash preconditions for controlled shared writes.

Success criteria:

- Policy tests cover each non-negotiable invariant.
- Violations return machine-readable error codes.
- CLI exits non-zero on guardrail violations.
- Direct child write to parent published memory fails.

Dependencies: T07.

## Phase 3: CLI Command Surface

### T09: Implement CLI Framework

Requirements:

- Add command groups: `workspace`, `validate`, `import`, `context`, `promote`, `job`, `node`, `actor`, `skill`, `archive`, `operation`, `upgrade`.
- Support `--json`.
- Support `--dry-run`, `--proposal-only`, and `--apply` where applicable.

Success criteria:

- All planned command groups appear in `hive --help`.
- Command output can be JSON for agent harness use.
- Unknown commands and invalid flags fail cleanly.

Dependencies: T06.

### T10: Implement Operation Log

Requirements:

- Every mutating command writes an operation record.
- Operation records include actor, command, mode, targets, changed files, changed records, status, and rollback metadata.
- Operation records are append-only.

Success criteria:

- Mutating CLI command without operation record fails tests.
- Operation records link to source command output.
- Failed operations remain visible.

Dependencies: T09.

### T11: Implement Backup and Rollback Preview

Requirements:

- `hive backup create` snapshots workspace-owned files.
- `hive rollback preview <operation-id>` shows affected records/files/generated artifacts.
- Rollback preview is available before rollback apply.

Success criteria:

- Backup creates manifest with file hashes.
- Rollback preview works for fixture operation.
- No rollback apply is implemented before preview tests pass.

Dependencies: T10.

## Phase 4: Import Workspace

### T12: Implement Import Add and Fetch

Requirements:

- `hive import add <target> <path-or-text>` creates import item.
- `hive import fetch <target> <url>` records external reference and fetched content when possible.
- Preserve raw artifact or stable external reference.
- Classify source type.

Success criteria:

- Local Markdown import creates raw source and import item.
- URL import creates external ref and import item.
- Import item starts in correct state.
- Raw artifact is not published memory.

Dependencies: T09, T10.

### T13: Implement Import Classification

Requirements:

- Classify likely targets, topics, sensitivity, current/historical/mixed status.
- Use deterministic heuristics first.
- Allow manual override.

Success criteria:

- Fixture imports classify deterministically.
- Unknown sensitivity blocks shared proposals.
- Classification is stored on import item.

Dependencies: T12.

### T14: Implement Import Compaction Stub

Requirements:

- Convert imported material into source-linked summaries and candidate records.
- Start with deterministic extraction/stub for fixtures.
- Define LLM adapter interface for future compaction.
- Never publish directly.

Success criteria:

- `hive import compact <import-id>` creates candidate memory.
- Candidate includes source refs.
- Conflicting imported claim creates conflict candidate when configured.
- `no_changes` result is written when nothing qualifies.

Dependencies: T13, T07.

### T15: Implement Import Proposals

Requirements:

- Create promotion proposals from import-created candidates.
- Route proposals to target node, parent, edge, or org based on classification.
- Preserve provenance and confidence.

Success criteria:

- `hive import propose <import-id>` creates proposals.
- Proposal cannot be applied without authority.
- Proposal report is human-readable Markdown plus JSON.

Dependencies: T14.

## Phase 5: Context Compiler and Refresh

### T16: Implement Graph Traversal

Requirements:

- Load graph nodes and edges.
- Compute parent chains.
- Compute descendants.
- Compute connected edges.
- Compute assigned actors for target.

Success criteria:

- Graph traversal tests cover org, department, project, edge, and agent nodes.
- Archived/inactive nodes are excluded by default.
- Traversal can explain paths.

Dependencies: T06.

### T17: Implement Context Pack Compiler

Requirements:

- Compile context pack from org, parent chain, node memory, relevant edges, task retrieval placeholder, dirty warnings, and skill registry.
- Include current memory by default, history only on request.
- Emit context pack manifest with runtime/schema/policy/tool/skill versions.

Success criteria:

- `hive context compile departments/engineering` writes pack and manifest.
- Pack excludes private partner memory.
- Pack excludes archived/inactive context by default.
- Manifest includes token estimates and version fields.

Dependencies: T16, T07.

### T18: Implement Context Budgeting

Requirements:

- Read context budget policy.
- Estimate tokens approximately.
- Enforce hard limits.
- Create pruning/compaction job when over threshold.

Success criteria:

- Over-budget fixture fails or creates job according to policy.
- Layer budget report is emitted.
- Stable-prefix ordering is deterministic.

Dependencies: T17.

### T19: Implement Context Invalidation and Dirty Markers

Requirements:

- `hive context impacted <target>` computes affected descendants, edges, graph neighbors, actors, sign-ins, packs, and skill manifests.
- `hive context invalidate <target>` writes invalidation events and dirty markers.
- Dirty markers persist for dormant agents.

Success criteria:

- Parent update dirties descendants.
- Edge update dirties connected node packs.
- Runtime/schema version change dirties packs referencing old versions.
- `hive context status` blocks stale sign-in from shared write.

Dependencies: T16, T17, T10.

## Phase 6: Promotion, Review, and Shared Memory

### T20: Implement Promotion Proposal Flow

Requirements:

- Create, list, review, approve, reject, and apply promotion proposals.
- Enforce authority transitions.
- Require source refs.
- Emit operation records and invalidations on apply.

Success criteria:

- Candidate can be proposed to department.
- Department proposal can be applied only by steward role.
- Applied proposal updates current memory and invalidates impacted packs.
- Rejected proposal remains auditable.

Dependencies: T07, T10, T19.

### T21: Implement Conflict and Drift Records

Requirements:

- Detect direct conflicts during validation/import/promotion.
- Create conflict records.
- Support resolution outcomes.
- Create drift records when observed practice diverges.

Success criteria:

- Conflicting fixture import creates conflict record.
- Conflict resolution updates affected memory without deleting history.
- Drift record can become promotion proposal or policy review.

Dependencies: T20.

### T22: Implement Promotability Sweep

Requirements:

- Scan candidates, agent memory, import candidates, skills, conflicts, and drift records.
- Produce proposal-only recommendations.
- Score using promotability rules.

Success criteria:

- Sweep emits promotable, not_promotable, needs_more_evidence, conflicts_detected, and created_proposals.
- Sweep never publishes directly.
- Sweep produces `no_changes` when appropriate.

Dependencies: T20, T21.

## Phase 7: Job Runner and Automation

### T23: Implement Filesystem Job Queue

Requirements:

- Support pending, claimed, completed, failed job states.
- Claim jobs with lease files.
- Requeue expired leases.
- Write result records for every job.
- Detect overlapping leases for controlled-writer targets.

Success criteria:

- Concurrent claim test allows only one runner to claim a job.
- Expired lease can be requeued.
- Job completion always writes result or failure reason.
- Concurrent controlled write test aborts stale writer.

Dependencies: T06, T10.

### T24: Implement Built-In Job Handlers

Requirements:

- Handle import compact, node compact, edge compact, context rebuild, promotion sweep, archive sweep, and active sign-in refresh check.
- Stub LLM-dependent handlers initially with deterministic fixture behavior.

Success criteria:

- Fixture jobs run end-to-end.
- `no_changes` is recorded when no update qualifies.
- Failed job remains visible and retryable.

Dependencies: T14, T17, T19, T22, T23.

### T25: Implement Watchdogs

Requirements:

- Detect dirty nodes/edges without jobs.
- Detect stale context packs.
- Detect unprocessed imports.
- Detect invalidated sign-ins.
- Detect archive candidates missing final compaction.
- Detect Obsidian/sync conflict files.
- Detect duplicate logical IDs.
- Detect overlapping operation windows on the same target.

Success criteria:

- Watchdog report is Markdown and JSON.
- Watchdog can enqueue remediation jobs.
- Watchdog never silently mutates published memory.
- Sync conflicts block affected shared writes until resolved.

Dependencies: T23, T24.

## Phase 8: Lifecycle, Skills, and Archives

### T26: Implement Node Lifecycle Commands

Requirements:

- Create, move, split, merge, archive, and restore nodes.
- Update graph reports and invalidations.
- Require dry-run for destructive restructuring.

Success criteria:

- Node create wizard creates folders, graph record, current/history files, import workspace, and policies.
- Node archive runs or requires final compaction.
- Restore reactivates node without losing history.

Dependencies: T16, T19, T10.

### T27: Implement Actor Assignment Commands

Requirements:

- Assign, move, deactivate, archive, and restore actors.
- Sign-ins reference assignments.
- Actor archive excludes memory from startup context while preserving history.

Success criteria:

- Actor assigned to department inherits department context.
- Archived actor no longer appears as active owner.
- Actor archive creates archive record and invalidation.

Dependencies: T16, T19.

### T28: Implement Shared Skill Registry

Requirements:

- Register, share, install, list, deprecate, archive, and restore skills.
- Enforce owner, trigger conditions, permission profile, and review state.
- Include relevant skills in context pack manifest.

Success criteria:

- Department skill is visible to eligible department agents.
- Org skill is visible across org where allowed.
- Deprecated skill is excluded by default.

Dependencies: T17, T20.

### T29: Implement Archive Sweep

Requirements:

- Identify inactive nodes, agents, edges, skills, imports, and stale context.
- Require final compaction or explicit deferral.
- Preserve historical retrieval.

Success criteria:

- Sweep finds inactive fixture agent.
- Archive preview shows affected records and context packs.
- Archive apply excludes target from startup context and writes archive record.

Dependencies: T24, T26, T27, T28.

## Phase 9: Distribution, Upgrade, and Migration

### T30: Implement Workspace Doctor

Requirements:

- `hive doctor` checks runtime/workspace version compatibility.
- Validates paths, config, schemas, and generated artifact freshness.
- Reports upgrade or migration needs.

Success criteria:

- Doctor passes clean fixture workspace.
- Doctor detects schema mismatch.
- Doctor detects missing generated pack.

Dependencies: T02, T07, T17.

### T31: Implement Migration Framework

Requirements:

- List migrations.
- Dry-run migrations.
- Apply migrations with backup and operation record.
- Record migration status and rollback instructions.

Success criteria:

- Dry-run shows file changes without writing.
- Apply writes migration record and operation record.
- Migration cannot run without backup when policy requires backup.

Dependencies: T10, T11, T30.

### T32: Implement Template Diffing

Requirements:

- Compare runtime templates with local files.
- Suggest diffs without overwriting.
- Support explicit apply to new files only or approved patch.

Success criteria:

- Runtime template update does not overwrite local current memory.
- Diff report is generated.
- Explicit apply writes operation record.

Dependencies: T31.

## Phase 10: MCP and Harness Adapters

### T33: Implement MCP Server

Requirements:

- Expose context pack retrieval, validation, import, proposal, context status, context refresh, job enqueue, and memory search tools.
- Expose memory graph, policies, and manifests as resources.

Success criteria:

- MCP inspector can call `get_context_pack`.
- MCP tool can create import item in fixture workspace.
- MCP tool cannot publish memory without authority.

Dependencies: T09, T17, T19, T20.

### T34: Implement Codex Adapter

Requirements:

- Provide Codex skill wrappers for key commands.
- Provide recommended hook examples for context status checks.
- Provide `codex exec` job-runner examples.

Success criteria:

- Codex can call CLI/MCP for context status and compile.
- Skill docs reference canonical commands, not duplicated logic.
- Hook example blocks stale shared write.

Dependencies: T33.

### T35: Implement Claude Adapter

Requirements:

- Provide Claude slash command wrappers.
- Provide Claude skill wrappers.
- Provide hook examples for context status checks.
- Provide headless `claude -p` job examples.

Success criteria:

- Claude wrapper invokes canonical CLI/MCP operations.
- Hook example blocks stale shared write.
- No Claude-specific path owns memory semantics.

Dependencies: T33.

## Phase 11: Packaging, Docs, and Release

### T36: Add End-to-End Test Suite

Requirements:

- Cover init, validate, import, compact, propose, promote, context compile, invalidate, refresh, archive, rollback preview, and migration dry-run.
- Tests should run against temporary fixture workspaces.

Success criteria:

- E2E tests pass locally.
- Tests do not mutate committed fixtures.
- Tests include at least one failure-path test per critical guardrail.

Dependencies: T05 through T31.

### T37: Add User Documentation

Requirements:

- Quickstart.
- Workspace layout guide.
- Command reference.
- Agent onboarding guide.
- Upgrade guide.
- Troubleshooting guide.

Success criteria:

- A new user can initialize a workspace, import a doc, validate, and compile context by following docs.
- Docs distinguish runtime-owned vs organization-owned files.

Dependencies: T09, T17, T31.

### T38: Add Release Packaging

Requirements:

- Package runtime with CLI.
- Include schemas, templates, skills, and migrations.
- Exclude fixture workspace data unless explicitly packaged as examples.

Success criteria:

- Clean install runs `hive --help`.
- Package does not contain local org memory.
- Release notes include migration instructions.

Dependencies: T36, T37.

## Parallel Execution Plan

### Wave 1: Scaffold and Schemas

Can run with two agents:

- Agent A: T00, T01, T02, T03
- Agent B: T04, T05 fixture definitions after T00 decisions

Join point:

- T05 passes with fixture validation.

### Wave 2: Validation and CLI

- Agent A: T06, T07, T08
- Agent B: T09, T10, T11

Join point:

- Mutating CLI command writes operation record and validator passes fixture.

### Wave 3: Import and Context

- Agent A: T12, T13, T14, T15
- Agent B: T16, T17, T18, T19

Join point:

- Import creates candidate and context compiler can refresh impacted pack.

### Wave 4: Governance and Automation

- Agent A: T20, T21, T22
- Agent B: T23, T24, T25

Join point:

- Promotion apply invalidates impacted packs and job runner can process remediation.

### Wave 5: Lifecycle and Upgrade

- Agent A: T26, T27, T28, T29
- Agent B: T30, T31, T32

Join point:

- Archive, migration dry-run, and template diffing all preserve org-owned context.

### Wave 6: Adapters and Release

- Agent A: T33, T34
- Agent B: T35, T36, T37, T38

Join point:

- CLI, MCP, Codex, and Claude wrappers all use canonical operations.

## Confirmed Planning Decisions

- Use Python 3.11+ for the runtime unless implementation constraints force a change.
- Move implementation to a dedicated repository; this plan should not assume the final location.
- Use deterministic compaction stubs first, with LLM adapters added after the kernel is stable.
- Include connector architecture for local files, Obsidian folders, URLs, GitHub/Git, Notion, and Google Drive.
- Treat sync conflicts and multi-agent race conditions as MVP concerns.
- Make MCP a fast follow after the CLI is stable and operational.
- Use role files and validators for MVP permission enforcement.

## Remaining Clarifying Questions

These should be answered before implementation starts, but defaults are available in `docs/implementation-decisions.md`.

1. What is the target dedicated repo/workspace location?
2. Should Notion/GDrive/GitHub connectors use real credentials in MVP, or should implementation begin with mocked/stubbed connector tests?
3. Should the first MCP server start immediately after context compilation works, or after archive/upgrade workflows are implemented?
4. Which Obsidian sync provider should be used for real conflict testing, if any?

## Definition of MVP Complete

The MVP is complete when:

- A new workspace can be initialized.
- A sample organization graph validates.
- A local document can be imported and compacted into candidate memory.
- A candidate can be proposed and reviewed.
- A context pack can be compiled for a department.
- A context update invalidates descendants, edges, assigned agents, and stale packs.
- A dormant agent run detects dirty context before loading stale memory.
- An archive operation removes inactive context from startup packs while preserving history.
- A migration dry-run proves upgrades will not clobber organization-owned memory.
- All critical guardrails are covered by tests.
