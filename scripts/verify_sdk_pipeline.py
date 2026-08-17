#!/usr/bin/env python3
"""AgentMeasure SDK pipeline gate（External-Ready，禁止绕过 canonical ingestion）。

跑通并断言完整链路——所有输入都经过 Collector 唯一 canonical 入口：

    SDK fixture (examples/mcp-integration.js)
      → Canonical Observation JSONL
      → 逐行 validate_canonical（与 ingestion 同一校验）
      → ingest_canonical_jsonl（唯一 canonical 输入）
      → match_invocations → compute
      → 断言期望输出

用法:
  python3 scripts/verify_sdk_pipeline.py [--events <file>] [--project demo/acme-weather]

--events 缺省时自行运行 v1 示例（独立临时目录，不触碰 ~/.agentmeasure）。
退出码：0 = gate 通过；1 = 断言失败；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "registry"))
from collector.ingest import ingest_canonical_jsonl, validate_canonical  # noqa: E402
from collector.correlator.correlator import connect, match_invocations  # noqa: E402
from collector.aggregator.aggregator import compute  # noqa: E402

EXPECTED = {
    "observations": 84,
    "accepted": 84,
    "rejected": 0,
    "attempts": 42,
    "qualified": 0,
    "operation_resolution_coverage": 0.0,
    "caller_by_runtime": {"claude": 14, "codex": 14, "unknown": 14},
    "latency_count": 42,
    "types": {"attempt_started", "attempt_completed"},
}


def run_example(events_dir: Path) -> int:
    env = dict(os.environ, AGENTMEASURE_EVENTS_DIR=str(events_dir))
    return subprocess.run(
        ["node", "examples/mcp-integration.js"],
        cwd=str(ROOT / "sdk"), env=env, capture_output=True, text=True,
        timeout=180,
    )


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path)
    parser.add_argument("--project", default="demo/acme-weather")
    args = parser.parse_args(argv)

    tmp = Path(tempfile.mkdtemp(prefix="am-pipeline-gate-"))
    try:
        if args.events:
            events_file = args.events
        else:
            events_dir = tmp / "events"
            r = run_example(events_dir)
            if r.returncode != 0:
                print(f"example failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
                return 1
            events_file = events_dir / "agentmeasure-events.jsonl"

        # 1) canonical validation（与 ingestion 同一校验器）
        lines = [l for l in events_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        errors = 0
        for lineno, line in enumerate(lines, 1):
            env = json.loads(line)
            errs = validate_canonical(env)
            if errs:
                errors += 1
                print(f"line {lineno}: " + "; ".join(errs))
        if errors:
            print(f"GATE FAIL: {errors} invalid canonical observation(s)")
            return 1
        if len(lines) != EXPECTED["observations"]:
            print(f"GATE FAIL: expected {EXPECTED['observations']} observations, got {len(lines)}")
            return 1

        types = {json.loads(l)["observation_type"] for l in lines}
        if types != EXPECTED["types"]:
            print(f"GATE FAIL: provider emitted types {sorted(types)}; "
                  f"must be only {sorted(EXPECTED['types'])} (no invented events)")
            return 1

        # 2) canonical ingestion → metrics（Collector 唯一输入路径）
        conn = connect(tmp / "collector.db")
        ingested = ingest_canonical_jsonl(
            conn, events_file, source="provider-sdk",
            project_id=args.project, principal="pipeline-gate")
        match_invocations(conn)
        s = compute(conn, args.project, days=365)

        failures = []
        if ingested["accepted"] != EXPECTED["accepted"]:
            failures.append(f"accepted {ingested['accepted']} != {EXPECTED['accepted']}")
        if ingested["rejected"] != EXPECTED["rejected"]:
            failures.append(f"rejected {ingested['rejected']} != {EXPECTED['rejected']}")
        if s["attempts"] != EXPECTED["attempts"]:
            failures.append(f"attempts {s['attempts']} != {EXPECTED['attempts']}")
        if s["qualified_invocations"] != EXPECTED["qualified"]:
            failures.append(f"qualified {s['qualified_invocations']} != {EXPECTED['qualified']} (synthetic must not qualify)")
        if s["operation_resolution_coverage"] != EXPECTED["operation_resolution_coverage"]:
            failures.append(f"op resolution coverage {s['operation_resolution_coverage']} != 0.0 (fail-closed)")
        if s.get("caller_by_runtime") != EXPECTED["caller_by_runtime"]:
            failures.append(f"caller_by_runtime {s.get('caller_by_runtime')} != {EXPECTED['caller_by_runtime']}")
        lat = s.get("latency") or {}
        if lat.get("count") != EXPECTED["latency_count"]:
            failures.append(f"latency count {lat.get('count')} != {EXPECTED['latency_count']}")

        if failures:
            print("GATE FAIL:")
            for f in failures:
                print("  - " + f)
            return 1

        print(f"GATE PASS: {len(lines)} canonical observations → {ingested['accepted']} accepted, "
              f"0 rejected → {s['attempts']} attempts, 0 qualified (synthetic), "
              f"caller {s['caller_by_runtime']}, latency n={lat.get('count')} p50={lat.get('p50_ms')}ms")
        return 0
    finally:
        if not args.events:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
