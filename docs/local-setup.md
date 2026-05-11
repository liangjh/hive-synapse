# Local Setup Guide

This guide is for setting up Hive Synapse on a local machine once the MVP is close enough to use with real personal or team context. For a disposable demo, use [Getting Started](getting-started.md).

## Setup Model

Keep runtime code separate from organization memory:

```text
~/Workspace/hive-synapse/      # runtime code, CLI, docs, tests
~/Obsidian/HiveSecondBrain/    # canonical synced organization workspace
```

Any filesystem sync layer can hold the workspace. Obsidian is recommended for human visibility, but Hive only assumes normal files and directories. Do not put a real workspace inside the runtime repository unless you intentionally want that local memory mixed with source control.

## Prerequisites

- Python 3.11 or newer
- Git
- `uv` recommended, but not required
- Optional: Obsidian or another Markdown editor for inspecting the workspace
- Optional: an LLM provider key or local OpenAI-compatible model server

The core runtime currently has no required third-party dependencies. The optional `llm` extra installs LiteLLM for broader provider coverage.

## 1. Install the CLI

From a source checkout:

```bash
git clone <hive-synapse-repo-url>
cd hive-synapse
./bin/hive --help
```

With `uv`:

```bash
uv run hive --help
```

With a Python virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
hive --help
```

If you want the optional LiteLLM adapter:

```bash
uv sync --extra llm
```

or:

```bash
python -m pip install -e ".[llm]"
```

For contributor checkouts, install the same Ruff hooks that CI expects:

```bash
uv run --extra dev pre-commit install
uv run --extra dev pre-commit run --all-files
```

## 2. Create a Workspace

Start with a fixture workspace to verify the installation:

```bash
./bin/hive init /tmp/hive-demo --fixture basic-org
./bin/hive validate /tmp/hive-demo
./bin/hive context compile departments/engineering --workspace /tmp/hive-demo
```

Then create a real local workspace outside the repo. For Obsidian, use a folder inside your vault:

```bash
export HIVE_WORKSPACE="$HOME/Obsidian/HiveSecondBrain"
mkdir -p "$(dirname "$HIVE_WORKSPACE")"
./bin/hive init "$HIVE_WORKSPACE"
./bin/hive validate "$HIVE_WORKSPACE"
```

Use `--fixture basic-org` for a realistic starter graph. Use no fixture for a cleaner workspace.

## 3. Inspect Workspace Policy

```bash
./bin/hive policy show --workspace "$HIVE_WORKSPACE"
```

Fresh workspaces use low-noise defaults. Context invalidation is observed unless an explicit command or stricter policy writes dirty markers. Promotion sweeps are manual, watchdogs report only, and import sync is manual.

Before relying on automation, review:

```text
$HIVE_WORKSPACE/policies/operations.yaml
$HIVE_WORKSPACE/policies/context-budget.yaml
```

For stricter local behavior, set operation policy intentionally rather than relying on prompt instructions.

## 4. Configure Optional LLM Execution

LLMs are disabled by default. Deterministic behavior remains the safe fallback.

Create the policy and credential registry:

```bash
./bin/hive llm init --workspace "$HIVE_WORKSPACE"
./bin/hive llm providers
./bin/hive llm config --workspace "$HIVE_WORKSPACE"
```

Provider configuration lives in:

```text
$HIVE_WORKSPACE/policies/llm.yaml
$HIVE_WORKSPACE/policies/credentials.yaml
```

Secrets should stay in environment variables or an external secret store. Do not write API keys into memory records, policy files, operation logs, or context packs.

Example remote provider profile:

```bash
export OPENAI_API_KEY="<your-key>"
./bin/hive llm credential add openai-local \
  --workspace "$HIVE_WORKSPACE" \
  --provider openai \
  --api-key-env OPENAI_API_KEY

./bin/hive llm profile add openai-general \
  --workspace "$HIVE_WORKSPACE" \
  --provider openai \
  --model "<model-name>" \
  --credential openai-local \
  --enable \
  --allow-network-models \
  --organization-default
```

Example local OpenAI-compatible profile:

```bash
./bin/hive llm profile add local-compatible \
  --workspace "$HIVE_WORKSPACE" \
  --provider openai_compatible \
  --base-url http://localhost:11434/v1 \
  --model "<local-model-name>" \
  --enable \
  --organization-default
```

You can also force one operation to use a profile:

```bash
./bin/hive import compact <import-id> \
  --workspace "$HIVE_WORKSPACE" \
  --llm-profile local-compatible
```

Model-backed flows currently assist import classification, import compaction, and promotion sweep recommendations. They create candidate memory, proposals, advisories, and model-run records; they do not publish shared memory directly.

## 5. Add Initial Memory Sources

Import existing notes and documents through staging, not by editing generated context packs.

```bash
./bin/hive import add departments/engineering /path/to/source.md \
  --workspace "$HIVE_WORKSPACE" \
  --json
```

Then move the import through the governed flow:

```bash
./bin/hive import classify <import-id> --workspace "$HIVE_WORKSPACE"
./bin/hive import compact <import-id> --workspace "$HIVE_WORKSPACE"
./bin/hive import propose <import-id> --workspace "$HIVE_WORKSPACE"
```

Review before publishing:

```bash
./bin/hive promote list --workspace "$HIVE_WORKSPACE"
./bin/hive promote review <proposal-id> \
  --workspace "$HIVE_WORKSPACE" \
  --decision approved \
  --actor steward:local \
  --rationale "source-backed local setup seed"
./bin/hive promote apply <proposal-id> \
  --workspace "$HIVE_WORKSPACE" \
  --actor steward:local
```

This keeps raw evidence, candidate memory, review decisions, and published current memory inspectable.

## 6. Create Departments, Assign Agents, and Sign In

Create an organization and a first department if you did not use the fixture:

```bash
./bin/hive node create org --workspace "$HIVE_WORKSPACE" --kind organization --title "Personal Operating System" --actor human:you
./bin/hive node create departments/research --workspace "$HIVE_WORKSPACE" --kind department --title "Research" --parent org --actor human:you
```

Assign an agent to a home node:

```bash
./bin/hive actor assign agent:research-001 \
  --workspace "$HIVE_WORKSPACE" \
  --home-node departments/research \
  --role research-partner \
  --actor human:you
```

Sign the agent in to generate scoped startup context:

```bash
./bin/hive actor signin agent:research-001 \
  --workspace "$HIVE_WORKSPACE" \
  --require-assignment \
  --json
```

Generated context appears under:

```text
$HIVE_WORKSPACE/memory/generated/context-packs/
```

Agents should load the returned `context_pack` path. They should not import the full Hive workspace unless you explicitly grant that broader filesystem access. Before shared writes, check freshness:

```bash
./bin/hive context status departments/research --workspace "$HIVE_WORKSPACE"
```

Adapter wrappers live under `adapters/`, and portable skills live under `skills/hive/`, but the canonical behavior is the CLI/MCP surface. Do not copy memory semantics into agent-specific prompts.

## 7. Run Maintenance

Use a small routine before and after meaningful changes:

```bash
./bin/hive validate "$HIVE_WORKSPACE"
./bin/hive backup create "$HIVE_WORKSPACE"
./bin/hive job watchdog --workspace "$HIVE_WORKSPACE"
./bin/hive upgrade doctor --workspace "$HIVE_WORKSPACE"
```

If jobs are pending:

```bash
./bin/hive job list --workspace "$HIVE_WORKSPACE"
./bin/hive job run --workspace "$HIVE_WORKSPACE"
```

Backups live inside the workspace under `memory/backups/`. Rollback preview is read-only in the current implementation.

## 8. Install Agent Skills and Use Agent Harnesses

Install portable Hive skills or commands:

```bash
scripts/install-agent-skills.py codex
scripts/install-agent-skills.py claude
scripts/install-agent-skills.py generic --target ./agent-skills
```

Use the generic target for Hermes, OpenClaw, or other harnesses. See `docs/agent-interoperability.md` for harness-specific notes.

List the MCP-compatible tools:

```bash
./bin/hive mcp tools
```

Fetch a context pack through the tool surface:

```bash
./bin/hive mcp call get_context_pack \
  --workspace "$HIVE_WORKSPACE" \
  --args-json '{"target":"departments/research"}'
```

Use this surface for Codex, Claude, Hermes, OpenClaw, Cursor, ChatGPT, or custom runners when you want harness-neutral access.

## 9. Local Safety Rules

- Keep real workspace data outside the runtime repo.
- Validate before and after mutating workflows.
- Treat `memory/generated/` as rebuildable output.
- Publish through proposals and authorized apply commands.
- Store secrets in environment variables, not YAML or Markdown memory.
- Start with manual or observed automation, then tighten policy after the workspace is understandable.
- Keep raw imports and source refs; they are the evidence trail for future debugging.

## 10. Feature-Completion Gate

Before using this for important local work, confirm:

```bash
./bin/hive --help
./bin/hive validate "$HIVE_WORKSPACE"
./bin/hive mcp tools
./bin/hive llm config --workspace "$HIVE_WORKSPACE"
```

Also review [Implementation Backlog](implementation-backlog.md), [Implementation Test Plan](implementation-test-plan.md), and the README feature matrix for remaining gaps. In the current slice, import LLM flows, promotion advisories, actor sign-in, node/edge compaction, scheduler templates, and adapter skills are wired. Rollback apply, authenticated Notion/GDrive sync, vector/relational persistence, hard actor write-scope enforcement, and per-agent filesystem projections remain future work.
