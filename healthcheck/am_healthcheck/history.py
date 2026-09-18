"""Local run history — distinguishes demo runs, real runs, errors, repeats.
Also provides trend aggregation to track changes over time.

A tiny append-only file at ~/.agentmeasure/history.jsonl. It never leaves the
machine: this package contains no network code (asserted by tests). Delete the
file to reset first-run detection.
"""
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

HISTORY_DIRNAME = os.path.join(".agentmeasure")
HISTORY_FILENAME = "history.jsonl"


def history_path(home: Optional[str] = None) -> str:
    return os.path.join(home or os.path.expanduser("~"), HISTORY_DIRNAME, HISTORY_FILENAME)


def record_run(entry: Dict[str, object], home: Optional[str] = None) -> None:
    path = history_path(home)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n")
    except OSError:
        pass  # history is best-effort; never block the report


def load_history(home: Optional[str] = None) -> List[Dict[str, object]]:
    path = history_path(home)
    out: List[Dict[str, object]] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        out.append(value)
                except (ValueError, RecursionError):
                    continue
    except OSError:
        pass
    return out


def run_number(mode: str, home: Optional[str] = None) -> int:
    """1 for the first run of this mode, 2, 3, ... for repeats."""
    n = 0
    for entry in load_history(home):
        if entry.get("mode") == mode:
            n += 1
    return n + 1


def trend(home: Optional[str] = None) -> Dict[str, object]:
    """Aggregate history into a trend report.

    Returns dict with weekly and monthly aggregates showing check verdict
    progression over time.
    """
    entries = load_history(home)
    if not entries:
        return {"status": "no_data", "message": "no runs recorded yet"}

    # Filter to own-data runs only (skip synthetic demos)
    real = [e for e in entries if e.get("mode") == "own-data"]
    if not real:
        return {"status": "no_real_data", "message": "no own-data runs recorded yet"}

    # Sort by timestamp
    real.sort(key=lambda e: e.get("ts", ""))

    def _week_key(ts: str) -> str:
        """ISO week string from timestamp."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(ts)
            return "%d-W%02d" % (dt.isocalendar()[0], dt.isocalendar()[1])
        except (ValueError, TypeError):
            return "unknown"

    def _month_key(ts: str) -> str:
        try:
            return ts[:7]  # YYYY-MM
        except (IndexError, TypeError):
            return "unknown"

    # Weekly aggregation
    weeks: Dict[str, dict] = defaultdict(lambda: {
        "runs": 0, "sessions": 0, "executions": 0, "failed": 0,
        "retry_chains": 0, "check_verdicts": defaultdict(list),
    })
    for e in real:
        wk = _week_key(e.get("ts", ""))
        weeks[wk]["runs"] += 1
        weeks[wk]["sessions"] += e.get("sessions", 0)
        weeks[wk]["executions"] += e.get("executions", 0)
        weeks[wk]["failed"] += e.get("failed", 0)
        weeks[wk]["retry_chains"] += e.get("retry_chains", 0)
        for cid, status in (e.get("checks") or {}).items():
            weeks[wk]["check_verdicts"][cid].append(status)

    # Monthly aggregation
    months: Dict[str, dict] = defaultdict(lambda: {
        "runs": 0, "sessions": 0, "executions": 0, "failed": 0,
        "retry_chains": 0, "check_verdicts": defaultdict(list),
    })
    for e in real:
        mk = _month_key(e.get("ts", ""))
        months[mk]["runs"] += 1
        months[mk]["sessions"] += e.get("sessions", 0)
        months[mk]["executions"] += e.get("executions", 0)
        months[mk]["failed"] += e.get("failed", 0)
        months[mk]["retry_chains"] += e.get("retry_chains", 0)
        for cid, status in (e.get("checks") or {}).items():
            months[mk]["check_verdicts"][cid].append(status)

    def _summarize_verdicts(vd: dict) -> dict:
        return {cid: {"ok": lst.count("ok"), "finding": lst.count("finding"),
                      "unprovable": lst.count("unprovable"), "info": lst.count("info"),
                      "total": len(lst)}
                for cid, lst in sorted(vd.items())}

    return {
        "status": "ok",
        "total_runs": len(real),
        "date_range": "%s → %s" % (real[0].get("ts", "?")[:10], real[-1].get("ts", "?")[:10]),
        "weekly": {k: {kk: vv for kk, vv in v.items() if kk != "check_verdicts"}
                   for k, v in sorted(weeks.items())},
        "weekly_checks": {k: _summarize_verdicts(v["check_verdicts"])
                          for k, v in sorted(weeks.items())},
        "monthly": {k: {kk: vv for kk, vv in v.items() if kk != "check_verdicts"}
                    for k, v in sorted(months.items())},
        "monthly_checks": {k: _summarize_verdicts(v["check_verdicts"])
                           for k, v in sorted(months.items())},
        "latest": real[-1],
    }


def render_trend(t: Dict[str, object]) -> str:
    """Render trend report as human-readable text."""
    if t.get("status") != "ok":
        return t.get("message", "no trend data")

    lines = ["AgentMeasure Trend Report", "=" * 40, ""]
    lines.append("Period: %s" % t["date_range"])
    lines.append("Total runs: %d (own-data only)" % t["total_runs"])
    lines.append("")

    if t.get("monthly"):
        lines.append("Monthly summary:")
        for mk, m in t["monthly"].items():
            lines.append("  %s: %d runs, %d sessions, %d execs, %d failed, %d retry chains"
                         % (mk, m["runs"], m["sessions"], m["executions"],
                            m["failed"], m["retry_chains"]))
        lines.append("")

    if t.get("weekly_checks"):
        lines.append("Check verdicts by week:")
        lines.append("  %-12s %s" % ("Week", "HC-01      HC-02      HC-03      HC-04      HC-05      HC-06"))
        lines.append("  " + "-" * 70)
        for wk, checks in sorted(t["weekly_checks"].items()):
            cells = []
            for cid in ("HC-01", "HC-02", "HC-03", "HC-04", "HC-05", "HC-06"):
                v = checks.get(cid, {})
                lst = []
                if v.get("ok", 0): lst.append("%do" % v["ok"])
                if v.get("finding", 0): lst.append("%df" % v["finding"])
                if v.get("unprovable", 0): lst.append("%du" % v["unprovable"])
                cells.append("/".join(lst) if lst else "-")
            lines.append("  %-12s %s" % (wk, "  ".join("%-10s" % c for c in cells)))

    return "\n".join(lines)
