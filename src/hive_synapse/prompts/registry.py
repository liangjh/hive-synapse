from __future__ import annotations

from typing import Any

from .import_classify import IMPORT_CLASSIFY_PROMPT
from .import_compact import IMPORT_COMPACT_PROMPT
from .promotion_sweep import PROMOTION_SWEEP_PROMPT
from .session_prompts import (
    OPENCLAW_TOOLS_PROMPT,
    SESSION_BOOTSTRAP_PROMPT,
    SESSION_OUTBOX_README_PROMPT,
    SESSION_SOUL_PROMPT,
    SESSION_USER_PROMPT,
    SIGNIN_BOOTSTRAP_PROMPT,
)
from .types import PromptSpec

ALL_PROMPTS: tuple[PromptSpec, ...] = (
    IMPORT_CLASSIFY_PROMPT,
    IMPORT_COMPACT_PROMPT,
    PROMOTION_SWEEP_PROMPT,
    SESSION_OUTBOX_README_PROMPT,
    SESSION_BOOTSTRAP_PROMPT,
    SESSION_SOUL_PROMPT,
    SESSION_USER_PROMPT,
    OPENCLAW_TOOLS_PROMPT,
    SIGNIN_BOOTSTRAP_PROMPT,
)


def prompt_catalog() -> list[dict[str, Any]]:
    return [prompt.audit_record() for prompt in ALL_PROMPTS]


def get_prompt(prompt_id: str) -> PromptSpec:
    for prompt in ALL_PROMPTS:
        if prompt.id == prompt_id or prompt.full_id == prompt_id:
            return prompt
    raise KeyError(f"Unknown prompt: {prompt_id}")
