# Second Brain Setup Guide

This guide configures Hive Synapse as a local, filesystem-backed second brain that can be synced through Obsidian, Git, iCloud, Dropbox, or another file sync layer. The initial MVP assumes Markdown files are the canonical store; vector and database persistence can be added later as secondary indexes.

## 1. Choose the workspace location

Keep runtime code and personal context separate:

- `~/Workspace/hive-synapse/` — the Hive Synapse codebase.
- `~/Obsidian/HiveSecondBrain/` or another synced folder — your actual second-brain workspace.

Initialize the workspace:

```bash
cd ~/Workspace/hive-synapse
./bin/hive init ~/Obsidian/HiveSecondBrain
./bin/hive validate ~/Obsidian/HiveSecondBrain
```

If you want demo content for exploration:

```bash
./bin/hive init ~/Obsidian/HiveSecondBrain --fixture basic-org
```

## 2. Define the top-level organization

For a personal second brain, treat `org` as your personal operating system. Store mission, goals, tone, principles, and identity in the org charter:

```bash
./bin/hive node create org \
  --workspace ~/Obsidian/HiveSecondBrain \
  --kind organization \
  --title "Personal Operating System" \
  --actor human:you

./bin/hive charter update org \
  --workspace ~/Obsidian/HiveSecondBrain \
  --section mission \
  --mode replace \
  --text "Help me maintain clarity across projects, research, creative work, and personal goals without mixing unrelated domains." \
  --actor human:you

./bin/hive charter update org \
  --workspace ~/Obsidian/HiveSecondBrain \
  --section goals \
  --text "Keep current priorities visible; preserve history separately; promote only reusable knowledge upward." \
  --actor human:you
```

Human-editable files:

- `memory/records/nodes/org/CHARTER.md` — mission, goals, tone, soul, principles.
- `memory/records/nodes/org/CURRENT.md` — current operating context.
- `memory/records/nodes/org/HISTORY.md` — longitudinal context and superseded decisions.
- `memory/records/nodes/org/BRIEF.md` — generated compacted brief after compaction.

## 3. Create isolated domains or pods

Create sibling nodes for domains that should not automatically co-mingle:

```bash
./bin/hive node create domains/quant-trading \
  --workspace ~/Obsidian/HiveSecondBrain \
  --kind domain \
  --title "Quant Trading" \
  --parent org \
  --actor human:you

./bin/hive node create domains/philosophy \
  --workspace ~/Obsidian/HiveSecondBrain \
  --kind domain \
  --title "Philosophy" \
  --parent org \
  --actor human:you

./bin/hive node create domains/art \
  --workspace ~/Obsidian/HiveSecondBrain \
  --kind domain \
  --title "Art" \
  --parent org \
  --actor human:you
```

Isolation rule:

- An agent signed into `domains/quant-trading` receives `org` context plus `domains/quant-trading` context.
- It does not receive `domains/philosophy` or `domains/art` context unless an explicit shared edge is created.
- Shared context belongs in an edge, not in either private domain by default.

## 4. Define agents and roles

Assign humans or agents to home nodes:

```bash
./bin/hive actor assign agent:codex-quant-001 \
  --workspace ~/Obsidian/HiveSecondBrain \
  --home-node domains/quant-trading \
  --role research-analyst \
  --actor human:you

./bin/hive actor assign agent:claude-philosophy-001 \
  --workspace ~/Obsidian/HiveSecondBrain \
  --home-node domains/philosophy \
  --role synthesis-partner \
  --actor human:you
```

Each agent can keep private working memory under `memory/records/agents/<agent-id>/`, while reusable knowledge is compacted into candidate records and promoted through review workflows. Hive Synapse does not need to own the agent's entire private memory; it owns the shared organizational memory and the context packs agents must load at startup.

## 5. Sign agents in and hydrate context

Do not copy organization memory into the agent folder. Sign the actor in and let Hive Synapse compile the correct context pack from the hierarchy and graph:

```bash
./bin/hive actor signin agent:codex-quant-001 \
  --workspace ~/Obsidian/HiveSecondBrain \
  --require-assignment \
  --json
```

For an ad hoc actor without an assignment, provide the node and role explicitly:

```bash
./bin/hive actor signin agent:adhoc-research-001 \
  --workspace ~/Obsidian/HiveSecondBrain \
  --home-node domains/philosophy \
  --role research-partner
```

Sign-in creates `org/signins/<signin-id>.yaml`, compiles `memory/generated/context-packs/nodes/<node-id>/PACK.md`, and returns bootstrap instructions. The context pack includes:

- parent node charters, briefs, and current context from the top of the tree down to the actor's node;
- the actor's effective node charter, brief, and current context;
- active shared edge briefs and current context for explicitly connected cross-domain collaborations;
- dirty context warnings and a manifest with source paths and token estimates.

Long-running agents should refresh before important work or after upstream context changes:

```bash
./bin/hive actor refresh <signin-id> \
  --workspace ~/Obsidian/HiveSecondBrain
```

Two-way information flow:

- **Top-down:** org, department, team, and edge updates trigger context invalidation; the next sign-in or refresh recompiles the pack.
- **Bottom-up:** agents summarize their private work into import/candidate records, then use promotion workflows for team or org memory.
- **Lateral:** teams share bounded context only through explicit graph edges; unrelated domains remain isolated.
- **Audit:** sign-ins, refreshes, compactions, promotions, and context compiles are recorded under `memory/operations/`.

## 6. Configure LLM profiles

Initialize LLM policy and add profiles. Profiles are metadata and policy; credentials are referenced by environment variable names rather than stored as raw secrets.

```bash
./bin/hive llm init --workspace ~/Obsidian/HiveSecondBrain

./bin/hive llm credential add openai-default \
  --workspace ~/Obsidian/HiveSecondBrain \
  --provider openai \
  --api-key-env OPENAI_API_KEY \
  --organization-default

./bin/hive llm profile add gpt-default \
  --workspace ~/Obsidian/HiveSecondBrain \
  --provider openai \
  --model gpt-5.4 \
  --credential openai-default \
  --organization-default \
  --enable

./bin/hive llm config --workspace ~/Obsidian/HiveSecondBrain
```

For local or deterministic operation, use the built-in deterministic profile first and add network profiles only when you are ready to run real summarization/classification.

## 7. Add ingestion points

Every node has an import workspace:

- `memory/imports/<node-id>/inbox/` — drop files here.
- `memory/imports/<node-id>/items/` — import item metadata.
- `memory/imports/<node-id>/compacted/` — normalized summaries.
- `memory/imports/<node-id>/candidates/` — candidate memory created from imports.
- `memory/imports/<node-id>/reports/` — processing reports.

Examples:

```bash
./bin/hive import add domains/quant-trading ~/Downloads/trading-notes.md \
  --workspace ~/Obsidian/HiveSecondBrain \
  --actor human:you

./bin/hive import fetch domains/philosophy https://example.com/essay \
  --workspace ~/Obsidian/HiveSecondBrain \
  --connector url \
  --actor human:you
```

Processing flow:

```bash
./bin/hive import classify <import-id> --workspace ~/Obsidian/HiveSecondBrain
./bin/hive import compact <import-id> --workspace ~/Obsidian/HiveSecondBrain
./bin/hive import propose <import-id> --workspace ~/Obsidian/HiveSecondBrain
./bin/hive promote review <proposal-id> --workspace ~/Obsidian/HiveSecondBrain --decision approved --actor human:you --rationale "Reusable, source-backed context."
./bin/hive promote apply <proposal-id> --workspace ~/Obsidian/HiveSecondBrain --actor human:you
```

## 8. Create explicit cross-domain collaborations

Use edges when two domains need scoped shared memory. Example: quant trading and philosophy share a bounded collaboration on risk, decision-making, and epistemology:

```bash
./bin/hive edge create collaborations/risk-epistemology \
  --workspace ~/Obsidian/HiveSecondBrain \
  --kind collaboration \
  --title "Risk Epistemology" \
  --node domains/quant-trading \
  --node domains/philosophy \
  --summary "Shared context is limited to decision quality, uncertainty, risk framing, and epistemic hygiene." \
  --actor human:you
```

Edge files:

- `memory/graph/edges/collaborations/risk-epistemology.md` — graph relationship.
- `memory/records/edges/collaborations/risk-epistemology/CURRENT.md` — current shared context.
- `memory/records/edges/collaborations/risk-epistemology/HISTORY.md` — longitudinal shared context.
- `memory/records/edges/collaborations/risk-epistemology/BRIEF.md` — generated compacted edge brief.
- `memory/imports/edges/collaborations/risk-epistemology/inbox/` — shared ingestion inbox.

List edges:

```bash
./bin/hive edge list --workspace ~/Obsidian/HiveSecondBrain
./bin/hive edge list --workspace ~/Obsidian/HiveSecondBrain --node domains/quant-trading
```

## 9. Compact summaries and build context packs

Generate a node brief:

```bash
./bin/hive node compact domains/quant-trading \
  --workspace ~/Obsidian/HiveSecondBrain \
  --actor human:you
```

Generate an edge brief:

```bash
./bin/hive edge compact collaborations/risk-epistemology \
  --workspace ~/Obsidian/HiveSecondBrain \
  --actor human:you
```

Compile the startup context pack for an agent entering a node:

```bash
./bin/hive context compile domains/quant-trading \
  --workspace ~/Obsidian/HiveSecondBrain
```

Read:

- `memory/records/nodes/<node-id>/BRIEF.md` — compacted node summary.
- `memory/records/edges/<edge-id>/BRIEF.md` — compacted collaboration summary.
- `memory/generated/context-packs/nodes/<node-id>/PACK.md` — generated startup context for agents.
- `memory/generated/context-packs/nodes/<node-id>/MANIFEST.yaml` — sources, token estimate, and validation status.

## 10. Schedule recurring maintenance

Hive Synapse writes OS scheduler templates instead of running its own daemon. This keeps the runtime simple and auditable.

Cron template:

```bash
./bin/hive scheduler install cron \
  --workspace ~/Obsidian/HiveSecondBrain \
  --interval-minutes 15
```

Launchd template on macOS:

```bash
./bin/hive scheduler install launchd \
  --workspace ~/Obsidian/HiveSecondBrain \
  --interval-minutes 15
```

Templates are written to `local-overrides/schedulers/`. Install them only after reviewing paths and runtime commands. The scheduled loop runs:

1. `hive job watchdog --enqueue`
2. `hive job run`

You can enqueue explicit compaction work:

```bash
./bin/hive job enqueue node_compact domains/quant-trading \
  --workspace ~/Obsidian/HiveSecondBrain \
  --reason "scheduled domain rollup"

./bin/hive job enqueue edge_compact collaborations/risk-epistemology \
  --workspace ~/Obsidian/HiveSecondBrain \
  --reason "scheduled collaboration rollup"
```

## 11. View audit history and rollback surface

List recent operations:

```bash
./bin/hive operation list --workspace ~/Obsidian/HiveSecondBrain
```

Show one operation:

```bash
./bin/hive operation show <operation-id> --workspace ~/Obsidian/HiveSecondBrain
```

Preview rollback impact:

```bash
./bin/hive rollback preview <operation-id> --workspace ~/Obsidian/HiveSecondBrain
```

Use Git or your sync provider for hard rollback. Hive operation records tell you what changed, which files were touched, and whether the operation has a supported rollback strategy.

## 12. Validate and operate safely

Run this after major changes, sync events, or agent activity:

```bash
./bin/hive validate ~/Obsidian/HiveSecondBrain
./bin/hive job watchdog --workspace ~/Obsidian/HiveSecondBrain --enqueue
./bin/hive job run --workspace ~/Obsidian/HiveSecondBrain
```

Recommended second-brain routine:

1. Drop raw material into the correct node or edge import inbox.
2. Classify and compact imports into candidate records.
3. Promote only reusable, source-backed knowledge to shared context.
4. Compact node and edge briefs.
5. Compile context packs before agents start work.
6. Keep unrelated domains isolated unless an explicit edge defines a collaboration scope.
