"""Connector registry for import source references.

Module guide:
- `ConnectorSpec` describes supported import connector metadata.
- `list_connectors` returns connector registry entries.
- `classify_connector` and `external_ref_for` normalize import references.

Maintenance: update this guide when adding public functions/classes to this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ConnectorSpec:
    name: str
    description: str
    auth: str
    modes: list[str]


CONNECTORS = {
    "local": ConnectorSpec(
        "local", "Local file or text import connector.", "none", ["copy_file", "preserve_text"]
    ),
    "obsidian": ConnectorSpec(
        "obsidian",
        "Obsidian vault/folder connector using local filesystem paths.",
        "none",
        ["copy_file", "folder_inventory"],
    ),
    "url": ConnectorSpec(
        "url",
        "URL connector preserving external references; network fetch is explicit future work.",
        "none",
        ["external_ref"],
    ),
    "git": ConnectorSpec(
        "git",
        "Git repository connector preserving clone/fetch references.",
        "env_or_ssh_agent",
        ["external_ref"],
    ),
    "github": ConnectorSpec(
        "github",
        "GitHub connector preserving repo, issue, PR, or file references.",
        "GITHUB_TOKEN optional",
        ["external_ref"],
    ),
    "notion": ConnectorSpec(
        "notion",
        "Notion connector preserving page/database references for later authenticated fetch.",
        "NOTION_TOKEN",
        ["external_ref"],
    ),
    "gdrive": ConnectorSpec(
        "gdrive",
        "Google Drive connector preserving file/document references for later authenticated fetch.",
        "GOOGLE_APPLICATION_CREDENTIALS or OAuth",
        ["external_ref"],
    ),
}


def list_connectors() -> dict[str, Any]:
    return {"ok": True, "connectors": [spec.__dict__ for spec in CONNECTORS.values()]}


def classify_connector(ref: str, explicit: str | None = None) -> str:
    if explicit:
        if explicit not in CONNECTORS:
            raise ValueError(f"Unknown connector: {explicit}")
        return explicit
    path = Path(ref).expanduser()
    if path.exists():
        return "local"
    parsed = urlparse(ref)
    host = parsed.netloc.lower()
    if "notion." in host:
        return "notion"
    if "drive.google." in host or "docs.google." in host:
        return "gdrive"
    if "github." in host:
        return "github"
    if parsed.scheme in {"http", "https"}:
        return "url"
    if ref.startswith("git@") or ref.endswith(".git"):
        return "git"
    return "url"


def external_ref_for(connector: str, ref: str) -> dict[str, Any]:
    parsed = urlparse(ref)
    result: dict[str, Any] = {"connector": connector, "ref": ref}
    if parsed.scheme:
        result.update({"scheme": parsed.scheme, "host": parsed.netloc, "path": parsed.path})
    if connector == "github":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            result.update({"owner": parts[0], "repo": parts[1]})
    return result
