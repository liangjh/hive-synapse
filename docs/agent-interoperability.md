# Agent Interoperability Guide

Hive Synapse is designed to be agent-harness neutral. Codex, Claude, Hermes, OpenClaw, and future agent frameworks should all interact with the same Hive workspace through the same memory protocol.

## Core Contract

Every agent integration should follow this contract:

1. Make the `hive` CLI available to the agent runtime.
2. Set `HIVE_WORKSPACE` to the canonical Hive workspace path.
3. Assign the actor to a home node with `hive actor assign`.
4. Start or refresh the actor with `hive actor signin` / `hive actor refresh`, or use `hive session start` to create a harness-ready mount.
5. Load the returned context pack or generated session mount, not the full workspace.
6. Write new source material through session outboxes, imports, candidates, and proposals.
7. Let Hive manage shared team, department, organization, and edge memory.

```bash
export HIVE_WORKSPACE="$HOME/Obsidian/HiveSecondBrain"
./bin/hive actor signin agent:research-001 \
  --workspace "$HIVE_WORKSPACE" \
  --require-assignment \
  --json
```

The sign-in response includes:

- `context_pack`: generated `PACK.md` for the actor's effective node;
- `manifest`: generated `MANIFEST.yaml` with source paths and validation state;
- `personal_memory_home`: where private actor memory may live;
- `inherited_nodes`: parent context included in the pack;
- `connected_edges`: explicit collaboration edges included in the pack.

## Memory Boundary

Hive Synapse owns shared memory:

- organization, department, team, project, and edge `CURRENT.md` / `HISTORY.md`;
- generated node and edge `BRIEF.md` rollups;
- context packs;
- import items, candidate memory, proposals, operations, policies, and audit records.

Agent harnesses may own private memory:

- session transcripts;
- short-term scratchpads;
- private long-term memory;
- harness-native skills or tool configuration.

Agents should not directly update parent department or organization memory. They should submit reusable findings through import, candidate, and promotion flows.

## Install Hive Skills

Canonical, tool-agnostic Hive skills live in `skills/hive/`.

Install for Codex:

```bash
scripts/install-agent-skills.py codex
```

Install for Claude:

```bash
scripts/install-agent-skills.py claude
```

Install a generic copy for Hermes, OpenClaw, or another harness:

```bash
scripts/install-agent-skills.py generic --target ./agent-skills
```

Preview everything:

```bash
scripts/install-agent-skills.py all --dry-run
```

## Codex

Codex consumes skill directories containing `SKILL.md`.

```bash
scripts/install-agent-skills.py codex
```

Default install target:

```text
${CODEX_HOME:-$HOME/.codex}/skills/
```

Recommended runtime pattern:

```bash
export HIVE_WORKSPACE="$HOME/Obsidian/HiveSecondBrain"
./bin/hive actor signin agent:codex-research-001 --workspace "$HIVE_WORKSPACE" --require-assignment --json
```

For the simpler Codex workflow, materialize a mount and start Codex inside it:

```bash
./bin/hive session start agent:codex-research-001 --workspace "$HIVE_WORKSPACE" --adapter codex --output "$HOME/.hive/mounts/codex-research-001" --require-assignment
cd "$HOME/.hive/mounts/codex-research-001"
codex
```

At shutdown, write `.hive/outbox/memory-delta.jsonl` and run `hive session finish <mount> --workspace "$HIVE_WORKSPACE"`. If using direct sign-in instead, instruct Codex to load the returned `context_pack` path before work and to use Hive commands for memory mutations.

## Claude

Claude-style adapters currently use command Markdown wrappers in `adapters/claude/commands/`.

```bash
scripts/install-agent-skills.py claude
```

Default install target:

```text
${CLAUDE_HOME:-$HOME/.claude}/commands/
```

Useful commands after install:

- `hive-context-sync`
- `hive-ingest-summarize`
- `hive-compaction-rollups`
- `hive-scheduler-jobs`
- `hive-governance-promotion`
- `hive-validate`

The command wrappers translate natural language requests into Hive CLI calls while keeping Hive as the source of truth.

## Hermes

Hermes public docs describe a self-hosted agent with persistent local memory, scheduled automations, local execution, and portable `SKILL.md` skills. Hive's generic skills are intended to fit that model.

Recommended setup:

```bash
scripts/install-agent-skills.py generic --target "$HOME/.hermes/skills/hive"
```

If your Hermes installation uses a different skills directory, use that path instead. The important part is that Hermes can read the canonical `SKILL.md` files and execute the `hive` CLI.

Suggested Hermes bootstrap instruction:

```text
Use Hive Synapse for shared organizational memory. Do not ingest the full Hive workspace. Run `hive actor signin <actor-id> --workspace "$HIVE_WORKSPACE" --require-assignment --json`, load the returned context pack, and submit memory changes through Hive imports, candidates, promotions, compaction, and jobs.
```

For scheduled automations, Hermes can either call Hive directly from its own scheduler or use Hive-generated cron/launchd templates:

```bash
./bin/hive scheduler install cron --workspace "$HIVE_WORKSPACE" --interval-minutes 15
```

## OpenClaw

OpenClaw public docs describe a single agent workspace directory, bootstrap files such as `AGENTS.md`, `SOUL.md`, `TOOLS.md`, and `BOOTSTRAP.md`, plus skill loading from workspace, project, personal, managed, bundled, and extra skill directories.

Recommended setup:

```bash
scripts/install-agent-skills.py generic --target "$HOME/.openclaw/skills/hive"
```

Alternative if the OpenClaw agent workspace has a local skills directory:

```bash
scripts/install-agent-skills.py generic --target "<openclaw-agent-workspace>/skills/hive"
```

Recommended OpenClaw bootstrap files:

`AGENTS.md`:

```text
Use Hive Synapse as the shared memory control plane. Before work, run `hive session start` or `hive actor signin`, load only the generated session/context pack, and do not read unrelated Hive workspace directories.
```

`SOUL.md`:

```text
Follow the persona and operating boundaries assigned by the Hive node charter and the active context pack.
```

`TOOLS.md`:

```text
Use the `hive` CLI for context sync, imports, compaction, jobs, promotion, validation, and audit. Do not hand-edit generated context packs or parent organization memory.
```

If OpenClaw is configured with a per-agent workspace, point that workspace at a `hive session start --adapter openclaw` mount. Do not give OpenClaw the full canonical workspace unless you intentionally want broader access.

## Generic Harnesses

For OpenClaw-like, Hermes-like, or custom agents:

1. Copy `skills/hive/*/SKILL.md` into the harness's skill/plugin directory.
2. Ensure the harness can execute `hive` commands.
3. Set `HIVE_WORKSPACE` in the agent environment.
4. Assign the agent with `hive actor assign`.
5. Run `hive session start` at startup, or run `hive actor signin` for direct context-pack mode.
6. Load only the generated session mount or returned `PACK.md` and optional `MANIFEST.yaml`.
7. Route memory changes through `hive session finish`, `hive import`, `hive promote`, `hive node compact`, `hive edge compact`, and `hive job`.

## Current Gaps

- Hive now generates per-agent session mounts, but hard OS-level sandboxing is still the launcher/harness responsibility.
- Hive does not yet enforce hard actor write scopes across every command.
- Notion and Google Drive connectors preserve references but do not yet perform authenticated fetch or change watching.
- Vector and relational persistence are registry entries, not active backing stores.

These gaps do not block local use if agents operate through session mounts or sign-in context packs and Hive commands.

## References

- OpenClaw agent runtime docs: https://docs.openclaw.ai/concepts/agent
- Hermes Agent overview: https://hermes-agent.org/
