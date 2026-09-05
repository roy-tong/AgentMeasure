"""CLI orchestration: check / demo / selftest / history.

Exit codes (R5 contract):
  0  the check ran and produced a report (findings or not)
  2  input/output error: no readable logs, bad arguments, unreadable directory,
     or report output cannot be written

A run with FINDING results still exits 0 — findings describe the user's agent
runs, not a failure of this tool.
"""
import argparse
import json
import os
import shlex
import sys
from datetime import datetime, timezone
from typing import List

from . import __version__
from . import checks as checks_mod
from . import codex as codex_adapter
from . import discover as discover_mod
from . import history as history_mod
from . import report_html as html_mod
from . import report_text as text_mod
from . import share as share_mod

DEFAULT_DAYS = 7
DEFAULT_HTML = "agentmeasure-report.html"


def _window_label(args) -> str:
    if getattr(args, "all", False):
        return "all local sessions"
    if getattr(args, "dir", None):
        return "explicit directory: %s" % args.dir
    return "last %d day(s) of local sessions" % getattr(args, "days", DEFAULT_DAYS)


def _validate_output_paths(input_paths: List[str], *output_paths) -> str:
    """Reject collisions and missing parents before any report is written."""
    outputs = [str(p) for p in output_paths if p]
    normalized = [os.path.realpath(os.path.abspath(p)) for p in outputs]
    if len(set(normalized)) != len(normalized):
        return "HTML, JSON, and share outputs must use different paths"
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


def _run_check(paths: List[str], mode: str, window_label: str, command: str,
               html_path: str, json_path, share_path, use_history: bool,
               home=None) -> int:
    output_error = _validate_output_paths(paths, html_path, json_path, share_path)
    if output_error:
        print("error: %s" % output_error, file=sys.stderr)
        return 2
    sessions = [codex_adapter.parse_session(p) for p in paths]
    if not any(_has_supported_signal(s) for s in sessions):
        print("error: no supported Codex rollout events found in the selected input",
              file=sys.stderr)
        return 2
    ov, check_results, coverage, top3 = checks_mod.run_checks(sessions, window_label)
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
            "tool": "agentmeasure-healthcheck", "version": __version__,
            "mode": mode, "window": window_label, "overview": _overview_dict(ov),
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


def _overview_dict(ov):
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
    }


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
    return os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "demo", "demo-codex.jsonl")


def _fixture_path(name: str) -> str:
    return os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "fixtures", name)


def cmd_check(args) -> int:
    command = "python3 healthcheck/agentmeasure " + shlex.join(
        getattr(args, "_argv", sys.argv[1:]) or ["check"])
    mode = "own-data"
    window_label = _window_label(args)

    if args.days < 0:
        print("error: --days must be >= 0", file=sys.stderr)
        return 2

    if args.dir:
        if not os.path.isdir(args.dir):
            print("error: --dir %s is not a directory" % args.dir, file=sys.stderr)
            return 2
        paths = sorted(
            os.path.join(base, name)
            for base, _dirs, names in os.walk(args.dir)
            for name in names if name.endswith(".jsonl"))
        if not paths:
            print("error: no .jsonl files under %s" % args.dir, file=sys.stderr)
            return 2
    else:
        result = discover_mod.discover(
            since_days=None if args.all else args.days, scan_all=args.all)
        primary = result.primary()
        paths = primary.files if primary else []
        for rt in result.runtimes:
            if rt.note:
                print("note [%s]: %s" % (rt.runtime, rt.note))
        if not paths:
            print("error: no supported log files found in the selected window. "
                  "Try --days N, --all, or --dir <path>.", file=sys.stderr)
            return 2

    print("reading %d rollout file(s)…" % len(paths))
    html_path = args.html or DEFAULT_HTML
    return _run_check(paths, mode, window_label, command, html_path,
                      args.json, args.share, not args.no_history)


def cmd_demo(args) -> int:
    fixture = _demo_fixture_path()
    if not os.path.isfile(fixture):
        print("error: demo fixture missing: %s" % fixture, file=sys.stderr)
        return 2
    command = "python3 healthcheck/agentmeasure " + shlex.join(
        getattr(args, "_argv", sys.argv[1:]) or ["demo"])
    html_path = args.html or "agentmeasure-demo-report.html"
    return _run_check([fixture], "synthetic-demo", "synthetic demo session",
                      command, html_path, args.json, args.share,
                      not args.no_history)


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

    print("selftest: %s" % ("PASS" if failures == 0 else
                            "FAIL (%d mismatches)" % failures))
    return 0 if failures == 0 else 1


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
    p_check.add_argument("--dir", help="explicit directory with rollout-*.jsonl "
                                       "(skips auto-discovery)")
    p_check.add_argument("--days", type=int, default=DEFAULT_DAYS,
                         help="look back N days (default %d)" % DEFAULT_DAYS)
    p_check.add_argument("--all", action="store_true",
                         help="ignore the day window, scan every local session")
    p_check.add_argument("--html", metavar="PATH", default=None,
                         help="HTML report path (default ./%s)" % DEFAULT_HTML)
    p_check.add_argument("--json", metavar="PATH", default=None,
                         help="also write a full JSON export")
    p_check.add_argument("--share", metavar="PATH", default=None,
                         help="write the sanitized share summary (.md or .json)")
    p_check.add_argument("--no-history", action="store_true",
                         help="do not append to the local run history")
    p_check.set_defaults(func=cmd_check)

    p_demo = sub.add_parser("demo", help="run on a bundled synthetic session")
    p_demo.add_argument("--html", metavar="PATH", default=None)
    p_demo.add_argument("--json", metavar="PATH", default=None)
    p_demo.add_argument("--share", metavar="PATH", default=None)
    p_demo.add_argument("--no-history", action="store_true")
    p_demo.set_defaults(func=cmd_demo)

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
