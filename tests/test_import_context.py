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


class ImportContextTests(unittest.TestCase):
    def test_import_pipeline_creates_candidate_and_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            workspace = temp / "workspace"
            source = temp / "source.md"
            source.write_text("# Practice Note\n\nCurrent engineering project practice.")
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)

            add = run_hive("import", "add", "departments/engineering", str(source), "--workspace", str(workspace), "--json")
            self.assertEqual(add.returncode, 0, add.stderr)
            import_id = json.loads(add.stdout)["import_id"]

            classify = run_hive("import", "classify", import_id, "--workspace", str(workspace), "--json")
            self.assertEqual(classify.returncode, 0, classify.stderr)
            self.assertIn("practice", json.loads(classify.stdout)["classification"]["topics"])

            compact = run_hive("import", "compact", import_id, "--workspace", str(workspace), "--json")
            self.assertEqual(compact.returncode, 0, compact.stderr)
            candidate_id = json.loads(compact.stdout)["candidate_id"]
            candidate_paths = list((workspace / "memory/records/nodes/departments/engineering/candidates").glob(f"{candidate_id}.md"))
            self.assertEqual(len(candidate_paths), 1)

            propose = run_hive("import", "propose", import_id, "--workspace", str(workspace), "--json")
            self.assertEqual(propose.returncode, 0, propose.stderr)
            self.assertEqual(len(json.loads(propose.stdout)["proposals"]), 1)

            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

    def test_context_impact_and_invalidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            impacted = run_hive("context", "impacted", "org", "--workspace", str(workspace), "--json")
            self.assertEqual(impacted.returncode, 0, impacted.stderr)
            payload = json.loads(impacted.stdout)
            self.assertIn("departments/engineering", payload["descendants"])
            self.assertIn("agents/codex-engineering-001", payload["affected_targets"])

            invalidate = run_hive(
                "context",
                "invalidate",
                "org",
                "--workspace",
                str(workspace),
                "--reason",
                "org update",
                "--json",
            )
            self.assertEqual(invalidate.returncode, 0, invalidate.stderr)
            dirty_files = list((workspace / "memory/state/context-dirty").glob("ctxinv_*.yaml"))
            self.assertTrue(dirty_files)

    def test_context_compile_includes_parent_and_edge_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            compile_result = run_hive("context", "compile", "departments/engineering", "--workspace", str(workspace), "--json")
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            pack = workspace / "memory/generated/context-packs/nodes/departments/engineering/PACK.md"
            text = pack.read_text()
            self.assertIn("Parent Context: org", text)
            self.assertIn("Shared Edge Context: engineering__marketing__project-launch-x", text)


if __name__ == "__main__":
    unittest.main()
