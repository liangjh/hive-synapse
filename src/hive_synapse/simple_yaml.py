"""Small YAML-compatible parser/dumper used without runtime dependencies.

Module guide:
- `safe_dump` serializes simple Python values to YAML-like text.
- `safe_load` parses the subset Hive writes and reads.
- `YamlError` reports unsupported or invalid YAML input.

Maintenance: update this guide when adding public functions/classes to this module.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any


class YamlError(ValueError):
    """Raised when the built-in YAML subset parser cannot read a document."""


def safe_dump(data: Any, *, sort_keys: bool = False, allow_unicode: bool = True) -> str:
    del allow_unicode
    return _dump(data, indent=0, sort_keys=sort_keys).rstrip() + "\n"


def safe_load(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    lines = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        lines.append(raw_line.rstrip())
    if not lines:
        return None
    value, index = _parse_block(lines, 0, _indent(lines[0]))
    if index != len(lines):
        raise YamlError(f"Unexpected trailing content at line {index + 1}")
    return value


def _dump(value: Any, *, indent: int, sort_keys: bool) -> str:
    prefix = " " * indent
    if isinstance(value, Mapping):
        items: Iterable[tuple[Any, Any]] = value.items()
        if sort_keys:
            items = sorted(items, key=lambda item: str(item[0]))
        rendered: list[str] = []
        for key, child in items:
            key_text = str(key)
            if _is_scalar(child):
                rendered.append(f"{prefix}{key_text}: {_format_scalar(child)}")
            elif child == []:
                rendered.append(f"{prefix}{key_text}: []")
            elif child == {}:
                rendered.append(f"{prefix}{key_text}: {{}}")
            else:
                rendered.append(f"{prefix}{key_text}:")
                rendered.append(_dump(child, indent=indent + 2, sort_keys=sort_keys))
        return "\n".join(rendered)
    if isinstance(value, list):
        rendered = []
        for item in value:
            if _is_scalar(item):
                rendered.append(f"{prefix}- {_format_scalar(item)}")
            elif isinstance(item, Mapping):
                item_items = list(item.items())
                if not item_items:
                    rendered.append(f"{prefix}- {{}}")
                    continue
                first_key, first_value = item_items[0]
                if _is_scalar(first_value):
                    rendered.append(f"{prefix}- {first_key}: {_format_scalar(first_value)}")
                else:
                    rendered.append(f"{prefix}- {first_key}:")
                    rendered.append(_dump(first_value, indent=indent + 4, sort_keys=sort_keys))
                for key, child in item_items[1:]:
                    if _is_scalar(child):
                        rendered.append(f"{prefix}  {key}: {_format_scalar(child)}")
                    elif child == []:
                        rendered.append(f"{prefix}  {key}: []")
                    elif child == {}:
                        rendered.append(f"{prefix}  {key}: {{}}")
                    else:
                        rendered.append(f"{prefix}  {key}:")
                        rendered.append(_dump(child, indent=indent + 4, sort_keys=sort_keys))
            else:
                rendered.append(f"{prefix}-")
                rendered.append(_dump(item, indent=indent + 2, sort_keys=sort_keys))
        return "\n".join(rendered)
    return f"{prefix}{_format_scalar(value)}"


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_block(lines: list[str], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return None, index
    stripped = lines[index][indent:]
    if stripped.startswith("- ") or stripped == "-":
        return _parse_list(lines, index, indent)
    return _parse_dict(lines, index, indent)


def _parse_dict(lines: list[str], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        line = lines[index]
        current_indent = _indent(line)
        if current_indent < indent:
            break
        if current_indent > indent:
            raise YamlError(f"Unexpected indentation at line {index + 1}")
        stripped = line[indent:]
        if stripped.startswith("- ") or stripped == "-":
            break
        if ":" not in stripped:
            raise YamlError(f"Expected key/value at line {index + 1}")
        key, rest = stripped.split(":", 1)
        key = key.strip()
        rest = rest.strip()
        if rest:
            result[key] = _parse_scalar(rest)
            index += 1
            continue
        index += 1
        if index >= len(lines) or _indent(lines[index]) <= indent:
            result[key] = None
            continue
        result[key], index = _parse_block(lines, index, _indent(lines[index]))
    return result, index


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        line = lines[index]
        current_indent = _indent(line)
        if current_indent < indent:
            break
        if current_indent > indent:
            raise YamlError(f"Unexpected indentation at line {index + 1}")
        stripped = line[indent:]
        if not stripped.startswith("-"):
            break
        rest = stripped[1:].strip()
        if not rest:
            index += 1
            if index >= len(lines) or _indent(lines[index]) <= indent:
                result.append(None)
                continue
            item, index = _parse_block(lines, index, _indent(lines[index]))
            result.append(item)
            continue
        if ":" in rest and not rest.startswith(('"', "'", "[", "{")):
            key, value_text = rest.split(":", 1)
            item: dict[str, Any] = {}
            if value_text.strip():
                item[key.strip()] = _parse_scalar(value_text.strip())
                index += 1
            else:
                index += 1
                if index < len(lines) and _indent(lines[index]) > indent + 2:
                    item[key.strip()], index = _parse_block(lines, index, _indent(lines[index]))
                else:
                    item[key.strip()] = None
            while index < len(lines) and _indent(lines[index]) == indent + 2:
                child_line = lines[index][indent + 2 :]
                if child_line.startswith("- ") or ":" not in child_line:
                    break
                child_key, child_rest = child_line.split(":", 1)
                child_rest = child_rest.strip()
                if child_rest:
                    item[child_key.strip()] = _parse_scalar(child_rest)
                    index += 1
                else:
                    index += 1
                    if index < len(lines) and _indent(lines[index]) > indent + 2:
                        item[child_key.strip()], index = _parse_block(
                            lines, index, _indent(lines[index])
                        )
                    else:
                        item[child_key.strip()] = None
            result.append(item)
            continue
        result.append(_parse_scalar(rest))
        index += 1
    return result, index


def _parse_scalar(value: str) -> Any:
    if value in {"null", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value in {"[]", "{}"}:
        return [] if value == "[]" else {}
    if value.startswith(('"', "[", "{")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value.strip("'")
