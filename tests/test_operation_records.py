from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from tests.support import init_basic_workspace, operation_records, run_hive


class OperationRecordTests(unittest.TestCase):
    def test_init_writes_append_only_operation_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            records = operation_records(workspace)

            self.assertEqual(len(records), 1)
            first_path, first_record = records[0]
            self.assertEqual(first_record["type"], "workspace_init")
            self.assertEqual(first_record["actor"], "system:init")
            self.assertEqual(first_record["command"], "hive init")
            self.assertEqual(first_record["mode"], "apply")
            self.assertEqual(first_record["status"], "completed")
            self.assertIn(str(workspace.resolve()), first_record["targets"])
            self.assertIn({"path": "hive.config.yaml"}, first_record["changed_files"])
            self.assertIn("supported", first_record["rollback"])

            first_text = first_path.read_text(encoding="utf-8")
            result = run_hive("init", str(workspace), "--fixture", "basic-org")

            self.assertEqual(result.returncode, 0, result.stderr)
            after_records = operation_records(workspace)
            self.assertEqual(len(after_records), 2)
            self.assertEqual(first_path.read_text(encoding="utf-8"), first_text)

    def test_context_compile_appends_operation_record_for_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            before_names = {path.name for path, _record in operation_records(workspace)}

            result = run_hive(
                "context",
                "compile",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            new_records = [
                record
                for path, record in operation_records(workspace)
                if path.name not in before_names
            ]
            self.assertTrue(
                new_records,
                "context compile mutates generated artifacts and must append an operation record",
            )

            compile_records = [
                record
                for record in new_records
                if str(record.get("command", "")).startswith("hive context compile")
            ]
            self.assertTrue(compile_records, f"new operation records: {new_records!r}")
            record = compile_records[0]
            self.assertEqual(record["mode"], "apply")
            self.assertEqual(record["status"], "completed")
            self.assertIn(str(workspace.resolve()), record["targets"])
            changed_paths = self._changed_paths(record)
            self.assertIn(
                "memory/generated/context-packs/nodes/departments/engineering/PACK.md",
                changed_paths,
            )
            self.assertIn(
                "memory/generated/context-packs/nodes/departments/engineering/MANIFEST.yaml",
                changed_paths,
            )
            self.assertIn("supported", record["rollback"])

    @staticmethod
    def _changed_paths(record: dict[str, Any]) -> set[str]:
        paths = set()
        for changed_file in record.get("changed_files", []):
            if isinstance(changed_file, dict) and "path" in changed_file:
                paths.add(changed_file["path"])
        return paths


if __name__ == "__main__":
    unittest.main()
