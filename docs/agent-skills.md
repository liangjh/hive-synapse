# Agent Skills and Commands

Hive Synapse ships adapter-native skills and commands inside the repo so they can be copied into agents deployed on a Hive network.

## Locations

- Codex skills: `adapters/codex/skills/<skill-name>/SKILL.md`
- Codex skill manifest: `adapters/codex/skills/MANIFEST.yaml`
- Claude commands: `adapters/claude/commands/hive-*.md`
- Install helpers: `adapters/codex/install-skills.sh`, `adapters/claude/install-commands.sh`

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

## Natural Language Examples

- "Sign in the research agent and load only its context." → `hive-context-sync`
- "Summarize this Notion link into research candidate memory." → `hive-ingest-summarize`
- "Compact engineering and the launch collaboration edge every night." → `hive-compaction-rollups` + `hive-scheduler-jobs`
- "Install a 15-minute cron runner for watchdogs and queued jobs." → `hive-scheduler-jobs`
- "Promote this candidate to department knowledge after review." → `hive-governance-promotion`

## Operating Boundary

Skills should call Hive commands rather than hand-editing shared memory. Agent-private memory may remain harness-specific, while Hive controls shared node, edge, department, and organization memory through imports, candidates, promotions, compaction, context packs, and operation records.
