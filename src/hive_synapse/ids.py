from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    timestamp = utc_now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{timestamp}_{uuid4().hex[:8]}"
