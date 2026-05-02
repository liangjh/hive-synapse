from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .frontmatter import read_markdown
from .models import EdgeRecord, NodeRecord
from .paths import WorkspacePaths


@dataclass(frozen=True)
class GraphImpact:
    target: str
    descendants: list[str]
    connected_edges: list[str]
    assigned_actors: list[str]
    context_packs: list[str]
    affected_targets: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "descendants": self.descendants,
            "connected_edges": self.connected_edges,
            "assigned_actors": self.assigned_actors,
            "context_packs": self.context_packs,
            "affected_targets": self.affected_targets,
        }


class MemoryGraph:
    def __init__(self, root: Path):
        self.paths = WorkspacePaths(root.resolve())
        self.paths.require_workspace()
        self.nodes = self._load_nodes()
        self.edges = self._load_edges()

    def _load_nodes(self) -> dict[str, NodeRecord]:
        nodes: dict[str, NodeRecord] = {}
        if not self.paths.graph_nodes.exists():
            return nodes
        for path in sorted(self.paths.graph_nodes.rglob("*.md")):
            data = read_markdown(path).frontmatter
            if data:
                node = NodeRecord.model_validate(data)
                nodes[node.id] = node
        return nodes

    def _load_edges(self) -> dict[str, EdgeRecord]:
        edges: dict[str, EdgeRecord] = {}
        if not self.paths.graph_edges.exists():
            return edges
        for path in sorted(self.paths.graph_edges.rglob("*.md")):
            data = read_markdown(path).frontmatter
            if data:
                edge = EdgeRecord.model_validate(data)
                edges[edge.id] = edge
        return edges

    def active_nodes(self) -> dict[str, NodeRecord]:
        return {node_id: node for node_id, node in self.nodes.items() if node.status == "active"}

    def parent_chain(self, node_id: str) -> list[str]:
        seen: set[str] = set()
        chain: list[str] = []

        def visit(current: str) -> None:
            node = self.nodes.get(current)
            if not node:
                return
            for parent in node.parents:
                if parent in seen:
                    continue
                seen.add(parent)
                visit(parent)
                chain.append(parent)

        visit(node_id)
        return chain

    def descendants(self, node_id: str) -> list[str]:
        children: dict[str, list[str]] = {}
        for node in self.active_nodes().values():
            for parent in node.parents:
                children.setdefault(parent, []).append(node.id)
        result: list[str] = []
        queue = sorted(children.get(node_id, []))
        while queue:
            child = queue.pop(0)
            if child in result:
                continue
            result.append(child)
            queue.extend(sorted(children.get(child, [])))
        return result

    def connected_edges(self, node_id: str) -> list[str]:
        return sorted(
            edge.id
            for edge in self.edges.values()
            if edge.status == "active" and node_id in edge.nodes
        )

    def edge_neighbor_nodes(self, node_id: str) -> list[str]:
        neighbors: set[str] = set()
        for edge in self.edges.values():
            if edge.status != "active" or node_id not in edge.nodes:
                continue
            neighbors.update(edge.nodes)
        neighbors.discard(node_id)
        return sorted(neighbors)

    def assigned_actors(self, node_id: str) -> list[str]:
        assignments = self.paths.root / "org" / "assignments"
        actors: list[str] = []
        if not assignments.exists():
            return actors
        for path in sorted(assignments.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if data.get("home_node") == node_id and data.get("status", "active") == "active":
                actors.append(str(data.get("actor")))
        return actors

    def impact(self, target: str) -> GraphImpact:
        descendants = self.descendants(target)
        edges = self.connected_edges(target)
        neighbors = self.edge_neighbor_nodes(target)
        affected_targets = sorted({target, *descendants, *neighbors})
        actors: list[str] = []
        for item in affected_targets:
            actors.extend(self.assigned_actors(item))
        pack_paths = [
            f"memory/generated/context-packs/nodes/{item}/PACK.md"
            for item in affected_targets
        ]
        return GraphImpact(
            target=target,
            descendants=descendants,
            connected_edges=edges,
            assigned_actors=sorted(set(actors)),
            context_packs=pack_paths,
            affected_targets=affected_targets,
        )
