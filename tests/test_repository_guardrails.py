from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def env() -> dict[str, str]:
    result = os.environ.copy()
    result["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + result.get("PYTHONPATH", "")
    return result


def run_hive(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "hive_synapse.cli", *args],
        cwd=ROOT,
        env=env(),
        text=True,
        capture_output=True,
        check=False,
    )


class RepositoryGuardrailTests(unittest.TestCase):
    def test_validate_detects_missing_edge_node(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            edge = workspace / "memory/graph/edges/engineering__marketing__project-launch-x.md"
            edge.write_text(
                edge.read_text().replace("departments/marketing", "departments/missing")
            )
            result = run_hive("validate", str(workspace), "--json")
            self.assertNotEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            codes = {issue["code"] for issue in report["errors"]}
            self.assertIn("graph.edge_node_missing", codes)

    def test_context_status_reports_dirty_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            result = run_hive(
                "context",
                "status",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["stale"])
            self.assertTrue(payload["dirty_markers"])

    def test_backup_and_rollback_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            backup = run_hive("backup", "create", str(workspace), "--json")
            self.assertEqual(backup.returncode, 0, backup.stderr)
            payload = json.loads(backup.stdout)
            self.assertTrue(Path(payload["manifest"]).exists())
            preview = run_hive(
                "rollback",
                "preview",
                payload["operation"],
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(preview.returncode, 0, preview.stderr)
            preview_payload = json.loads(preview.stdout)
            self.assertTrue(preview_payload["ok"])
            self.assertFalse(preview_payload["mutates"])


if __name__ == "__main__":
    unittest.main()
