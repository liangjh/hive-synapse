from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import ROOT, run_hive


class EndToEndFixtureTests(unittest.TestCase):
    def test_committed_basic_org_fixture_validates(self) -> None:
        fixture = ROOT / "fixtures/workspaces/basic-org"
        self.assertTrue(fixture.exists())
        result = run_hive("validate", str(fixture), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_full_mvp_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            source = Path(temp_dir) / "notes.md"
            source.write_text(
                "# Engineering Practice\n\nCurrent practice: document launch risks before release."
            )
            self.assertEqual(
                run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0
            )
            add = run_hive(
                "import",
                "add",
                "departments/engineering",
                str(source),
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(add.returncode, 0, add.stderr)
            import_id = json.loads(add.stdout)["import_id"]
            for command in ["classify", "compact", "propose"]:
                result = run_hive(
                    "import", command, import_id, "--workspace", str(workspace), "--json"
                )
                self.assertEqual(result.returncode, 0, command + result.stdout + result.stderr)
            sweep = run_hive(
                "promote", "sweep", "--workspace", str(workspace), "--create-proposals", "--json"
            )
            self.assertEqual(sweep.returncode, 0, sweep.stderr)
            proposal_id = json.loads(sweep.stdout)["created_proposals"][0]["id"]
            review = run_hive(
                "promote",
                "review",
                proposal_id,
                "--workspace",
                str(workspace),
                "--decision",
                "approved",
                "--actor",
                "steward:engineering",
                "--rationale",
                "e2e",
                "--json",
            )
            self.assertEqual(review.returncode, 0, review.stderr)
            apply = run_hive(
                "promote",
                "apply",
                proposal_id,
                "--workspace",
                str(workspace),
                "--actor",
                "steward:engineering",
                "--json",
            )
            self.assertEqual(apply.returncode, 0, apply.stderr)
            compile_result = run_hive(
                "context",
                "compile",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            archive = run_hive("archive", "sweep", "--workspace", str(workspace), "--json")
            self.assertEqual(archive.returncode, 0, archive.stderr)
            migration = run_hive(
                "upgrade",
                "migration-dry-run",
                "001_runtime_markers",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(migration.returncode, 0, migration.stderr)
            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)


if __name__ == "__main__":
    unittest.main()
