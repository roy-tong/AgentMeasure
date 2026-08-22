"""Read-only MCP query interface (LAB-009).

Agents are first-class users of the substrate: after an experiment runs,
an agent (or CI) can query the results over MCP — the same evidence an
engineer sees, in machine-readable form, with evidence grades.

Contract (PRD LAB-009 acceptance):
- read-only: no tool mutates anything, no execution-class operations;
- every returned recommendation carries its evidence grade;
- no rankings, no competitor data, no cross-customer baselines — only the
  customer's own experiment results.

Protocol: JSON-RPC 2.0 over stdio, one message per line (MCP stdio
transport). Minimal, dependency-free; implements initialize / ping /
tools/list / tools/call.
"""

import json
import sys
from typing import Any, Dict, List, Optional

from . import __version__

PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "agentmeasure-lab", "version": __version__}

_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_run_summary",
        "description": (
            "Summary of one experiment run: status, per-variant verdicts, "
            "preregistration hash, determinism fingerprint, harness disclosures."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["run_dir"],
            "properties": {"run_dir": {"type": "string", "description": "path to the run directory (contains run.json/report.json)"}},
        },
    },
    {
        "name": "get_presentation_advice",
        "description": (
            "Which variant(s) to present/ship, with the evidence behind each "
            "recommendation (effect size, CI, p-value, guardrails, fake-growth "
            "warnings, evidence grade). No rankings; production verification is "
            "reported separately when a calibration report exists."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["run_dir"],
            "properties": {"run_dir": {"type": "string"}},
        },
    },
    {
        "name": "get_funnel_metrics",
        "description": (
            "Reach → Choice → Success → Consumption rates per variant, each with "
            "numerator, denominator, 95% Wilson interval and measurement label."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["run_dir"],
            "properties": {
                "run_dir": {"type": "string"},
                "variant": {"type": "string", "description": "optional: single variant id"},
            },
        },
    },
]


class JsonRpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _ok(result: Any, req_id) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(code: int, message: str, req_id) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _load_report(run_dir: str) -> Dict[str, Any]:
    import os

    path = os.path.join(run_dir, "report.json")
    if not os.path.exists(path):
        raise JsonRpcError(-32602, f"no report.json under {run_dir} — run `am lab run` first")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _has_calibration(run_dir: str) -> Optional[Dict[str, Any]]:
    import os

    path = os.path.join(run_dir, "calibration-report.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _fmt_rate(m: Dict[str, Any]) -> Dict[str, Any]:
    value = m.get("value")
    return {
        "value": value,
        "percent": round(value * 100, 2) if value is not None else None,
        "numerator": m.get("numerator"),
        "denominator": m.get("denominator"),
        "ci95": m.get("ci95"),
        "label": m.get("measurement_label"),
    }


def tool_run_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    report = _load_report(args["run_dir"])
    return {
        "experiment_id": report["experiment_id"],
        "hypothesis": report["hypothesis"],
        "status": report["run"]["status"],
        "stopped_reason": report["run"].get("stopped_reason"),
        "assignments": f"{report['run']['assignments_executed']}/{report['run']['assignments_planned']}",
        "preregistration_hash": report["preregistration"]["manifest_hash"],
        "run_fingerprint": report["run"]["run_fingerprint"],
        "verdicts": {v["variant_id"]: v["verdict"] for v in report["variants"]},
        "engine_version": report["engine_version"],
        "harness_disclosures": [
            {"runner_id": h.get("runner_id"), "disclosure": h.get("disclosure")}
            for h in report["run"].get("harnesses", [])
        ],
    }


def tool_presentation_advice(args: Dict[str, Any]) -> Dict[str, Any]:
    run_dir = args["run_dir"]
    report = _load_report(run_dir)
    calibration = _has_calibration(run_dir)
    decisions = {r["variant_id"]: r for r in report.get("decision", {}).get("recommendations", [])}

    from .analysis import PLAIN_LABELS

    advice = []
    for v in sorted(report["variants"], key=lambda x: x["variant_id"]):  # alphabetical — no ranking
        if v.get("baseline"):
            continue
        cmp = v.get("primary_comparison", {})
        cal = None
        if calibration:
            for cv in calibration.get("variants", []):
                if cv["variant_id"] == v["variant_id"]:
                    cal = cv.get("calibration")
        margin = (v.get("value") or {}).get("incremental_margin_per_month")
        advice.append(
            {
                "variant_id": v["variant_id"],
                "verdict": v["verdict"],
                "plain_label": v.get("plain_label") or PLAIN_LABELS.get(v["verdict"]),
                "recommended_action": decisions.get(v["variant_id"], {}).get("recommended_action"),
                "verified_margin_per_month": margin,
                "dominated_by": v.get("dominated_by"),
                "evidence": {
                    "grade": "preregistered controlled experiment (offline)",
                    "primary_metric": report["preregistration"]["primary_metric"],
                    "difference": cmp.get("difference"),
                    "ci95": cmp.get("diff_ci95"),
                    "p_value": cmp.get("p_value"),
                    "significant": cmp.get("verdict") == "significant",
                    "guardrails": [
                        {"metric": g["metric"], "status": g["status"]} for g in v.get("guardrails", [])
                    ],
                    "fake_growth_warning": (v.get("fake_growth") or {}).get("flagged", False),
                    "power_note": cmp.get("power_note"),
                    "production_verification": (
                        {"status": cal["calibration"], "reason": cal.get("reason")}
                        if cal
                        else {"status": "not_performed", "reason": "no calibration report in this run dir"}
                    ),
                },
            }
        )
    return {
        "advice": advice,
        "note": report.get("decision", {}).get("note"),
        "no_ranking": "variants are listed alphabetically; ranking capabilities is explicitly out of scope",
    }


def tool_funnel_metrics(args: Dict[str, Any]) -> Dict[str, Any]:
    report = _load_report(args["run_dir"])
    variant_filter = args.get("variant")
    out = {}
    for v in report["variants"]:
        if variant_filter and v["variant_id"] != variant_filter:
            continue
        m = v["metrics"]
        out[v["variant_id"]] = {
            "levels": v["levels"],
            "reach": m["reach"],
            "selection_rate": _fmt_rate(m["selection_rate"]),
            "operation_success_rate": _fmt_rate(m["operation_success_rate"]),
            "consumption_rate": _fmt_rate(m["consumption_rate"]),
            "attempts_per_operation": m["attempts_per_operation"],
        }
    if variant_filter and variant_filter not in out:
        raise JsonRpcError(-32602, f"unknown variant {variant_filter!r}")
    return out


_TOOL_FN = {
    "get_run_summary": tool_run_summary,
    "get_presentation_advice": tool_presentation_advice,
    "get_funnel_metrics": tool_funnel_metrics,
}


def handle_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle one JSON-RPC message; return the response or None (notification)."""
    req_id = message.get("id")
    method = message.get("method", "")

    if method.startswith("notifications/"):
        return None

    try:
        if method == "initialize":
            requested = message.get("params", {}).get("protocolVersion")
            version = requested if requested in (PROTOCOL_VERSION,) else PROTOCOL_VERSION
            return _ok(
                {"protocolVersion": version, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO},
                req_id,
            )
        if method == "ping":
            return _ok({}, req_id)
        if method == "tools/list":
            return _ok({"tools": _TOOLS}, req_id)
        if method == "tools/call":
            params = message.get("params", {})
            name = params.get("name", "")
            fn = _TOOL_FN.get(name)
            if fn is None:
                raise JsonRpcError(-32602, f"unknown tool {name!r} (read-only tools only)")
            result = fn(params.get("arguments", {}))
            return _ok({"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": False}, req_id)
        return _err(-32601, f"method not found: {method}", req_id)
    except JsonRpcError as e:
        return _err(e.code, e.message, req_id)
    except (OSError, ValueError, KeyError) as e:
        return _err(-32000, f"tool error: {e}", req_id)


def serve(stdin=None, stdout=None) -> None:
    """stdio loop: one JSON message per line until EOF."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = _err(-32700, "parse error", None)
        else:
            response = handle_message(message)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
