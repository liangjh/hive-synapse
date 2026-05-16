# Prompt Audit Guide

Hive Synapse keeps model-facing prompts and generated agent instructions in one Python package:

```text
src/hive_synapse/prompts/
  import_classify.py
  import_compact.py
  promotion_sweep.py
  session_prompts.py
  registry.py
  types.py
```

The goal is simple: a human can audit the text that influences LLM reasoning without hunting through workflow code.

## Prompt Types

- `ChatPromptSpec`: prompts sent to model providers through `generate_structured`.
- `TextPromptSpec`: generated agent-facing instructions such as session bootstraps and outbox guidance.

Each prompt has:

- stable `id`;
- explicit `version`;
- `purpose`;
- optional `safety_notes`;
- template text.

## Current Prompt Registry

The registry lives in `src/hive_synapse/prompts/registry.py`. It includes:

- `import_classify.v1`: classifies imported source material.
- `import_compact.v1`: summarizes imports into candidate memory.
- `promotion_sweep.v1`: evaluates candidate memory for promotion proposals.
- `session_outbox_readme.v1`: tells agents how to emit `memory-delta.jsonl`.
- `session_bootstrap.v1`: renders generated `AGENTS.md` / `CLAUDE.md` style session bootstraps.
- `session_soul.v1`: renders generated `SOUL.md` session identity.
- `session_user.v1`: renders generated `USER.md` session instructions.
- `openclaw_tools.v1`: renders generated OpenClaw `TOOLS.md`.
- `actor_signin_bootstrap.v1`: renders direct sign-in instructions.

## Runtime Metadata

Model calls pass `prompt_id` and `prompt_version` into the LLM request. LLM run records under `memory/generated/llm-runs/` persist that metadata, so an output can be traced back to the prompt version that produced it.

## Guardrail Test

`tests/test_prompt_registry.py` fails if workflow modules call `generate_structured(..., messages=[...])` with inline message literals. New model prompts should be added to `src/hive_synapse/prompts/` and referenced by ID/version from callers.
