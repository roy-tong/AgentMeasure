"""Engagement templates — 附录 E's reuse, made into an artifact (BP r28 p17 Q5).

What survives from one engagement to the next is the *method*, never the
data: the column mapping (the prepare fingerprint), the buyer's contract
overlay, and the boundary cases with their expected verdicts. A template is
that trio, versioned and portable. A second engagement on the same vendor
with the same fingerprint imports it and starts from the mapping already
proven — which is what "同类客户首查 ≤10 小时" is made of.

Boundary cases double as regression fixtures: re-running a template's cases
through the recount must reproduce the expected three-state verdicts, so a
rules change that silently moves a boundary is caught before it moves a claim.

Client data stays out by construction: fingerprints are column-provenance
names, boundary cases must be synthetic ids, and the template carries no
export rows.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

TEMPLATE_SCHEMA = "agentmeasure.commercial/engagement-template"
TEMPLATE_VERSION = "0.1.0"


class TemplateError(ValueError):
    pass


def export_template(vendor_id: str, fingerprint: str,
                    contract: Optional[Dict[str, Any]] = None,
                    boundary_cases: Optional[List[Dict[str, Any]]] = None,
                    note: str = "") -> Dict[str, Any]:
    if not vendor_id:
        raise TemplateError("vendor is required")
    boundary_cases = boundary_cases or []
    for case in boundary_cases:
        if not isinstance(case, dict) or "expected_3state" not in case:
            raise TemplateError(
                "each boundary case needs columns + expected_3state")
        if case["expected_3state"] not in ("PASS", "FAIL", "UNPROVABLE"):
            raise TemplateError("expected_3state must be PASS/FAIL/UNPROVABLE")
    return {
        "schema": TEMPLATE_SCHEMA,
        "schema_version": TEMPLATE_VERSION,
        "vendor": vendor_id,
        "mapping_fingerprint": fingerprint,
        "contract_overlay": contract,
        "boundary_cases": boundary_cases,
        "note": note,
        "reuse_rule": "method only: fingerprints name column provenance, "
                      "boundary cases are synthetic — no client rows travel",
    }


def validate_template(doc: Dict[str, Any]) -> None:
    if doc.get("schema") != TEMPLATE_SCHEMA:
        raise TemplateError("not an engagement template (schema %r)"
                            % doc.get("schema"))
    if not doc.get("vendor"):
        raise TemplateError("template has no vendor")
    for case in doc.get("boundary_cases", []):
        if "expected_3state" not in case:
            raise TemplateError("boundary case without expected_3state")


def save_template(doc: Dict[str, Any], directory: str) -> str:
    validate_template(doc)
    os.makedirs(directory, exist_ok=True)
    name = "%s-%s.json" % (doc["vendor"], doc.get("mapping_fingerprint") or "nofp")
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return path


def load_template(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    validate_template(doc)
    return doc


def list_templates(directory: str) -> List[Dict[str, Any]]:
    if not os.path.isdir(directory):
        return []
    out = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        try:
            doc = load_template(os.path.join(directory, name))
        except (TemplateError, json.JSONDecodeError):
            continue
        out.append({
            "file": name,
            "vendor": doc["vendor"],
            "fingerprint": doc.get("mapping_fingerprint", ""),
            "contract": bool(doc.get("contract_overlay")),
            "boundary_cases": len(doc.get("boundary_cases", [])),
        })
    return out


def replay_boundary_cases(doc: Dict[str, Any], recount_fn) -> List[Dict[str, Any]]:
    """Re-run the template's cases through a recount function.

    recount_fn(rows) -> list of dicts with at least verdict_3state. Returns
    per-case pass/fail against the expected verdicts — a rules change that
    moves a boundary shows up here before it moves a claim.
    """
    cases = doc.get("boundary_cases", [])
    if not cases:
        return []
    results = []
    rows = [case["columns"] for case in cases]
    verdicts = recount_fn(rows)
    for case, verdict in zip(cases, verdicts):
        got = verdict.get("verdict_3state")
        results.append({
            "case": case.get("name") or case["columns"].get("conversation_id"),
            "expected": case["expected_3state"],
            "got": got,
            "holds": got == case["expected_3state"],
        })
    return results
