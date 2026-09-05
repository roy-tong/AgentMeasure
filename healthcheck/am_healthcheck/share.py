"""Sanitized share summary — whitelist-only, reviewed before export.

The share summary is built from a fixed whitelist of aggregate fields. Anything
not on the list (commands, paths, prompts, session ids, file names, repo names)
cannot appear in it, by construction. The unit tests assert this against known
planted strings.
"""
import json
import re
from typing import Dict

from . import __version__


_VERSION = re.compile(r"^(\d+\.\d+\.\d+)(?:-[0-9A-Za-z.-]+)?$")

# The whitelist IS the redaction mechanism: the share summary may contain
# exactly these top-level keys, nothing else. Tests import this set.
ALLOWED_KEYS = {
    "tool", "tool_version", "mode", "runtime", "runtime_versions", "window",
    "sessions", "log_files", "turns", "command_executions", "failed_executions",
    "retry_chains", "retry_executions", "unresolved_retry_chains", "checks",
    "notes",
}


def summary_problems(summary) -> list:
    """Defense in depth for the preview-then-export flow: re-check the exact
    shape before showing or exporting anything as 'sanitized'."""
    if not isinstance(summary, dict):
        return ["share summary is not an object"]
    problems = []
    extra = sorted(set(summary.keys()) - ALLOWED_KEYS)
    if extra:
        problems.append("unexpected key(s) outside the whitelist: %s"
                        % ", ".join(extra))
    for check in summary.get("checks", []) or []:
        if not isinstance(check, dict) or set(check.keys()) != {"check", "name", "status"}:
            problems.append("checks entries must have exactly check/name/status")
            break
    return problems


def _safe_versions(values) -> list:
    if not isinstance(values, (list, tuple)):
        return []
    versions = set()
    for value in values:
        if not isinstance(value, str):
            continue
        match = _VERSION.fullmatch(value)
        if match:
            # Keep only the numeric release. Pre-release labels are useful to
            # recognize, but arbitrary suffix metadata must never be exported.
            versions.add(match.group(1))
    return sorted(versions)


def _safe_window(mode: str, value: str) -> str:
    """Keep useful window context while excluding explicit local paths."""
    if mode == "synthetic-demo":
        return "synthetic demo session"
    if not isinstance(value, str):
        return "selected local window"
    if value.startswith("last ") and value.endswith(" day(s) of local sessions"):
        prefix = value[5:-len(" day(s) of local sessions")]
        if prefix.isdigit():
            return "last %s day(s) of local sessions" % prefix
    if value == "all local sessions":
        return value
    if value.startswith("explicit directory"):
        return "explicit local directory"
    return "selected local window"


def build_share_summary(ov, checks, mode: str, window_label: str) -> Dict[str, object]:
    categories = []
    for c in checks:
        categories.append({
            "check": c.check_id,
            "name": c.name,
            "status": c.status,
        })
    return {
        "tool": "AgentMeasure Healthcheck",
        "tool_version": __version__,
        "mode": mode,                       # "own-data" | "synthetic-demo"
        "runtime": "codex-rollout",
        "runtime_versions": _safe_versions(ov.cli_versions),
        "window": _safe_window(mode, window_label),
        "sessions": ov.sessions,
        "log_files": ov.files,
        "turns": ov.turns,
        "command_executions": ov.exec_total,
        "failed_executions": ov.exec_failed,
        "retry_chains": ov.retry_chains,
        "retry_executions": ov.retry_attempts_in_chains,
        "unresolved_retry_chains": ov.unresolved_chains,
        "checks": categories,
        "notes": "Aggregate counts only. No prompts, paths, commands, repo names, "
                 "or session ids are included.",
    }


def share_markdown(summary: Dict[str, object]) -> str:
    s = summary
    lines = [
        "**AgentMeasure Healthcheck** — local coding-agent check-up "
        "(_%s_, %s)" % (s.get("mode"), s.get("window")),
        "",
        "- Runtime: Codex rollout %s" % (", ".join(s.get("runtime_versions") or ["?"]) or "?"),
        "- Sessions: %s · turns: %s · command executions: %s"
        % (s.get("sessions"), s.get("turns"), s.get("command_executions")),
        "- Failed executions: %s · retry chains: %s (%s executions, %s unresolved)"
        % (s.get("failed_executions"), s.get("retry_chains"),
           s.get("retry_executions"), s.get("unresolved_retry_chains")),
        "- Checks: " + " · ".join(
            "%s %s" % (c["check"], c["status"].upper())
            for c in s.get("checks", [])),
        "",
        "Aggregate counts only — no prompts, paths, commands, repo names, or "
        "session ids. Generated locally by AgentMeasure v%s." % s.get("tool_version"),
    ]
    return "\n".join(lines)


def share_json(summary: Dict[str, object]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
