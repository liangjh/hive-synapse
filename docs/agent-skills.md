# Agent Skills and Commands

Hive Synapse ships adapter-native skills and commands inside the repo so they can be copied into agents deployed on a Hive network.

## Locations

- Codex skills: `adapters/codex/skills/<skill-name>/SKILL.md`
- Codex skill manifest: `adapters/codex/skills/MANIFEST.yaml`
- Claude commands: `adapters/claude/commands/hive-*.md`
- Install helpers: `adapters/codex/install-skills.sh`, `adapters/claude/install-commands.sh`


## Tool-Agnostic Source

Canonical skill definitions live in `skills/hive/`. Treat this directory as the source of truth for portable Hive behavior. Adapter-specific folders translate the same behavior into harness-native packaging:

- Codex uses skill directories containing `SKILL.md`.
- Claude uses slash-command Markdown files with command metadata and allowed-tool hints.
- Generic/other agents can consume `skills/hive/*/SKILL.md` directly or transform them into their own plugin format.

Install from the canonical source with the unified installer:

```bash
scripts/install-agent-skills.py codex
scripts/install-agent-skills.py claude
scripts/install-agent-skills.py generic --target ./agent-skills
scripts/install-agent-skills.py all
```

Preview without writing:

```bash
scripts/install-agent-skills.py all --dry-run
```

## Adapter Differences

The Hive semantics are the same across harnesses; only the packaging and invocation surface differs.

| Harness | Repo source | Installed form | Practical difference |
| --- | --- | --- | --- |
| Codex | `skills/hive/<skill>/SKILL.md` | `$CODEX_HOME/skills/<skill>/SKILL.md` | Skills are discovered by name/description and loaded when relevant. |
| Claude | `adapters/claude/commands/hive-*.md` | `$CLAUDE_HOME/commands/hive-*.md` | Commands are explicit slash-command style prompt wrappers with allowed-tool metadata. |
| Generic/OpenClaw/Hermes/etc. | `skills/hive/<skill>/SKILL.md` | Any configured skill/plugin directory | Use the canonical Markdown and manifest, then map Hive commands to that harness's tool permission model. |

For new harnesses, start from `skills/hive/MANIFEST.yaml`, copy each `SKILL.md`, and add only the harness-specific metadata required for invocation and tool permissions. Do not fork Hive memory semantics per harness.

## Categories

- `hive-context` — general Hive command routing.
- `hive-context-sync` — agent sign-in, scoped hydration, context packs, refresh, stale checks.
- `hive-ingest-summarize` — imports, classification, compaction, candidate summaries.
- `hive-compaction-rollups` — node/edge rollups and generated briefs.
- `hive-scheduler-jobs` — cron/launchd templates, job queues, watchdogs, audit operations.
- `hive-governance-promotion` — proposals, review, promotion, policy, rollback.

## Deploy to Codex

From the Hive Synapse repo:

```bash
adapters/codex/install-skills.sh
```

Or copy manually:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
cp -R adapters/codex/skills/hive-* "${CODEX_HOME:-$HOME/.codex}/skills/"
```

## Deploy to Claude

From the Hive Synapse repo:

```bash
adapters/claude/install-commands.sh
```

Or copy manually:

```bash
mkdir -p "${CLAUDE_HOME:-$HOME/.claude}/commands"
cp adapters/claude/commands/hive-*.md "${CLAUDE_HOME:-$HOME/.claude}/commands/"
```

## Deploy to Hermes, OpenClaw, or Other Agents

Use the generic installer when a harness supports Markdown skills or has its own plugin directory:

```bash
scripts/install-agent-skills.py generic --target <agent-skill-directory>
```

Examples:

```bash
scripts/install-agent-skills.py generic --target "$HOME/.hermes/skills/hive"
scripts/install-agent-skills.py generic --target "$HOME/.openclaw/skills/hive"
scripts/install-agent-skills.py generic --target "<openclaw-agent-workspace>/skills/hive"
```

If the target framework requires a different manifest or permission schema, transform from `skills/hive/MANIFEST.yaml` and preserve the `SKILL.md` command semantics.

## Natural Language Examples

- "Sign in the research agent and load only its context." → `hive-context-sync`
- "Summarize this Notion link into research candidate memory." → `hive-ingest-summarize`
- "Compact engineering and the launch collaboration edge every night." → `hive-compaction-rollups` + `hive-scheduler-jobs`
- "Install a 15-minute cron runner for watchdogs and queued jobs." → `hive-scheduler-jobs`
- "Promote this candidate to department knowledge after review." → `hive-governance-promotion`

## Operating Boundary

Skills should call Hive commands rather than hand-editing shared memory. Agent-private memory may remain harness-specific, while Hive controls shared node, edge, department, and organization memory through imports, candidates, promotions, compaction, context packs, and operation records.
