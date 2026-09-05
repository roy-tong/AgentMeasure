"""Snapshots and before/after comparison — the re-run preview (plan R7).

A snapshot is a small, versioned JSON record of one check run: window, verdicts,
and the aggregate counters. Save one before a change, another after, and
`compare` shows what moved — with the same honesty rules as the checks:

- a metric that is UNPROVABLE on either side is labelled, never differenced;
- check verdict transitions are shown as A → B;
- version and window mismatches are disclosed, because they change what a
  delta is allowed to mean.

Snapshots are local artifacts like the HTML report: they contain project names
and session short-ids. Do not upload them; use the share summary for that.
"""
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from . import __version__

SNAPSHOT_SCHEMA = 1
TOOL_TAG = "agentmeasure-healthcheck"


class SnapshotError(ValueError):
    """Raised when a snapshot file cannot be used for comparison."""


def overview_dict(ov) -> Dict[str, object]:
    return {
        "sessions": ov.sessions, "files": ov.files, "lines": ov.lines,
        "corrupt_lines": ov.corrupt_lines, "corrupt_ratio": round(ov.corrupt_ratio, 5),
        "truncated_files": ov.truncated_files,
        "first_ts": ov.first_ts, "last_ts": ov.last_ts, "models": ov.models,
        "cli_versions": sorted(ov.cli_versions), "turns": ov.turns,
        "exec_total": ov.exec_total, "exec_ok": ov.exec_ok,
        "exec_failed": ov.exec_failed, "exec_unknown": ov.exec_unknown,
        "call_total": ov.call_total, "retry_chains": ov.retry_chains,
        "retry_attempts_in_chains": ov.retry_attempts_in_chains,
        "unresolved_chains": ov.unresolved_chains, "compactions": ov.compactions,
        "token_provable": ov.token_provable,
        "token_missing_sessions": ov.token_missing_sessions,
        "token_invalid_sessions": ov.token_invalid_sessions,
        "token": None if not ov.token_provable else {
            "input": ov.token_total_input, "cached_input": ov.token_cached_input,
            "output": ov.token_output, "reasoning_output": ov.token_reasoning_output,
            "total_reported": ov.token_total_reported,
            "subset_rule": "cached ⊆ input; reasoning ⊆ output; never summed",
        },
        "projects": ov.projects,
    }


def build_snapshot(ov, checks, session_rows: List[Dict[str, object]],
                   mode: str, window_label: str, command: str) -> Dict[str, object]:
    return {
        "schema": SNAPSHOT_SCHEMA,
        "tool": TOOL_TAG,
        "tool_version": __version__,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "window_label": window_label,
        "source_command": command,
        "overview": overview_dict(ov),
        "checks": [{"check_id": c.check_id, "name": c.name, "status": c.status,
                    "summary": c.summary} for c in checks],
        "sessions": session_rows,
        "notes": "Local artifact: contains project names and session short-ids. "
                 "Do not upload; use the share summary for sharing.",
    }


def save_snapshot(snapshot: Dict[str, object], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        # ASCII escaping keeps lone surrogates from malformed input from
        # turning an otherwise valid snapshot into a write error.
        json.dump(snapshot, fh, ensure_ascii=True, indent=2)


def load_snapshot(path: str) -> Dict[str, object]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise SnapshotError("cannot read snapshot %s: %s" % (path, exc))
    except ValueError as exc:
        raise SnapshotError("snapshot %s is not valid JSON: %s" % (path, exc))
    if not isinstance(data, dict):
        raise SnapshotError("snapshot %s is not an object" % path)
    if data.get("tool") != TOOL_TAG:
        raise SnapshotError("%s is not an AgentMeasure healthcheck snapshot" % path)
    if data.get("schema") != SNAPSHOT_SCHEMA:
        raise SnapshotError("snapshot %s uses schema %r; this tool reads schema %d — "
                            "re-save the snapshot with the current version"
                            % (path, data.get("schema"), SNAPSHOT_SCHEMA))
    if not isinstance(data.get("overview"), dict):
        raise SnapshotError("snapshot %s has no overview section" % path)
    return data


_METRIC_ROWS = [
    ("sessions", "sessions"),
    ("files", "log files"),
    ("turns", "turns"),
    ("exec_total", "command executions"),
    ("exec_ok", "ok executions"),
    ("exec_failed", "failed executions"),
    ("exec_unknown", "unknown-outcome executions"),
    ("retry_chains", "retry chains"),
    ("retry_attempts_in_chains", "executions inside retry chains"),
    ("unresolved_chains", "unresolved retry chains"),
    ("compactions", "context compactions"),
    ("corrupt_lines", "corrupt lines"),
]

_TOKEN_ROWS = [
    ("input", "input tokens"),
    ("cached_input", "cached input (⊆ input)"),
    ("output", "output tokens"),
    ("reasoning_output", "reasoning output (⊆ output)"),
]


def _delta(a: int, b: int) -> str:
    diff = b - a
    if diff > 0:
        return "+%s" % "{:,}".format(diff)
    if diff < 0:
        return "−%s" % "{:,}".format(-diff)
    return "±0"


def _token_side_unprovable_reason(snap: Dict[str, object]) -> str:
    ov = snap["overview"]
    if ov.get("token_invalid_sessions"):
        return "invalid/incomplete in %s session(s)" % ov.get("token_invalid_sessions")
    if ov.get("token_missing_sessions"):
        return "missing in %s session(s)" % ov.get("token_missing_sessions")
    return "no token events"


def compare_snapshots(a: Dict[str, object], b: Dict[str, object]) -> Dict[str, object]:
    oa, ob = a["overview"], b["overview"]
    rows = []
    for key, label in _METRIC_ROWS:
        va, vb = oa.get(key, 0), ob.get(key, 0)
        rows.append({"metric": label, "a": va, "b": vb,
                     "delta": _delta(va, vb) if isinstance(va, int) and
                     isinstance(vb, int) else "?"})

    token_rows: List[Dict[str, object]] = []
    token_state = "provable"
    if oa.get("token") is None or ob.get("token") is None:
        token_state = "unprovable"
    else:
        for key, label in _TOKEN_ROWS:
            va = (oa["token"] or {}).get(key, 0)
            vb = (ob["token"] or {}).get(key, 0)
            token_rows.append({"metric": label, "a": va, "b": vb,
                               "delta": _delta(va, vb)})

    verdicts = {}
    for snap in (a, b):
        for c in snap.get("checks", []):
            entry = verdicts.setdefault(c.get("check_id", "?"),
                                        {"name": c.get("name", ""), "a": None, "b": None})
            entry["a" if snap is a else "b"] = c.get("status")
    changed = [{"check_id": cid, "name": v["name"], "a": v["a"], "b": v["b"]}
               for cid, v in sorted(verdicts.items()) if v["a"] != v["b"]]

    warnings = []
    if a.get("tool_version") != b.get("tool_version"):
        warnings.append(
            "saved with different tool versions (%s vs %s); check rules may "
            "differ, so deltas are not guaranteed comparable"
            % (a.get("tool_version", "?"), b.get("tool_version", "?")))
    if a.get("window_label") != b.get("window_label"):
        warnings.append("windows differ (%r vs %r); deltas mix different scopes"
                        % (a.get("window_label", "?"), b.get("window_label", "?")))
    if a.get("mode") != b.get("mode"):
        warnings.append("modes differ (%s vs %s); synthetic demos must not be "
                        "compared with own data" % (a.get("mode", "?"), b.get("mode", "?")))

    return {
        "schema": 1,
        "a": {"path": a.get("_path", ""), "saved_at": a.get("saved_at", "?"),
              "window": a.get("window_label", "?"), "mode": a.get("mode", "?"),
              "tool_version": a.get("tool_version", "?")},
        "b": {"path": b.get("_path", ""), "saved_at": b.get("saved_at", "?"),
              "window": b.get("window_label", "?"), "mode": b.get("mode", "?"),
              "tool_version": b.get("tool_version", "?")},
        "rows": rows,
        "token_state": token_state,
        "token_rows": token_rows,
        "token_a_reason": None if token_state == "provable"
        else _token_side_unprovable_reason(a),
        "token_b_reason": None if token_state == "provable"
        else _token_side_unprovable_reason(b),
        "verdicts": [{"check_id": cid, "name": v["name"], "a": v["a"], "b": v["b"]}
                     for cid, v in sorted(verdicts.items())],
        "changed_verdicts": changed,
        "warnings": warnings,
    }


def render_compare_text(cmp: Dict[str, object]) -> str:
    out = []
    bar = "─" * 62
    out.append(bar)
    out.append("AgentMeasure Healthcheck compare v%s" % __version__)
    for side in ("a", "b"):
        info = cmp[side]
        where = info.get("path") or "fresh run"
        out.append("  %s: %s · %s · saved %s"
                   % (side.upper(), where, info.get("window", "?"),
                      str(info.get("saved_at", "?"))[:19]))
    out.append(bar)
    if cmp["warnings"]:
        out.append("Caveats")
        for w in cmp["warnings"]:
            out.append("  ! %s" % w)
        out.append("")
    out.append("Metric                        A → B (Δ)")
    for row in cmp["rows"]:
        out.append("  %-28s %s → %s (%s)"
                   % (row["metric"], "{:,}".format(row["a"]),
                      "{:,}".format(row["b"]), row["delta"]))
    if cmp["token_state"] == "provable":
        for row in cmp["token_rows"]:
            out.append("  %-28s %s → %s (%s)"
                       % (row["metric"], "{:,}".format(row["a"]),
                          "{:,}".format(row["b"]), row["delta"]))
    else:
        out.append("  %-28s UNPROVABLE — no delta shown (A: %s; B: %s)"
                   % ("tokens", cmp["token_a_reason"], cmp["token_b_reason"]))
    out.append("")
    out.append("Check verdicts")
    for v in cmp["verdicts"]:
        marker = "" if v["a"] == v["b"] else "  ← changed"
        out.append("  %s %-24s %s → %s%s"
                   % (" ", v["check_id"], str(v["a"]).upper(),
                      str(v["b"]).upper(), marker))
    out.append("")
    out.append("What to read first: failed executions, retry chains, and any "
               "verdict that moved to FINDING.")
    out.append("UNPROVABLE sides are never differenced. Same logs + same "
               "version → same snapshot.")
    out.append(bar)
    return "\n".join(out)
