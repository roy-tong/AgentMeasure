#!/usr/bin/env python3
"""AgentMeasure test vectors runner（参考实现侧验证；fixtures 本身语言无关）。

用法: python3 verify_vectors.py
任何 AgentMeasure 实现（Go/Rust/TS...）应对同一 fixtures 产生同一结果。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "reference"))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_receipt_vectors() -> int:
    from collector.receipt import build_receipt, receipts_correspond, correlation_commitment
    from collector.usage import empty_observation

    data = json.loads((FIXTURES / "receipts.json").read_text(encoding="utf-8"))
    failed = 0
    for v in data["vectors"]:
        vid = v["id"]
        if vid == "receipt-valid":
            obs = empty_observation()
            obs.update({k: val for k, val in v["input"].items() if k != "receipt_id"})
            r = build_receipt(obs, observer_principal=v["input"]["observer_principal"],
                              observer_side=v["input"]["observer_side"],
                              provenance=v["input"]["provenance"],
                              project_id=v["input"]["project_id"])
            ok = r["spec_version"] == "agentmeasure-0.1"
        elif vid == "receipt-forbidden-fields":
            # 输入故意含内容字段；检查构建出的收据不含任何内容
            obs = empty_observation()
            obs.update({k: val for k, val in v["input"].items() if k != "receipt_id"})
            r = build_receipt(obs, observer_principal=v["input"]["observer_principal"],
                              observer_side=v["input"]["observer_side"],
                              provenance=v["input"]["provenance"],
                              project_id=v["input"]["project_id"])
            raw = json.dumps(r, ensure_ascii=False)
            ok = "SECRET" not in raw and "prompt" not in raw
        elif vid in ("commitment-same-call", "commitment-different-call", "same-side-never-corroborates"):
            a, b = v["input"]["a"], v["input"]["b"]
            ca = correlation_commitment(a["project_id"], a["trace_id"], a["tool_call_id"])
            cb = correlation_commitment(b["project_id"], b["trace_id"], b["tool_call_id"])
            correspond = (ca == cb) and (a["observer_side"] != b["observer_side"])
            ok = correspond == v["expect"]["correspond"]
        else:
            ok = True
        if not ok:
            print(f"  ✗ {vid}")
            failed += 1
        else:
            print(f"  ✓ {vid}")
    return failed


def run_correlation_vectors() -> int:
    from collector.correlator.correlator import connect, store_observation, match_invocations
    from collector.aggregator.aggregator import compute
    from collector.usage import empty_observation, new_observation_id

    data = json.loads((FIXTURES / "correlation.json").read_text(encoding="utf-8"))
    failed = 0
    for v in data["vectors"]:
        tmp = tempfile.mkdtemp()
        conn = connect(Path(tmp) / "v.db")
        for o in v["input"]["observations"]:
            obs = empty_observation()
            obs.update(dict(
                observation_id=new_observation_id(),
                observed_at=o["ts"],
                observer_principal=o["principal"],
                observer_side=o["side"],
                provenance="hook" if o["side"] == "client" else "wrapper",
                trust_domain=o["principal"].split("@")[-1],
                project_id=v["input"]["project"],
                tool=o["tool"],
                tool_call_id=o["call_id"],
                outcome=o["outcome"],
                lifecycle_stage="L2"))
            store_observation(conn, obs)
        match_invocations(conn)
        s = compute(conn, v["input"]["project"])
        exp = v["expect"]
        ok = True
        if "invocations" in exp and s["logical_invocations"] != exp["invocations"]:
            ok = False
        if "outcome" in exp:
            row = conn.execute("SELECT outcome FROM invocations").fetchone()
            if not row or row["outcome"] != exp["outcome"]:
                ok = False
        if exp.get("evidence_none_E2"):
            row = conn.execute("SELECT evidence FROM invocations").fetchone()
            if row and row["evidence"] == "E2":
                ok = False
        if not ok:
            print(f"  ✗ {v['id']} (got invocations={s['logical_invocations']})")
            failed += 1
        else:
            print(f"  ✓ {v['id']}")
    return failed


def main() -> int:
    failed = 0
    print("receipt vectors:")
    failed += run_receipt_vectors()
    print("correlation/aggregation vectors:")
    failed += run_correlation_vectors()
    print(f"\n{'ALL VECTORS PASS' if failed == 0 else f'{failed} VECTORS FAILED'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
