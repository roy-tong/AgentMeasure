#!/usr/bin/env python3
"""AgentMeasure metric registry validator（零依赖，Draft 0.4.2）。

用法: python3 registry/validate_metrics.py
校验 registry/metrics.yaml：
  - 结构（id/name/family/grain/object/status 等必填）
  - 枚举（status: defined|draft|proposed|research）
  - 与 METRICS.md 的指标 ID 一致（METRICS.md 中出现的 Mx.y 都必须在 registry，
    反之亦然——Metric Contract 是唯一事实源）
退出码：0 = 通过；1 = 失败。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from mini_yaml import parse  # noqa: E402

METRICS_YAML = ROOT / "metrics.yaml"
METRICS_MD = ROOT.parent / "standard" / "METRICS.md"

STATUSES = ("defined", "draft", "proposed", "research")
FAMILIES = ("adoption-relationship", "choice", "execution", "utility",
            "outcome", "distribution")
REQUIRED = ("id", "name", "family", "grain", "object", "status",
            "numerator", "denominator", "qualification", "dedup")


def main() -> int:
    data = parse(METRICS_YAML.read_text(encoding="utf-8"))
    metrics = data.get("metrics", [])
    failed = 0
    if not isinstance(metrics, list) or not metrics:
        print("  ✗ metrics.yaml: 'metrics' 必须是非空 list")
        return 1

    ids = set()
    for m in metrics:
        mid = m.get("id")
        if not isinstance(mid, str) or not re.fullmatch(r"M[0-9]\.[0-9]", mid):
            print(f"  ✗ {mid}: id 格式应为 M<f>.<n>")
            failed += 1
            continue
        ids.add(mid)
        for key in REQUIRED:
            if key not in m:
                print(f"  ✗ {mid}: 缺少 '{key}'")
                failed += 1
        if m.get("status") not in STATUSES:
            print(f"  ✗ {mid}: status {m.get('status')!r} 不在 {STATUSES}")
            failed += 1
        if m.get("family") not in FAMILIES:
            print(f"  ✗ {mid}: family {m.get('family')!r} 不在 {FAMILIES}")
            failed += 1
        q = m.get("qualification") or {}
        if q.get("context") != "production" or q.get("validity") != "normal":
            print(f"  ✗ {mid}: qualification 必须是 Strict Qualified (production+normal)")
            failed += 1
        if not failed and mid:
            print(f"  ✓ {mid} {m.get('name', '')} ({m.get('status')})")

    # 与 METRICS.md 的指标 ID 一致性（双向）
    md_text = METRICS_MD.read_text(encoding="utf-8")
    md_ids = set(re.findall(r"^### (M[0-9]\.[0-9])", md_text, re.M))
    only_md = sorted(md_ids - ids)
    only_reg = sorted(ids - md_ids)
    if only_md:
        print(f"  ✗ METRICS.md 有但 registry 缺: {only_md}")
        failed += 1
    if only_reg:
        print(f"  ✗ registry 有但 METRICS.md 缺: {only_reg}")
        failed += 1

    print(f"\nmetric registry {'VALID' if failed == 0 else f'{failed} ERROR(S)'} "
          f"({len(metrics)} metrics)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
