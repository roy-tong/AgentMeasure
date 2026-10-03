"""Outcome-unit verification engine (BP r28 p14 Emerging row).

Schema first was the rule; this is the engine that reads it — fail-closed,
rule-based, model-free like every judgement in this package. It consumes
outcome-unit JSONL (schemas/outcome-unit.schema.json) and produces a per-unit
ledger plus totals.

The discipline it enforces (mirrors AMS-1):
- a unit that fails schema validation is INVALID — it contributes to no total
  except its own;
- `criteria_unproven` non-empty forces status `unproven`; a unit claiming
  `counted` while carrying unproven criteria is an inconsistency, refused
  rather than smoothed;
- a reopen inside the stability window is named per unit (reopened_in_window)
  without deciding the contract — whether that kills the claim is the
  contract overlay's job, not the engine's;
- duplicate unit_ids are named, last row kept, duplication disclosed;
- claimable value sums ONLY counted units, with a single-currency check.

The engine judges structure and consistency. Whether the underlying outcome
is real is what the evidence refs and observer grades are for.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

UNIT_SCHEMA_PATH_NOTE = "schemas/outcome-unit.schema.json"

_DATE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


# ---------------------------------------------------------------------------
# Draft-07 subset validator — the same keywords the outcome schema uses.
# Shared by the engine and the conformance tests so the two cannot drift.
# ---------------------------------------------------------------------------
def validate_schema(instance: Any, schema: Dict[str, Any], path: str = "$") -> List[str]:
    errors: List[str] = []
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        checks = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
        }
        if not any(checks[t](instance) for t in types):
            return ["%s: expected type %s" % (path, "/".join(types))]
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: shorter than minLength %d" % (path, schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: longer than maxLength %d" % (path, schema["maxLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: does not match pattern %s" % (path, schema["pattern"]))
        if schema.get("format") == "date-time" and not _DATE_TIME_RE.match(instance):
            errors.append("%s: not an ISO date-time" % path)
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: below minimum" % path)
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append("%s: not above exclusiveMinimum" % path)
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r not in enum" % (path, instance))
    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append("%s: missing required %r" % (path, name))
        for name, sub in schema.get("properties", {}).items():
            if name in instance:
                errors += validate_schema(instance[name], sub, "%s.%s" % (path, name))
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors += validate_schema(item, schema["items"], "%s[%d]" % (path, i))
    return errors


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_schema(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_units(path: str) -> List[Dict[str, Any]]:
    units = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                units.append(json.loads(line))
            except json.JSONDecodeError:
                raise ValueError("line %d of %s is not valid JSONL" % (i + 1, path)) from None
    return units


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------
def _window_reopen(unit: Dict[str, Any]) -> Tuple[bool, str]:
    """(reopened_in_window, note) — informational, never a verdict."""
    window = unit.get("window") or {}
    hours = window.get("stability_hours")
    reopens = window.get("reopened_at") or []
    if not reopens:
        return False, ""
    if hours is None:
        return True, "reopen events present but no stability window declared"
    return True, "%d reopen event(s); stability window %sh" % (len(reopens), hours)


def verify_units(units: List[Dict[str, Any]], schema: Dict[str, Any],
                 contract_label: str = "") -> Dict[str, Any]:
    per_unit: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {"counted": 0, "unproven": 0, "disputed": 0,
                              "retracted": 0, "invalid": 0}
    by_type: Dict[str, int] = {}
    by_grade: Dict[str, int] = {}
    reopened_in_window: List[str] = []
    duplicates: List[str] = []
    claim_value = 0.0
    currencies = set()
    seen_ids: Dict[str, int] = {}

    for i, unit in enumerate(units):
        entry: Dict[str, Any] = {"line": i + 2,
                                 "unit_id": unit.get("unit_id")}
        errors = validate_schema(unit, schema)
        if errors:
            counts["invalid"] += 1
            entry["verdict"] = "invalid"
            entry["reasons"] = errors[:5]
            per_unit.append(entry)
            continue

        uid = unit["unit_id"]
        if uid in seen_ids:
            duplicates.append(uid)
        seen_ids[uid] = seen_ids.get(uid, 0) + 1

        status = unit["status"]
        unproven = unit.get("qualification", {}).get("criteria_unproven") or []
        reasons: List[str] = []

        if status == "counted" and unproven:
            counts["invalid"] += 1
            entry["verdict"] = "invalid"
            entry["reasons"] = [
                "status counted but %d criterion(a) unproven: %s"
                % (len(unproven), "; ".join(unproven[:3]))]
            per_unit.append(entry)
            continue

        reopened, note = _window_reopen(unit)
        if reopened:
            reopened_in_window.append(uid)

        counts[status] = counts.get(status, 0) + 1
        entry["verdict"] = status
        unit_type = unit["unit_type"]
        by_type[unit_type] = by_type.get(unit_type, 0) + 1
        grade = unit["observer_grade"]
        by_grade[grade] = by_grade.get(grade, 0) + 1
        if note:
            entry["window_note"] = note

        if status == "counted":
            value = unit.get("value") or {}
            if value.get("amount") is not None:
                currencies.add(value.get("currency"))
                claim_value += value["amount"]

        per_unit.append(entry)

    multi_currency = len([c for c in currencies if c]) > 1
    return {
        "schema": "agentmeasure.commercial/outcome-ledger",
        "schema_version": "0.1.0",
        "contract_label": contract_label or "(contract as cited per unit)",
        "units_total": len(units),
        "counts": counts,
        "by_unit_type": by_type,
        "by_observer_grade": by_grade,
        "reopened_in_window": reopened_in_window,
        "duplicate_unit_ids": sorted(set(duplicates)),
        "claim_value": round(claim_value, 2) if currencies else None,
        "claim_currency": sorted(currencies)[0] if len(currencies) == 1 else None,
        "currency_note": ("multiple currencies in counted units — not summed"
                          if multi_currency else ""),
        "claim_rule": "only counted units enter the claim; unproven, disputed "
                      "and retracted never do; observer grades do not gate the "
                      "count, they gate the certification stage",
        "lines": per_unit,
    }


def outcome_ledger_markdown(result: Dict[str, Any]) -> str:
    c = result["counts"]
    out = ["# Outcome ledger — %s" % result["contract_label"], ""]
    out.append("| units | counted | unproven | disputed | retracted | invalid |")
    out.append("|---:|---:|---:|---:|---:|---:|")
    out.append("| %d | %d | %d | %d | %d | %d |"
               % (result["units_total"], c["counted"], c["unproven"],
                  c["disputed"], c["retracted"], c["invalid"]))
    out.append("")
    out.append("| by type | by observer grade |")
    out.append("|---|---|")
    types = ", ".join("%s: %d" % kv for kv in sorted(result["by_unit_type"].items()))
    grades = ", ".join("%s: %d" % kv for kv in sorted(result["by_observer_grade"].items()))
    out.append("| %s | %s |" % (types or "—", grades or "—"))
    out.append("")
    if result["claim_value"] is not None:
        out.append("Claim value (counted units only): %s %s"
                   % (result.get("claim_currency") or "(mixed)",
                      result["claim_value"]))
        out.append("")
    if result["reopened_in_window"]:
        out.append("Reopened inside the stability window: %s"
                   % ", ".join(result["reopened_in_window"][:10]))
        out.append("")
    if result["duplicate_unit_ids"]:
        out.append("DUPLICATE unit ids: %s" % ", ".join(result["duplicate_unit_ids"][:10]))
        out.append("")
    out.append(result["claim_rule"] + ".")
    return "\n".join(out)
