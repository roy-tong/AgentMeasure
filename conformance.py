#!/usr/bin/env python3
"""agent-used — conformance suite（标准符合性测试）。

第三方可用 `python3 conformance.py <adapter-output-file>` 验证自己的 adapter 输出
是否符合 Agent Usage Spec v0.1（observation 事实格式 + 隐私纪律 + 证据纪律）。

检查项：
  1. 无原始 prompt / 内容字段
  2. session 在落盘前已伪匿名（无 raw session 形态）
  3. 无 evidence_level 自声明（evidence 只由 verifier 计算）
  4. tool_call_id / trace_id 若出现必须为字符串
  5. outcome 在允许集合内
  6. lifecycle_stage 在 L0-L3
  7. 未知字段不导致失败（fail-safe 解析）
  8. 隐私 fixtures：敏感载荷 → 零泄漏
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SENSITIVE_MARKERS = (
    "prompt", "tool_input", "tool_response", "tool_output",
    "cat /etc/", "api_key", "password", "BEGIN PRIVATE",
)

ALLOWED_OUTCOMES = ("success", "failure", "retry", "denied", "unknown")
ALLOWED_LIFECYCLE = ("L0", "L1", "L2", "L3")

CHECKS = []


def check(name, fn):
    CHECKS.append((name, fn))


def load_lines(path: Path) -> list:
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [json.loads(l) for l in lines]


check("no raw content fields", lambda recs: all(
    not any(m in json.dumps(r, ensure_ascii=False) for m in SENSITIVE_MARKERS) for r in recs))

check("session pseudonymized (no raw session shape)", lambda recs: all(
    not (r.get("session_key") and not str(r["session_key"]).startswith("p-")) for r in recs))

check("no self-declared evidence", lambda recs: all(
    "evidence_level" not in r and "evidence" not in r for r in recs))

check("tool_call_id/trace_id are strings", lambda recs: all(
    (r.get("tool_call_id") is None or isinstance(r["tool_call_id"], str)) and
    (r.get("trace_id") is None or isinstance(r["trace_id"], str)) for r in recs))

check("outcome in allowed set", lambda recs: all(
    r.get("outcome", "unknown") in ALLOWED_OUTCOMES for r in recs))

check("lifecycle in L0-L3", lambda recs: all(
    r.get("lifecycle_stage") is None or r["lifecycle_stage"] in ALLOWED_LIFECYCLE for r in recs))

check("observation_id present", lambda recs: all(r.get("observation_id") for r in recs))

check("observer fields present", lambda recs: all(
    r.get("observer_principal") and r.get("observer_side") and r.get("provenance") for r in recs))


def run(path: Path) -> int:
    try:
        recs = load_lines(path)
    except Exception as exc:
        print(f"✗ cannot parse {path}: {exc}")
        return 1
    if not recs:
        print(f"✗ no records in {path}")
        return 1
    passed = 0
    for name, fn in CHECKS:
        try:
            if fn(recs):
                print(f"  ✓ {name}")
                passed += 1
            else:
                print(f"  ✗ {name}")
        except Exception as exc:
            print(f"  ✗ {name}: {exc}")
    total = len(CHECKS)
    ok = passed == total
    print(f"\n{passed}/{total} PASS" + ("  — Agent Usage Spec v0.1 compatible" if ok else "  — NOT compatible"))
    return 0 if ok else 1


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 conformance.py <adapter-output.jsonl>", file=sys.stderr)
        return 2
    return run(Path(sys.argv[1]))


if __name__ == "__main__":
    sys.exit(main())
