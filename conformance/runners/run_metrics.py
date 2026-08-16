#!/usr/bin/env python3
"""AgentMeasure conformance runner（Draft 0.3，按指标运行 vectors）。

用法: python3 conformance/runners/run_metrics.py
读 conformance/vectors/*.json，对每个 metric 的 vectors 跑参考实现，
断言输出与 expect 一致。任何 AgentMeasure 实现应对同一 vectors 产生同一结果。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

VECTORS_DIR = ROOT / "conformance" / "vectors"


def _run_selection_rate(vector: dict) -> bool:
    from collector.choice import connect, ingest_choice_events, selection_metrics

    conn = connect(Path(tempfile.mkdtemp()) / "v.db")
    path = Path(tempfile.mkdtemp()) / "events.jsonl"
    events = []
    for e in vector["input"]["events"]:
        ev = dict(e)
        ev.setdefault("project_id", vector["input"]["project"])
        events.append(ev)
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    ingest_choice_events(conn, path)
    sm = selection_metrics(conn, vector["input"]["project"])
    exp = vector["expect"]
    if exp.get("denominator_empty"):
        # presentation 不可观察 → 无分母；绝不能产出"0% 选择"类误导值
        return len(sm["tools"]) == 0 or sm["tools"][0]["presented_opportunities"] == 0
    if not sm["tools"]:
        return False
    tool = sm["tools"][0]
    return (tool["presented_opportunities"] == exp["presented"]
            and tool["selections"] == exp["selected"]
            and tool["observed_selection_rate"] == exp["observed_selection_rate"])


def _run_conditional_choice_share(vector: dict) -> bool:
    from collector.choice import connect, ingest_choice_events, conditional_choice_share

    conn = connect(Path(tempfile.mkdtemp()) / "v.db")
    path = Path(tempfile.mkdtemp()) / "events.jsonl"
    events = []
    for e in vector["input"]["events"]:
        ev = dict(e)
        # 事件自带 project_id 时（跨项目向量）不覆盖；否则用向量级 project
        ev.setdefault("project_id", vector["input"].get("project"))
        events.append(ev)
    path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    ingest_choice_events(conn, path)
    inp = vector["input"]
    s = conditional_choice_share(
        conn, inp["tool_a"], inp["tool_b"],
        project_id=inp.get("project"),
        choice_mode=inp.get("choice_mode"),
        category_id=inp.get("category_id"),
        decision_authority=inp.get("decision_authority"),
        selection_constraint=inp.get("selection_constraint"))
    exp = vector["expect"]
    return (s["co_presented_decisions"] == exp["co_presented"]
            and s["a_selected"] == exp["a_selected"]
            and s["b_selected"] == exp["b_selected"]
            and s["conditional_choice_share_a"] == exp["share_a"])


def _run_consumed_rate(vector: dict) -> bool:
    from collector.correlator.correlator import connect, store_observation, match_invocations
    from collector.consumption import ingest_consumption_events, consumed_rate
    from collector.usage import empty_observation, new_observation_id

    tmp = tempfile.mkdtemp()
    conn = connect(Path(tmp) / "v.db")
    project = vector["input"]["project"]
    for i, inv in enumerate(vector["input"]["invocations"]):
        # 每调用双侧观察（client=observer + server=wrapper）保证 eligible
        for side, principal in (("client", inv["observer"]), ("server", "mcp-wrapper@t")):
            o = empty_observation(); o.update(dict(
                observation_id=new_observation_id(),
                observed_at=f"2026-08-16T00:{i:02d}:00Z",
                observer_principal=principal, observer_side=side,
                provenance="hook" if side == "client" else "wrapper",
                trust_domain="td-a" if side == "client" else "td-s",
                project_id=project, tool="foo.search", tool_call_id=inv["tool_call_id"],
                outcome=inv["outcome"], lifecycle_stage="L2",
                usage_context=inv["context"], validity=inv["validity"]))
            store_observation(conn, o)
    match_invocations(conn)
    path = Path(tmp) / "consume.jsonl"
    path.write_text("\n".join(
        json.dumps({"type": "tool_result", "tool_use_id": c["tool_use_id"], "tool": "foo.search",
                    "ts": "2026-08-16T00:01:00Z"}) + "\n" +
        json.dumps({"type": "request", "mcp_tool": "foo.search", "ts": "2026-08-16T00:01:05Z", "seq": i})
        for i, c in enumerate(vector["input"]["consumptions"])), encoding="utf-8")
    ingest_consumption_events(conn, path, project)
    s = consumed_rate(conn, project)
    exp = vector["expect"]
    return (s["consumed_results"] == exp["consumed"]
            and s["consumption_observable_invocations"] == exp["observable"]
            and s["consumption_unobservable_invocations"] == exp.get("unobservable", 0)
            and s["consumed_rate"] == exp["rate"])


RUNNERS = {
    "M2.2 Observed Selection Rate": _run_selection_rate,
    "M2.5 Conditional Choice Share": _run_conditional_choice_share,
    "M4.1 Result Consumed Rate": _run_consumed_rate,
}


def main() -> int:
    failed = 0
    total = 0
    for vec_file in sorted(VECTORS_DIR.glob("*.json")):
        data = json.loads(vec_file.read_text(encoding="utf-8"))
        metric = data["metric"]
        runner = RUNNERS.get(metric)
        if runner is None:
            print(f"  ! no runner for {metric}")
            continue
        for v in data["vectors"]:
            total += 1
            try:
                ok = runner(v)
            except Exception as exc:
                ok = False
                print(f"    error: {exc}")
            if ok:
                print(f"  ✓ [{metric}] {v['id']}")
            else:
                print(f"  ✗ [{metric}] {v['id']}")
                failed += 1
    print(f"\n{total - failed}/{total} vectors PASS" + ("" if failed == 0 else f" ({failed} FAILED)"))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
