from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import WorkspaceError

WORKSPACE_CONFIG = "hive.config.yaml"

REQUIRED_DIRS = [
    "memory/imports",
    "memory/raw",
    "memory/records",
    "memory/graph/nodes",
    "memory/graph/edges",
    "memory/jobs/pending",
    "memory/jobs/claimed",
    "memory/jobs/completed",
    "memory/jobs/failed",
    "memory/state/context-dirty",
    "memory/state/leases",
    "memory/proposals",
    "memory/drift",
    "memory/conflicts",
    "memory/operations",
    "memory/generated/context-packs",
    "memory/generated/graph",
    "memory/audit",
    "memory/migrations",
    "memory/skills",
    "memory/backups",
    "org/members",
    "org/roles",
    "org/assignments",
    "org/signins",
    "personas",
    "policies",
    "policies/nodes",
    "local-overrides",
]

APPEND_FRIENDLY_DIRS = [
    "memory/records/agents",
    "memory/proposals",
    "memory/drift",
    "memory/conflicts",
    "memory/jobs/pending",
    "memory/imports",
    "memory/operations",
    "memory/audit",
    "memory/migrations",
    "memory/skills",
    "memory/backups",
]

CONTROLLED_WRITER_DIRS = [
    "memory/records/nodes",
    "memory/records/edges",
    "memory/graph",
    "memory/generated",
    "org/assignments",
    "policies",
    "policies/nodes",
]


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path

    @property
    def config(self) -> Path:
        return self.root / WORKSPACE_CONFIG

    @property
    def memory(self) -> Path:
        return self.root / "memory"

    @property
    def graph_nodes(self) -> Path:
        return self.root / "memory" / "graph" / "nodes"

    @property
    def graph_edges(self) -> Path:
        return self.root / "memory" / "graph" / "edges"

    @property
    def operations(self) -> Path:
        return self.root / "memory" / "operations"

    @property
    def context_dirty(self) -> Path:
        return self.root / "memory" / "state" / "context-dirty"

    def ensure_required_dirs(self) -> None:
        for rel in REQUIRED_DIRS:
            (self.root / rel).mkdir(parents=True, exist_ok=True)

    def require_workspace(self) -> None:
        if not self.config.exists():
            raise WorkspaceError(f"Missing {WORKSPACE_CONFIG} under {self.root}")


def find_workspace(start: Path | None = None) -> WorkspacePaths:
    current = (start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / WORKSPACE_CONFIG).exists():
            return WorkspacePaths(candidate)
    raise WorkspaceError(f"Could not find {WORKSPACE_CONFIG} from {current}")


def target_to_path_fragment(target: str) -> Path:
    return Path(*[part for part in target.split("/") if part])
