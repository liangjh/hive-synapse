"""Shared exception types.

Module guide:
- `HiveError` is the base exception for controlled CLI/API failures.
- `WorkspaceError`, `ValidationFailure`, and `PreconditionFailed` specialize it.

Maintenance: update this guide when adding public functions/classes to this module.
"""

from __future__ import annotations


class HiveError(Exception):
    """Base runtime error for Hive Synapse."""


class WorkspaceError(HiveError):
    """Raised for invalid workspace state or paths."""


class ValidationFailure(HiveError):
    """Raised when validation fails and an exception form is needed."""


class PreconditionFailed(HiveError):
    """Raised when an optimistic write precondition fails."""
