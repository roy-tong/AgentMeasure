"""Versioned export schemas and a minimal structural validator.

External consumers integrate against the JSON documents this tool exports
(`--json` report export, snapshots, compare export), not against internal
modules. Those documents are versioned:

  report-v1    the `--json` export of a check/demo run
  snapshot-v1  the file written by `--save-snapshot` (schema field = 1)
  compare-v1   the `compare --json` export

Compatibility policy (R8 contract):
- within a schema version, fields are only added, never renamed or removed;
- a consumer that meets an unknown newer schema version must stop and say so
  (`agentmeasure validate` models this behaviour);
- the reference schema documents live in `healthcheck/schemas/`.

The validator below checks the structural subset we actually guarantee
(required keys and basic types) with the standard library only. It is
deliberately small: it validates OUR exports, it is not a JSON Schema engine.
"""
import json
from typing import Dict, List, Optional

REPORT_SCHEMA = 1
SNAPSHOT_SCHEMA = 1
COMPARE_SCHEMA = 1

_TYPE_NAMES = {
    dict: "object", list: "array", str: "string", bool: "boolean",
    int: "number", float: "number",
}

_OVERVIEW_FIELDS = {
    "sessions": int, "files": int, "lines": int, "corrupt_lines": int,
    "corrupt_ratio": (int, float), "truncated_files": int,
    "first_ts": str, "last_ts": str, "models": list, "cli_versions": list,
    "turns": int, "exec_total": int, "exec_ok": int, "exec_failed": int,
    "exec_unknown": int, "call_total": int, "retry_chains": int,
    "retry_attempts_in_chains": int, "unresolved_chains": int,
    "compactions": int, "token_provable": bool,
    "token_missing_sessions": int, "token_invalid_sessions": int,
    "token": (dict, type(None)), "projects": list,
}

_CHECK_FIELDS = {"check_id": str, "name": str, "status": str, "summary": str}

_STATUS_VALUES = {"ok", "finding", "unprovable", "info"}


def _type_name(expected) -> str:
    if isinstance(expected, tuple):
        return "/".join(_TYPE_NAMES.get(t, "?") for t in expected)
    return _TYPE_NAMES.get(expected, "?")


def _check_object(obj, spec: Dict[str, object], path: str,
                  errors: List[str], required: bool = True) -> None:
    for key, expected in spec.items():
        if key not in obj:
            if required:
                errors.append("%s: missing required field %r" % (path, key))
            continue
        value = obj[key]
        if expected == (dict, type(None)):
            if value is not None and not isinstance(value, dict):
                errors.append("%s.%s: expected object or null" % (path, key))
        elif not isinstance(value, expected) or (
                isinstance(expected, tuple) and isinstance(value, bool)):
            errors.append("%s.%s: expected %s, got %s"
                          % (path, key, _type_name(expected),
                             type(value).__name__))


def validate_overview(overview: dict, path: str = "overview",
                      errors: Optional[List[str]] = None) -> List[str]:
    errors = errors if errors is not None else []
    if not isinstance(overview, dict):
        errors.append("%s: expected object" % path)
        return errors
    _check_object(overview, _OVERVIEW_FIELDS, path, errors)
    token = overview.get("token")
    if isinstance(token, dict):
        _check_object(token, {k: int for k in
                              ("input", "cached_input", "output",
                               "reasoning_output", "total_reported")},
                      path + ".token", errors)
    return errors


def validate_report(data: dict) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["top level: expected object"]
    _check_object(data, {
        "schema": int, "tool": str, "version": str, "mode": str,
        "window": str, "overview": dict, "checks": list,
        "coverage": list, "share_summary": dict,
    }, "report", errors)
    if data.get("tool") != "agentmeasure-healthcheck":
        errors.append("report.tool: expected 'agentmeasure-healthcheck'")
    if data.get("schema") != REPORT_SCHEMA:
        errors.append("report.schema: expected %d (this build speaks "
                      "report-v%d only)" % (REPORT_SCHEMA, REPORT_SCHEMA))
    if isinstance(data.get("overview"), dict):
        validate_overview(data["overview"], errors=errors)
    checks = data.get("checks")
    if isinstance(checks, list):
        for i, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append("report.checks[%d]: expected object" % i)
                continue
            _check_object(check, _CHECK_FIELDS, "report.checks[%d]" % i, errors)
            if check.get("status") not in _STATUS_VALUES:
                errors.append("report.checks[%d].status: unknown verdict %r"
                              % (i, check.get("status")))
    return errors


def validate_snapshot(data: dict) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["top level: expected object"]
    _check_object(data, {
        "schema": int, "tool": str, "tool_version": str, "saved_at": str,
        "mode": str, "window_label": str, "source_command": str,
        "overview": dict, "checks": list, "sessions": list, "notes": str,
    }, "snapshot", errors)
    if data.get("tool") != "agentmeasure-healthcheck":
        errors.append("snapshot.tool: expected 'agentmeasure-healthcheck'")
    if data.get("schema") != SNAPSHOT_SCHEMA:
        errors.append("snapshot.schema: expected %d — a different schema "
                      "version must be handled by its own reader"
                      % SNAPSHOT_SCHEMA)
    if isinstance(data.get("overview"), dict):
        validate_overview(data["overview"], errors=errors)
    return errors


def validate_compare(data: dict) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["top level: expected object"]
    _check_object(data, {
        "schema": int, "a": dict, "b": dict, "rows": list,
        "token_state": str, "token_rows": list, "verdicts": list,
        "changed_verdicts": list, "warnings": list,
    }, "compare", errors)
    if data.get("schema") != COMPARE_SCHEMA:
        errors.append("compare.schema: expected %d" % COMPARE_SCHEMA)
    return errors


def detect_kind(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    if "saved_at" in data and "window_label" in data:
        return "snapshot"
    if "share_summary" in data and "window" in data:
        return "report"
    if "changed_verdicts" in data and "token_state" in data:
        return "compare"
    return None


def validate_file(path: str):
    """Load a JSON export and validate it against its detected schema.

    Returns (kind, errors); kind is None when the document cannot be
    identified, with errors explaining why.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        return None, ["cannot read %s: %s" % (path, exc)]
    except ValueError as exc:
        return None, ["%s is not valid JSON: %s" % (path, exc)]
    kind = detect_kind(data)
    if kind is None:
        return None, ["%s is not an AgentMeasure export (no known top-level "
                      "shape)" % path]
    validators = {"report": validate_report, "snapshot": validate_snapshot,
                  "compare": validate_compare}
    return kind, validators[kind](data)
