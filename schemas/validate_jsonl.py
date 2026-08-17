#!/usr/bin/env python3
"""AgentMeasure canonical JSONL validator（零依赖，Draft 0.4.3）。

用法: python3 schemas/validate_jsonl.py <observations.jsonl>

校验每一行都是合法 Canonical Observation Envelope（顶层 schema +
per-type payload + caller 自洽），与 Collector ingestion 使用同一套校验
（reference/collector/ingest.py validate_canonical）。

用途：
  - Provider SDK 测试（sdk/test/schema.test.mjs）
  - CI：SDK 管道端到端（examples → JSONL → 本校验 → ingest → metrics）

退出码：0 = 全部通过；1 = 存在非法行；2 = 用法错误。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "registry"))
sys.path.insert(0, str(ROOT / "reference"))
from collector.ingest import validate_canonical  # noqa: E402


def main(argv) -> int:
    if len(argv) != 1:
        print("usage: python3 schemas/validate_jsonl.py <observations.jsonl>",
              file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 2
    failed = 0
    total = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        total += 1
        try:
            envelope = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"line {lineno}: invalid JSON: {exc}")
            failed += 1
            continue
        errors = validate_canonical(envelope)
        if errors:
            failed += 1
            print(f"line {lineno}: " + "; ".join(errors))
    if failed:
        print(f"validation failed: {failed}/{total} invalid observation(s) in {path}")
        return 1
    print(f"validation OK: {total} canonical observation(s) in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
