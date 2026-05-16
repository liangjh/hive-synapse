"""Import compaction prompt definition.

Module guide:
- `IMPORT_COMPACT_PROMPT` is the versioned chat prompt for candidate-memory summaries.

Maintenance: update this guide when adding public prompt specs to this module.
"""

from __future__ import annotations

from .types import ChatPromptSpec

IMPORT_COMPACT_PROMPT = ChatPromptSpec(
    id="import_compact",
    version="v1",
    purpose="Summarize imported source material into concise candidate memory.",
    system_template=(
        "Summarize imported source text into concise candidate memory. Return only JSON "
        "with summary, confidence, tags, optional sensitivity, and optional rationale. "
        "Preserve source-grounded facts and avoid invention."
    ),
    user_template=(
        "Import id: {import_id}\n"
        "Target node: {target}\n"
        "Classification: {classification}\n\n"
        "Text:\n{text}"
    ),
    expected_output=(
        "JSON object with summary, confidence, tags, optional sensitivity, and optional rationale."
    ),
    safety_notes="Produces candidate memory only; promotion review is required for publication.",
)
