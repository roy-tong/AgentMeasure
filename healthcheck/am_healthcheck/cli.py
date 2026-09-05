"""CLI orchestration: check / demo / compare / selftest / history.

Exit codes (R5 contract):
  0  the check or compare ran and produced its output (findings or not)
  2  input/output error: no readable logs, bad arguments, unreadable directory,
     unusable snapshot, or report output cannot be written

A run with FINDING results still exits 0 — findings describe the user's agent
runs, not a failure of this tool.
"""
import argparse
import json
import os
import shlex
import sys
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from . import __version__
from . import checks as checks_mod
from . import codex as codex_adapter
from . import discover as discover_mod
from . import history as history_mod
from . import report_html as html_mod
from . import report_text as text_mod
from . import share as share_mod
from . import snapshot as snapshot_mod
from . import schema as schema_mod

DEFAULT_DAYS = 7
DEFAULT_HTML = "agentmeasure-report.html"


class _InputError(Exception):
    """User-facing input problem; message is printed and the run exits 2."""


def _window_label(args, since=None, until=None) -> str:
    if getattr(args, "all", False):
        base = "all local sessions"
    elif since or until:
        parts = []
        if since:
            parts.append(since.strftime("%Y-%m-%d"))
        parts.append("→")
        if until:
            parts.append(until.strftime("%Y-%m-%d"))
        base = "sessions %s" % " ".join(parts)
    elif getattr(args, "dir", None):
        base = "explicit directory: %s" % args.dir
    else:
        base = "last %d day(s) of local sessions" % getattr(args, "days", DEFAULT_DAYS)
    project = getattr(args, "project", None)
    if project:
        base += " · project ~%s" % project
    return base


def _parse_date_arg(text: Optional[str], flag: str):
    if not text:
        return None
    try:
        return discover_mod.parse_date(text)
    except ValueError as exc:
        raise _InputError("%s: %s" % (flag, exc))


def _validate_output_paths(input_paths: List[str], *output_paths) -> str:
    """Reject collisions and missing parents before any report is written."""
    outputs = [str(p) for p in output_paths if p]
    normalized = [os.path.realpath(os.path.abspath(p)) for p in outputs]
    if len(set(normalized)) != len(normalized):
        return "HTML, JSON, snapshot, and share outputs must use different paths"
    inputs = {os.path.realpath(os.path.abspath(p)) for p in input_paths}
    if inputs.intersection(normalized):
        return "an output path would overwrite an input log; choose another path"
    for p, absolute in zip(outputs, normalized):
        if os.path.exists(absolute):
            for source in input_paths:
                try:
                    if os.path.exists(source) and os.path.samefile(absolute, source):
                        return "an output path refers to an input log (including a hard link); choose another path"
                except OSError:
                    continue
        if os.path.isdir(absolute):
            return "output path is a directory: %s" % p
        parent = os.path.dirname(absolute)
        if not os.path.isdir(parent):
            return "output parent directory does not exist: %s" % parent
    return ""


def _has_supported_signal(session) -> bool:
    return bool(session.session_id or session.execs or session.calls or session.tokens or
                session.thread_tokens or session.turns or session.compactions or
                session.file_changes or session.subagent_activity)


def _collect_paths(args, since=None, until=None) -> List[str]:
    """Shared input collection for check and compare-fresh runs."""
    if getattr(args, "dir", None):
        if not os.path.isdir(args.dir):
            raise _InputError("--dir %s is not a directory" % args.dir)
        paths = sorted(
            os.path.join(base, name)
            for base, _dirs, names in os.walk(args.dir)
            for name in names if name.endswith(".jsonl"))
        if not paths:
            raise _InputError("no .jsonl files under %s" % args.dir)
        if since or until:
            paths, skipped, undated = discover_mod.filter_by_date(paths, since, until)
            if skipped:
                print("note: date filter skipped %d file(s)" % skipped)
            if undated:
                print("note: %d file(s) have no rollout date in the name and were "
                      "kept (window cannot be decided)" % undated)
            if not paths:
                raise _InputError("the date filter removed every file under %s" % args.dir)
        return paths

    result = discover_mod.discover(
        since_days=None if (getattr(args, "all", False) or since or until)
        else getattr(args, "days", DEFAULT_DAYS),
        scan_all=getattr(args, "all", False), since=since, until=until)
    primary = result.primary()
    for rt in result.runtimes:
        if rt.note:
            print("note [%s]: %s" % (rt.runtime, rt.note))
    paths = primary.files if primary else []
    if not paths:
        raise _InputError("no supported log files found in the selected window. "
                          "Try --days N, --since/--until, --all, or --dir <path>.")
    return paths


def _analyze(paths: List[str], project: Optional[str], window_label: str):
    """Parse, filter, and run checks. Returns everything a report needs."""
    sessions = [codex_adapter.parse_session(p) for p in paths]
    if not any(_has_supported_signal(s) for s in sessions):
        raise _InputError("no supported Codex rollout events found in the selected input")
    if project:
        needle = project.lower()
        known = sorted({s.project or "(unknown)" for s in sessions})
        sessions = [s for s in sessions if needle in (s.project or "(unknown)").lower()]
        if not sessions:
            raise _InputError("no sessions match --project %r; known projects: %s"
                              % (project, ", ".join(known) or "none"))
    ov, check_results, coverage, top3 = checks_mod.run_checks(sessions, window_label)
    rows = checks_mod.session_summaries(sessions)
    return sessions, ov, check_results, coverage, top3, rows


def _run_check(paths: List[str], mode: str, window_label: str, command: str,
               html_path: str, json_path, share_path, snapshot_path,
               use_history: bool, home=None, project=None) -> int:
    output_error = _validate_output_paths(paths, html_path, json_path, share_path,
                                          snapshot_path)
    if output_error:
        print("error: %s" % output_error, file=sys.stderr)
        return 2
    try:
        sessions, ov, check_results, coverage, top3, rows = _analyze(
            paths, project, window_label)
    except _InputError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    summary = share_mod.build_share_summary(ov, check_results, mode, window_label)

    run_no = history_mod.run_number(mode, home) if use_history else 1
    runtime_note = "runtime: codex-rollout adapter v%s" % __version__

    print(text_mod.render_terminal(ov, check_results, top3, mode, run_no,
                                   runtime_note))

    try:
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html_mod.render_html(ov, check_results, coverage, top3,
                                          sessions, mode, window_label,
                                          command, summary))
        print("\nHTML report  → %s (contains local paths — do not upload as-is)"
              % os.path.abspath(html_path))
    except OSError as exc:
        print("\nerror: could not write HTML report: %s" % exc, file=sys.stderr)
        return 2

    if json_path:
        payload = {
            "schema": schema_mod.REPORT_SCHEMA,
            "tool": "agentmeasure-healthcheck", "version": __version__,
            "mode": mode, "window": window_label,
            "overview": snapshot_mod.overview_dict(ov),
            "checks": [_check_dict(c) for c in check_results],
            "coverage": [_finding_dict(f) for f in coverage],
            "share_summary": summary,
        }
        try:
            with open(json_path, "w", encoding="utf-8") as fh:
                # ASCII escaping keeps lone Unicode surrogates from malformed
                # input from turning an otherwise valid export into a write
                # error. The JSON remains standards-compliant and readable.
                json.dump(payload, fh, ensure_ascii=True, indent=2)
        except OSError as exc:
            print("error: could not write JSON export: %s" % exc, file=sys.stderr)
            return 2
        print("JSON export  → %s" % os.path.abspath(json_path))

    if share_path:
        if share_path.endswith(".json"):
            body = share_mod.share_json(summary)
        else:
            body = share_mod.share_markdown(summary)
        try:
            with open(share_path, "w", encoding="utf-8") as fh:
                fh.write(body + "\n")
        except OSError as exc:
            print("error: could not write share summary: %s" % exc, file=sys.stderr)
            return 2
        print("Share summary → %s (sanitized: aggregate counts only)"
              % os.path.abspath(share_path))

    if snapshot_path:
        snap = snapshot_mod.build_snapshot(ov, check_results, rows, mode,
                                           window_label, command)
        try:
            snapshot_mod.save_snapshot(snap, snapshot_path)
        except OSError as exc:
            print("error: could not write snapshot: %s" % exc, file=sys.stderr)
            return 2
        print("Snapshot     → %s (local artifact; compare with `compare`)"
              % os.path.abspath(snapshot_path))

    if use_history:
        history_mod.record_run({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": mode, "window": window_label, "sessions": ov.sessions,
            "executions": ov.exec_total, "failed": ov.exec_failed,
            "retry_chains": ov.retry_chains,
            "checks": {c.check_id: c.status for c in check_results},
            "report": os.path.abspath(html_path),
        }, home)
    return 0


def _check_dict(c):
    return {"check_id": c.check_id, "name": c.name, "status": c.status,
            "summary": c.summary, "unprovable_reason": c.unprovable_reason,
            "findings": [_finding_dict(f) for f in c.findings]}


def _finding_dict(f):
    return {"title": f.title, "severity": f.severity,
            "explanation": f.explanation, "next_step": f.next_step,
            "evidence": [{"session": e.session, "file": e.file, "line": e.line,
                          "detail": e.detail} for e in f.evidence]}


def _demo_fixture_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "demo", "demo-codex.jsonl")


def _fixture_path(name: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", name)


def _resolve_snapshot_path(value) -> Optional[str]:
    if value is True:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return "agentmeasure-snapshot-%s.json" % stamp
    return value


def _validate_run_args(args) -> Tuple[Optional[object], Optional[object]]:
    if getattr(args, "days", DEFAULT_DAYS) < 0:
        raise _InputError("--days must be >= 0")
    since = _parse_date_arg(getattr(args, "since", None), "--since")
    until = _parse_date_arg(getattr(args, "until", None), "--until")
    if since and until and until < since:
        raise _InputError("--until is earlier than --since")
    return since, until


def cmd_check(args) -> int:
    command = "python3 healthcheck/agentmeasure " + shlex.join(
        getattr(args, "_argv", sys.argv[1:]) or ["check"])
    mode = "own-data"
    try:
        since, until = _validate_run_args(args)
        paths = _collect_paths(args, since, until)
        window_label = _window_label(args, since, until)
    except _InputError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    print("reading %d rollout file(s)…" % len(paths))
    html_path = args.html or DEFAULT_HTML
    snapshot_path = _resolve_snapshot_path(args.save_snapshot)
    return _run_check(paths, mode, window_label, command, html_path,
                      args.json, args.share, snapshot_path,
                      not args.no_history, project=args.project)


def cmd_demo(args) -> int:
    fixture = _demo_fixture_path()
    if not os.path.isfile(fixture):
        print("error: demo fixture missing: %s" % fixture, file=sys.stderr)
        return 2
    command = "python3 healthcheck/agentmeasure " + shlex.join(
        getattr(args, "_argv", sys.argv[1:]) or ["demo"])
    html_path = args.html or "agentmeasure-demo-report.html"
    snapshot_path = _resolve_snapshot_path(args.save_snapshot)
    return _run_check([fixture], "synthetic-demo", "synthetic demo session",
                      command, html_path, args.json, args.share, snapshot_path,
                      not args.no_history)


def cmd_compare(args) -> int:
    if len(args.snapshots) > 2:
        print("error: compare takes one snapshot (compared against a fresh run) "
              "or two snapshots", file=sys.stderr)
        return 2
    command = "python3 healthcheck/agentmeasure " + shlex.join(
        getattr(args, "_argv", sys.argv[1:]) or ["compare"])
    try:
        snap_a = snapshot_mod.load_snapshot(args.snapshots[0])
        snap_a["_path"] = os.path.abspath(args.snapshots[0])
        if len(args.snapshots) == 2:
            snap_b = snapshot_mod.load_snapshot(args.snapshots[1])
            snap_b["_path"] = os.path.abspath(args.snapshots[1])
        else:
            since, until = _validate_run_args(args)
            paths = _collect_paths(args, since, until)
            window_label = _window_label(args, since, until)
            print("reading %d rollout file(s) for the fresh side…" % len(paths))
            _sessions, ov, check_results, _cov, _top, rows = _analyze(
                paths, getattr(args, "project", None), window_label)
            snap_b = snapshot_mod.build_snapshot(
                ov, check_results, rows, "own-data", window_label, command)
            snap_b["_path"] = ""
    except (_InputError, snapshot_mod.SnapshotError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    if args.json:
        output_error = _validate_output_paths(
            [p for p in (snap_a.get("_path"), snap_b.get("_path")) if p], args.json)
        if output_error:
            print("error: %s" % output_error, file=sys.stderr)
            return 2

    cmp = snapshot_mod.compare_snapshots(snap_a, snap_b)
    print(snapshot_mod.render_compare_text(cmp))

    if args.json:
        try:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(cmp, fh, ensure_ascii=True, indent=2)
        except OSError as exc:
            print("error: could not write compare export: %s" % exc, file=sys.stderr)
            return 2
        print("\nCompare export → %s" % os.path.abspath(args.json))

    if not args.no_history:
        history_mod.record_run({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "mode": "compare",
            "a": snap_a.get("_path") or "in-memory",
            "b": snap_b.get("_path") or "fresh run",
            "changed_verdicts": len(cmp["changed_verdicts"]),
        })
    return 0


def cmd_share(args) -> int:
    """Preview-then-export: show the sanitized summary, write only with --out.

    The default is a PREVIEW on the terminal — nothing is exported until the
    user re-runs with an explicit --out after reviewing what would leave the
    machine. The summary is re-checked against the whitelist before either
    step (defense in depth for hand-edited or future report files).
    """
    kind, errors = schema_mod.validate_file(args.report)
    if errors:
        for err in errors:
            print("error: %s" % err, file=sys.stderr)
        return 2
    if kind != "report":
        print("error: %s is a %s export; sharing works from a report export "
              "(`check --json` / `demo --json`)" % (args.report, kind),
              file=sys.stderr)
        return 2
    try:
        with open(args.report, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        print("error: cannot re-read %s: %s" % (args.report, exc), file=sys.stderr)
        return 2
    summary = data.get("share_summary")
    problems = share_mod.summary_problems(summary)
    if problems:
        for problem in problems:
            print("error: refusing to show/export: %s" % problem, file=sys.stderr)
        return 2

    body = (share_mod.share_json(summary) if (args.out or "").endswith(".json")
            else share_mod.share_markdown(summary))
    print("— sanitized share summary (preview) —")
    print(body)
    print("— end of preview · contains aggregate counts only; no prompts, "
          "paths, commands, repo names, or session ids —")

    if args.out:
        output_error = _validate_output_paths([args.report], args.out)
        if output_error:
            print("error: %s" % output_error, file=sys.stderr)
            return 2
        try:
            with open(args.out, "w", encoding="utf-8") as fh:
                fh.write(body + "\n")
        except OSError as exc:
            print("error: could not write share summary: %s" % exc, file=sys.stderr)
            return 2
        print("\nExported → %s (you reviewed the preview above)" % os.path.abspath(args.out))
    else:
        print("\nPreview only — nothing was written. To export after review, "
              "re-run with: --out summary.md")
    return 0


def cmd_validate(args) -> int:
    """Validate exported JSON files against their versioned schemas."""
    problems = 0
    for path in args.paths:
        kind, errors = schema_mod.validate_file(path)
        if errors:
            problems += 1
            print("%s: INVALID" % path)
            for err in errors:
                print("  - %s" % err)
        else:
            print("%s: valid %s" % (path, kind))
    print("validate: %s" % ("PASS" if problems == 0 else
                            "FAIL (%d invalid file(s))" % problems))
    return 0 if problems == 0 else 2


def cmd_history(args) -> int:
    if args.last < 1:
        print("error: --last must be >= 1", file=sys.stderr)
        return 2
    entries = history_mod.load_history()
    if not entries:
        print("no runs recorded yet (~/.agentmeasure/history.jsonl)")
        return 0
    print("%d run(s) recorded locally (newest last):" % len(entries))
    for e in entries[-max(1, args.last):]:
        print("  %s  %-14s sessions=%s exec=%s failed=%s chains=%s"
              % (e.get("ts", "?"), e.get("mode", "?"), e.get("sessions", "?"),
                 e.get("executions", "?"), e.get("failed", "?"),
                 e.get("retry_chains", "?")))
    print("local file only — never uploaded; delete it to reset run numbering.")
    return 0


def _selftest_snapshot_and_compare() -> int:
    ok = codex_adapter.parse_session(_fixture_path("codex-ok.jsonl"))
    retries = codex_adapter.parse_session(_fixture_path("codex-retries.jsonl"))
    ov_a, checks_a, _cov, _top = checks_mod.run_checks([ok], "selftest-a")
    ov_b, checks_b, _cov, _top = checks_mod.run_checks([retries], "selftest-b")
    rows_a = checks_mod.session_summaries([ok])
    rows_b = checks_mod.session_summaries([retries])
    snap_a = snapshot_mod.build_snapshot(ov_a, checks_a, rows_a, "synthetic-demo",
                                         "selftest-a", "selftest")
    snap_b = snapshot_mod.build_snapshot(ov_b, checks_b, rows_b, "synthetic-demo",
                                         "selftest-b", "selftest")
    problems = 0

    cmp = snapshot_mod.compare_snapshots(snap_a, snap_b)
    failed_row = next(r for r in cmp["rows"] if r["metric"] == "failed executions")
    if not failed_row["delta"].startswith("+"):
        print("  compare: failed-executions delta not positive  [MISMATCH]")
        problems += 1
    changed = {v["check_id"] for v in cmp["changed_verdicts"]}
    if not {"HC-02", "HC-03"}.issubset(changed):
        print("  compare: expected HC-02/HC-03 transitions missing  [MISMATCH]")
        problems += 1
    if cmp["token_state"] != "provable" or not cmp["token_rows"]:
        print("  compare: token sides should be provable here  [MISMATCH]")
        problems += 1

    unprov = dict(snap_b)
    unprov["overview"] = dict(snap_b["overview"], token=None,
                              token_provable=False, token_missing_sessions=1)
    cmp2 = snapshot_mod.compare_snapshots(snap_a, unprov)
    if cmp2["token_state"] != "unprovable" or cmp2["token_rows"]:
        print("  compare: unprovable side must not produce deltas  [MISMATCH]")
        problems += 1
    if "UNPROVABLE" not in snapshot_mod.render_compare_text(cmp2):
        print("  compare: unprovable token not rendered  [MISMATCH]")
        problems += 1

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "snap.json")
        snapshot_mod.save_snapshot(snap_a, path)
        loaded = snapshot_mod.load_snapshot(path)
        if loaded["overview"]["exec_total"] != snap_a["overview"]["exec_total"]:
            print("  snapshot roundtrip lost counts  [MISMATCH]")
            problems += 1
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"tool": "other", "schema": 1}, fh)
            snapshot_mod.load_snapshot(path)
            print("  snapshot: foreign file accepted  [MISMATCH]")
            problems += 1
        except snapshot_mod.SnapshotError:
            pass

    print("  snapshot + compare contracts  [%s]"
          % ("ok" if problems == 0 else "see above"))
    return problems


def cmd_selftest(args) -> int:
    """Run the bundled fixtures through adapter + checks and verify verdicts."""
    cases = [
        ("codex-ok.jsonl", "HC-02", "ok"),
        ("codex-retries.jsonl", "HC-02", "finding"),
        ("codex-retries.jsonl", "HC-03", "finding"),
        ("codex-duplicates.jsonl", "HC-01", "finding"),
        ("codex-corrupt.jsonl", "HC-01", "ok"),
    ]
    failures = 0
    for name, check_id, expected in cases:
        path = _fixture_path(name)
        session = codex_adapter.parse_session(path)
        ov, results, coverage, top3 = checks_mod.run_checks([session], "selftest")
        verdict = next((c.status for c in results if c.check_id == check_id), None)
        status = "ok" if verdict == expected else "MISMATCH"
        if verdict != expected:
            failures += 1
        print("  %-28s %s expect=%s got=%s  [%s]"
              % (name, check_id, expected, verdict, status))

    empty = codex_adapter.parse_session(_fixture_path("codex-empty.jsonl"))
    if empty.line_stats.total != 0 or empty.execs or empty.calls:
        print("  %-28s [MISMATCH] empty file produced records" % "codex-empty.jsonl")
        failures += 1
    else:
        print("  %-28s empty file → 0 records  [ok]" % "codex-empty.jsonl")

    summary_session = codex_adapter.parse_session(_fixture_path("codex-ok.jsonl"))
    _ov, results, _cov, _top = checks_mod.run_checks([summary_session], "selftest")
    share = share_mod.build_share_summary(_ov, results, "synthetic-demo", "selftest")
    blob = share_mod.share_json(share) + share_mod.share_markdown(share)
    for planted in ("secret-project", "Users/tongxiarui", "call_demo_1",
                    "deploy-prod", "SESSIONUUID"):
        if planted in blob:
            print("  share redaction [MISMATCH]: %s leaked" % planted)
            failures += 1
    print("  share redaction planted-string scan  [%s]"
          % ("ok" if failures == 0 else "see above"))

    failures += _selftest_snapshot_and_compare()
    failures += _selftest_export_schemas()
    failures += _selftest_share_flow()

    print("selftest: %s" % ("PASS" if failures == 0 else
                            "FAIL (%d mismatches)" % failures))
    return 0 if failures == 0 else 1


def _selftest_share_flow() -> int:
    import tempfile
    problems = 0
    ok = codex_adapter.parse_session(_fixture_path("codex-ok.jsonl"))
    ov, checks, _cov, _top = checks_mod.run_checks([ok], "selftest")
    summary = share_mod.build_share_summary(ov, checks, "synthetic-demo",
                                            "selftest")
    if share_mod.summary_problems(summary):
        print("  share flow: summary fails whitelist  [MISMATCH]")
        problems += 1
    preview = share_mod.share_markdown(summary)
    for planted in ("secret-project", "Users/tongxiarui", "call_demo_1",
                    "deploy-prod", "SESSIONUUID"):
        if planted in preview:
            print("  share flow: %s leaked into preview  [MISMATCH]" % planted)
            problems += 1
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, "run.json")
        snap = dict(schema=schema_mod.REPORT_SCHEMA,
                    tool="agentmeasure-healthcheck", version=__version__,
                    mode="synthetic-demo", window="selftest",
                    overview=snapshot_mod.overview_dict(ov),
                    checks=[_check_dict(c) for c in checks], coverage=[],
                    share_summary=summary)
        with open(report, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, ensure_ascii=True)
        body = share_mod.share_markdown(json.load(
            open(report, encoding="utf-8"))["share_summary"])
        if "AgentMeasure Healthcheck" not in body:
            print("  share flow: report roundtrip preview broken  [MISMATCH]")
            problems += 1
    print("  share preview-then-export contracts  [%s]"
          % ("ok" if problems == 0 else "see above"))
    return problems


def _selftest_export_schemas() -> int:
    import tempfile
    problems = 0
    ok = codex_adapter.parse_session(_fixture_path("codex-ok.jsonl"))
    ov, checks, _cov, _top = checks_mod.run_checks([ok], "selftest")
    rows = checks_mod.session_summaries([ok])
    snap = snapshot_mod.build_snapshot(ov, checks, rows, "synthetic-demo",
                                       "selftest", "selftest")
    errors = schema_mod.validate_snapshot(snap)
    if errors:
        print("  schema: snapshot has errors: %s" % errors[:3])
        problems += 1
    report = {
        "schema": schema_mod.REPORT_SCHEMA,
        "tool": "agentmeasure-healthcheck", "version": __version__,
        "mode": "synthetic-demo", "window": "selftest",
        "overview": snapshot_mod.overview_dict(ov),
        "checks": [_check_dict(c) for c in checks], "coverage": [],
        "share_summary": share_mod.build_share_summary(ov, checks,
                                                       "synthetic-demo", "selftest"),
    }
    errors = schema_mod.validate_report(report)
    if errors:
        print("  schema: report has errors: %s" % errors[:3])
        problems += 1
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "snap.json")
        snapshot_mod.save_snapshot(snap, path)
        detected, errors = schema_mod.validate_file(path)
        if detected != "snapshot" or errors:
            print("  schema: file detection/validation failed  [MISMATCH]")
            problems += 1
        broken = dict(snap, schema=99)
        if not schema_mod.validate_snapshot(broken):
            print("  schema: broken schema version accepted  [MISMATCH]")
            problems += 1
    print("  export schema contracts  [%s]" % ("ok" if problems == 0 else "see above"))
    return problems


def _add_filter_args(parser) -> None:
    parser.add_argument("--dir", help="explicit directory with rollout-*.jsonl "
                                       "(skips auto-discovery)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                         help="look back N days (default %d)" % DEFAULT_DAYS)
    parser.add_argument("--all", action="store_true",
                         help="ignore the day window, scan every local session")
    parser.add_argument("--since", metavar="YYYY-MM-DD", default=None,
                         help="only sessions on/after this date (overrides --days)")
    parser.add_argument("--until", metavar="YYYY-MM-DD", default=None,
                         help="only sessions on/before this date (overrides --days)")
    parser.add_argument("--project", metavar="SUBSTRING", default=None,
                         help="keep only sessions whose project (cwd basename) "
                              "contains SUBSTRING, case-insensitive")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentmeasure",
        description="AgentMeasure Healthcheck — a local check-up report for "
                    "your coding agent runs. Reads local logs, checks duplicate "
                    "records, retry amplification and tool-error runs, and "
                    "writes a local HTML report. No network, no upload.")
    parser.add_argument("--version", action="version",
                        version="agentmeasure-healthcheck %s" % __version__)
    sub = parser.add_subparsers(dest="cmd")

    p_check = sub.add_parser("check", help="check local agent logs (default)")
    _add_filter_args(p_check)
    p_check.add_argument("--html", metavar="PATH", default=None,
                         help="HTML report path (default ./%s)" % DEFAULT_HTML)
    p_check.add_argument("--json", metavar="PATH", default=None,
                         help="also write a full JSON export")
    p_check.add_argument("--share", metavar="PATH", default=None,
                         help="write the sanitized share summary (.md or .json)")
    p_check.add_argument("--save-snapshot", metavar="PATH", nargs="?", const=True,
                         default=None,
                         help="save a snapshot for later `compare` "
                              "(default name: agentmeasure-snapshot-<date>.json)")
    p_check.add_argument("--no-history", action="store_true",
                         help="do not append to the local run history")
    p_check.set_defaults(func=cmd_check)

    p_demo = sub.add_parser("demo", help="run on a bundled synthetic session")
    p_demo.add_argument("--html", metavar="PATH", default=None)
    p_demo.add_argument("--json", metavar="PATH", default=None)
    p_demo.add_argument("--share", metavar="PATH", default=None)
    p_demo.add_argument("--save-snapshot", metavar="PATH", nargs="?", const=True,
                        default=None,
                        help="save a synthetic snapshot (try `compare` with it)")
    p_demo.add_argument("--no-history", action="store_true")
    p_demo.set_defaults(func=cmd_demo)

    p_cmp = sub.add_parser(
        "compare", help="compare two snapshots, or one snapshot against a fresh run")
    p_cmp.add_argument("snapshots", nargs="+", metavar="SNAPSHOT",
                       help="snapshot file(s): one (vs fresh run) or two (vs each other)")
    _add_filter_args(p_cmp)
    p_cmp.add_argument("--json", metavar="PATH", default=None,
                       help="write the machine-readable comparison")
    p_cmp.add_argument("--no-history", action="store_true")
    p_cmp.set_defaults(func=cmd_compare)

    p_share = sub.add_parser(
        "share", help="preview the sanitized summary from a report export; "
                      "write it only with --out (preview-then-export)")
    p_share.add_argument("report", metavar="REPORT.json",
                         help="a `check --json` / `demo --json` export")
    p_share.add_argument("--out", metavar="PATH", default=None,
                         help="export after review (.md or .json); "
                              "without it, nothing is written")
    p_share.set_defaults(func=cmd_share)

    p_val = sub.add_parser("validate",
                           help="validate exported JSON (report/snapshot/compare) "
                                "against its versioned schema")
    p_val.add_argument("paths", nargs="+", metavar="FILE")
    p_val.set_defaults(func=cmd_validate)

    p_hist = sub.add_parser("history", help="show local run history")
    p_hist.add_argument("--last", type=int, default=10)
    p_hist.set_defaults(func=cmd_history)

    p_self = sub.add_parser("selftest", help="verify adapters/checks on bundled fixtures")
    p_self.set_defaults(func=cmd_selftest)
    return parser


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    if not argv:
        argv = ["check"]
    args = parser.parse_args(argv)
    args._argv = argv
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    return args.func(args)
