#!/usr/bin/env python3
"""AgentMeasure registry validator（零依赖，JSON Schema 子集）。

用法: python3 registry/validate_entities.py
校验：
  - registry/entities/*.yaml   → schemas/entity.schema.json
  - registry/project-identity/*.json → 结构性检查（既有格式）
退出码：0 = 全部通过；1 = 任一失败。

支持的 JSON Schema 子集：type / required / properties / additionalProperties /
items / enum / pattern。用于 AgentMeasure 自有 schema，非通用校验器。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from mini_yaml import parse  # noqa: E402

ENTITIES_DIR = ROOT / "entities"
PROJECT_DIR = ROOT / "project-identity"
SCHEMA_FILE = ROOT.parent / "schemas" / "entity.schema.json"


def validate(value, schema, path: str = "$") -> list:
    errors = []
    # fail-closed（#8 同类防护）：本子集不支持的组合关键字显式报错，
    # 绝不静默跳过——否则 schema 声明了 oneOf 而校验器装作没看见。
    for kw in ("oneOf", "anyOf", "allOf", "not"):
        if kw in schema:
            errors.append(f"{path}: schema uses unsupported keyword {kw!r} (fail-closed)")
    typ = schema.get("type")
    if typ == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object, got {type(value).__name__}")
            return errors
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required property '{req}'")
        props = schema.get("properties", {})
        for key, v in value.items():
            if key in props:
                errors += validate(v, props[key], f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property '{key}'")
    elif typ == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array, got {type(value).__name__}")
            return errors
        item_schema = schema.get("items", {})
        for idx, item in enumerate(value):
            errors += validate(item, item_schema, f"{path}[{idx}]")
    elif typ == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string, got {type(value).__name__}")
        else:
            pattern = schema.get("pattern")
            if pattern and not re.fullmatch(pattern, value):
                errors.append(f"{path}: '{value}' does not match pattern {pattern!r}")
    elif typ == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean, got {type(value).__name__}")
    elif typ == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer, got {type(value).__name__}")
    elif typ is not None and value is not None:
        errors.append(f"{path}: unknown type constraint {typ!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']}")
    return errors


def validate_entity_yaml(path: Path, schema: dict) -> list:
    try:
        data = parse(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{path.name}: YAML 解析失败: {exc}"]
    return [f"{path.name}: {e}" for e in validate(data, schema)]


def validate_project_json(path: Path) -> list:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path.name}: JSON 解析失败: {exc}"]
    for key in ("project_id", "name", "declared_by", "verified"):
        if key not in data:
            errors.append(f"{path.name}: 缺少 '{key}'")
    if not isinstance(data.get("verified"), bool):
        errors.append(f"{path.name}: 'verified' 必须是 boolean")
    if not isinstance(data.get("tools"), list):
        errors.append(f"{path.name}: 'tools' 必须是 list")
    return errors


def main() -> int:
    failed = 0
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    for path in sorted(ENTITIES_DIR.glob("*.yaml")):
        errs = validate_entity_yaml(path, schema)
        if errs:
            failed += 1
            for e in errs:
                print(f"  ✗ {e}")
        else:
            print(f"  ✓ {path.name}（{path.stat().st_size} bytes）")
    for path in sorted(PROJECT_DIR.glob("*.json")):
        errs = validate_project_json(path)
        if errs:
            failed += 1
            for e in errs:
                print(f"  ✗ {e}")
        else:
            print(f"  ✓ {path.name}")
    print(f"\nregistry {'VALID' if failed == 0 else f'{failed} FILE(S) INVALID'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
