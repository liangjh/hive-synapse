from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.support import (
    init_basic_workspace,
    json_from_stdout,
    load_yaml,
    required_workspace_dirs,
    run_hive,
)


class WorkspaceInitTests(unittest.TestCase):
    def test_basic_org_fixture_creates_expected_workspace_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))

            for rel_path in required_workspace_dirs():
                self.assertTrue((workspace / rel_path).is_dir(), rel_path)

            expected_files = [
                "hive.config.yaml",
                "memory/graph/nodes/org.md",
                "memory/graph/nodes/departments/engineering.md",
                "memory/graph/nodes/departments/marketing.md",
                "memory/graph/nodes/projects/project-launch-x.md",
                "memory/graph/nodes/agents/codex-engineering-001.md",
                "memory/graph/edges/engineering__marketing__project-launch-x.md",
                "memory/raw/demo-source.md",
                "memory/records/nodes/org/CURRENT.md",
                "memory/records/nodes/departments/engineering/CURRENT.md",
                "memory/records/nodes/departments/engineering/HISTORY.md",
                "memory/records/nodes/departments/engineering/candidates/"
                "mem_demo_engineering_practice_001.md",
                "memory/imports/departments/engineering/workspace.yaml",
                "memory/imports/departments/engineering/import-item-demo.yaml",
                "memory/proposals/promotion_demo_001.yaml",
                "memory/jobs/pending/job_demo_node_compact_001.yaml",
                "memory/state/context-dirty/ctxinv_demo_001.yaml",
                "memory/audit/archive_demo_001.yaml",
                "org/assignments/assignment_codex_engineering_001.yaml",
                "org/signins/signin_demo_001.yaml",
            ]
            for rel_path in expected_files:
                self.assertTrue((workspace / rel_path).is_file(), rel_path)

            config = load_yaml(workspace / "hive.config.yaml")
            self.assertEqual(config["hive_workspace"]["workspace_id"], "workspace")
            self.assertEqual(config["hive_workspace"]["install_mode"], "external_runtime")

    def test_init_json_reports_basic_org_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"

            result = run_hive("init", str(workspace), "--fixture", "basic-org", "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            output = json_from_stdout(result)
            self.assertEqual(output["fixture"], "basic-org")
            self.assertTrue(output["ok"])
            self.assertEqual(Path(output["workspace"]), workspace.resolve())

    def test_repeated_fixture_init_preserves_existing_workspace_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = init_basic_workspace(Path(temp_dir))
            candidate = (
                workspace
                / "memory/records/nodes/departments/engineering/candidates/"
                "mem_demo_engineering_practice_001.md"
            )
            edited_text = (
                candidate.read_text(encoding="utf-8")
                + "\n<!-- local edit must survive repeated init -->\n"
            )
            candidate.write_text(edited_text, encoding="utf-8")

            result = run_hive("init", str(workspace), "--fixture", "basic-org")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(candidate.read_text(encoding="utf-8"), edited_text)


if __name__ == "__main__":
    unittest.main()
