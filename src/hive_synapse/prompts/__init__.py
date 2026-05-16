from __future__ import annotations

from .import_classify import IMPORT_CLASSIFY_PROMPT
from .import_compact import IMPORT_COMPACT_PROMPT
from .promotion_sweep import PROMOTION_SWEEP_PROMPT
from .registry import ALL_PROMPTS, get_prompt, prompt_catalog
from .session_prompts import (
    OPENCLAW_TOOLS_PROMPT,
    SESSION_BOOTSTRAP_PROMPT,
    SESSION_OUTBOX_README_PROMPT,
    SESSION_SOUL_PROMPT,
    SESSION_USER_PROMPT,
    SIGNIN_BOOTSTRAP_PROMPT,
)
from .types import ChatPromptSpec, PromptSpec, TextPromptSpec

__all__ = [
    "ALL_PROMPTS",
    "ChatPromptSpec",
    "IMPORT_CLASSIFY_PROMPT",
    "IMPORT_COMPACT_PROMPT",
    "OPENCLAW_TOOLS_PROMPT",
    "PROMOTION_SWEEP_PROMPT",
    "PromptSpec",
    "SESSION_BOOTSTRAP_PROMPT",
    "SESSION_OUTBOX_README_PROMPT",
    "SESSION_SOUL_PROMPT",
    "SESSION_USER_PROMPT",
    "SIGNIN_BOOTSTRAP_PROMPT",
    "TextPromptSpec",
    "get_prompt",
    "prompt_catalog",
]
