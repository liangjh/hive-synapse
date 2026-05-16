from __future__ import annotations

from .types import ChatPromptSpec

IMPORT_CLASSIFY_PROMPT = ChatPromptSpec(
    id="import_classify",
    version="v1",
    purpose="Classify imported source material before it enters memory workflows.",
    system_template=(
        "Classify imported memory for a workspace. Return only JSON with topics, "
        "temporal_status, sensitivity, and optional rationale. Do not invent facts "
        "beyond the supplied text."
    ),
    user_template=(
        "Import id: {import_id}\n"
        "Target: {target}\n"
        "Source type: {source_type}\n\n"
        "Text:\n{text}"
    ),
    expected_output=(
        "JSON object with topics, temporal_status, sensitivity, and optional rationale."
    ),
    safety_notes="Source-grounded classification only; no durable memory is published here.",
)
