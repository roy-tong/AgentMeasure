"""Terminal summary — what the user sees first. Honest numbers only."""
from typing import List

from . import __version__
from .model import CheckResult, Finding, Overview

VERDICT_STYLE = {
    "ok": "OK ",
    "finding": "FINDING ",
    "unprovable": "UNPROVABLE ",
    "info": "INFO ",
}


def _fmt_int(n: int) -> str:
    return "{:,}".format(n)


def render_terminal(ov: Overview, checks: List[CheckResult], top3: List[Finding],
                    mode: str, run_no: int, runtime_note: str) -> str:
    out: List[str] = []
    bar = "─" * 62
    out.append(bar)
    out.append("AgentMeasure Healthcheck v%s · %s · run #%d"
               % (__version__, mode, run_no))
    out.append(ov.window_label)
    if runtime_note:
        out.append(runtime_note)
    out.append(bar)

    out.append("Coverage")
    out.append("  sessions %s · files %s · lines %s · corrupt %s (%.2f%%)"
               % (_fmt_int(ov.sessions), _fmt_int(ov.files), _fmt_int(ov.lines),
                  _fmt_int(ov.corrupt_lines), ov.corrupt_ratio * 100))
    span = ov.first_ts[:19].replace("T", " ") if ov.first_ts else "?"
    span_end = ov.last_ts[:19].replace("T", " ") if ov.last_ts else "?"
    out.append("  window data: %s → %s · models: %s"
               % (span, span_end, ", ".join(ov.models[:3]) or "?"))
    if ov.cli_versions:
        out.append("  runtime cli: %s" % ", ".join(sorted(ov.cli_versions)))
    if ov.projects:
        parts = ["%s (%s sess · %s exec · %s failed)"
                 % (p["project"], p["sessions"], p["exec_total"], p["exec_failed"])
                 for p in ov.projects[:3]]
        more = "" if len(ov.projects) <= 3 else " · +%d more" % (len(ov.projects) - 3)
        out.append("  projects: %s%s" % (" · ".join(parts), more))

    out.append("")
    out.append("Activity")
    out.append("  turns %s · command executions %s (ok %s · failed %s · unknown %s)"
               % (_fmt_int(ov.turns), _fmt_int(ov.exec_total), _fmt_int(ov.exec_ok),
                  _fmt_int(ov.exec_failed), _fmt_int(ov.exec_unknown)))
    if ov.token_provable:
        out.append("  tokens (cumulative snapshots): input %s (cached %s) · "
                   "output %s (reasoning %s)"
                   % (_fmt_int(ov.token_total_input), _fmt_int(ov.token_cached_input),
                      _fmt_int(ov.token_output), _fmt_int(ov.token_reasoning_output)))
        out.append("  subsets are never added into totals")
    else:
        if ov.token_invalid_sessions or ov.token_missing_sessions:
            reasons = []
            if ov.token_invalid_sessions:
                reasons.append("invalid/incomplete in %s session(s)"
                               % _fmt_int(ov.token_invalid_sessions))
            if ov.token_missing_sessions:
                reasons.append("missing in %s session(s)" % _fmt_int(ov.token_missing_sessions))
            out.append("  tokens: UNPROVABLE (" + "; ".join(reasons) + ")")
        else:
            out.append("  tokens: UNPROVABLE (no token events in window)")
    if ov.compactions:
        out.append("  compactions: %s (token totals not comparable across them)"
                   % ov.compactions)
    if ov.subagent_activity:
        out.append("  sub-agent activity records: %s" % ov.subagent_activity)

    out.append("")
    out.append("Checks")
    for c in checks:
        out.append("  [%s] %s — %s" % (VERDICT_STYLE.get(c.status, c.status),
                                        c.check_id, c.name))
        out.append("         %s" % c.summary)
        if c.unprovable_reason:
            out.append("         unprovable: %s" % c.unprovable_reason)

    if top3:
        out.append("")
        out.append("Worth checking first")
        for i, f in enumerate(top3, 1):
            out.append("  %d. %s" % (i, f.title))
            out.append("     → %s" % f.next_step)
    else:
        out.append("")
        out.append("Worth checking first: nothing ranked — no findings in this window.")

    out.append("")
    out.append("Subsets never summed · UNPROVABLE is a result, not an error.")
    out.append("Local only: no network code, no upload. Full evidence: HTML report.")
    out.append(bar)
    return "\n".join(out)
