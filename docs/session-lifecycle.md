# Agent Session Lifecycle

Hive sessions make agent startup and shutdown repeatable across Codex, Claude, Hermes, OpenClaw, and generic harnesses. A session is a disposable local mount compiled from canonical Hive memory plus an outbox that is collected back into Hive at the end of the run.

This workflow assumes the canonical Hive workspace is already available on a local disk or network mount. Obsidian, Syncthing, iCloud, Dropbox, Git, or another sync layer can host that workspace, but the session commands only require normal filesystem access.

## Directory Model

Recommended layout:

```text
~/Workspace/hive-synapse/       # Hive runtime repo and CLI
~/HiveOrg/                      # canonical organization memory workspace
~/.hive/mounts/                 # disposable per-session agent mounts
```

Environment variables used in examples:

```bash
export HIVE_REPO="$HOME/Workspace/hive-synapse"
export HIVE_WORKSPACE="$HOME/HiveOrg"
export HIVE_MOUNTS="$HOME/.hive/mounts"
mkdir -p "$HIVE_MOUNTS"
```

## One-Time Actor Assignment

Assign the actor to a node. For example, Bethesda in consumer marketing:

```bash
$HIVE_REPO/bin/hive actor assign agent:bethesda \
  --workspace "$HIVE_WORKSPACE" \
  --home-node departments/consumer-marketing \
  --role "consumer marketing agent" \
  --actor human:you
```

If the department does not exist yet, create it first:

```bash
$HIVE_REPO/bin/hive node create departments/consumer-marketing \
  --workspace "$HIVE_WORKSPACE" \
  --kind department \
  --title "Consumer Marketing" \
  --parent org \
  --actor human:you
```

## Start a Codex Session

Materialize a scoped session mount:

```bash
RUN_ID="$(date +%Y%m%d-%H%M%S)"
MOUNT="$HIVE_MOUNTS/bethesda-consumer-marketing-$RUN_ID"

$HIVE_REPO/bin/hive session start agent:bethesda \
  --workspace "$HIVE_WORKSPACE" \
  --adapter codex \
  --output "$MOUNT" \
  --require-assignment \
  --purpose "Work on consumer marketing tasks" \
  --json
```

The command signs the actor in, compiles inherited context for the assigned node, snapshots Bethesda's private memory, and writes a mount ready for Codex.

Generated mount shape:

```text
$MOUNT/
  AGENTS.md                  # generated Codex bootstrap, read-only
  .hive/
    context/
      SOUL.md                # generated identity/persona/session stance
      CONTEXT.md             # generated org/department/edge context snapshot
      USER.md                # generated role and session instructions
      MEMORY.md              # generated actor-private memory snapshot
      SCOPE.yaml             # generated read/write scope
      manifest.yaml          # generated provenance and load-order metadata
    outbox/
      README.md              # memory-delta schema and examples
      memory-delta.jsonl     # agent writes durable memory here
      session-summary.md     # optional fallback summary
      artifacts/             # optional session artifacts
```

Start Codex from the mount:

```bash
cd "$MOUNT"
codex
```

Codex reads `AGENTS.md`, then loads `.hive/context/*`. Generated files are read-only session artifacts. Do not edit them as canonical memory.

## Write Session Memory

Before the agent session ends, write durable memory to:

```text
$MOUNT/.hive/outbox/memory-delta.jsonl
```

Each line is one JSON object:

```json
{"type":"observation","summary":"Bethesda prefers concise campaign briefs.","body":"Use short briefs with target audience, positioning, channel, test plan, and open questions.","target_scope":"private","confidence":0.8,"tags":["preference","marketing"]}
{"type":"decision","summary":"Consumer marketing sessions use generated Hive mounts.","body":"Codex should start inside the session mount and submit shared learnings through memory-delta.jsonl, not direct department edits.","target_scope":"node_candidate","target":"departments/consumer-marketing","confidence":0.9,"tags":["workflow","codex"]}
```

Allowed `target_scope` values:

- `private`: append to the actor's private `MEMORY.md`.
- `node_candidate`: route through import, compaction, and proposal for a node.
- `org_candidate`: route through import, compaction, and proposal for `org` unless a target is provided.
- `edge_candidate`: collected into the session archive; promotion for edge candidates is not wired in this MVP.

If there is no durable memory, write `no-memory-delta.md` with a short explanation. If `memory-delta.jsonl` is absent but `session-summary.md` exists, Hive collects the summary as private session memory.

## Finish the Session

Collect memory back into Hive:

```bash
$HIVE_REPO/bin/hive session finish "$MOUNT" \
  --workspace "$HIVE_WORKSPACE" \
  --json
```

Default finish behavior:

1. archives the outbox under the actor's canonical memory home;
2. writes a normalized session report;
3. appends `private` deltas to actor `MEMORY.md`;
4. imports `node_candidate` and `org_candidate` deltas as raw source material;
5. classifies and compacts those imports into candidate memory;
6. creates promotion proposals for shared memory review.

Use `--no-process` to collect shared deltas as imports without classification, compaction, or proposal creation:

```bash
$HIVE_REPO/bin/hive session finish "$MOUNT" \
  --workspace "$HIVE_WORKSPACE" \
  --no-process
```

Use `--no-propose` to classify and compact imports without creating proposals:

```bash
$HIVE_REPO/bin/hive session finish "$MOUNT" \
  --workspace "$HIVE_WORKSPACE" \
  --no-propose
```

Use `--compact-target` to refresh the assigned node brief after collection:

```bash
$HIVE_REPO/bin/hive session finish "$MOUNT" \
  --workspace "$HIVE_WORKSPACE" \
  --compact-target
```

## Review Shared Memory

Shared memory is not published directly. Review and apply proposals explicitly:

```bash
$HIVE_REPO/bin/hive promote list --workspace "$HIVE_WORKSPACE"
$HIVE_REPO/bin/hive promote review <proposal-id> \
  --workspace "$HIVE_WORKSPACE" \
  --decision approved \
  --actor steward:consumer-marketing \
  --rationale "source-backed session learning"
$HIVE_REPO/bin/hive promote apply <proposal-id> \
  --workspace "$HIVE_WORKSPACE" \
  --actor steward:consumer-marketing
```

After shared memory is applied, refresh impacted session mounts with a new `hive session start` or `hive actor refresh`.

## Harness Adapters

Use the same session commands with different adapters:

```bash
$HIVE_REPO/bin/hive session start agent:bethesda --workspace "$HIVE_WORKSPACE" --adapter claude --output "$HIVE_MOUNTS/bethesda-claude"
$HIVE_REPO/bin/hive session start agent:bethesda --workspace "$HIVE_WORKSPACE" --adapter hermes --output "$HIVE_MOUNTS/bethesda-hermes"
$HIVE_REPO/bin/hive session start agent:bethesda --workspace "$HIVE_WORKSPACE" --adapter openclaw --output "$HIVE_MOUNTS/bethesda-openclaw"
```

Adapter output is a generated view over canonical Hive context. Hive does not sync `.claude`, `.codex`, Hermes, or OpenClaw runtime internals into organization memory.

## Current Limits

- Users or agents invoke `hive session start` and `hive session finish` explicitly for now.
- `AGENTS.md`, `CLAUDE.md`, and `.hive/context/*` are generated read-only artifacts.
- Edge candidate promotion is collected but not fully promotable yet.
- Harness runtime transcripts and caches are ignored unless an agent explicitly summarizes them into `memory-delta.jsonl`.
