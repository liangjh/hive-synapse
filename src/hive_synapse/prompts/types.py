"""Prompt spec types.

Module guide:
- `PromptSpec` stores common prompt ID, version, purpose, and safety metadata.
- `ChatPromptSpec` renders model chat messages.
- `TextPromptSpec` renders generated instruction/document templates.

Maintenance: update this guide when adding public prompt classes or helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PromptKind = Literal["chat", "text"]


@dataclass(frozen=True)
class PromptSpec:
    id: str
    version: str
    kind: PromptKind
    purpose: str
    safety_notes: str = ""

    @property
    def full_id(self) -> str:
        return f"{self.id}.{self.version}"

    def audit_record(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "full_id": self.full_id,
            "kind": self.kind,
            "purpose": self.purpose,
            "safety_notes": self.safety_notes,
        }


@dataclass(frozen=True)
class ChatPromptSpec(PromptSpec):
    system_template: str = ""
    user_template: str = ""
    expected_output: str = ""

    def __init__(
        self,
        *,
        id: str,
        version: str,
        purpose: str,
        system_template: str,
        user_template: str,
        expected_output: str,
        safety_notes: str = "",
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "kind", "chat")
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "safety_notes", safety_notes)
        object.__setattr__(self, "system_template", system_template)
        object.__setattr__(self, "user_template", user_template)
        object.__setattr__(self, "expected_output", expected_output)

    def render_messages(self, **kwargs: Any) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_template.format(**kwargs)},
            {"role": "user", "content": self.user_template.format(**kwargs)},
        ]

    def audit_record(self) -> dict[str, Any]:
        record = super().audit_record()
        record.update(
            {
                "system_template": self.system_template,
                "user_template": self.user_template,
                "expected_output": self.expected_output,
            }
        )
        return record


@dataclass(frozen=True)
class TextPromptSpec(PromptSpec):
    template: str = ""

    def __init__(
        self,
        *,
        id: str,
        version: str,
        purpose: str,
        template: str,
        safety_notes: str = "",
    ) -> None:
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "kind", "text")
        object.__setattr__(self, "purpose", purpose)
        object.__setattr__(self, "safety_notes", safety_notes)
        object.__setattr__(self, "template", template)

    def render(self, **kwargs: Any) -> str:
        return self.template.format(**kwargs)

    def audit_record(self) -> dict[str, Any]:
        record = super().audit_record()
        record["template"] = self.template
        return record
