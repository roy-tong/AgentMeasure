#!/usr/bin/env python3
"""AgentMeasure Local Analytics（Draft 0.4.3，MVP 本地面板/CLI）。

读取 Canonical Observation JSONL → collector → 六类可信指标：
  Observed Attempts · Strict Qualified Usage · Success/Failure · Latency ·
  Caller Attribution · Operation Resolution

只显示 Provider-only 拓扑真正可信的数字；不做 Choice/Value/Metering。

用法:
  python3 product/local-analytics.py <events.jsonl> [--project <id>] [--days 30]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
from collector.correlator.correlator import connect, match_invocations  # noqa: E402
from collector.aggregator.aggregator import compute  # noqa: E402
from collector.ingest import ingest_canonical_jsonl  # noqa: E402


def resolve_events(path: Path) -> list:
    """接受单个文件 / 目录（glob agentmeasure-events*.jsonl）/ glob 模式。"""
    if path.is_dir():
        return sorted(path.glob("agentmeasure-events*.jsonl"))
    if "*" in str(path):
        return sorted(Path().glob(str(path)))
    return [path]


def report(events_path: Path, project: str, days: int = 30) -> dict:
    tmp = Path(tempfile.mkdtemp())
    conn = connect(tmp / "collector.db")
    files = resolve_events(events_path)
    if not files:
        raise FileNotFoundError(f"no events files matched: {events_path}")
    ingested = {"accepted": 0, "rejected": 0, "reject_reasons": {}}
    for f in files:
        r = ingest_canonical_jsonl(
            conn, f, source="provider-sdk", project_id=project,
            principal="local-analytics")
        ingested["accepted"] += r["accepted"]
        ingested["rejected"] += r["rejected"]
        for k, v in (r.get("reject_reasons") or {}).items():
            ingested["reject_reasons"][k] = ingested["reject_reasons"].get(k, 0) + v
    match_invocations(conn)
    s = compute(conn, project, days=days)
    return {"ingest": ingested, "stats": s, "files": [str(f) for f in files]}


def render(r: dict) -> str:
    s = r["stats"]
    i = r["ingest"]
    lines = [
        "AgentMeasure Local Analytics — Provider-observed Capability Usage",
        "=" * 58,
        f"Canonical observations accepted : {i['accepted']}   rejected: {i['rejected']}",
        f"  reject reasons               : {i['reject_reasons'] or 'none'}",
        "",
        "Observed attempts               : %d" % s["attempts"],
        "Strict Qualified attempts      : %d (%s%%)" % (
            s["qualified_invocations"],
            f"{s['qualified_rate'] * 100:.1f}"),
        "  qualification status         : %s" % {k: v for k, v in s["qualification_status"].items()},
        "",
        "Success / Failure              : success-rate %s%%  unknown/inconsistent %d"
        % (f"{s['success_rate'] * 100:.1f}", s["unknown_or_inconsistent_outcomes"]),
        "Latency (duration_ms)          : " + _latency(s),
        "",
        "Operation resolution           : resolved %d / %d attempts (coverage %s%%)"
        % (s["resolved_operations"], s["attempts"],
           f"{s['operation_resolution_coverage'] * 100:.1f}"),
        f"  resolution                   : {s['operation_resolution']}",
        f"  legacy_attempt_equivalent    : {s['legacy_attempt_equivalent']} (0.3 迁移期)",
        "",
        "Caller attribution             : " + _caller(s),
        "Measurement coverage           : participating_network (observed only)",
    ]
    return "\n".join(lines)


def _latency(s: dict) -> str:
    l = s.get("latency") or {}
    if not l.get("count"):
        return "no duration_ms observations (unknown)"
    buckets = " · ".join(f"{k}:{v}" for k, v in (l.get("buckets") or {}).items() if v)
    return (f"n={l['count']} mean={l.get('mean_ms')}ms p50={l.get('p50_ms')}ms "
            f"p95={l.get('p95_ms')}ms min={l.get('min_ms')}ms max={l.get('max_ms')}ms "
            f"[{buckets}]")


def _caller(s: dict) -> str:
    by_runtime = s.get("caller_by_runtime") or {}
    by_strength = s.get("caller_by_strength") or {}
    if not by_runtime:
        return "no caller claims (all unknown)"
    parts = [f"{rt}:{n}" for rt, n in sorted(by_runtime.items())]
    strength = " / ".join(f"{k}={v}" for k, v in sorted(by_strength.items()))
    return f"{' '.join(parts)} (strength: {strength})"


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("events", type=Path, help="canonical observations JSONL")
    parser.add_argument("--project", default="local")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args(argv)
    if not args.events.exists():
        print(f"events file not found: {args.events}", file=sys.stderr)
        return 2
    r = report(args.events, args.project, days=args.days)
    print(render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
