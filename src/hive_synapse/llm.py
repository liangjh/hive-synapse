from __future__ import annotations

import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import simple_yaml as yaml
from .errors import WorkspaceError
from .fs import atomic_write_text, sha256_file
from .ids import new_id, utc_now_iso
from .operations import OperationLog
from .paths import WorkspacePaths

PROVIDERS = [
    {
        "name": "deterministic",
        "description": "Offline deterministic strategy used by default and by tests.",
        "network": False,
        "requires_dependency": None,
    },
    {
        "name": "openai",
        "description": "Native OpenAI Chat Completions compatible HTTP adapter.",
        "network": True,
        "requires_dependency": None,
    },
    {
        "name": "openai_compatible",
        "description": "Generic OpenAI-compatible endpoint adapter for hosted or local servers.",
        "network": True,
        "requires_dependency": None,
    },
    {
        "name": "openrouter",
        "description": "OpenRouter adapter using the OpenAI-compatible API shape.",
        "network": True,
        "requires_dependency": None,
    },
    {
        "name": "anthropic",
        "description": "Native Anthropic Messages API HTTP adapter.",
        "network": True,
        "requires_dependency": None,
    },
    {
        "name": "litellm",
        "description": "Optional LiteLLM adapter for broad provider coverage.",
        "network": True,
        "requires_dependency": "litellm",
    },
    {
        "name": "command",
        "description": "Local command adapter; sends ModelRequest JSON on stdin.",
        "network": False,
        "requires_dependency": None,
    },
]

NETWORK_PROVIDERS = {"openai", "openai_compatible", "openrouter", "anthropic", "litellm"}


@dataclass
class ModelRequest:
    task: str
    messages: list[dict[str, str]]
    profile: dict[str, Any]
    credential: dict[str, Any] | None = None
    actor: str | None = None
    expected_schema: dict[str, Any] | None = None
    input_refs: list[dict[str, Any]] = field(default_factory=list)
    input_hashes: list[dict[str, Any]] = field(default_factory=list)
    prompt_id: str | None = None
    prompt_version: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "messages": self.messages,
            "profile": _redact_secrets(self.profile),
            "credential": _redact_secrets(self.credential or {}),
            "actor": self.actor,
            "expected_schema": self.expected_schema or {},
            "input_refs": self.input_refs,
            "input_hashes": self.input_hashes,
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
        }


@dataclass
class ModelResponse:
    content: str
    output_json: dict[str, Any]
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None
    raw_response_hash: str | None = None


def default_llm_policy() -> dict[str, Any]:
    return {
        "enabled": False,
        "default_profile": "deterministic",
        "organization_profile": "deterministic",
        "allow_network_models": False,
        "record_raw_prompts": False,
        "profiles": [
            {"id": "deterministic", "provider": "deterministic", "model": "deterministic"},
        ],
        "actor_profiles": [],
        "task_profiles": [],
    }


def default_credentials_registry() -> dict[str, Any]:
    return {
        "credentials": [],
        "organization_credential": "none",
        "actor_credentials": [],
    }


def list_providers() -> dict[str, Any]:
    return {"ok": True, "providers": PROVIDERS}


def ensure_llm_policy(root: Path, *, actor: str = "system:llm") -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    policy_path = _policy_path(paths)
    credentials_path = _credentials_path(paths)
    changed_files = []
    if not policy_path.exists():
        atomic_write_text(policy_path, yaml.safe_dump(default_llm_policy(), sort_keys=False))
        changed_files.append({"path": str(policy_path.relative_to(paths.root))})
    if not credentials_path.exists():
        atomic_write_text(
            credentials_path,
            yaml.safe_dump(default_credentials_registry(), sort_keys=False),
        )
        changed_files.append({"path": str(credentials_path.relative_to(paths.root))})
    operation = None
    if changed_files:
        operation = OperationLog(paths).append(
            operation_type="llm_policy_init",
            actor=actor,
            targets=[str(paths.root)],
            command="hive llm init",
            changed_files=changed_files,
            changed_records=[],
            rollback={"supported": True, "strategy": "remove_created_policy_files"},
        )
    return {
        "ok": True,
        "policy": _load_llm_policy(paths),
        "credentials": _redact_secrets(_load_credentials_registry(paths)),
        "operation": operation.id if operation else None,
    }


def list_llm_config(root: Path) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    return {
        "ok": True,
        "policy": _load_llm_policy(paths),
        "credentials": _redact_secrets(_load_credentials_registry(paths)),
        "providers": PROVIDERS,
    }


def add_credential(
    root: Path,
    credential_id: str,
    *,
    provider: str,
    api_key_env: str | None = None,
    actor: str = "system:llm",
    assign_actor: str | None = None,
    organization_default: bool = False,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    _ensure_provider(provider)
    registry = _load_credentials_registry(paths)
    credentials = _as_list(registry.get("credentials"))
    existing = _find_by_id(credentials, credential_id)
    record = {"id": credential_id, "provider": provider}
    if api_key_env:
        record["api_key_env"] = api_key_env
    if existing is None:
        credentials.append(record)
    else:
        existing.update(record)
    registry["credentials"] = credentials
    if organization_default:
        registry["organization_credential"] = credential_id
    if assign_actor:
        _upsert_actor_choice(
            registry, "actor_credentials", assign_actor, "credential", credential_id
        )
    path = _credentials_path(paths)
    atomic_write_text(path, yaml.safe_dump(registry, sort_keys=False))
    operation = OperationLog(paths).append(
        operation_type="llm_credential_upsert",
        actor=actor,
        targets=[credential_id],
        command="hive llm credential add",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": credential_id, "type": "llm_credential"}],
        rollback={"supported": True, "strategy": "restore_credentials_registry_from_backup"},
    )
    return {
        "ok": True,
        "credential": _redact_secrets(record),
        "credentials": _redact_secrets(registry),
        "operation": operation.id,
    }


def assign_credential(
    root: Path,
    credential_id: str,
    *,
    actor: str = "system:llm",
    assign_actor: str | None = None,
    organization_default: bool = False,
) -> dict[str, Any]:
    if not assign_actor and not organization_default:
        raise WorkspaceError(
            "Credential assignment requires --assign-actor or --organization-default"
        )
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    registry = _load_credentials_registry(paths)
    if (
        credential_id != "none"
        and _find_by_id(_as_list(registry.get("credentials")), credential_id) is None
    ):
        raise WorkspaceError(f"LLM credential not found: {credential_id}")
    if organization_default:
        registry["organization_credential"] = credential_id
    if assign_actor:
        _upsert_actor_choice(
            registry, "actor_credentials", assign_actor, "credential", credential_id
        )
    path = _credentials_path(paths)
    atomic_write_text(path, yaml.safe_dump(registry, sort_keys=False))
    operation = OperationLog(paths).append(
        operation_type="llm_credential_assign",
        actor=actor,
        targets=[credential_id],
        command="hive llm credential assign",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": credential_id, "type": "llm_credential_assignment"}],
        rollback={"supported": True, "strategy": "restore_credentials_registry_from_backup"},
    )
    return {"ok": True, "credentials": _redact_secrets(registry), "operation": operation.id}


def add_profile(
    root: Path,
    profile_id: str,
    *,
    provider: str,
    model: str,
    base_url: str | None = None,
    credential: str | None = None,
    command: list[str] | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    actor: str = "system:llm",
    assign_actor: str | None = None,
    organization_default: bool = False,
    enable: bool = False,
    allow_network_models: bool = False,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    _ensure_provider(provider)
    policy = _load_llm_policy(paths)
    profiles = _as_list(policy.get("profiles"))
    existing = _find_by_id(profiles, profile_id)
    profile = {"id": profile_id, "provider": provider, "model": model}
    if base_url:
        profile["base_url"] = base_url
    if credential:
        profile["credential"] = credential
    if command:
        profile["command"] = command
    if temperature is not None:
        profile["temperature"] = temperature
    if max_output_tokens is not None:
        profile["max_output_tokens"] = max_output_tokens
    if existing is None:
        profiles.append(profile)
    else:
        existing.update(profile)
    policy["profiles"] = profiles
    if organization_default:
        policy["organization_profile"] = profile_id
        policy["default_profile"] = profile_id
    if assign_actor:
        _upsert_actor_choice(policy, "actor_profiles", assign_actor, "profile", profile_id)
    if enable:
        policy["enabled"] = True
    if allow_network_models:
        policy["allow_network_models"] = True
    path = _policy_path(paths)
    atomic_write_text(path, yaml.safe_dump(policy, sort_keys=False))
    operation = OperationLog(paths).append(
        operation_type="llm_profile_upsert",
        actor=actor,
        targets=[profile_id],
        command="hive llm profile add",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": profile_id, "type": "llm_profile"}],
        rollback={"supported": True, "strategy": "restore_llm_policy_from_backup"},
    )
    return {
        "ok": True,
        "profile": _redact_secrets(profile),
        "policy": _redact_secrets(policy),
        "operation": operation.id,
    }


def assign_profile(
    root: Path,
    profile_id: str,
    *,
    actor: str = "system:llm",
    assign_actor: str | None = None,
    organization_default: bool = False,
    enable: bool = False,
) -> dict[str, Any]:
    if not assign_actor and not organization_default:
        raise WorkspaceError("Profile assignment requires --assign-actor or --organization-default")
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    policy = _load_llm_policy(paths)
    if _find_by_id(_as_list(policy.get("profiles")), profile_id) is None:
        raise WorkspaceError(f"LLM profile not found: {profile_id}")
    if organization_default:
        policy["organization_profile"] = profile_id
        policy["default_profile"] = profile_id
    if assign_actor:
        _upsert_actor_choice(policy, "actor_profiles", assign_actor, "profile", profile_id)
    if enable:
        policy["enabled"] = True
    path = _policy_path(paths)
    atomic_write_text(path, yaml.safe_dump(policy, sort_keys=False))
    operation = OperationLog(paths).append(
        operation_type="llm_profile_assign",
        actor=actor,
        targets=[profile_id],
        command="hive llm profile assign",
        changed_files=[{"path": str(path.relative_to(paths.root))}],
        changed_records=[{"id": profile_id, "type": "llm_profile_assignment"}],
        rollback={"supported": True, "strategy": "restore_llm_policy_from_backup"},
    )
    return {"ok": True, "policy": _redact_secrets(policy), "operation": operation.id}


def generate_structured(
    root: Path,
    *,
    task: str,
    actor: str,
    messages: list[dict[str, str]],
    expected_schema: dict[str, Any] | None = None,
    input_refs: list[dict[str, Any]] | None = None,
    input_hashes: list[dict[str, Any]] | None = None,
    profile_id: str | None = None,
    credential_id: str | None = None,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
) -> tuple[ModelRequest, ModelResponse]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    policy = _load_llm_policy(paths)
    registry = _load_credentials_registry(paths)
    profile = _resolve_profile(policy, task=task, actor=actor, explicit_profile=profile_id)
    credential = _resolve_credential(
        registry,
        profile=profile,
        actor=actor,
        explicit_credential=credential_id,
    )
    provider = str(profile.get("provider", "deterministic"))
    if provider in NETWORK_PROVIDERS and not bool(policy.get("allow_network_models")):
        local_base = _is_local_base_url(str(profile.get("base_url", "")))
        if not local_base:
            raise WorkspaceError("Network model execution is disabled by policies/llm.yaml")
    request = ModelRequest(
        task=task,
        messages=messages,
        profile=profile,
        credential=credential,
        actor=actor,
        expected_schema=expected_schema,
        input_refs=input_refs or [],
        input_hashes=input_hashes or [],
        prompt_id=prompt_id,
        prompt_version=prompt_version,
    )
    client = _provider_for(provider)
    response = client.generate(request)
    if not isinstance(response.output_json, dict):
        raise WorkspaceError("Model response did not produce a JSON object")
    return request, response


def write_model_run(
    root: Path,
    *,
    request: ModelRequest,
    response: ModelResponse | None,
    status: str,
    created_records: list[str] | None = None,
    created_proposals: list[str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    run_id = new_id("llmrun")
    profile = request.profile
    record: dict[str, Any] = {
        "id": run_id,
        "task": request.task,
        "provider": profile.get("provider", "deterministic"),
        "model": profile.get("model", "deterministic"),
        "model_profile": profile.get("id", "deterministic"),
        "credential": (request.credential or {}).get("id", "none"),
        "actor": request.actor,
        "started_at": utc_now_iso(),
        "completed_at": utc_now_iso(),
        "status": status,
        "input_refs": request.input_refs,
        "input_hashes": request.input_hashes,
        "prompt_id": request.prompt_id,
        "prompt_version": request.prompt_version,
        "output_schema": request.expected_schema or {},
        "created_records": created_records or [],
        "created_proposals": created_proposals or [],
        "warnings": [],
    }
    if response is not None:
        record["output_hash"] = response.raw_response_hash or _hash_text(response.content)
        record["usage"] = response.usage
        record["finish_reason"] = response.finish_reason
    if error:
        record["error"] = error
    path = paths.root / "memory" / "generated" / "llm-runs" / f"{run_id}.yaml"
    atomic_write_text(path, yaml.safe_dump(record, sort_keys=False))
    return {"record": record, "path": path}


def should_use_model(root: Path, *, task: str, actor: str, profile_id: str | None = None) -> bool:
    paths = WorkspacePaths(root.resolve())
    paths.require_workspace()
    policy = _load_llm_policy(paths)
    if profile_id:
        return True
    if bool(policy.get("enabled")):
        profile = _resolve_profile(policy, task=task, actor=actor, explicit_profile=None)
        return str(profile.get("provider", "deterministic")) != "deterministic"
    return False


def input_hash_for_path(root: Path, rel_path: str | None) -> list[dict[str, Any]]:
    if not rel_path:
        return []
    path = root / rel_path
    if not path.exists() or not path.is_file():
        return []
    return [{"path": rel_path, "sha256": sha256_file(path)}]


class DeterministicProvider:
    def generate(self, request: ModelRequest) -> ModelResponse:
        text = "\n\n".join(message.get("content", "") for message in request.messages)
        if request.task == "import_classify":
            lower = text.lower()
            topics = [
                topic
                for topic in ["policy", "practice", "project", "decision", "risk", "skill"]
                if topic in lower
            ]
            output = {
                "topics": topics or ["general"],
                "temporal_status": "historical" if "deprecated" in lower else "current",
                "sensitivity": "confidential" if "confidential" in lower else "internal",
            }
        elif request.task == "promotion_sweep":
            output = {
                "recommended": True,
                "confidence": 0.6,
                "rationale": "Deterministic provider returned advisory approval.",
                "risk_flags": [],
                "missing_evidence": [],
            }
        else:
            output = {
                "summary": " ".join(text.strip().split())[:600],
                "confidence": 0.6,
                "tags": [],
                "rationale": "Deterministic provider summarized by truncation.",
            }
        content = json.dumps(output, sort_keys=True)
        return ModelResponse(
            content=content,
            output_json=output,
            provider="deterministic",
            model="deterministic",
            raw_response_hash=_hash_text(content),
        )


class OpenAICompatibleProvider:
    default_base_url = "https://api.openai.com/v1"

    def generate(self, request: ModelRequest) -> ModelResponse:
        profile = request.profile
        model = str(profile.get("model") or "")
        if not model:
            raise WorkspaceError(
                f"{profile.get('provider', 'openai_compatible')} profile requires a model"
            )
        base_url = str(profile.get("base_url") or self.default_base_url).rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": request.messages,
            "temperature": float(profile.get("temperature", 0)),
        }
        max_tokens = profile.get("max_output_tokens")
        if max_tokens is not None:
            payload["max_tokens"] = int(max_tokens)
        data = _post_json(url, payload, _auth_headers(request))
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        content = str(message.get("content") or "")
        return ModelResponse(
            content=content,
            output_json=_parse_json_object(content),
            provider=str(profile.get("provider", "openai_compatible")),
            model=model,
            usage=data.get("usage") or {},
            finish_reason=choice.get("finish_reason"),
            raw_response_hash=_hash_text(json.dumps(data, sort_keys=True)),
        )


class OpenRouterProvider(OpenAICompatibleProvider):
    default_base_url = "https://openrouter.ai/api/v1"


class AnthropicProvider:
    def generate(self, request: ModelRequest) -> ModelResponse:
        profile = request.profile
        model = str(profile.get("model") or "")
        if not model:
            raise WorkspaceError("Anthropic profile requires a model")
        base_url = str(profile.get("base_url") or "https://api.anthropic.com").rstrip("/")
        system_parts = [m.get("content", "") for m in request.messages if m.get("role") == "system"]
        messages = [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in request.messages
            if m.get("role") != "system"
        ]
        payload = {
            "model": model,
            "max_tokens": int(profile.get("max_output_tokens", 1024)),
            "messages": messages,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        headers = _auth_headers(request)
        headers["anthropic-version"] = str(profile.get("anthropic_version", "2023-06-01"))
        data = _post_json(f"{base_url}/v1/messages", payload, headers)
        content_blocks = data.get("content") or []
        content = "\n".join(
            str(block.get("text", "")) for block in content_blocks if isinstance(block, dict)
        )
        return ModelResponse(
            content=content,
            output_json=_parse_json_object(content),
            provider="anthropic",
            model=model,
            usage=data.get("usage") or {},
            finish_reason=data.get("stop_reason"),
            raw_response_hash=_hash_text(json.dumps(data, sort_keys=True)),
        )


class LiteLLMProvider:
    def generate(self, request: ModelRequest) -> ModelResponse:
        try:
            import litellm  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WorkspaceError("LiteLLM provider selected but litellm is not installed") from exc
        profile = request.profile
        model = str(profile.get("model") or "")
        if not model:
            raise WorkspaceError("LiteLLM profile requires a model")
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": request.messages,
            "temperature": float(profile.get("temperature", 0)),
        }
        api_key = _api_key(request)
        if api_key:
            kwargs["api_key"] = api_key
        if profile.get("base_url"):
            kwargs["api_base"] = profile.get("base_url")
        response = litellm.completion(**kwargs)
        choice = response.choices[0]
        content = str(choice.message.content or "")
        usage = getattr(response, "usage", None)
        usage_dict = usage if isinstance(usage, dict) else getattr(usage, "dict", lambda: {})()
        return ModelResponse(
            content=content,
            output_json=_parse_json_object(content),
            provider="litellm",
            model=model,
            usage=usage_dict or {},
            finish_reason=getattr(choice, "finish_reason", None),
            raw_response_hash=_hash_text(str(response)),
        )


class CommandProvider:
    def generate(self, request: ModelRequest) -> ModelResponse:
        command = request.profile.get("command")
        if not isinstance(command, list) or not command:
            raise WorkspaceError("Command model profile requires command argv list")
        timeout = int(request.profile.get("timeout_seconds", 120))
        completed = subprocess.run(
            [str(part) for part in command],
            input=json.dumps(request.as_dict()),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            raise WorkspaceError(f"Command model failed: {completed.stderr.strip()}")
        data = json.loads(completed.stdout)
        if isinstance(data, dict) and isinstance(data.get("output_json"), dict):
            output_json = data["output_json"]
            content = str(data.get("content") or json.dumps(output_json, sort_keys=True))
        elif isinstance(data, dict):
            output_json = data
            content = json.dumps(output_json, sort_keys=True)
        else:
            raise WorkspaceError("Command model must return a JSON object")
        return ModelResponse(
            content=content,
            output_json=output_json,
            provider="command",
            model=str(request.profile.get("model", "command")),
            raw_response_hash=_hash_text(completed.stdout),
        )


def _provider_for(provider: str):
    if provider == "deterministic":
        return DeterministicProvider()
    if provider == "openai":
        return OpenAICompatibleProvider()
    if provider == "openai_compatible":
        return OpenAICompatibleProvider()
    if provider == "openrouter":
        return OpenRouterProvider()
    if provider == "anthropic":
        return AnthropicProvider()
    if provider == "litellm":
        return LiteLLMProvider()
    if provider == "command":
        return CommandProvider()
    raise WorkspaceError(f"Unknown LLM provider: {provider}")


def _ensure_provider(provider: str) -> None:
    if provider not in {entry["name"] for entry in PROVIDERS}:
        raise WorkspaceError(f"Unknown LLM provider: {provider}")


def _policy_path(paths: WorkspacePaths) -> Path:
    return paths.root / "policies" / "llm.yaml"


def _credentials_path(paths: WorkspacePaths) -> Path:
    return paths.root / "policies" / "credentials.yaml"


def _load_mapping(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise WorkspaceError(f"Expected YAML mapping: {path}")
    return data


def _load_llm_policy(paths: WorkspacePaths) -> dict[str, Any]:
    policy = _load_mapping(_policy_path(paths), default_llm_policy())
    policy.setdefault("profiles", default_llm_policy()["profiles"])
    policy.setdefault("default_profile", "deterministic")
    policy.setdefault("organization_profile", policy.get("default_profile", "deterministic"))
    policy.setdefault("actor_profiles", [])
    policy.setdefault("task_profiles", [])
    policy.setdefault("enabled", False)
    policy.setdefault("allow_network_models", False)
    return policy


def _load_credentials_registry(paths: WorkspacePaths) -> dict[str, Any]:
    registry = _load_mapping(_credentials_path(paths), default_credentials_registry())
    registry.setdefault("credentials", [])
    registry.setdefault("organization_credential", "none")
    registry.setdefault("actor_credentials", [])
    return registry


def _resolve_profile(
    policy: dict[str, Any],
    *,
    task: str,
    actor: str,
    explicit_profile: str | None,
) -> dict[str, Any]:
    profiles = _as_list(policy.get("profiles"))
    profile_id = explicit_profile
    if not profile_id:
        for entry in _as_list(policy.get("actor_profiles")):
            if entry.get("actor") == actor:
                profile_id = str(entry.get("profile"))
                break
    if not profile_id:
        for entry in _as_list(policy.get("task_profiles")):
            if entry.get("task") == task:
                profile_id = str(entry.get("profile"))
                break
    if not profile_id:
        profile_id = str(
            policy.get("organization_profile") or policy.get("default_profile") or "deterministic"
        )
    profile = _find_by_id(profiles, profile_id)
    if profile is None:
        raise WorkspaceError(f"LLM profile not found: {profile_id}")
    return dict(profile)


def _resolve_credential(
    registry: dict[str, Any],
    *,
    profile: dict[str, Any],
    actor: str,
    explicit_credential: str | None,
) -> dict[str, Any] | None:
    credential_id = explicit_credential
    if credential_id == "none":
        return None
    if not credential_id:
        for entry in _as_list(registry.get("actor_credentials")):
            if entry.get("actor") == actor:
                credential_id = str(entry.get("credential"))
                break
    if credential_id == "none":
        return None
    if not credential_id:
        credential_id = profile.get("credential")
    if credential_id == "none":
        return None
    if not credential_id:
        credential_id = registry.get("organization_credential")
    if not credential_id or credential_id == "none":
        return None
    credential = _find_by_id(_as_list(registry.get("credentials")), str(credential_id))
    if credential is None:
        raise WorkspaceError(f"LLM credential not found: {credential_id}")
    return dict(credential)


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"content-type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise WorkspaceError(f"Model provider HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise WorkspaceError(f"Model provider request failed: {exc}") from exc
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise WorkspaceError("Model provider returned non-object JSON")
    return parsed


def _auth_headers(request: ModelRequest) -> dict[str, str]:
    api_key = _api_key(request)
    provider = str(request.profile.get("provider", ""))
    if not api_key:
        return {}
    if provider == "anthropic":
        return {"x-api-key": api_key}
    return {"authorization": f"Bearer {api_key}"}


def _api_key(request: ModelRequest) -> str | None:
    api_key_env = (request.credential or {}).get("api_key_env") or request.profile.get(
        "api_key_env"
    )
    if not api_key_env:
        return None
    value = os.environ.get(str(api_key_env))
    if not value:
        raise WorkspaceError(f"Missing credential environment variable: {api_key_env}")
    return value


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise WorkspaceError("Model response did not contain valid JSON") from None
        parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise WorkspaceError("Model response JSON must be an object")
    return parsed


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _as_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise WorkspaceError("Expected list in LLM policy")
    return [item for item in value if isinstance(item, dict)]


def _find_by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def _upsert_actor_choice(
    mapping: dict[str, Any],
    key: str,
    actor: str,
    value_key: str,
    value: str,
) -> None:
    entries = _as_list(mapping.get(key))
    for entry in entries:
        if entry.get("actor") == actor:
            entry[value_key] = value
            break
    else:
        entries.append({"actor": actor, value_key: value})
    mapping[key] = entries


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, child in value.items():
            if key in {"api_key", "secret", "token", "password"}:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = _redact_secrets(child)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _is_local_base_url(base_url: str) -> bool:
    return (
        base_url.startswith("http://localhost")
        or base_url.startswith("http://127.0.0.1")
        or base_url.startswith("http://0.0.0.0")
    )
