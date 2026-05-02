from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from tests.support import (
    init_basic_workspace,
    json_from_stdout,
    read_markdown_file,
    run_hive,
    write_markdown_file,
)


def error_codes(report: dict[str, Any]) -> set[str]:
    return {error["code"] for error in report.get("errors", [])}


class ValidationContractsTests(unittest.TestCase):
    def test_validate_basic_org_fixture_succeeds_with_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))

            result = run_hive("validate", str(workspace), "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json_from_stdout(result)
            self.assertTrue(report["ok"], report)
            self.assertEqual(report["errors"], [])

    def test_validate_missing_workspace_config_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "not-initialized"
            workspace.mkdir()

            result = run_hive("validate", str(workspace), "--json")

            self.assertEqual(result.returncode, 1)
            report = json_from_stdout(result)
            self.assertFalse(report["ok"], report)
            self.assertIn("workspace.config_missing", error_codes(report))

    def test_validate_missing_source_refs_for_reviewed_shared_memory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            record_path = (
                workspace
                / "memory/records/nodes/departments/engineering/candidates/"
                "mem_demo_engineering_practice_001.md"
            )
            document = read_markdown_file(record_path)
            frontmatter = dict(document.frontmatter)
            frontmatter["authority"] = "reviewed"
            frontmatter["review"] = {
                "reviewer": "steward:engineering",
                "decision": "approved",
            }
            frontmatter["promotion"] = {"proposal": "promotion_demo_001"}
            frontmatter.pop("source_refs", None)
            write_markdown_file(record_path, frontmatter, document.body)

            result = run_hive("validate", str(workspace), "--json")

            self.assertEqual(result.returncode, 1)
            report = json_from_stdout(result)
            self.assertFalse(report["ok"], report)
            self.assertIn("guardrail.source_refs_required", error_codes(report))

    def test_validate_broken_edge_node_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            edge_path = workspace / "memory/graph/edges/engineering__marketing__project-launch-x.md"
            document = read_markdown_file(edge_path)
            frontmatter = dict(document.frontmatter)
            frontmatter["nodes"] = [*frontmatter["nodes"], "departments/missing"]
            write_markdown_file(edge_path, frontmatter, document.body)

            result = run_hive("validate", str(workspace), "--json")

            self.assertEqual(result.returncode, 1)
            report = json_from_stdout(result)
            self.assertFalse(report["ok"], report)
            self.assertIn("graph.edge_node_missing", error_codes(report))


if __name__ == "__main__":
    unittest.main()
