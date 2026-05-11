from __future__ import annotations

from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .frontmatter import read_markdown
from .guardrails import validate_generated_artifact, validate_memory_guardrails
from .models import EdgeRecord, MemoryRecord, ModelValidationError, NodeRecord, ValidationReport
from .paths import REQUIRED_DIRS, WorkspacePaths

SHARED_AUTHORITIES = {"candidate", "reviewed", "published"}


def _load_frontmatter_records(paths: list[Path]) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        doc = read_markdown(path)
        if doc.frontmatter:
            records.append((path, doc.frontmatter))
    return records


def validate_workspace(root: Path) -> ValidationReport:
    paths = WorkspacePaths(root.resolve())
    report = ValidationReport(ok=True)

    if not paths.config.exists():
        report.add_error("workspace.config_missing", "Missing hive.config.yaml", str(paths.config))
        return report

    for rel in REQUIRED_DIRS:
        path = paths.root / rel
        if not path.exists():
            report.add_error(
                "workspace.required_dir_missing", f"Missing required directory: {rel}", str(path)
            )

    nodes: dict[str, NodeRecord] = {}
    for path, data in _load_frontmatter_records(list(paths.graph_nodes.rglob("*.md"))):
        try:
            node = NodeRecord.model_validate(data)
            if node.id in nodes:
                report.add_error("graph.duplicate_node", f"Duplicate node id {node.id}", str(path))
            nodes[node.id] = node
        except ModelValidationError as exc:
            report.add_error("graph.invalid_node", str(exc), str(path))

    edges: dict[str, EdgeRecord] = {}
    for path, data in _load_frontmatter_records(list(paths.graph_edges.rglob("*.md"))):
        try:
            edge = EdgeRecord.model_validate(data)
            if edge.id in edges:
                report.add_error("graph.duplicate_edge", f"Duplicate edge id {edge.id}", str(path))
            edges[edge.id] = edge
            for node_id in edge.nodes:
                if node_id not in nodes:
                    report.add_error(
                        "graph.edge_node_missing",
                        f"Edge {edge.id} references missing node {node_id}",
                        str(path),
                    )
        except ModelValidationError as exc:
            report.add_error("graph.invalid_edge", str(exc), str(path))

    seen_record_ids: dict[str, Path] = {}
    record_paths = [
        path
        for path in (paths.root / "memory" / "records").rglob("*.md")
        if path.name not in {"CURRENT.md", "HISTORY.md"}
    ]
    for path, data in _load_frontmatter_records(record_paths):
        try:
            record = MemoryRecord.model_validate(data)
            if record.id in seen_record_ids:
                report.add_error(
                    "memory.duplicate_id", f"Duplicate memory id {record.id}", str(path)
                )
            seen_record_ids[record.id] = path
            if record.node and record.node not in nodes:
                report.add_error(
                    "memory.node_missing",
                    f"Memory {record.id} references missing node {record.node}",
                    str(path),
                )
            if record.edge and record.edge not in edges:
                report.add_error(
                    "memory.edge_missing",
                    f"Memory {record.id} references missing edge {record.edge}",
                    str(path),
                )
            validate_memory_guardrails(
                path=path, data=data, body=read_markdown(path).body, report=report
            )
        except ModelValidationError as exc:
            report.add_error("memory.invalid_record", str(exc), str(path))

    _detect_duplicate_yaml_ids(paths, report)
    _detect_sync_conflicts(paths, report)
    _validate_generated_artifacts(paths, report)
    return report


def _detect_duplicate_yaml_ids(paths: WorkspacePaths, report: ValidationReport) -> None:
    seen: dict[str, Path] = {}
    for path in paths.root.rglob("*.yaml"):
        if ".git" in path.parts:
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            report.add_error("yaml.parse_failed", f"Could not parse YAML: {exc}", str(path))
            continue
        if not isinstance(data, dict) or "id" not in data:
            continue
        item_id = str(data["id"])
        if item_id in seen:
            report.add_error("workspace.duplicate_id", f"Duplicate id {item_id}", str(path))
        seen[item_id] = path


def _detect_sync_conflicts(paths: WorkspacePaths, report: ValidationReport) -> None:
    markers = ["conflict", "conflicted copy", "sync conflict"]
    for path in paths.root.rglob("*"):
        if not path.is_file():
            continue
        if str(path.relative_to(paths.root)).startswith("memory/conflicts/"):
            continue
        lower = path.name.lower()
        if any(marker in lower for marker in markers):
            report.add_error(
                "workspace.sync_conflict", "Potential sync conflict file detected", str(path)
            )


def _validate_generated_artifacts(paths: WorkspacePaths, report: ValidationReport) -> None:
    generated = paths.root / "memory" / "generated"
    if not generated.exists():
        return
    for path in generated.rglob("*.md"):
        validate_generated_artifact(path, report)
