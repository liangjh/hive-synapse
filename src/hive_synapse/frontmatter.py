from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import simple_yaml as yaml


@dataclass(frozen=True)
class MarkdownDocument:
    frontmatter: dict[str, Any]
    body: str


def read_markdown(path: Path) -> MarkdownDocument:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return MarkdownDocument({}, text)
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return MarkdownDocument({}, text)
    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        data = {}
    return MarkdownDocument(data, parts[2])


def dump_markdown(frontmatter: dict[str, Any], body: str) -> str:
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    clean_body = body.strip() + "\n"
    return f"---\n{yaml_text}\n---\n\n{clean_body}"


def write_markdown(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    from .fs import atomic_write_text

    atomic_write_text(path, dump_markdown(frontmatter, body))
