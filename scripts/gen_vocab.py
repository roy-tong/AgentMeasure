#!/usr/bin/env python3
"""AgentMeasure vocabulary generator & drift checker（单一事实源，Draft 0.4.3）。

`registry/vocabularies.yaml` 是受管枚举的单一事实源。

--build：
  - 重写 schemas/observation.schema.json 的受管 enum（usage_context / validity /
    context_source / validity_source / caller.type / caller.identity_strength /
    observer.side / provenance / observation_type）
  - 生成 registry/VOCABULARIES.md

--check（CI）：
  - 校验 observation.schema.json 受管 enum 与 yaml 一致
  - 校验 sdk/src/index.ts 的 TS 联合类型字面量与 yaml 一致
  - 校验 reference/collector/usage.py 的 Python 元组与 yaml 一致
  任何漂移 → 退出码 1。

用法:
  python3 scripts/gen_vocab.py --build
  python3 scripts/gen_vocab.py --check
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "registry"))
from mini_yaml import parse as yaml_parse  # noqa: E402

VOCAB = ROOT / "registry" / "vocabularies.yaml"
SCHEMA = ROOT / "schemas" / "observation.schema.json"
MD_OUT = ROOT / "registry" / "VOCABULARIES.md"
SDK_TS = ROOT / "sdk" / "src" / "index.ts"
USAGE_PY = ROOT / "reference" / "collector" / "usage.py"

# yaml key → JSON Schema enum 路径
SCHEMA_ENUM_PATHS = {
    "usage_context": ("properties", "usage_context", "enum"),
    "validity": ("properties", "validity", "enum"),
    "context_source": ("properties", "context_source", "enum"),
    "validity_source": ("properties", "validity_source", "enum"),
    "caller_type": ("properties", "caller", "properties", "type", "enum"),
    "caller_identity_strength": ("properties", "caller", "properties", "identity_strength", "enum"),
    "observer_side": ("properties", "observer", "properties", "side", "enum"),
    "provenance": ("properties", "provenance", "enum"),
    "observation_type": ("properties", "observation_type", "enum"),
}

# yaml key → TS 联合类型名（只检查 index.ts 中实际导出的类型）
TS_TYPES = {
    "usage_context": "UsageContext",
    "validity": "Validity",
    "caller_type": "CallerType",
    "caller_identity_strength": "CallerStrength",
    "observation_type": "ObservationType",
}

# yaml key → usage.py 元组名
PY_TUPLES = {
    "usage_context": "USAGE_CONTEXTS",
    "validity": "VALIDITIES",
    "context_source": "CONTEXT_SOURCES",
    "validity_source": "VALIDITY_SOURCES",
    "caller_identity_strength": "CALLER_STRENGTHS",
    "observer_side": "SIDES",
    "provenance": "PROVENANCES",
    "observation_type": "OBSERVATION_TYPES",
}

DOC_NAMES = {
    "usage_context": "Usage Context（Core §7，数据环境语义）",
    "validity": "Validity（Core §7，执行有效性）",
    "context_source": "Context Source",
    "validity_source": "Validity Source",
    "caller_type": "Caller Type（TRUST §5）",
    "caller_identity_strength": "Caller Identity Strength（TRUST §5）",
    "observer_side": "Observer Side",
    "provenance": "Provenance",
    "observation_type": "Observation Type（DATA §1）",
    "choice_mode": "Choice Mode（Core §6 三轴）",
    "decision_authority": "Decision Authority（Core §6 三轴）",
    "selection_constraint": "Selection Constraint（Core §6 三轴）",
}


def load_vocab() -> dict:
    return yaml_parse(VOCAB.read_text(encoding="utf-8"))


def _get(d: dict, path: tuple):
    cur = d
    for k in path:
        cur = cur[k]
    return cur


def _set(d: dict, path: tuple, value):
    cur = d
    for k in path[:-1]:
        cur = cur[k]
    cur[path[-1]] = value


def build(vocab: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for key, path in SCHEMA_ENUM_PATHS.items():
        _set(schema, path, list(vocab[key]))
    SCHEMA.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")

    lines = [
        "# AgentMeasure — Vocabulary Registry（由 scripts/gen_vocab.py 生成，勿手改）",
        "",
        f"> 单一事实源：`registry/vocabularies.yaml`（vocab revision 0.4.3-2）。",
        "> 消费者：`schemas/observation.schema.json`（生成）· `sdk/src/index.ts`（CI 校验）·",
        "> `reference/collector/usage.py`（CI 校验）。",
        "",
    ]
    for key, doc in DOC_NAMES.items():
        lines.append(f"## {key} — {doc}")
        lines.append("")
        lines.append("```text")
        lines.append(" · ".join(vocab.get(key, [])))
        lines.append("```")
        lines.append("")
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"vocab --build: {len(SCHEMA_ENUM_PATHS)} schema enums rewritten, "
          f"{MD_OUT.name} generated")


def check(vocab: dict) -> int:
    fails: list[str] = []

    # 1) JSON Schema
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for key, path in SCHEMA_ENUM_PATHS.items():
        actual = _get(schema, path)
        expected = list(vocab[key])
        if actual != expected:
            fails.append(f"schema {key}: {actual} != {expected}")

    # 2) TypeScript（index.ts 导出的联合类型）
    ts_src = SDK_TS.read_text(encoding="utf-8")
    for key, type_name in TS_TYPES.items():
        m = re.search(
            rf"export type {type_name}\s*=\s*(.*?);", ts_src, re.S)
        if not m:
            fails.append(f"ts: type {type_name} not found in {SDK_TS.name}")
            continue
        literals = set(re.findall(r'"([a-z_]+)"', m.group(1)))
        expected = set(vocab[key])
        if literals != expected:
            fails.append(f"ts {type_name}: missing={expected - literals} extra={literals - expected}")

    # 3) Python（usage.py 元组）
    py_src = USAGE_PY.read_text(encoding="utf-8")
    for key, tuple_name in PY_TUPLES.items():
        m = re.search(rf"{tuple_name}\s*=\s*\((.*?)\)", py_src, re.S)
        if not m:
            fails.append(f"py: {tuple_name} not found in {USAGE_PY.name}")
            continue
        literals = set(re.findall(r'"([a-z_]+)"', m.group(1)))
        expected = set(vocab[key])
        if literals != expected:
            fails.append(f"py {tuple_name}: missing={expected - literals} extra={literals - expected}")

    if fails:
        print("VOCAB DRIFT:")
        for f in fails:
            print("  - " + f)
        print(f"fix: update registry/vocabularies.yaml then run "
              f"`python3 scripts/gen_vocab.py --build` (and sync TS/Python consumers)")
        return 1
    print(f"vocab --check: {len(vocab)} vocabularies in sync "
          f"(schema/TS/Python consumers)")
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    vocab = load_vocab()
    if args.build:
        build(vocab)
        return 0
    return check(vocab)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
