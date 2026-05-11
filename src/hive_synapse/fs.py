from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from .errors import PreconditionFailed, WorkspaceError


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_within_root(path: Path, root: Path) -> Path:
    resolved_path = path.resolve()
    resolved_root = root.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise WorkspaceError(
            f"Path {resolved_path} is outside workspace root {resolved_root}"
        ) from exc
    return resolved_path


def atomic_write_text(path: Path, text: str, *, expected_sha256: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if expected_sha256 is not None:
        if not path.exists():
            raise PreconditionFailed(f"Expected existing file for hash precondition: {path}")
        actual = sha256_file(path)
        if actual != expected_sha256:
            raise PreconditionFailed(
                f"Hash precondition failed for {path}: expected {expected_sha256}, got {actual}"
            )
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def write_new_text(path: Path, text: str) -> None:
    if path.exists():
        raise WorkspaceError(f"Refusing to overwrite existing file: {path}")
    atomic_write_text(path, text)
