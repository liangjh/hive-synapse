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

Hive Synapse is a filesystem-first memory framework for teams of humans and AI agents. It keeps organizational context in Markdown/YAML, compiles bounded context packs for agents, and enforces promotion, validation, invalidation, rollback preview, audit, and upgrade safety through deterministic CLI/MCP operations.

## What It Solves

AI agents in real organizations do not just need more tokens. They need a dependable way to know which context is current, source-backed, scoped to their role, safe to share, and approved for use. Without that layer, each agent run starts from scratch, re-reads scattered docs, misses cross-team context, trusts stale snippets, or turns private notes into accidental shared truth.

Hive Synapse organizes shared memory like infrastructure: raw sources are preserved, candidate memories move through review, current and historical context stay separate, graph edges carry cross-team knowledge, and agents boot from generated context packs rather than ad hoc prompt dumps.

## Current Status

Hive Synapse is usable today as a local-first Markdown/YAML MVP with Obsidian, Git, Dropbox, Syncthing, iCloud Drive, or another filesystem sync layer. It is not yet a hosted multi-tenant memory service, and remote SaaS connectors such as Notion and Google Drive are currently reference-preserving stubs rather than live sync integrations.

Recommended first deployment:

```text
~/Workspace/hive-synapse/      # runtime code, CLI, docs, tests
~/Obsidian/HiveSecondBrain/    # canonical synced organization workspace
```

Agents should call `hive actor signin` and load the generated context pack. They should not ingest the entire workspace unless you intentionally grant them that broader filesystem access.

## Feature Matrix

| Capability | Current Support | Status / Caveat |
|---|---|---|
| Filesystem workspace | `hive init`, `hive validate`, required Markdown/YAML directory contract. | Supported. Canonical storage is local files. |
| Hierarchical graph memory | Node records for orgs, departments, teams, projects, agents, and arbitrary child nodes. | Supported via `hive node create\|move\|archive\|restore\|compact`. |
| Cross-team graph edges | Explicit edge records and edge memory for scoped collaborations. | Supported via `hive edge create\|list\|archive\|restore\|compact`. |
| Charters / goals / tone / soul | `CHARTER.md` per node for mission, goals, tone, principles, and notes. | Supported via `hive charter init\|show\|list\|update`. |
| Scoped agent sign-in | Actors sign into a home/effective node and receive a generated context pack. | Supported via `hive actor assign\|signin\|refresh`; does not copy parent memory into agent folders. |
| Context pack compilation | Parent hierarchy + target node + active edge context compiled into `PACK.md` and `MANIFEST.yaml`. | Supported via `hive context compile`; packs are generated artifacts. |
| Partial hydration | Agents load only the context pack for their assigned node plus explicit edge context. | Supported at context level. Filesystem-level projection/export is not implemented yet. |
| Import staging | Local files/text and URL references are captured as import items. | Supported via `hive import add\|fetch`. Remote URL fetch stores references unless a connector implements content retrieval. |
| Import summarization | Classification and compaction create source-linked candidate memory. | Supported, deterministic by default; optional LLM profiles can assist import classify/compact. |
| Node and edge compaction | Generated `BRIEF.md` rollups for nodes and edges. | Supported via `hive node compact`, `hive edge compact`, and job handlers. |
| Promotion workflow | Candidate memories can be proposed, reviewed, approved/rejected, and applied. | Supported via `hive promote list\|sweep\|review\|apply\|reject`. |
| Jobs and watchdogs | Filesystem job queue plus watchdog reports and optional remediation enqueue. | Supported via `hive job enqueue\|list\|claim\|complete\|fail\|run\|watchdog`. |
| Scheduling | Cron and launchd templates for watchdog/job-runner loops. | Supported via `hive scheduler install cron\|launchd`; systemd/GitHub Actions examples are future docs. |
| Operation audit | Mutating commands write records under `memory/operations/`. | Supported via `hive operation list\|show`. |
| Backup and rollback preview | Full workspace backups and read-only rollback impact preview. | Backup and preview supported; rollback apply is not implemented. |
| Operation policy | Workspace and node policy files for invalidation, promotion, watchdog, import sync, archive, and compaction defaults. | Supported via policy files and `hive policy show`; defaults are conservative/manual. |
| Shared skills | Skills can be registered in workspace memory and adapter skills ship in the repo. | Supported via `hive skill register\|list\|status` plus `skills/hive/` and adapter installers. |
| Agent adapter packages | Codex skills, Claude command wrappers, and generic SKILL.md definitions. | Supported. Hermes/OpenClaw use the generic skill source unless custom adapters are added. |
| MCP-compatible surface | Tool listing, tool calls, and JSON-line serving. | Supported for current tool subset; broader MCP server polish is ongoing. |
| LLM profiles | Provider registry, credentials-by-env, and profile assignment. | Supported for import classify/compact and promotion sweep advisories; secrets stay outside memory files. |
| Persistence backends | Registry lists planned Markdown/vector/relational/graph layers. | Markdown is canonical today; vector/relational databases are not active persistence engines yet. |
| Notion / Google Drive | Connector registry recognizes and preserves references. | Authenticated fetch, watch, webhook, and polling are not implemented yet. |
| Scoped filesystem projection | Per-agent materialized workspace containing only allowed folders. | Not implemented yet; planned as `actor scope/materialize/collect` style workflow. |
| Hard access enforcement | CLI-level write-scope enforcement per actor. | Partial by convention/policy today; strict enforcement is future work. |

## Quick Start

```bash
git clone https://github.com/liangjh/hive-synapse.git
cd hive-synapse
./bin/hive --help
./bin/hive init /tmp/hive-demo --fixture basic-org
./bin/hive validate /tmp/hive-demo
./bin/hive actor signin agent:codex-engineering-001 --workspace /tmp/hive-demo --require-assignment --json
./bin/hive node compact departments/engineering --workspace /tmp/hive-demo
./bin/hive context compile departments/engineering --workspace /tmp/hive-demo
./bin/hive operation list --workspace /tmp/hive-demo
```

For a real Obsidian-backed workspace:

```bash
export HIVE_WORKSPACE="$HOME/Obsidian/HiveSecondBrain"
./bin/hive init "$HIVE_WORKSPACE"
./bin/hive node create org --workspace "$HIVE_WORKSPACE" --kind organization --title "Personal Operating System" --actor human:you
./bin/hive validate "$HIVE_WORKSPACE"
```

See [`docs/local-setup.md`](docs/local-setup.md), [`docs/second-brain-setup.md`](docs/second-brain-setup.md), and [`docs/agent-interoperability.md`](docs/agent-interoperability.md) for step-by-step deployment.

## Agent Interoperability

Hive Synapse is harness-neutral at the memory layer. The shared contract is:

1. install or expose the `hive` CLI;
2. point agents at `HIVE_WORKSPACE`;
3. run `hive actor signin` to obtain scoped context;
4. load the generated `PACK.md`;
5. submit updates through imports, candidates, promotions, compaction, and jobs.

Packaged adapters are included for common harnesses:

- Codex: canonical skills can be installed into `$CODEX_HOME/skills`.
- Claude: command wrappers can be installed into `$CLAUDE_HOME/commands`.
- Hermes, OpenClaw, and other agents: consume `skills/hive/*/SKILL.md` or install generic skills into the harness-specific skill/plugin directory.

Install skills:

```bash
scripts/install-agent-skills.py codex
scripts/install-agent-skills.py claude
scripts/install-agent-skills.py generic --target ./agent-skills
scripts/install-agent-skills.py all --dry-run
```

OpenClaw public docs describe a workspace model with bootstrap files such as `AGENTS.md`, `SOUL.md`, `TOOLS.md`, and workspace/project/personal skill directories. Hermes public docs describe portable `SKILL.md` skills, persistent local memory, and scheduled automations. Hive does not depend on either implementation; use the generic `skills/hive/` definitions and point those agents at generated Hive context packs.

## Design and Build Plans

- [`docs/local-setup.md`](docs/local-setup.md): local installation and real-workspace setup guide.
- [`docs/second-brain-setup.md`](docs/second-brain-setup.md): end-to-end personal/team second-brain setup.
- [`docs/agent-interoperability.md`](docs/agent-interoperability.md): Codex, Claude, Hermes, OpenClaw, and generic agent setup.
- [`docs/agent-skills.md`](docs/agent-skills.md): deployable skill categories and installers.
- [`docs/setup-checklist.md`](docs/setup-checklist.md): short checklist for feature-completion readiness.
- [`docs/command-reference.md`](docs/command-reference.md): CLI command reference.
- [`docs/operation-policy.md`](docs/operation-policy.md): configurable automation defaults.
- [`docs/workspace-layout.md`](docs/workspace-layout.md): workspace storage model.
- [`docs/agent-onboarding.md`](docs/agent-onboarding.md): agent boot sequence and guardrails.
- [`docs/mcp.md`](docs/mcp.md): MCP-compatible tool surface and adapter notes.
- [`docs/implementation-backlog.md`](docs/implementation-backlog.md): task-by-task implementation backlog.
- [`docs/implementation-test-plan.md`](docs/implementation-test-plan.md): task-mapped test plan.
- [`docs/implementation-decisions.md`](docs/implementation-decisions.md): confirmed implementation defaults.
- [`docs/concurrency-sync.md`](docs/concurrency-sync.md): Markdown/Obsidian concurrency strategy.
- [`docs/distribution-upgrade.md`](docs/distribution-upgrade.md): runtime/workspace separation and non-clobbering upgrades.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
