#!/usr/bin/env python3
"""map_to_fmt002.py — 把任意事件流按映射表转成 FMT-002 funnel-event JSONL。

用法：
  python3 scripts/map_to_fmt002.py --mapping map.json --input calls.jsonl --out fmt002.jsonl

这是免费测量任务（free measurement runs）使用的映射器，随项目开源：
docs/review-method/ 里有映射表格式（fmt002-input-and-mapping.md）与完整 run-book。
只做字段搬运与整型强转，不推断、不补造数据：每条记录须有真实会话/任务归属；
任何缺字段、重复身份或 schema 错误拒绝整份输入，不输出部分样本。
"""
from __future__ import annotations

import argparse
import json
import sys
import os
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "lab"))
from verovo_lab.schemas import validate
EVENT_SCHEMA = json.loads((REPO / "lab/schemas/funnel-event.schema.json").read_text())

SCHEMA = "verovo.lab/funnel-event"
SCHEMA_VERSION = "1.0.0"


def resolve(src: dict, spec):
    """spec 是字符串：'@字面量' 取字面量，否则取源字段（缺失返回 KeyError 上抛）。"""
    if isinstance(spec, str) and spec.startswith("@"):
        return spec[1:]
    if spec not in src:
        raise KeyError(f"source field missing: {spec}")
    return src[spec]


def convert_line(src: dict, envelope: dict, rules: list) -> dict:
    rule = None
    for r in rules:
        cond = r.get("when", {})
        f, v = cond.get("field"), cond.get("equals")
        if f is None or src.get(f) == v:
            rule = r
            break
    if rule is None:
        raise ValueError("no event rule matched")
    out = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "event": rule["event"],
        **{k: v for k, v in envelope.items()},
    }
    for fmt_field, spec in rule.get("map", {}).items():
        try:
            val = resolve(src, spec)
        except KeyError as e:
            raise KeyError(f"[{rule['event']}] {fmt_field}: {e}") from e
        if val is not None:
            tr = rule.get("translate", {}).get(fmt_field)
            if tr is not None and val in tr:
                val = tr[val]
            out[fmt_field] = val
    for fld in ("operation_index", "attempt_index", "steps", "latency_ms",
                "replicate", "attempts"):
        if fld in out:
            v = out[fld]
            if isinstance(v, int) and not isinstance(v, bool):
                continue
            if isinstance(v, float) and v.is_integer():
                out[fld] = int(v)
            elif isinstance(v, str) and v.isdigit():
                out[fld] = int(v)
            # 其余类型保留原值，交给 schema 校验报错
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    source, output = Path(args.input), Path(args.out)
    if output.resolve() in (source.resolve(), Path(args.mapping).resolve()):
        ap.error("output must not overwrite input or mapping")
    try:
        cfg = json.loads(Path(args.mapping).read_text())
        envelope, rules = cfg["envelope"], cfg["event_rules"]
        identity_field = cfg.get("identity_field")
        if not isinstance(identity_field, str) or not identity_field:
            raise ValueError("identity_field must name a real session/task scope field; constant assignment_id is unsafe")
        records = []
        seen_attempts = set()
        seen_operations = set()
        for n, line in enumerate(source.read_text().splitlines(), 1):
            if not line.strip():
                continue
            src = json.loads(line)
            if not isinstance(src, dict):
                raise ValueError(f"line {n}: event must be an object")
            scope = src.get(identity_field)
            if not isinstance(scope, str) or not scope.strip():
                raise ValueError(f"line {n}: missing/non-string scope {identity_field}")
            rec = convert_line(src, envelope, rules)
            # Never group operations from independent sessions under a constant.
            rec["assignment_id"] = scope
            validate(rec, EVENT_SCHEMA)
            for key in ("schema", "schema_version", "event"):
                if key in envelope:
                    raise ValueError(f"envelope must not override {key}")
            if rec["event"] == "attempt":
                key = (scope, rec["operation_index"], rec["attempt_index"])
                if key in seen_attempts:
                    raise ValueError(f"line {n}: duplicate attempt identity; investigate, do not deduplicate")
                seen_attempts.add(key)
            if rec["event"] == "operation_result":
                key = (scope, rec["operation_index"])
                if key in seen_operations:
                    raise ValueError(f"line {n}: duplicate operation result")
                seen_operations.add(key)
            json.dumps(rec, allow_nan=False)
            records.append(rec)
        if not records:
            raise ValueError("empty sample")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"REFUSED: {exc}; output not changed", file=sys.stderr)
        return 2
    # All rows validated before publishing; no partial sample can be audited.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         delete=False) as fh:
            tmp = fh.name
            for rec in records:
                fh.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")
        os.replace(tmp, output)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    print(f"converted={len(records)} dropped=0 scopes={len({r['assignment_id'] for r in records})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
