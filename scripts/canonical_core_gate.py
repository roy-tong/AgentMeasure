#!/usr/bin/env python3
"""AgentMeasure core semantics gate（0.4.3，全部经 canonical ingestion）。

取代旧的 store_observation + lifecycle_stage 直构测试：本门禁只通过
Collector 唯一 canonical 输入（ingest_canonical_jsonl）喂数据，任何测试
都不再绕过 canonical boundary。

覆盖（与 Core 不变量一致）：
  1. 100 次双边调用 → 100 attempts；无 operation 证据 → 0 operations（无回退）
  2. 单边单观察 → evidence=observed（最低显示等级）
  3. 显式 operation_id → 3 attempts 归并为 1 operation，coverage 1.0
  4. qualification 冲突（production vs test）→ inconsistent（不压平）

用法: python3 scripts/canonical_core_gate.py
退出码：0 = gate 通过；1 = 断言失败。
"""
from __future__ import annotations

import json
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "registry"))
from collector.correlator.correlator import connect, match_invocations  # noqa: E402
from collector.aggregator.aggregator import compute  # noqa: E402
from collector.ingest import ingest_canonical_jsonl  # noqa: E402

PROJECT = "github.com/foo/bar"


def envelope(otype: str, payload: dict, principal: str, side: str, ts: str,
             ctx: str = "unknown", val: str = "unknown",
             tool: str = "foo.search", provenance: str = "wrapper",
             ctx_source: str = "none", val_source: str = "none") -> dict:
    return {
        "spec_version": "agentmeasure-0.4",
        "observation_id": str(uuid.uuid4()),
        "observation_type": otype,
        "observer": {"principal": principal, "trust_domain": "t", "side": side},
        "observed_at": ts,
        "deployment_context": {"project_id": PROJECT},
        "surface": {"surface_id": f"mcp_tool:{tool}", "surface_namespace": "mcp"},
        "caller": {"type": "unknown", "runtime": "unknown", "identity_strength": "unknown"},
        "usage_context": ctx,
        "validity": val,
        "context_source": ctx_source,
        "validity_source": val_source,
        "provenance": provenance,
        "payload": payload,
    }


def write_and_ingest(events: list, name: str):
    tmp = Path(tempfile.mkdtemp(prefix="am-core-gate-"))
    p = tmp / f"{name}.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    conn = connect(tmp / f"{name}.db")
    ingested = ingest_canonical_jsonl(
        conn, p, source="gate", project_id=PROJECT, principal="core-gate")
    match_invocations(conn)
    return conn, ingested


def main() -> int:
    fails = []

    # 1) 100 次双边调用：client attempt_started + server attempt_completed
    events = []
    for n in range(100):
        ts = f"2026-08-16T00:{n // 60:02d}:{n % 60:02d}Z"
        events.append(envelope("attempt_started",
                               {"tool_call_id": f"tc-{n}"},
                               "codex-hook@t", "client", ts, provenance="hook"))
        events.append(envelope("attempt_completed",
                               {"tool_call_id": f"tc-{n}", "outcome": "success"},
                               "mcp-wrapper@t", "server", ts))
    conn, ingested = write_and_ingest(events, "bilateral")
    s = compute(conn, PROJECT)
    if ingested["rejected"] != 0:
        fails.append(f"bilateral: rejected {ingested['rejected']} (all envelopes must be canonical)")
    if s["logical_invocations"] != 0:
        fails.append(f"bilateral: logical_invocations {s['logical_invocations']} != 0 (no fallback)")
    if s["attempts"] != 100:
        fails.append(f"bilateral: attempts {s['attempts']} != 100")
    if s["operation_resolution"]["unknown"] != 100:
        fails.append(f"bilateral: resolution unknown {s['operation_resolution']} != 100")
    if s["operation_resolution_coverage"] != 0.0:
        fails.append(f"bilateral: coverage {s['operation_resolution_coverage']} != 0.0")
    if s["corroborated_share"] != 1.0:
        fails.append(f"bilateral: corroborated_share {s['corroborated_share']} != 1.0")
    print("core-1: 100 attempts / 0 operations (no fallback), corroborated share 1.0 OK")

    # 2) 单边单观察 → observed（最低显示等级）
    events = [envelope("attempt_started", {"tool_call_id": "tc-s"},
                       "codex-hook@t", "client", "2026-08-16T03:00:00Z", provenance="hook")]
    conn, _ = write_and_ingest(events, "single")
    ev = conn.execute("SELECT evidence FROM invocations WHERE tool='foo.search'").fetchone()
    if not ev or ev["evidence"] != "observed":
        fails.append(f"single: evidence {ev['evidence'] if ev else None} != observed")
    print("core-2: single observation -> observed OK")

    # 3) 显式 operation_id → 3 attempts 归并为 1 operation
    events = []
    for i, outcome in enumerate(("failure", "failure", "success")):
        events.append(envelope("attempt_started",
                               {"tool_call_id": f"tc-op-{i}", "operation_id": "op-1",
                                "task_id": "tk-1"},
                               "mcp-wrapper@t", "server", f"2026-08-16T03:00:0{i}Z"))
        events.append(envelope("attempt_completed",
                               {"tool_call_id": f"tc-op-{i}", "outcome": outcome},
                               "mcp-wrapper@t", "server", f"2026-08-16T03:00:0{i}Z"))
    conn, _ = write_and_ingest(events, "operation")
    s = compute(conn, PROJECT)
    if s["logical_invocations"] != 1:
        fails.append(f"operation: logical_invocations {s['logical_invocations']} != 1")
    if s["attempts"] != 3:
        fails.append(f"operation: attempts {s['attempts']} != 3")
    if s["operation_resolution"]["explicit"] != 3:
        fails.append(f"operation: resolution explicit {s['operation_resolution']} != 3")
    if s["operation_resolution_coverage"] != 1.0:
        fails.append(f"operation: coverage {s['operation_resolution_coverage']} != 1.0")
    print("core-3: explicit operation -> 3 attempts / 1 operation, coverage 1.0 OK")

    # 4) qualification 冲突：production+normal vs test+normal → inconsistent
    events = [
        envelope("attempt_started", {"tool_call_id": "tc-q"}, "p0@t", "server",
                 "2026-08-16T03:00:00Z", ctx="production", val="normal"),
        envelope("attempt_started", {"tool_call_id": "tc-q"}, "p1@t", "server",
                 "2026-08-16T03:00:01Z", ctx="test", val="normal"),
    ]
    conn, _ = write_and_ingest(events, "qualification")
    row = conn.execute(
        "SELECT attempt_context, qualification_status FROM invocations").fetchone()
    if row["attempt_context"] != "inconsistent" or row["qualification_status"] != "inconsistent":
        fails.append(f"qualification: {dict(row)} != inconsistent/inconsistent")
    print("core-4: qualification conflict production+test -> inconsistent OK")

    # 5) provider_configuration validity 不是强资格（激励漏洞防护）：
    #    production + validity=normal + validity_source=provider_configuration
    #    → 不得派生为 qualified
    events = [
        envelope("attempt_started", {"tool_call_id": "tc-v"}, "p0@t", "server",
                 "2026-08-16T04:00:00Z", ctx="production", val="normal",
                 val_source="provider_configuration"),
    ]
    conn, _ = write_and_ingest(events, "validity-source")
    row = conn.execute(
        "SELECT attempt_validity, qualification_status FROM invocations").fetchone()
    if row["attempt_validity"] == "normal":
        fails.append(f"validity-source: attempt_validity normal (provider claim must not qualify)")
    if row["qualification_status"] == "qualified":
        fails.append(f"validity-source: qualified via provider_configuration validity")
    print("core-5: provider_configuration validity=normal -> not qualified OK")

    # 6) #9 operation summary reconciliation：task_outcome 声明 vs attempt rows
    #    a) 一致声明（2 attempts，最后一个 success，task_success=true, attempt_count=2）→ passed
    #    b) 矛盾声明（attempt_count=5 但实际 2 行；task_success=false 但最后 success）→ failed
    events = []
    for i, outcome in enumerate(("failure", "success")):
        events.append(envelope("attempt_started",
                               {"tool_call_id": f"tc-ok-{i}", "task_id": "tk-ok"},
                               "mcp-wrapper@t", "server", f"2026-08-16T05:00:0{i}Z"))
        events.append(envelope("attempt_completed",
                               {"tool_call_id": f"tc-ok-{i}", "outcome": outcome},
                               "mcp-wrapper@t", "server", f"2026-08-16T05:00:0{i}Z"))
    events.append(envelope("task_outcome",
                           {"task_id": "tk-ok", "task_success": True, "attempt_count": 2},
                           "mcp-wrapper@t", "server", "2026-08-16T05:00:10Z"))
    for i, outcome in enumerate(("failure", "success")):
        events.append(envelope("attempt_started",
                               {"tool_call_id": f"tc-bad-{i}", "task_id": "tk-bad"},
                               "mcp-wrapper@t", "server", f"2026-08-16T05:01:0{i}Z"))
        events.append(envelope("attempt_completed",
                               {"tool_call_id": f"tc-bad-{i}", "outcome": outcome},
                               "mcp-wrapper@t", "server", f"2026-08-16T05:01:0{i}Z"))
    events.append(envelope("task_outcome",
                           {"task_id": "tk-bad", "task_success": False, "attempt_count": 5},
                           "mcp-wrapper@t", "server", "2026-08-16T05:01:10Z"))
    conn, _ = write_and_ingest(events, "reconciliation")
    s = compute(conn, PROJECT)
    rec = s["operation_summary_reconciliation"]
    if rec["status"] != "failed":
        fails.append(f"reconciliation: status {rec['status']} != failed (mismatch must surface)")
    if rec["declared_summaries"] != 2:
        fails.append(f"reconciliation: declared {rec['declared_summaries']} != 2")
    if rec["failed"] != 1 or rec["reconciled"] != 1:
        fails.append(f"reconciliation: {rec}")
    bad = next((f for f in rec["failures"] if f["task_id"] == "tk-bad"), None)
    if not bad or len(bad["reasons"]) != 2:
        fails.append(f"reconciliation: tk-bad reasons {bad}")
    ok = any(f["task_id"] == "tk-ok" for f in rec["failures"])
    if ok:
        fails.append("reconciliation: consistent tk-ok must NOT be a failure")
    print("core-6: declared summary vs attempt rows -> mismatch surfaces as reconciliation: failed OK")

    # 7) #9 空 dataset：无 task_outcome 声明 → no_declared_summaries（不报错）
    events = [envelope("attempt_started", {"tool_call_id": "tc-none"},
                       "mcp-wrapper@t", "server", "2026-08-16T06:00:00Z")]
    conn, _ = write_and_ingest(events, "no-summary")
    rec = compute(conn, PROJECT)["operation_summary_reconciliation"]
    if rec["status"] != "no_declared_summaries":
        fails.append(f"no-summary: status {rec['status']} != no_declared_summaries")
    print("core-7: no declared summaries -> no_declared_summaries OK")

    if fails:
        print("CORE GATE FAIL:")
        for f in fails:
            print("  - " + f)
        return 1
    print("CORE GATE PASS: canonical ingestion path only; all 0.4.3 invariants hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
