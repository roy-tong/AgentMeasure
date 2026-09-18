"""Report export converters — OTel, Prometheus, and enriched JSON.

This module converts the AgentMeasure healthcheck report JSON (from
``agentmeasure check --json``) into observability-industry-standard formats.
It uses only the Python standard library — no external dependencies.

Three entry points:

* ``to_otel(report)``        — OpenTelemetry metrics protobuf JSON (flat list of
                               Metric items).
* ``to_prometheus(report)``  — Prometheus text exposition format (gauge type
                               for all metrics).
* ``to_json_export(report)`` — Enriched JSON with audit_summary, trends
                               placeholder, and auto-generated recommendations.
"""

import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Status encoding shared by OTel and Prometheus output
# ---------------------------------------------------------------------------
# The four healthcheck verdicts mapped to numeric values for use in gauge
# metrics.  -1 (unprovable) is always below 0 so dashboards can alert on
# "anything < 0" to flag inconclusive results.
_STATUS_CODE: Dict[str, float] = {
    "ok": 0.0,
    "info": 1.0,
    "finding": 2.0,
    "unprovable": -1.0,
}

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------
# Each entry is a tuple of (metric_name, description, unit).
#
# Overview-derived metrics (from report["overview"]):
_OVERVIEW_METRICS: List[Tuple[str, str, str]] = [
    ("attempts_total",
     "Total number of command executions (canonical, deduplicated).",
     "1"),
    ("operations_total",
     "Total number of model-side tool calls (response_item records, "
     "never summed with executions).",
     "1"),
    ("retry_chains_total",
     "Total number of retry chains (maximal consecutive same-command failure "
     "blocks).",
     "1"),
]

# HC check metrics (from report["checks"]).  The check_id field in the report
# maps to the metric name used here.
_HC_METRICS: List[Tuple[str, str, str]] = [
    ("hc_duplicate_records",
     "Duplicate records check (HC-01): identical lines, repeated call_ids, "
     "execution id conflicts.",
     "1"),
    ("hc_retry_amplification",
     "Retry amplification check (HC-02): same-command failure-retry chains.",
     "1"),
    ("hc_tool_error_runs",
     "Tool error runs check (HC-03): consecutive same-tool failures.",
     "1"),
    ("hc_operation_resolution_coverage",
     "Operation resolution coverage check (HC-04): percentage of operations "
     "with a tracked operation_id and successful outcome.",
     "1"),
    ("hc_cache_accounting",
     "Cache accounting cross-check (HC-05): token snapshot arithmetic "
     "anomalies.",
     "1"),
    ("hc_token_stability",
     "Token accounting stability check (HC-06): cross-session "
     "tokens-per-execution coefficient of variation.",
     "1"),
]

# Mapping from metric name to the expected HC check_id in the report checks
# array.
_METRIC_TO_CHECK_ID: Dict[str, str] = {
    "hc_duplicate_records": "HC-01",
    "hc_retry_amplification": "HC-02",
    "hc_tool_error_runs": "HC-03",
    "hc_operation_resolution_coverage": "HC-04",
    "hc_cache_accounting": "HC-05",
    "hc_token_stability": "HC-06",
}

_HC_NAME_LABEL: Dict[str, str] = {
    "HC-01": "Duplicate records",
    "HC-02": "Retry amplification",
    "HC-03": "Tool error runs",
    "HC-04": "Operation resolution coverage",
    "HC-05": "Cache accounting",
    "HC-06": "Token stability",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lookup_check(report: Dict[str, Any], check_id: str) -> Optional[Dict[str, Any]]:
    """Return the check dict for *check_id*, or *None* if not present.

    Checks are identified by the ``check_id`` field inside the report's
    ``checks`` array.  Audit-only checks (HC-04, HC-05, HC-06) are absent
    when the user runs without ``--audit``.
    """
    for c in report.get("checks", []):
        if c.get("check_id") == check_id:
            return c
    return None


def _derive_timestamp_ns(report: Dict[str, Any]) -> str:
    """Return a nanosecond-epoch timestamp string for OTel data points.

    Uses ``overview.last_ts`` if available, otherwise ``overview.first_ts``,
    otherwise the current time in UTC.  Returns a string (OTel proto JSON
    represents int64 as a string).
    """
    ov = report.get("overview") or {}
    for key in ("last_ts", "first_ts"):
        raw = ov.get(key)
        if raw and isinstance(raw, str):
            try:
                # Strip trailing "Z" and microseconds to keep parsing simple.
                cleaned = raw.rstrip("Z")
                dt = datetime.datetime.fromisoformat(cleaned)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                ns = int(dt.timestamp() * 1_000_000_000)
                return str(ns)
            except (ValueError, TypeError, OverflowError):
                continue
    now = datetime.datetime.now(datetime.timezone.utc)
    return str(int(now.timestamp() * 1_000_000_000))


def _check_status_value(check: Optional[Dict[str, Any]]) -> float:
    """Return the numeric status code for a check dict (or -1 if missing)."""
    if check is None:
        return -1.0
    return _STATUS_CODE.get(check.get("status", ""), -1.0)


def _otel_attributes(**kwargs: str) -> List[Dict[str, Any]]:
    """Build a list of OTel KeyValue dicts from keyword arguments.

    Each value is wrapped in ``{"stringValue": ...}`` per the OTel proto JSON
    mapping for ``any_value``.
    """
    return [
        {"key": k, "value": {"stringValue": v}}
        for k, v in kwargs.items()
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def to_otel(report: Dict[str, Any]) -> str:
    """Convert the check report to a JSON string containing a flat array of
    OTel ``Metric`` protobuf messages.

    The output follows the OTLP protobuf JSON mapping (proto3 canonical
    serialisation).  Each ``Metric`` has ``name``, ``description``, ``unit``,
    and one of ``gauge`` / ``sum``.  Overview counters use ``Sum`` with
    ``aggregation_temporality = AGGREGATION_TEMPORALITY_CUMULATIVE`` (2); HC
    check results use ``Gauge``.

    Usage::

        report = json.load(open("agentmeasure-report.json"))
        print(to_otel(report))
    """
    ov = report.get("overview") or {}
    timestamp_ns = _derive_timestamp_ns(report)
    ts_attr = _otel_attributes(window=report.get("window", ""),
                               mode=report.get("mode", ""))

    metrics: List[Dict[str, Any]] = []

    # ---- Overview counters as Sum (cumulative) ---------------------------
    for metric_name, description, unit in _OVERVIEW_METRICS:
        if metric_name == "attempts_total":
            value = ov.get("exec_total", 0)
        elif metric_name == "operations_total":
            value = ov.get("call_total", 0)
        elif metric_name == "retry_chains_total":
            value = ov.get("retry_chains", 0)
        else:
            continue

        metrics.append({
            "name": metric_name,
            "description": description,
            "unit": unit,
            "sum": {
                "dataPoints": [{
                    "attributes": ts_attr,
                    "asInt": str(value),
                    "timeUnixNano": timestamp_ns,
                }],
                "aggregationTemporality": 2,  # CUMULATIVE
                "isMonotonic": True,
            },
        })

    # ---- HC check results as Gauge ---------------------------------------
    for metric_name, description, unit in _HC_METRICS:
        check_id = _METRIC_TO_CHECK_ID.get(metric_name, "")
        check = _lookup_check(report, check_id)
        status_value = _check_status_value(check)
        status_str = check.get("status", "unprovable") if check else "unprovable"
        check_name = check.get("name", check_id) if check else check_id

        attrs = _otel_attributes(
            check_id=check_id,
            check_name=check_name,
            status=status_str,
            window=report.get("window", ""),
            mode=report.get("mode", ""),
        )

        metrics.append({
            "name": metric_name,
            "description": description,
            "unit": unit,
            "gauge": {
                "dataPoints": [{
                    "attributes": attrs,
                    "asDouble": status_value,
                    "timeUnixNano": timestamp_ns,
                }],
            },
        })

    return json.dumps(metrics, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------


def to_prometheus(report: Dict[str, Any]) -> str:
    """Convert the check report to Prometheus text exposition format.

    All metrics are declared as ``gauge``.  Every metric carries a ``# HELP``
    and ``# TYPE`` line.  Labels:

    * **Overview counters** — ``window``, ``mode``.
    * **HC check gauges** — ``check_id``, ``check_name``, ``status``,
      ``window``, ``mode``.

    Usage::

        report = json.load(open("agentmeasure-report.json"))
        print(to_prometheus(report))
    """
    ov = report.get("overview") or {}
    window = report.get("window", "")
    mode = report.get("mode", "")
    lines: List[str] = []

    def _escape_label_value(s: Any) -> str:
        """Prometheus label-value escaping: backslash, double-quote, newline."""
        raw = str(s)
        raw = raw.replace("\\", "\\\\")
        raw = raw.replace("\"", "\\\"")
        raw = raw.replace("\n", "\\n")
        return raw

    def _gauge_line(name: str, labels: Dict[str, str], value: float) -> str:
        """Build one metric line: ``name{labels} value``.

        Labels are sorted for deterministic output.  The label set is omitted
        entirely when it is empty (producing a bare ``name value`` line).
        """
        if labels:
            parts = ",".join(
                '%s="%s"' % (k, _escape_label_value(v))
                for k, v in sorted(labels.items())
            )
            return "%s{%s} %s" % (name, parts, value)
        return "%s %s" % (name, value)

    # ---- Overview counters -------------------------------------------------
    overview_fields = [
        ("attempts_total", ov.get("exec_total", 0),
         "Total number of command executions"),
        ("operations_total", ov.get("call_total", 0),
         "Total number of model-side tool calls"),
        ("retry_chains_total", ov.get("retry_chains", 0),
         "Total number of retry chains"),
    ]
    base_labels = {"window": window, "mode": mode}
    for metric_name, value, help_text in overview_fields:
        lines.append("# HELP %s %s" % (metric_name, help_text))
        lines.append("# TYPE %s gauge" % metric_name)
        lines.append(_gauge_line(metric_name, base_labels, float(value)))

    # ---- HC check gauges ---------------------------------------------------
    for metric_name, description, _unit in _HC_METRICS:
        check_id = _METRIC_TO_CHECK_ID.get(metric_name, "")
        check = _lookup_check(report, check_id)
        status_value = _check_status_value(check)
        status_str = check.get("status", "unprovable") if check else "unprovable"
        check_name = check.get("name", check_id) if check else check_id

        lines.append("# HELP %s %s" % (metric_name, description))
        lines.append("# TYPE %s gauge" % metric_name)
        lines.append(_gauge_line(metric_name, {
            "check_id": check_id,
            "check_name": check_name,
            "status": status_str,
            "window": window,
            "mode": mode,
        }, status_value))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------


def to_json_export(report: Dict[str, Any]) -> Dict[str, Any]:
    """Return an enriched copy of the report with an ``audit_summary`` section,
    a ``trends`` placeholder, and auto-generated ``recommendations``.

    The original report dict is **not** mutated — the returned dict is a deep
    copy (JSON round-trip) with the extra sections merged in.

    **audit_summary** contains::

        {
            "overall_verdict": "pass" | "fail" | "unprovable" | "mixed",
            "total_checks": <int>,
            "passed": <int>,
            "failed": <int>,
            "unprovable": <int>,
            "info": <int>,
        }

    **trends** is an empty dict reserved for future time-series data.

    **recommendations** is a list of strings, one per check with a non-ok
    status, suggesting concrete next steps.

    Usage::

        report = json.load(open("agentmeasure-report.json"))
        enriched = to_json_export(report)
        json.dump(enriched, open("agentmeasure-report-audited.json", "w"),
                  indent=2)
    """
    # Deep copy via JSON round-trip so the original reference is untouched.
    exported = json.loads(json.dumps(report))

    checks = exported.get("checks", [])

    # ---- audit_summary ----------------------------------------------------
    passed = 0
    failed = 0
    unprovable = 0
    info_count = 0

    for c in checks:
        status = c.get("status", "")
        if status == "ok":
            passed += 1
        elif status == "finding":
            failed += 1
        elif status == "unprovable":
            unprovable += 1
        elif status == "info":
            info_count += 1

    total = len(checks)

    if total == 0:
        overall_verdict = "unprovable"
    elif failed > 0:
        overall_verdict = "fail"
    elif unprovable > 0 and passed == 0:
        overall_verdict = "unprovable"
    elif passed == total:
        overall_verdict = "pass"
    else:
        # mix of ok, info, unprovable with no findings
        overall_verdict = "pass"

    exported["audit_summary"] = {
        "overall_verdict": overall_verdict,
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "unprovable": unprovable,
        "info": info_count,
    }

    # ---- trends (placeholder) ---------------------------------------------
    exported["trends"] = {}

    # ---- recommendations --------------------------------------------------
    recommendations: List[str] = []

    for c in checks:
        cid = c.get("check_id", "")
        status = c.get("status", "")
        name = c.get("name", cid)

        if status == "finding":
            if cid == "HC-01":
                recommendations.append(
                    "HC-01 Duplicate Records: Review the flagged duplicate "
                    "lines, repeated call_ids, or execution-id conflicts. "
                    "Deduplicate at the source (runtime writer) to prevent "
                    "inflated counts in downstream metrics."
                )
            elif cid == "HC-02":
                recommendations.append(
                    "HC-02 Retry Amplification: Inspect the retry chains "
                    "with the most attempts. The first failure in each chain "
                    "usually reveals a flaky command, missing dependency, or "
                    "incorrect path — fixing it eliminates all subsequent "
                    "retry cost."
                )
            elif cid == "HC-03":
                recommendations.append(
                    "HC-03 Tool Error Runs: Examine the longest consecutive "
                    "same-tool failure runs. Common root causes include "
                    "authentication errors, missing system tools, or "
                    "incorrect working directory assumptions."
                )
            elif cid == "HC-04":
                recommendations.append(
                    "HC-04 Operation Resolution Coverage: Below 50%% of "
                    "executions carry a tracked operation_id and succeed. "
                    "Check that the runtime assigns operation ids to every "
                    "command and that failures are handled gracefully."
                )
            elif cid == "HC-05":
                recommendations.append(
                    "HC-05 Cache Accounting: Token snapshots show arithmetic "
                    "that suggests cache amounts overlap with non-cache "
                    "totals. Review the raw token events around the flagged "
                    "lines; this is the most common token-bug category."
                )
            elif cid == "HC-06":
                recommendations.append(
                    "HC-06 Token Stability: The per-execution token ratio "
                    "varies widely across sessions in the same project. "
                    "Investigate differences in system prompt size, file "
                    "attachments, or compaction frequency."
                )
            else:
                recommendations.append(
                    "%s %s: Address the findings described in the check "
                    "evidence." % (cid, name)
                )

        elif status == "unprovable":
            reason = c.get("unprovable_reason", "")
            if reason:
                recommendations.append(
                    "%s %s: UNPROVABLE — %s "
                    "Provide additional log data or a wider time window to "
                    "make this check decidable." % (cid, name, reason)
                )
            else:
                recommendations.append(
                    "%s %s: UNPROVABLE due to insufficient data. "
                    "A wider window or more complete logs may resolve this."
                    % (cid, name)
                )

        elif status == "info":
            if cid == "HC-04":
                recommendations.append(
                    "HC-04: Resolution coverage is in the borderline "
                    "50–80%% range. Monitor for regression below 50%%."
                )
            # Other info-level checks have no prescriptive recommendation
            # beyond what the check's next_step already covers.

    if not recommendations:
        recommendations.append(
            "All health checks pass — no actionable recommendations at "
            "this time."
        )

    exported["recommendations"] = recommendations

    return exported