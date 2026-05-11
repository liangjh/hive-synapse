from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

from .fs import atomic_write_text
from .ids import utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths


def _default_runtime_command() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    source_runner = repo_root / "bin" / "hive"
    if source_runner.exists():
        return str(source_runner)
    return "hive"


def _scheduler_dir(paths: WorkspacePaths) -> Path:
    return paths.root / "local-overrides" / "schedulers"


def install_scheduler(
    root: Path,
    kind: str,
    *,
    runtime_command: str | None = None,
    interval_minutes: int = 15,
    actor: str = "system:scheduler",
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    if kind not in {"cron", "launchd"}:
        raise ValueError("Scheduler kind must be 'cron' or 'launchd'")
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be >= 1")
    command = runtime_command or _default_runtime_command()
    scheduler_dir = _scheduler_dir(paths)
    scheduler_dir.mkdir(parents=True, exist_ok=True)
    log_path = paths.root / "memory" / "audit" / "scheduler.log"
    workspace_q = shlex.quote(str(paths.root))
    command_fragment = command
    log_q = shlex.quote(str(log_path))
    generated_at = utc_now_iso()

    if kind == "cron":
        schedule = f"*/{interval_minutes} * * * *"
        output_path = scheduler_dir / "hive-synapse.cron"
        watchdog_line = (
            f"{schedule} cd {workspace_q} && {command_fragment} job watchdog "
            f"--workspace {workspace_q} --enqueue >> {log_q} 2>&1"
        )
        run_line = (
            f"{schedule} cd {workspace_q} && {command_fragment} job run "
            f"--workspace {workspace_q} --runner runner:scheduler >> {log_q} 2>&1"
        )
        text = f"""# Hive Synapse scheduler template
# Generated at {generated_at}
# Install manually with: (crontab -l 2>/dev/null; cat {shlex.quote(str(output_path))}) | crontab -
# Workspace: {paths.root}
{watchdog_line}
{run_line}
"""
        install_hint = f"(crontab -l 2>/dev/null; cat {output_path}) | crontab -"
    else:
        output_path = scheduler_dir / "com.hive-synapse.job-runner.plist"
        seconds = interval_minutes * 60
        shell_command = (
            f"cd {workspace_q} && "
            f"{command_fragment} job watchdog --workspace {workspace_q} --enqueue "
            f">> {log_q} 2>&1 && "
            f"{command_fragment} job run --workspace {workspace_q} "
            f"--runner runner:scheduler >> {log_q} 2>&1"
        )
        text = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
  <key>Label</key>
  <string>com.hive-synapse.job-runner</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>-lc</string>
    <string>{shell_command}</string>
  </array>
  <key>StartInterval</key>
  <integer>{seconds}</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{log_path}</string>
  <key>StandardErrorPath</key>
  <string>{log_path}</string>
</dict>
</plist>
"""
        install_hint = f"launchctl load {output_path}"

    atomic_write_text(output_path, text)
    op = OperationLog(paths).append(
        operation_type="scheduler_install",
        actor=actor,
        targets=[str(paths.root), kind],
        command=f"hive scheduler install {kind}",
        changed_files=[{"path": str(output_path.relative_to(paths.root))}],
        changed_records=[{"id": f"scheduler_{kind}", "type": "scheduler_template"}],
        rollback={
            "supported": True,
            "strategy": "remove_scheduler_template_or_unload_external_scheduler",
        },
    )
    return {
        "ok": True,
        "kind": kind,
        "path": str(output_path),
        "operation": op.id,
        "install_hint": install_hint,
        "runtime_command": command,
        "interval_minutes": interval_minutes,
    }
