#!/usr/bin/env python3
"""Executable evidence case: self-hosted OpenAI-compatible server, two surfaces.

Run from the repository root:
    python3 conformance/evidence/selfhosted-openai-compatible-reconcile/run_case.py

Pins standard/known-limits-unprovable-by-surface.md section 6 with one live
capture (vLLM 0.27.1 on a T4). The client surface is what three responses
carried; the server surface is four /metrics counters before and after.
Offline, stdlib only. Includes fault injections that a conformant reader
must reject.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture.jsonl"
EXPECTED = HERE / "expected.json"

SERVER_METRICS = {
    "requests": "vllm:request_success_total",
    "prompt_tokens": "vllm:request_prompt_tokens_sum",
    "output_tokens": "vllm:request_generation_tokens_sum",
    "cached_prompt_tokens": "vllm:prompt_tokens_cached_total",
}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path.name}:{n}: each row must be an object")
        rows.append(row)
    return rows


def client_surface(rows: list[dict]) -> dict:
    """What the responses said. Absent usage stays absent: it is counted, never summed as 0."""
    calls = [r for r in rows if r.get("surface") == "client"]
    present = [r for r in calls if isinstance(r.get("usage"), dict)]
    split_reported = [r for r in present if isinstance(r["usage"].get("prompt_tokens_details"), dict)]
    cached = None
    if present and len(split_reported) == len(present):
        cached = sum(r["usage"]["prompt_tokens_details"].get("cached_tokens") or 0 for r in present)
    return {
        "calls": len(calls),
        "usage_present": len(present),
        "usage_absent": len(calls) - len(present),
        "prompt_tokens_reported": sum(r["usage"]["prompt_tokens"] for r in present),
        "output_tokens_reported": sum(r["usage"]["completion_tokens"] for r in present),
        "cache_split": "REPORTED" if cached is not None else "UNREPORTED",
        "cached_prompt_tokens": cached,
    }


def server_surface(rows: list[dict]) -> dict:
    """Counter deltas. A missing counter or one that went down is unknown (None), never 0."""
    by_metric = {r["metric"]: r for r in rows if r.get("surface") == "server"}
    out = {}
    for key, metric in SERVER_METRICS.items():
        r = by_metric.get(metric)
        if r is None or r.get("before") is None or r.get("after") is None or r["after"] < r["before"]:
            out[key] = None
        else:
            out[key] = int(round(r["after"] - r["before"]))
    return out


def reconcile(client: dict, server: dict) -> dict:
    gap = lambda s, c: None if s is None else s - c
    req_gap = gap(server["requests"], client["calls"])
    out = {
        "requests_gap": req_gap,
        "prompt_tokens_gap": gap(server["prompt_tokens"], client["prompt_tokens_reported"]),
        "output_tokens_gap": gap(server["output_tokens"], client["output_tokens_reported"]),
    }
    complete = req_gap == 0 and None not in (server["prompt_tokens"], server["output_tokens"])
    out["period_total"] = "PROVABLE" if complete else "UNPROVABLE"
    if not complete or client["usage_absent"] == 0:
        out["absent_call_usage"] = "NOT_APPLICABLE" if complete else "UNPROVABLE"
    elif client["usage_absent"] == 1:
        out["absent_call_usage"] = "PROVABLE_BY_ELIMINATION"   # the whole gap is that one call
    else:
        out["absent_call_usage"] = "UNPROVABLE"                # sums cannot split it between calls
    out["cache_split_per_call"] = "REPORTED" if client["cache_split"] == "REPORTED" else "UNPROVABLE"
    return out


def violations(client: dict, recon: dict, server: dict) -> list[str]:
    """The forbidden outcomes from expected.json, as checks on a reader's output."""
    errs = []
    if client["usage_absent"] and recon.get("prompt_tokens_gap") in (0, None) and server["prompt_tokens"]:
        errs.append("absent usage read as zero tokens (no gap left for the absent call)")
    if recon.get("period_total") == "PROVABLE" and recon.get("requests_gap") != 0:
        errs.append("client-reported total presented as the period total")
    if client["cache_split"] == "UNREPORTED" and client.get("cached_prompt_tokens") is not None:
        errs.append("absent prompt_tokens_details read as zero cached tokens")
    if client["usage_absent"] >= 2 and recon.get("absent_call_usage") != "UNPROVABLE":
        errs.append("per-call attribution of the gap with two or more calls absent")
    return errs


def main() -> int:
    rows = load_jsonl(FIXTURE)
    exp = json.loads(EXPECTED.read_text(encoding="utf-8"))["expected"]
    ok = True

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and cond
        print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{detail}]"))

    client, server = client_surface(rows), server_surface(rows)
    recon = reconcile(client, server)
    check("client surface: 2 of 3 calls carry usage, 70 / 32, cache split unreported",
          client == exp["client"], f"got {client}")
    check("server surface: 3 requests, 105 / 48, 64 prompt tokens from the prefix cache",
          server == exp["server"], f"got {server}")
    check("reconciliation: gap 35 / 16 is the one absent call; period total provable",
          recon == exp["reconciliation"], f"got {recon}")
    check("no forbidden outcome in the reference reading", not violations(client, recon, server))

    # Fault 1: a reader that sums absent usage as 0 and reports the client total
    # as if it were the period total.
    bad = copy.deepcopy(recon)
    bad.update(prompt_tokens_gap=0, output_tokens_gap=0)
    check("fault rejected: absent usage read as zero",
          bool(violations(client, bad, server)))

    # Fault 2: a reader that turns the missing prompt_tokens_details into a cache of 0.
    bad_client = dict(client, cached_prompt_tokens=0)
    check("fault rejected: missing cache split read as 0 cached tokens",
          bool(violations(bad_client, recon, server)))

    # Fault 3: with two calls absent, attributing the gap per call is not allowed.
    two = copy.deepcopy(rows)
    next(r for r in two if r.get("call_id") == "A")["usage"] = None
    c2 = client_surface(two)
    r2 = reconcile(c2, server)
    check("two absent calls: per-call usage is UNPROVABLE (gap 70 / 32 is a total only)",
          r2["absent_call_usage"] == "UNPROVABLE" and r2["prompt_tokens_gap"] == 70
          and r2["output_tokens_gap"] == 32 and not violations(c2, r2, server), f"got {r2}")
    check("fault rejected: per-call attribution claimed with two calls absent",
          bool(violations(c2, dict(r2, absent_call_usage="PROVABLE_BY_ELIMINATION"), server)))

    # Fault 4: another client used the server in the window (4 requests counted
    # for 3 calls); claiming the period total is then not allowed.
    busy = copy.deepcopy(rows)
    next(r for r in busy if r.get("metric") == "vllm:request_success_total")["after"] = 4.0
    s5 = server_surface(busy)
    r5 = reconcile(client, s5)
    check("a request the client did not make leaves the period total UNPROVABLE",
          r5["requests_gap"] == 1 and r5["period_total"] == "UNPROVABLE", f"got {r5}")
    check("fault rejected: period total claimed while requests do not match",
          bool(violations(client, dict(r5, period_total="PROVABLE"), s5)))

    # A counter missing from a snapshot is unknown, and so is the period total.
    gone = [r for r in rows if r.get("metric") not in
            ("vllm:request_success_total", "vllm:prompt_tokens_cached_total")]
    s3 = server_surface(gone)
    r3 = reconcile(client, s3)
    check("missing counters stay unknown: no request count means no provable period total",
          s3["requests"] is None and s3["cached_prompt_tokens"] is None
          and r3["period_total"] == "UNPROVABLE", f"got {s3} {r3}")
    restarted = copy.deepcopy(rows)
    next(r for r in restarted if r.get("metric") == "vllm:request_prompt_tokens_sum")["before"] = 500.0
    s4 = server_surface(restarted)
    check("a counter that went down (server restart) is unknown, not a negative or zero delta",
          s4["prompt_tokens"] is None and reconcile(client, s4)["period_total"] == "UNPROVABLE",
          f"got {s4}")

    print("\nCONFORMANT" if ok else "\nNON-CONFORMANT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
