# Implementation Decisions

Updated: 2026-05-02

## Purpose

This file records defaults for implementation agents. Human answers override these defaults.

## Confirmed Defaults

| Decision | Default | Rationale |
|---|---|---|
| Runtime language | Python | Strong local CLI, filesystem, scripting, data-processing, and AI/ML ecosystem; easier for users to inspect and extend automation |
| Runtime platform | Python 3.11+ | Modern typing, stable async support, broad library compatibility |
| Package manager | `uv` preferred, `pipx` install supported | Fast reproducible local development plus simple CLI install path |
| CLI binary | `hive` | Short, memorable, matches current docs |
| Canonical workspace storage | Markdown + YAML frontmatter | Obsidian-compatible and inspectable |
| MVP database | None | Keep first slice filesystem-only |
| First generated indexes | JSON files | Rebuildable and easy to inspect |
| First LLM behavior | Adapter interface plus deterministic stubs | Avoid provider coupling before kernel is stable |
| First remote imports | Local files, Obsidian folders, URLs, GitHub/Git, Notion, and Google Drive | Core import use case includes existing organizational sources; use connector interfaces and stub/mock auth in early tests |
| MCP server timing | Fast follow after CLI stabilizes | Keep canonical semantics in CLI/runtime first |
| Permission model | Role files + validators first | OS/path enforcement can follow |
| Sync conflict handling | MVP-critical detection and safe write discipline | Obsidian sync and multi-agent writes can race; use append-only child proposals, parent pull-up, leases, hashes, and conflict reports |
| Operation automation policy | Low-noise defaults in `policies/operations.yaml` | Deployments can start with observed invalidation, manual promotion/watchdog/import sync, and threshold compaction, then tighten automation by policy |
| Repository strategy | Dedicated repo, location provided at implementation time | Plan should use relative paths and not assume final GitHub location |

## Python vs TypeScript Notes

Python advantages:

- Better fit for local automation, file processing, data transforms, import connectors, and future vector/ML work.
- Easier deterministic scripts for Obsidian/Markdown workflows.
- Strong ecosystem for Notion, Google APIs, Git, document parsing, and testing.
- Lower friction for users who want to customize operational scripts.

Python tradeoffs:

- MCP/TypeScript examples are common, so some MCP adapter patterns may require extra care.
- Packaging cross-platform CLIs requires discipline.
- Type checking depends on project standards rather than the language default.

Decision: use Python unless a later implementation constraint makes TypeScript materially better.

## Decisions Still Needing Human Confirmation

1. Confirm final dedicated repo/workspace location when implementation begins.
2. Confirm whether connector auth should be real in MVP or mocked/stubbed until the core import pipeline is stable.
3. Confirm whether MCP should be the first fast-follow after CLI, or after archive/upgrade flows are complete.
4. Confirm whether additional sync providers beyond Obsidian/Git should be tested in MVP.

## Sync Conflict Decision

Sync conflicts are both:

- a filesystem artifact of Obsidian/cloud sync creating duplicate/conflict files
- a coordination artifact of multiple agents trying to update shared context concurrently

MVP strategy:

- agents and child nodes append candidates, proposals, jobs, and operation records
- parent nodes pull from immediate children through rollup jobs
- parent published memory has controlled writers only
- controlled writes require leases and content-hash preconditions
- sync conflict files and duplicate IDs block affected shared writes until resolved
- generated context packs are rebuilt, not manually merged

## Non-Negotiable Implementation Constraints

- Runtime-owned code/templates/specs must stay separate from organization-owned memory.
- Markdown/YAML workspace data remains canonical for MVP.
- Generated artifacts must be rebuildable.
- Mutating commands must create operation records.
- Shared-memory publication must go through proposals and authority checks.
- Context-affecting changes must be evaluated and recorded through operation policy; dirty markers are emitted by manual command or stricter policy.
- Upgrades and migrations must be dry-runnable and non-clobbering.
- Child nodes and agents propose upward; parent rollups pull from children through reviewable jobs rather than accepting direct child writes to parent published memory.
