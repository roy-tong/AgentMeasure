#!/usr/bin/env python3
"""One-off concierge adapter: Langfuse export JSON -> canonical observations.

FROZEN FOR REPRODUCIBILITY — not a supported product surface. Handles exactly
the three pinned files of this evidence case; every mapping decision is
disclosed in PROVENANCE.md:

  Langfuse observation        canonical envelope
  ------------------------    -------------------------------------------
  TOOL  "running tool: X"     attempt_started + attempt_completed,
                              surface_id = X (namespace: unknown)
  GENERATION (model M)        attempt_started + attempt_completed,
                              surface_id = model:<M> (LLM API as capability)
  SPAN / AGENT                NOT an invocation (grouping context only) —
                              analysed structurally by run_case.py
  observation id              tool_call_id (pairs start/completed)
  traceId                     trace_id AND task_id (trace = task boundary,
                              correlation-grade, no operation declaration)
  startTime/endTime           started_at / duration_ms
  level (DEFAULT/ERROR)       outcome: ERROR -> failure, else success
                              (completion assumed — langfuse levels mark
                              errors only; disclosed limitation)
  usage fields                ABSENT in export -> no usage observations emitted
  operation_id / retry_of     ABSENT in export -> not emitted (the finding)
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

SPEC = "agentmeasure-0.4"


def _outcome(o: dict) -> str:
    return "failure" if (o.get("level") == "ERROR" or o.get("statusMessage")) else "success"


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _envelope(obs_id: str, otype: str, at: str, surface_id: str, payload: dict) -> dict:
    return {
        "spec_version": SPEC,
        "observation_id": obs_id,
        "observation_type": otype,
        "observer": {
            "principal": "langfuse-export@concierge",
            "trust_domain": "third-party",
            "side": "client",
        },
        "observed_at": at,
        "deployment_context": {"project_id": "langfuse/demo-seed-traces"},
        "surface": {"surface_id": surface_id, "surface_namespace": "unknown"},
        "usage_context": "demo",
        "validity": "unknown",
        "context_source": "none",
        "validity_source": "none",
        "caller": {"type": "claimed_agent", "identity_strength": "declared"},
        "provenance": "wrapper",
        "payload": payload,
    }


def convert(trace_file: Path) -> list:
    d = json.loads(trace_file.read_text())
    trace_id = d.get("trace", {}).get("id") or d["observations"][0]["traceId"]
    task_id = trace_id  # trace = task boundary (correlation-grade, disclosed)
    out = []
    for o in d.get("observations", []):
        t = o["type"]
        if t not in ("TOOL", "GENERATION"):
            continue  # SPAN/AGENT = grouping context, not capability usage
        oid = o["id"]
        if t == "TOOL":
            name = o["name"].replace("running tool: ", "").strip()
            surface = f"mcp_tool:{name}" if "." in name else f"tool:{name}"
        else:
            surface = f"model:{o.get('model') or 'unknown'}"
        start = o["startTime"]
        out.append(_envelope(
            f"{oid}-s", "attempt_started", start, surface,
            {"tool_call_id": oid, "trace_id": trace_id, "started_at": start, "task_id": task_id},
        ))
        payload_done = {"tool_call_id": oid, "outcome": _outcome(o)}
        end = o.get("endTime")
        if end and start:
            payload_done["duration_ms"] = int((_ts(end) - _ts(start)).total_seconds() * 1000)
        out.append(_envelope(f"{oid}-c", "attempt_completed", end or start, surface, payload_done))
    return out


def main(trace_dir: Path) -> int:
    canonical = trace_dir.parent / "canonical"
    canonical.mkdir(exist_ok=True)
    total = 0
    for f in sorted(trace_dir.glob("*.json")):
        obs = convert(f)
        dest = canonical / (f.stem + ".canonical.jsonl")
        dest.write_text("\n".join(json.dumps(e) for e in obs) + "\n")
        print(f"{f.name}: {len(obs)} canonical observations -> {dest.name}")
        total += len(obs)
    print(f"total: {total}")
    return 0
