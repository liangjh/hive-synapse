from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_hive(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "hive_synapse.cli", *args],
        cwd=cwd or ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class CliSmokeTests(unittest.TestCase):
    def test_help_runs(self) -> None:
        result = run_hive("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Hive Synapse", result.stdout)

    def test_init_validate_and_context_compile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "workspace"
            init = run_hive("init", str(workspace), "--fixture", "basic-org")
            self.assertEqual(init.returncode, 0, init.stderr)

            validate = run_hive("validate", str(workspace), "--json")
            self.assertEqual(validate.returncode, 0, validate.stderr)
            report = json.loads(validate.stdout)
            self.assertTrue(report["ok"], report)

            compile_result = run_hive(
                "context",
                "compile",
                "departments/engineering",
                "--workspace",
                str(workspace),
                "--json",
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            output = json.loads(compile_result.stdout)
            self.assertTrue(output["ok"], output)
            self.assertTrue(
                (
                    workspace
                    / "memory/generated/context-packs/nodes/departments/engineering/PACK.md"
                ).exists()
            )
            self.assertTrue(
                (
                    workspace
                    / "memory/generated/context-packs/nodes/departments/engineering/MANIFEST.yaml"
                ).exists()
            )


if __name__ == "__main__":
    unittest.main()
