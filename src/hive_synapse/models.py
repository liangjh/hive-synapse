from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, get_args, get_origin


class ModelValidationError(ValueError):
    """Raised when a record cannot be converted into a Hive model."""


class FactoryDefault:
    def __init__(self, factory):
        self.factory = factory

    def build(self):
        return self.factory()


def default_factory(factory):
    return FactoryDefault(factory)


def _all_annotations(cls: type) -> dict[str, Any]:
    annotations: dict[str, Any] = {}
    for parent in reversed(cls.mro()):
        annotations.update(getattr(parent, "__annotations__", {}))
    return {key: value for key, value in annotations.items() if not key.startswith("_")}


def _allows_none(annotation: Any) -> bool:
    if annotation is Any:
        return True
    origin = get_origin(annotation)
    if origin is None:
        return annotation is None or annotation is type(None)
    return type(None) in get_args(annotation)


def _serialize(value: Any) -> Any:
    if isinstance(value, HiveModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


class HiveModel:
    def __init__(self, **kwargs: Any):
        annotations = _all_annotations(self.__class__)
        for name, annotation in annotations.items():
            if name in kwargs:
                value = kwargs.pop(name)
            elif hasattr(self.__class__, name):
                default = getattr(self.__class__, name)
                value = default.build() if isinstance(default, FactoryDefault) else deepcopy(default)
            elif _allows_none(annotation):
                value = None
            else:
                raise ModelValidationError(f"Missing required field: {name}")
            setattr(self, name, value)
        for name, value in kwargs.items():
            setattr(self, name, value)

    @classmethod
    def model_validate(cls, data: Any):
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise ModelValidationError(f"Expected mapping for {cls.__name__}")
        return cls(**data)

    def model_dump(self, mode: str | None = None) -> dict[str, Any]:
        del mode
        return {key: _serialize(value) for key, value in self.__dict__.items() if not key.startswith("_")}


class SourceRef(HiveModel):
    source_id: str
    locator: str | None = None


class WorkspaceConfig(HiveModel):
    workspace_id: str
    schema_version: str = "0.1.0"
    runtime_version: str = "0.1.0"
    runtime_ref: str | None = None
    data_root: str = "memory/"
    policy_root: str = "policies/"
    local_overrides_root: str = "local-overrides/"
    generated_root: str = "memory/generated/"
    install_mode: str = "external_runtime"
    upgrade_policy: dict[str, Any] = default_factory(
        lambda: {
            "require_dry_run": True,
            "backup_before_migration": True,
            "never_overwrite_local_context": True,
            "require_operator_approval": False,
        }
    )


class NodeRecord(HiveModel):
    id: str
    kind: str
    title: str
    parents: list[str] = default_factory(list)
    status: str = "active"
    owners: list[str] = default_factory(list)
    current_memory_file: str | None = None
    history_memory_file: str | None = None
    import_workspace: str | None = None


class EdgeRecord(HiveModel):
    id: str
    kind: str
    title: str
    nodes: list[str]
    authority: str = "shared"
    status: str = "active"
    current_memory_file: str | None = None
    history_memory_file: str | None = None
    import_workspace: str | None = None


class MemoryRecord(HiveModel):
    id: str
    type: str
    scope: str
    authority: str
    created_at: str
    created_by: str
    source_refs: list[dict[str, Any]] = default_factory(list)
    node: str | None = None
    edge: str | None = None
    confidence: float | None = None
    sensitivity: str = "internal"
    status: str = "active"
    tags: list[str] = default_factory(list)


class ImportWorkspace(HiveModel):
    id: str
    target: str
    status: str = "active"
    owner: str | None = None
    paths: dict[str, str] = default_factory(dict)


class ImportItem(HiveModel):
    id: str
    workspace: str
    target: str
    source_type: str
    state: str
    created_at: str
    source_ref: dict[str, Any] | None = None
    external_ref: dict[str, Any] | None = None
    local_path: str | None = None
    raw_preserved: bool = False
    sensitivity: str = "unknown"


class ActorAssignment(HiveModel):
    id: str
    actor: str
    home_node: str
    role: str
    status: str = "active"
    assigned_at: str
    personal_memory_home: str | None = None


class SignInRecord(HiveModel):
    id: str
    actor: str
    instance: str
    effective_node: str
    role: str
    started_at: str
    status: str = "active"
    assignment: str | None = None
    context_pack: str | None = None
    loaded_context_packs: list[dict[str, Any]] = default_factory(list)


class PromotionProposal(HiveModel):
    id: str
    source_record: str
    source_scope: str
    target_scope: str
    promotion_type: str
    rationale: str
    status: str = "candidate"


class JobRecord(HiveModel):
    id: str
    type: str
    target: str
    status: str = "pending"
    reason: str
    created_at: str
    inputs: dict[str, Any] = default_factory(dict)


class OperationRecord(HiveModel):
    id: str
    type: str
    actor: str
    started_at: str
    status: str
    targets: list[str]
    command: str | None = None
    mode: str | None = None
    changed_files: list[dict[str, Any]] = default_factory(list)
    changed_records: list[dict[str, Any]] = default_factory(list)
    rollback: dict[str, Any] = default_factory(dict)


class ContextInvalidation(HiveModel):
    id: str
    target: str
    reason: str
    created_at: str
    severity: Literal["low", "normal", "high", "critical"] = "normal"
    affected_context_packs: list[str] = default_factory(list)
    affected_targets: list[str] = default_factory(list)
    status: str = "open"


class ContextDirtyMarker(HiveModel):
    id: str
    target: str
    reason: str
    created_at: str
    severity: Literal["low", "normal", "high", "critical"] = "normal"
    status: str = "open"
    affected_context_packs: list[str] = default_factory(list)


class ArchiveRecord(HiveModel):
    id: str
    target: str
    target_type: str
    reason: str
    archived_at: str
    archived_by: str
    status: str = "archived"
    excluded_from_startup_context: bool = True


class ContextPackManifest(HiveModel):
    id: str
    target: str
    version: int
    compiled_at: str
    policy_id: str
    estimated_tokens: int
    budget_tokens: int
    sections: list[dict[str, Any]] = default_factory(list)
    source_watermark: str
    validation: dict[str, Any]
    runtime_version: str = "0.1.0"
    workspace_schema_version: str = "0.1.0"
    policy_version: str = "default"
    command_version: str = "0.1.0"
    skill_registry_version: str = "default"


class MigrationRecord(HiveModel):
    id: str
    workspace_id: str
    from_schema_version: str
    to_schema_version: str
    status: str
    started_at: str


class ValidationIssue(HiveModel):
    code: str
    message: str
    path: str | None = None
    severity: Literal["error", "warning"] = "error"


class ValidationReport(HiveModel):
    ok: bool
    errors: list[ValidationIssue] = default_factory(list)
    warnings: list[ValidationIssue] = default_factory(list)

    def add_error(self, code: str, message: str, path: str | None = None) -> None:
        self.errors.append(ValidationIssue(code=code, message=message, path=path))
        self.ok = False

    def add_warning(self, code: str, message: str, path: str | None = None) -> None:
        self.warnings.append(
            ValidationIssue(code=code, message=message, path=path, severity="warning")
        )
