from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_hive(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "hive_synapse.cli", *args],
        cwd=cwd or ROOT,
        env=cli_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def json_from_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Expected JSON stdout, got:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        ) from exc
    if not isinstance(data, dict):
        raise AssertionError(f"Expected JSON object, got {type(data).__name__}: {data!r}")
    return data


def init_basic_workspace(parent: Path, name: str = "workspace") -> Path:
    workspace = parent / name
    result = run_hive("init", str(workspace), "--fixture", "basic-org", "--json")
    if result.returncode != 0:
        raise AssertionError(f"hive init failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    output = json_from_stdout(result)
    if output.get("ok") is not True:
        raise AssertionError(f"hive init did not report ok: {output!r}")
    return workspace


def load_yaml(path: Path) -> dict[str, Any]:
    from hive_synapse import simple_yaml

    data = simple_yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise AssertionError(f"Expected YAML mapping in {path}, got {type(data).__name__}")
    return data


def required_workspace_dirs() -> list[str]:
    from hive_synapse.paths import REQUIRED_DIRS

    return list(REQUIRED_DIRS)


def read_markdown_file(path: Path):
    from hive_synapse.frontmatter import read_markdown

    return read_markdown(path)


def write_markdown_file(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    from hive_synapse.frontmatter import write_markdown

    write_markdown(path, frontmatter, body)


def operation_records(workspace: Path) -> list[tuple[Path, dict[str, Any]]]:
    operations_dir = workspace / "memory" / "operations"
    return [(path, load_yaml(path)) for path in sorted(operations_dir.glob("*.yaml"))]
