<p align="left">
  <img src="logo-2.png" alt="hive-synapse logo" width="180">
</p>

<p align="left">
  <a href="https://github.com/liangjh/hive-synapse/actions/workflows/ci.yml">
    <img src="https://github.com/liangjh/hive-synapse/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI">
  </a>
</p>

# hive-synapse

Hierarchical memory and context management for organization-based AI agents.

Hive Synapse is a filesystem-first memory framework for teams of humans and AI agents. It keeps organizational context in Markdown/YAML, compiles bounded context packs for agents, and enforces promotion, validation, invalidation, rollback, and upgrade safety through deterministic CLI/MCP operations.

## What It Solves

AI agents in real organizations do not just need more tokens. They need a dependable way to know which context is current, source-backed, scoped to their role, safe to share, and approved for use. Without that layer, each agent run starts from scratch, re-reads scattered docs, misses cross-team context, trusts stale snippets, or turns private notes into accidental shared truth.

Hive Synapse organizes agent memory like infrastructure: raw sources are preserved, candidate memories move through review, current and historical context stay separate, graph edges carry cross-team knowledge, and agents boot from generated context packs rather than ad hoc prompt dumps.

## Memory Management Coverage

| Capability | Current Support | Why It Matters for Organizing AI Agents |
|---|---|---|
| Hierarchical memory | Workspaces model organization, department, project/workflow, edge, actor, and agent-owned memory roots. | Agents inherit the right level of context instead of rediscovering team basics every run. |
| Graph and cross-team context | Node and edge records capture shared context such as Engineering <-> Marketing launch work. | Agents can use collaboration-specific memory without broad access to every partner-team detail. |
| Context pack compilation | `hive context compile` generates rebuildable packs under `memory/generated/context-packs/`. | Agent startup becomes inspectable and reproducible instead of depending on prompt stuffing or retrieval luck. |
| Import staging | `hive import add\|fetch\|classify\|compact\|propose` stages local files, URLs, and connector references. | Existing docs, notes, and source material enter the system as evidence before they become trusted memory. |
| Summarization and compaction | Import compaction creates source-linked candidate memory; broader node/edge/org compaction is represented in the command and job model. | Long-running work can be condensed into durable memory without carrying raw transcripts forever. |
| Promotion workflow | `hive promote list\|review\|apply\|reject\|sweep` routes candidates through explicit review. | Agent-written observations cannot silently become shared organizational truth. |
| Current and historical memory | Workspaces include `CURRENT.md`, `HISTORY.md`, archive records, deprecated state, and operation history. | Agents can distinguish what is true now from what was true during prior decisions. |
| Longitudinal values and drift | The design tracks conflicts, drift, supersession, archives, and future temporal graph projections. | Agents can reason about changing practices instead of flattening history into one stale summary. |
| Freshness and invalidation | `hive context impacted\|invalidate\|status` computes impact and writes dirty markers when policy or an explicit command requests them. | Active or future agents can detect stale context without forcing every automated change to invalidate memory. |
| Agent assignment and sign-in | Workspace records map actors to home nodes, roles, personal memory homes, sign-ins, and loaded context. | Each agent run has an operating contract: who it is, where it belongs, and what context it loaded. |
| Guardrails and validation | `hive validate` checks required layout, graph records, memory records, source references, and duplicate IDs. | Memory safety is enforced by deterministic checks, not only by prompt instructions. |
| Jobs and watchdogs | `hive job` commands enqueue, claim, run, complete, fail, and watchdog memory work, with remediation controlled by operation policy. | Maintenance work such as rebuilds, imports, stale packs, and deferred review can be tracked explicitly. |
| Operation policy | `policies/operations.yaml` and `hive policy show` control invalidation, compaction, promotion sweeps, watchdogs, import sync, and archive defaults. | Deployments can start conservative and turn on stricter automation only when memory growth or workflow needs justify it. |
| Rollback and audit | Mutating commands append operation records; backups and `hive rollback preview` support guarded recovery. | Bad imports, promotions, compactions, or lifecycle operations can be inspected before reversal. |
| Lifecycle and archive | `hive node`, `hive actor`, `hive archive`, and related commands move entities out of active context while preserving history. | Retired agents, obsolete projects, and inactive teams do not pollute startup context. |
| Shared skills | `hive skill register\|list\|status` models reusable skills at scoped locations. | Agent capabilities can be governed alongside memory instead of living as untracked local prompts. |
| Harness-neutral access | CLI commands support JSON output, and `hive mcp tools\|call\|serve` exposes an MCP-compatible surface. | Codex, Claude Code, Cursor, ChatGPT, and custom harnesses can share one memory protocol. |
| Upgrade safety | `hive upgrade doctor\|migration-*\|template-*` separates runtime changes from organization-owned memory. | Agent memory workspaces can evolve without clobbering local context, imports, or audit data. |

## Current Build Status

Implementation has started with a dependency-free Python CLI/runtime scaffold. The current focus is the Markdown/Obsidian-compatible MVP:

```text
hive init -> hive validate -> hive context compile, with repository safety, backups, and rollback preview
```

## Quick Start

```bash
./bin/hive --help
./bin/hive init /tmp/hive-demo --fixture basic-org
./bin/hive validate /tmp/hive-demo
./bin/hive context compile departments/engineering --workspace /tmp/hive-demo
./bin/hive backup create /tmp/hive-demo
printf "# Launch Notes\n\nCurrent project practice." > /tmp/launch-notes.md
uv run hive import add departments/engineering /tmp/launch-notes.md --workspace /tmp/hive-demo
uv run hive promote sweep --workspace /tmp/hive-demo --create-proposals
uv run hive policy show --workspace /tmp/hive-demo
uv run hive job watchdog --workspace /tmp/hive-demo
uv run hive upgrade doctor --workspace /tmp/hive-demo
```

See [`docs/getting-started.md`](docs/getting-started.md) for the detailed guide.

## Design and Build Plans

- [`docs/implementation-backlog.md`](docs/implementation-backlog.md): task-by-task implementation backlog.
- [`docs/implementation-test-plan.md`](docs/implementation-test-plan.md): task-mapped test plan.
- [`docs/implementation-decisions.md`](docs/implementation-decisions.md): confirmed implementation defaults.
- [`docs/concurrency-sync.md`](docs/concurrency-sync.md): Markdown/Obsidian concurrency strategy.
- [`docs/distribution-upgrade.md`](docs/distribution-upgrade.md): runtime/workspace separation and non-clobbering upgrades.
- [`docs/command-reference.md`](docs/command-reference.md): CLI command reference.
- [`docs/operation-policy.md`](docs/operation-policy.md): configurable automation defaults.
- [`docs/workspace-layout.md`](docs/workspace-layout.md): workspace storage model.
- [`docs/agent-onboarding.md`](docs/agent-onboarding.md): agent boot sequence and guardrails.
- [`docs/mcp.md`](docs/mcp.md): MCP-compatible tool surface and adapter notes.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
