# Local Setup Checklist

Use this checklist for a real local Hive Synapse install using Obsidian or another filesystem sync layer.

## Runtime

- [ ] Install Python 3.11 or newer.
- [ ] Clone the runtime repository into a code directory such as `$HOME/Workspace/hive-synapse`.
- [ ] Run `./bin/hive --help`.
- [ ] Optional: run `uv sync --extra llm` for LiteLLM support.
- [ ] Optional: install editable package with `python -m pip install -e .`.
- [ ] Optional: install local hooks with `uv run --extra dev pre-commit install`.

## Workspace

- [ ] Choose a workspace path outside the repo, such as `$HOME/Obsidian/HiveSecondBrain`.
- [ ] Export `HIVE_WORKSPACE="$HOME/Obsidian/HiveSecondBrain"`.
- [ ] Run `./bin/hive init "$HIVE_WORKSPACE"`.
- [ ] Run `./bin/hive validate "$HIVE_WORKSPACE"`.
- [ ] Inspect `policies/operations.yaml` and `policies/context-budget.yaml`.
- [ ] Create the first backup with `./bin/hive backup create "$HIVE_WORKSPACE"`.

## Organization Structure

- [ ] Create or confirm the top node: `hive node create org ...`.
- [ ] Update org charter mission/goals/tone with `hive charter update org ...`.
- [ ] Create first departments/teams with `hive node create departments/<name> --parent org ...`.
- [ ] Create explicit shared edges only where cross-domain context should flow.
- [ ] Run `hive node compact <node>` after meaningful current-memory updates.

## LLMs

- [ ] Run `./bin/hive llm init --workspace "$HIVE_WORKSPACE"`.
- [ ] Choose deterministic, local, or remote model execution.
- [ ] Store provider secrets in environment variables only.
- [ ] Run `./bin/hive llm config --workspace "$HIVE_WORKSPACE"`.
- [ ] Test one model-backed `import compact` or `promote sweep` before enabling broader use.

## Agent Skills and Interop

- [ ] Install Codex skills if using Codex: `scripts/install-agent-skills.py codex`.
- [ ] Install Claude commands if using Claude: `scripts/install-agent-skills.py claude`.
- [ ] Install generic skills for Hermes/OpenClaw/custom agents: `scripts/install-agent-skills.py generic --target <agent-skill-dir>`.
- [ ] Read `docs/agent-interoperability.md` for harness-specific setup notes.
- [ ] Confirm the target agent can execute `hive --help`.

## Agent Use

- [ ] Decide the home node for each agent.
- [ ] Assign each agent with `hive actor assign <actor-id> --home-node <node> ...`.
- [ ] Sign each agent in with `hive actor signin <actor-id> --require-assignment --json`.
- [ ] Configure the agent to load only the returned `context_pack`.
- [ ] Use `hive actor refresh <signin-id>` for long-running agents.
- [ ] Avoid giving agents direct write access to parent org/department memory unless explicitly trusted.

## Initial Memory

- [ ] Add one source document with `hive import add`.
- [ ] Classify, compact, and propose the import.
- [ ] Review the proposal with an authorized actor.
- [ ] Apply the proposal only after confirming source refs.
- [ ] Compile/sign in again after promotion or compaction.

## Maintenance

- [ ] Install scheduler template if desired: `hive scheduler install cron|launchd --workspace "$HIVE_WORKSPACE"`.
- [ ] Run `hive job watchdog --workspace "$HIVE_WORKSPACE" --enqueue`.
- [ ] Run `hive job run --workspace "$HIVE_WORKSPACE"` until expected jobs complete.
- [ ] Review operations with `hive operation list --workspace "$HIVE_WORKSPACE"`.

## Readiness

- [ ] `hive validate "$HIVE_WORKSPACE"` passes.
- [ ] `hive mcp tools` lists expected tools.
- [ ] `hive job watchdog` reports no urgent issues.
- [ ] `hive upgrade doctor` reports no migration blockers.
- [ ] README feature matrix gaps are acceptable for your local use case.
