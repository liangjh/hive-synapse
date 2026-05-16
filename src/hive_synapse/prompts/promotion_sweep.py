from __future__ import annotations

from .types import ChatPromptSpec

PROMOTION_SWEEP_PROMPT = ChatPromptSpec(
    id="promotion_sweep",
    version="v1",
    purpose="Evaluate whether candidate memory is ready for a promotion proposal.",
    system_template=(
        "Judge whether candidate memory is ready to be proposed for promotion. Return "
        "only JSON with recommended, confidence, rationale, risk_flags, "
        "missing_evidence, and optional recommended_target_scope. Be conservative when "
        "evidence is missing or text appears conflicted."
    ),
    user_template=(
        "Candidate metadata:\n{candidate_metadata}\n\n"
        "Candidate body:\n{candidate_body}"
    ),
    expected_output=(
        "JSON object with recommended, confidence, rationale, risk_flags, "
        "missing_evidence, and optional recommended_target_scope."
    ),
    safety_notes="Advisory only; authorized review/apply is still required.",
)
