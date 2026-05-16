# Hive Synapse Architecture Map

Generated: 2026-05-16

This document maps the Hive Synapse codebase into a visual architecture. It is meant to help a reader move from the product concept to the files that implement it.

Hive Synapse is a dependency-light Python CLI/MCP runtime for a Markdown/YAML workspace. The runtime owns commands, validation, compilation, governance, jobs, adapters, and optional LLM calls. The workspace owns organization memory, graph records, imports, proposals, context packs, operation logs, and generated session mounts.

## Source Coverage

This map was compiled from:

- Runtime source: `src/hive_synapse/*.py`
- CLI entrypoint and package metadata: `bin/hive`, `pyproject.toml`
- Tests: `tests/test_*.py`
- Documentation: `README.md`, `docs/*.md`
- Agent packaging: `skills/hive/*`, `adapters/codex/*`, `adapters/claude/*`
- Workspace contract examples: `fixtures/workspaces/basic-org/**`, `templates/**`
- Design context: the untracked `designs` symlink was read as reference material, but the mapped implementation source of truth is the repository code and docs.

Reusable Mermaid sources live under `docs/diagrams/`.

## How To Read This

Start with the system overview, then follow one workflow:

- Agent startup: System Overview -> Runtime Module Map -> Actor Sign-In and Context Compilation.
- Shared memory ingestion: System Overview -> Import to Promotion Flow -> Workspace Data Model.
- Session mounts: System Overview -> Session Lifecycle Flow.
- Maintenance automation: Jobs and Maintenance Flow -> Workspace Data Model.

## System Overview

Primary diagram source: [`docs/diagrams/system-overview.mmd`](diagrams/system-overview.mmd)

```mermaid
flowchart LR
  Human["Human operator"]
  Agent["AI agents<br/>Codex / Claude / generic"]

  subgraph Interfaces["Interface Layer"]
    Bin["bin/hive<br/>shell launcher"]
    CLI["hive_synapse.cli<br/>argparse command surface"]
    MCP["hive_synapse.mcp<br/>JSON-line tool surface"]
    AdapterSkills["skills/ and adapters/<br/>Codex skills, Claude commands"]
  end

  subgraph Runtime["Runtime Services"]
    Workspace["workspace.py<br/>init fixtures and required dirs"]
    Lifecycle["lifecycle.py / edges.py / charters.py<br/>nodes, edges, assignments, charters"]
    GraphContext["graph.py / context.py / sessions.py<br/>graph traversal and context packs"]
    SessionLifecycle["session_lifecycle.py<br/>session mounts and outbox collection"]
    Ingest["imports.py / connectors.py<br/>source capture, classify, compact"]
    Governance["promotion.py / guardrails.py<br/>review, apply, validation guardrails"]
    Jobs["jobs.py / watchdog.py / scheduler.py<br/>queue, remediation, templates"]
    LLM["llm.py<br/>optional model adapters"]
    Upgrade["backup.py / upgrade.py / archive.py<br/>backup, migration, archive sweeps"]
    Audit["operations.py<br/>append-only operation records"]
  end

  subgraph WorkspaceStore["Filesystem Workspace"]
    Config["hive.config.yaml<br/>workspace binding"]
    Policies["policies/<br/>operation, budget, LLM"]
    Org["org/<br/>assignments and sign-ins"]
    GraphFiles["memory/graph/<br/>node and edge definitions"]
    Records["memory/records/<br/>current, history, charters, candidates, published"]
    Imports["memory/imports/ and memory/raw/<br/>staging and preserved evidence"]
    Proposals["memory/proposals/<br/>promotion proposals"]
    Queue["memory/jobs/ and memory/state/<br/>pending work, leases, dirty markers"]
    Generated["memory/generated/<br/>context packs, session records, LLM runs"]
    Operations["memory/operations/ and memory/audit/<br/>audit trail and reports"]
  end

  Human --> Bin
  Agent --> Bin
  Agent --> MCP
  AdapterSkills --> Bin
  Bin --> CLI
  CLI --> Workspace
  CLI --> Lifecycle
  CLI --> GraphContext
  CLI --> SessionLifecycle
  CLI --> Ingest
  CLI --> Governance
  CLI --> Jobs
  CLI --> LLM
  CLI --> Upgrade
  MCP --> GraphContext
  MCP --> Ingest
  MCP --> Jobs

  Workspace --> Config
  Workspace --> Policies
  Lifecycle --> GraphFiles
  Lifecycle --> Records
  Lifecycle --> Org
  GraphContext --> GraphFiles
  GraphContext --> Records
  GraphContext --> Generated
  SessionLifecycle --> Generated
  SessionLifecycle --> Imports
  Ingest --> Imports
  Ingest --> Records
  Ingest --> LLM
  Governance --> Proposals
  Governance --> Records
  Governance --> Queue
  Jobs --> Queue
  Jobs --> GraphContext
  Jobs --> Ingest
  Jobs --> Governance
  LLM --> Generated
  Upgrade --> Operations
  Audit --> Operations
```

## Runtime Module Map

Primary diagram source: [`docs/diagrams/runtime-module-map.mmd`](diagrams/runtime-module-map.mmd)

```mermaid
flowchart TB
  CLI["cli.py<br/>command routing"]
  MCP["mcp.py<br/>tool routing"]
  Bin["bin/hive"]

  subgraph Foundation["Foundation"]
    Models["models.py<br/>record contracts"]
    Paths["paths.py<br/>workspace layout"]
    FS["fs.py<br/>atomic writes and root checks"]
    Frontmatter["frontmatter.py"]
    YAML["simple_yaml.py"]
    IDs["ids.py"]
    Errors["errors.py"]
    Repository["repository.py"]
    Operations["operations.py"]
  end

  subgraph MemoryGraph["Graph and Context"]
    Graph["graph.py"]
    Context["context.py"]
    Sessions["sessions.py"]
    SessionLifecycle["session_lifecycle.py"]
  end

  subgraph MutationFlows["Mutation Flows"]
    Workspace["workspace.py"]
    Lifecycle["lifecycle.py"]
    Edges["edges.py"]
    Charters["charters.py"]
    Imports["imports.py"]
    Promotion["promotion.py"]
    Compaction["compaction.py"]
  end

  subgraph OperationsLayer["Operations and Maintenance"]
    Jobs["jobs.py"]
    Watchdog["watchdog.py"]
    Scheduler["scheduler.py"]
    Policies["policies.py"]
    Guardrails["guardrails.py"]
    Validator["validator.py"]
    Backup["backup.py"]
    Upgrade["upgrade.py"]
    Archive["archive.py"]
    Skills["skills.py"]
  end

  subgraph Integrations["Integrations"]
    LLM["llm.py"]
    Connectors["connectors.py"]
    Persistence["persistence.py"]
  end

  Bin --> CLI
  CLI --> Models
  CLI --> Graph
  CLI --> Workspace
  CLI --> Jobs
  CLI --> LLM
  MCP --> Context
  MCP --> Imports
  MCP --> Jobs
  MCP --> Validator

  Repository --> Paths
  Repository --> FS
  Repository --> Frontmatter
  Operations --> Paths
  Operations --> Models
  Graph --> Paths
  Graph --> Models
  Graph --> Frontmatter
  Context --> Graph
  Context --> Policies
  Sessions --> Context
  Sessions --> Graph
  SessionLifecycle --> Sessions
  SessionLifecycle --> Imports
  SessionLifecycle --> Compaction
  Lifecycle --> Charters
  Lifecycle --> Context
  Edges --> Graph
  Edges --> Context
  Imports --> Repository
  Imports --> Connectors
  Imports --> LLM
  Promotion --> Context
  Promotion --> LLM
  Compaction --> Graph
  Jobs --> Context
  Jobs --> Imports
  Jobs --> Promotion
  Jobs --> Compaction
  Watchdog --> Jobs
  Validator --> Guardrails
  Upgrade --> Backup
  Upgrade --> Validator
```

## Workspace Data Model

Primary diagram source: [`docs/diagrams/workspace-data-model.mmd`](diagrams/workspace-data-model.mmd)

```mermaid
flowchart TB
  Root["Hive workspace root"]
  Config["hive.config.yaml<br/>schema/runtime binding"]
  Policies["policies/<br/>operations, context budget, node overrides, LLM"]
  Org["org/<br/>assignments, signins, members, roles"]

  MemoryRoot["memory/"]

  subgraph MemoryDirs["memory/ directories"]
    Graph["graph/<br/>nodes/*.md, edges/*.md"]
    Records["records/<br/>nodes, edges, agents"]
    Imports["imports/<br/>per-target staging"]
    Raw["raw/<br/>preserved evidence"]
    Proposals["proposals/<br/>promotion queue"]
    Jobs["jobs/<br/>pending, claimed, completed, failed"]
    State["state/<br/>context-dirty, leases"]
    Generated["generated/<br/>context-packs, session-mounts, llm-runs"]
    Operations["operations/<br/>operation records"]
    Audit["audit/<br/>watchdog, archive, reports"]
    Backups["backups/ and migrations/"]
    Skills["skills/<br/>shared skill registry"]
  end

  Root --> Config
  Root --> Policies
  Root --> Org
  Root --> MemoryRoot
  MemoryRoot --> Graph
  MemoryRoot --> Records
  MemoryRoot --> Imports
  MemoryRoot --> Jobs
  MemoryRoot --> Generated
  MemoryRoot --> Operations
  Graph --> Records
  Imports --> Raw
  Imports --> Records
  Records --> Proposals
  Proposals --> Records
  Graph --> Generated
  Records --> Generated
  Policies --> Generated
  State --> Generated
  Jobs --> Generated
  Operations --> Audit
  Backups --> Audit
  Skills --> Generated

  Records --> Current["CURRENT.md<br/>startup memory"]
  Records --> Charter["CHARTER.md<br/>mission, goals, tone"]
  Records --> Brief["BRIEF.md<br/>generated rollup"]
  Records --> Candidate["candidates/*.md"]
  Records --> Published["published/*.md"]
```

## Actor Sign-In And Context Compilation

Primary diagram source: [`docs/diagrams/actor-context-sequence.mmd`](diagrams/actor-context-sequence.mmd)

```mermaid
sequenceDiagram
  autonumber
  participant A as Agent or human
  participant C as hive actor signin
  participant S as sessions.sign_in_actor
  participant G as MemoryGraph
  participant CP as compile_context_pack
  participant W as Filesystem workspace
  participant O as OperationLog

  A->>C: hive actor signin actor-id --workspace W
  C->>S: sign_in_actor(W, actor-id)
  S->>W: read assignment YAML files
  S->>G: load nodes and edges
  G-->>S: parent chain and connected edges
  S->>CP: compile_context_pack(W, effective node)
  CP->>W: read parent charters, briefs, current memory
  CP->>W: read target charter, brief, current memory
  CP->>W: read connected edge brief and current memory
  CP->>W: scan context dirty markers
  CP->>W: write PACK.md and MANIFEST.yaml
  CP->>O: append context_compile operation
  S->>W: write sign-in YAML file
  S->>O: append actor_signin operation
  S-->>A: context pack path, manifest path, bootstrap
```

## Import To Promotion Flow

Primary diagram source: [`docs/diagrams/import-promotion-sequence.mmd`](diagrams/import-promotion-sequence.mmd)

```mermaid
sequenceDiagram
  autonumber
  participant User as Human or agent
  participant CLI as hive import/promote
  participant Importer as imports.py
  participant LLM as llm.py optional
  participant Promotion as promotion.py
  participant Context as context.invalidate_context
  participant Workspace as Filesystem workspace
  participant Ops as OperationLog

  User->>CLI: hive import add target source
  CLI->>Importer: add_import()
  Importer->>Workspace: preserve source under memory/raw/imports
  Importer->>Workspace: write memory/imports/.../items/import_*.yaml
  Importer->>Ops: append import_add
  User->>CLI: hive import classify import-id
  CLI->>Importer: classify_import()
  Importer->>LLM: generate_structured() if policy enables model
  Importer->>Workspace: update import item classification
  Importer->>Ops: append import_classify
  User->>CLI: hive import compact import-id
  CLI->>Importer: compact_import()
  Importer->>LLM: summarize if policy enables model
  Importer->>Workspace: write memory/records/nodes/target/candidates/mem_*.md
  Importer->>Ops: append import_compact
  User->>CLI: hive import propose import-id
  Importer->>Workspace: write memory/proposals/proposal_*.yaml
  Importer->>Ops: append import_propose
  User->>CLI: hive promote review/apply proposal-id
  CLI->>Promotion: review_proposal(), apply_proposal()
  Promotion->>Workspace: require source_refs and authorized reviewer
  Promotion->>Workspace: write published record and append CURRENT.md
  Promotion->>Context: invalidate target context according to policy
  Promotion->>Ops: append promotion_review and promotion_apply
```

## Session Lifecycle Flow

Primary diagram source: [`docs/diagrams/session-lifecycle-sequence.mmd`](diagrams/session-lifecycle-sequence.mmd)

```mermaid
sequenceDiagram
  autonumber
  participant Agent as Agent runtime
  participant CLI as hive session
  participant Session as session_lifecycle.py
  participant SignIn as sessions.sign_in_actor
  participant Imports as imports.py
  participant Compaction as compaction.py
  participant Workspace as Canonical workspace
  participant Mount as Session mount
  participant Ops as OperationLog

  Agent->>CLI: hive session start actor-id --adapter codex --output mount
  CLI->>Session: start_session()
  Session->>SignIn: sign_in_actor()
  SignIn->>Workspace: compile context and write sign-in
  Session->>Workspace: read PACK.md, MANIFEST.yaml, actor MEMORY.md
  Session->>Mount: write AGENTS.md and .hive/context/*
  Session->>Mount: write .hive/outbox/README.md
  Session->>Workspace: write generated session-mount record
  Session->>Ops: append session_start
  Agent->>Mount: read generated context and do work
  Agent->>Mount: write .hive/outbox/memory-delta.jsonl
  Agent->>CLI: hive session finish mount
  CLI->>Session: finish_session()
  Session->>Mount: read manifest and memory deltas
  Session->>Workspace: archive outbox and write SESSION.md
  Session->>Workspace: append private deltas to actor MEMORY.md
  Session->>Imports: route shared deltas through add/classify/compact/propose
  Session->>Compaction: optional compact target
  Session->>Ops: append session_finish
  Session-->>Agent: private counts, imports, proposals, operation id
```

## Jobs And Maintenance Flow

Primary diagram source: [`docs/diagrams/jobs-maintenance.mmd`](diagrams/jobs-maintenance.mmd)

```mermaid
flowchart LR
  Scheduler["External scheduler<br/>cron or launchd template"]
  Watchdog["watchdog.py<br/>detect stale context, conflicts, unprocessed imports"]
  Enqueue["jobs.enqueue_job<br/>write pending job YAML"]
  Claim["jobs.claim_job<br/>lease and move pending to claimed"]
  Runner["jobs.run_next_job"]
  Complete["jobs.complete_job / fail_job"]

  subgraph Handlers["Implemented Job Handlers"]
    ImportCompact["import_compact"]
    ContextRebuild["context_rebuild"]
    PromotionSweep["promotion_sweep"]
    NodeCompact["node_compact"]
    EdgeCompact["edge_compact"]
  end

  subgraph WorkspaceState["Workspace State"]
    Pending["memory/jobs/pending"]
    Claimed["memory/jobs/claimed"]
    Completed["memory/jobs/completed"]
    Failed["memory/jobs/failed"]
    Leases["memory/state/leases"]
    Dirty["memory/state/context-dirty"]
    Audit["memory/audit and memory/operations"]
  end

  Scheduler --> Watchdog
  Watchdog --> Dirty
  Watchdog --> Enqueue
  Enqueue --> Pending
  Scheduler --> Runner
  Runner --> Claim
  Claim --> Pending
  Claim --> Claimed
  Claim --> Leases
  Runner --> ImportCompact
  Runner --> ContextRebuild
  Runner --> PromotionSweep
  Runner --> NodeCompact
  Runner --> EdgeCompact
  ImportCompact --> Complete
  ContextRebuild --> Complete
  PromotionSweep --> Complete
  NodeCompact --> Complete
  EdgeCompact --> Complete
  Complete --> Completed
  Complete --> Failed
  Complete --> Audit
```

## Code-To-Concept Index

| Concept | Implementation files | Notes |
|---|---|---|
| CLI command surface | `bin/hive`, `src/hive_synapse/cli.py` | `build_parser()` defines command groups and maps each subcommand to a handler. |
| Workspace layout | `src/hive_synapse/paths.py`, `src/hive_synapse/workspace.py`, `templates/` | `REQUIRED_DIRS` defines the workspace contract; `hive init` creates it. |
| Data contracts | `src/hive_synapse/models.py`, `src/hive_synapse/simple_yaml.py`, `src/hive_synapse/frontmatter.py` | Lightweight model validation and Markdown/YAML frontmatter parsing. |
| Graph traversal | `src/hive_synapse/graph.py` | Loads node and edge records, computes parents, descendants, connected edges, and impact. |
| Context packs | `src/hive_synapse/context.py`, `src/hive_synapse/sessions.py` | Compiles inherited parent, target, edge, and dirty-marker context into generated packs. |
| Node and edge lifecycle | `src/hive_synapse/lifecycle.py`, `src/hive_synapse/edges.py`, `src/hive_synapse/charters.py` | Creates records, memory files, import workspaces, policies, and invalidations. |
| Imports | `src/hive_synapse/imports.py`, `src/hive_synapse/connectors.py` | Preserves evidence, records external refs, classifies, compacts, and creates candidates. |
| Governance and promotion | `src/hive_synapse/promotion.py`, `src/hive_synapse/guardrails.py`, `src/hive_synapse/validator.py` | Enforces source refs, review metadata, authority transitions, and validation. |
| Session mounts | `src/hive_synapse/session_lifecycle.py` | Materializes harness-ready mounts and collects outbox deltas back into Hive. |
| Jobs and scheduling | `src/hive_synapse/jobs.py`, `src/hive_synapse/watchdog.py`, `src/hive_synapse/scheduler.py` | Filesystem queue, leases, watchdog reports, cron/launchd templates. |
| Audit and recovery | `src/hive_synapse/operations.py`, `src/hive_synapse/backup.py`, `src/hive_synapse/upgrade.py`, `src/hive_synapse/archive.py` | Append-only operation records, backup, rollback preview, migration, archive sweeps. |
| Agent adapters | `skills/hive/`, `adapters/codex/`, `adapters/claude/`, `scripts/install-agent-skills.py` | Harness packaging around the same CLI semantics. |
| Optional model layer | `src/hive_synapse/llm.py` | Deterministic default plus OpenAI-compatible, Anthropic, LiteLLM, and command providers. |
| Tests proving flows | `tests/test_e2e_fixture.py`, `tests/test_import_context.py`, `tests/test_actor_signin.py`, `tests/test_session_lifecycle.py`, `tests/test_promotion_jobs.py` | Exercise the main lifecycle flows shown above. |

## Architectural Takeaways

- The runtime is intentionally filesystem-first and dependency-light. Markdown/YAML remains the canonical store.
- Generated artifacts are rebuildable. `memory/generated/context-packs`, session materializations, and LLM run records should not be treated as user-authored source of truth.
- Shared memory changes are mediated: imports create candidates, proposals capture intent, authorized review applies published memory, and context invalidation marks dependent packs stale according to policy.
- Agent session mounts are disposable views over canonical memory. Agents read generated context and write durable deltas to an outbox; `hive session finish` routes those deltas back through private memory or governed shared-memory workflows.
- Operation records are the audit spine. Most mutating flows append `memory/operations/op_*.yaml` with changed files, changed records, and rollback strategy metadata.
