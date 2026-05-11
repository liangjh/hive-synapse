from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PersistenceBackend:
    name: str
    status: str
    canonical: bool
    description: str
    notes: str


BACKENDS = [
    PersistenceBackend(
        "filesystem-markdown",
        "available",
        True,
        "Canonical Markdown/YAML workspace backend.",
        "Source of truth for MVP; Obsidian/Git friendly.",
    ),
    PersistenceBackend(
        "json-index",
        "generated",
        False,
        "Generated JSON index backend.",
        "Rebuildable from Markdown records; not source of truth.",
    ),
    PersistenceBackend(
        "vector-db",
        "planned",
        False,
        "Vector retrieval backend for semantic recall.",
        "Future cache/index fed from canonical records and manifests.",
    ),
    PersistenceBackend(
        "relational-db",
        "planned",
        False,
        "Relational backend for audit/query/reporting.",
        "Future projection fed from operation records and schemas.",
    ),
    PersistenceBackend(
        "temporal-graph-db",
        "planned",
        False,
        "Temporal graph backend for longitudinal claims and conflicts.",
        "Future projection fed from memory records, edges, conflicts, and drift records.",
    ),
]


def list_backends() -> dict[str, Any]:
    return {"ok": True, "backends": [backend.__dict__ for backend in BACKENDS]}
