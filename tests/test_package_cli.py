from __future__ import annotations

import tomllib
import unittest

from tests.support import ROOT, run_hive


class PackageCliSmokeTests(unittest.TestCase):
    def test_package_metadata_declares_dependency_free_hive_cli(self) -> None:
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

        self.assertEqual(metadata["project"]["scripts"]["hive"], "hive_synapse.cli:main")
        self.assertEqual(metadata["project"]["dependencies"], [])
        self.assertEqual(
            metadata["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"],
            ["src/hive_synapse"],
        )

    def test_help_lists_first_slice_and_reserved_command_groups(self) -> None:
        result = run_hive("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Hive Synapse memory runtime", result.stdout)
        for command in ["init", "validate", "context", "policy", "operation", "upgrade"]:
            self.assertIn(command, result.stdout)

    def test_context_help_lists_compile_command(self) -> None:
        result = run_hive("context", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: hive context", result.stdout)
        self.assertIn("compile", result.stdout)

    def test_invalid_flags_fail_with_useful_error(self) -> None:
        result = run_hive("validate", "--not-a-real-flag")

        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
