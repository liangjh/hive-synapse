from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import run_hive


class LifecycleUpgradeTests(unittest.TestCase):
    def test_node_actor_skill_lifecycle_and_archive_sweep(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            create = run_hive(
                "node",
                "create",
                "departments/research",
                "--workspace",
                str(workspace),
                "--kind",
                "department",
                "--title",
                "Research",
                "--parent",
                "org",
                "--actor",
                "human:admin",
                "--json",
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            self.assertTrue((workspace / "memory/graph/nodes/departments/research.md").exists())
            assign = run_hive(
                "actor",
                "assign",
                "agent:research-001",
                "--workspace",
                str(workspace),
                "--home-node",
                "departments/research",
                "--role",
                "contributor",
                "--actor",
                "human:admin",
                "--json",
            )
            self.assertEqual(assign.returncode, 0, assign.stderr)
            skill = run_hive(
                "skill",
                "register",
                "literature-review",
                "--workspace",
                str(workspace),
                "--title",
                "Literature Review",
                "--scope",
                "departments/research",
                "--trigger",
                "research synthesis",
                "--actor",
                "steward:research",
                "--json",
            )
            self.assertEqual(skill.returncode, 0, skill.stderr)
            listed = run_hive("skill", "list", "--workspace", str(workspace), "--scope", "departments/research", "--json")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertEqual(json.loads(listed.stdout)["skills"][0]["id"], "literature-review")
            archived = run_hive(
                "node",
                "archive",
                "departments/research",
                "--workspace",
                str(workspace),
                "--actor",
                "human:admin",
                "--reason",
                "test archive",
                "--defer-compaction",
                "--json",
            )
            self.assertEqual(archived.returncode, 0, archived.stderr)
            sweep = run_hive("archive", "sweep", "--workspace", str(workspace), "--json")
            self.assertEqual(sweep.returncode, 0, sweep.stderr)
            self.assertTrue(json.loads(sweep.stdout)["candidates"])
            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)

    def test_upgrade_doctor_migration_and_template_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            self.assertEqual(run_hive("init", str(workspace), "--fixture", "basic-org").returncode, 0)
            doctor = run_hive("upgrade", "doctor", "--workspace", str(workspace), "--json")
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            migrations = run_hive("upgrade", "migration-list", "--workspace", str(workspace), "--json")
            self.assertEqual(migrations.returncode, 0, migrations.stderr)
            dry = run_hive("upgrade", "migration-dry-run", "001_runtime_markers", "--workspace", str(workspace), "--json")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertFalse(json.loads(dry.stdout)["mutates"])
            apply = run_hive("upgrade", "migration-apply", "001_runtime_markers", "--workspace", str(workspace), "--json")
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertTrue((workspace / "memory/migrations/001_runtime_markers.yaml").exists())
            diff = run_hive("upgrade", "template-diff", "--workspace", str(workspace), "--json")
            self.assertEqual(diff.returncode, 0, diff.stderr)
            self.assertIn("diffs", json.loads(diff.stdout))


if __name__ == "__main__":
    unittest.main()
