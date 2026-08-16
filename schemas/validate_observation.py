#!/usr/bin/env python3
"""AgentMeasure canonical observation validator（零依赖，Draft 0.4.3）。

用法: python3 schemas/validate_observation.py
校验 schemas/examples/observations.json 中的每条 observation：
  - Envelope 符合 schemas/observation.schema.json
  - payload 符合 schemas/payloads/<type>.schema.json
证明：任何 Adapter 只能产出一种 Canonical Observation（单一输入格式）。
退出码：0 = 全部通过；1 = 失败。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "registry"))
from mini_yaml import parse  # noqa: E402

# 复用 registry 校验器子集
sys.path.insert(0, str(ROOT.parent / "registry"))
from validate_entities import validate as schema_validate  # noqa: E402

ENVELOPE = ROOT / "observation.schema.json"
PAYLOADS = ROOT / "payloads"
EXAMPLES = ROOT / "examples" / "observations.json"


def main() -> int:
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    payload_schemas = {p.name.split(".")[0].replace("-", "_"): json.loads(p.read_text(encoding="utf-8"))
                       for p in sorted(PAYLOADS.glob("*.json"))}
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    failed = 0
    for obs in data["observations"]:
        oid = obs.get("observation_id", "?")
        errors = schema_validate(obs, envelope, f"observation.{oid}")
        # payload 类型化校验
        otype = obs.get("observation_type")
        key = otype.replace("-", "_") if otype else None
        payload = obs.get("payload")
        if key in payload_schemas:
            errors += schema_validate(payload, payload_schemas[key], f"observation.{oid}.payload")
        else:
            errors.append(f"observation.{oid}: 未知 observation_type {otype!r}")
        # Caller Claim 自洽性（type ↔ strength 必须兼容）
        caller = obs.get("caller") or {}
        ctype = caller.get("type", "unknown")
        strength = caller.get("identity_strength", "unknown")
        compatible = {
            "unknown": {"unknown"},
            "claimed_agent": {"declared"},
            "correlated_agent": {"correlated"},
            "platform_attested": {"attested"},
        }.get(ctype, set())
        if strength not in compatible:
            errors.append(
                f"observation.{oid}: caller type={ctype!r} 与 strength={strength!r} 矛盾"
                f"（claimed→declared / correlated_agent→correlated / platform_attested→attested）")
        # 非法时间戳已由 schema pattern 拒绝
        if errors:
            failed += 1
            for e in errors:
                print(f"  ✗ {e}")
        else:
            print(f"  ✓ {oid} ({otype})")
    print(f"\ncanonical observation {'VALID' if failed == 0 else f'{failed} INVALID'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
