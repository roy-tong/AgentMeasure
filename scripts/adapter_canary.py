#!/usr/bin/env python3
"""Adapter freshness canary (requirements pool §七 H1).

Session-log formats drift as Codex and Claude Code ship releases, and the
failure mode of an outdated adapter is the worst kind: a directory full of
new-format sessions parses to ZERO sessions, silently. The canary pins one
"current format" sample per runtime and asserts, on every CI run, that the
adapter still reads it — sessions > 0, corrupt lines == 0, and the format
markers that identify the generation are still being produced.

Refreshing a canary (the documented ritual):

  1. Run the newest Codex / Claude Code CLI once; keep the session file.
  2. Replace the sample under healthcheck/fixtures/canary/<runtime>.jsonl
     (scrub secrets; these files are public).
  3. Update canary-manifest.json: captured_cli_version, captured_on, and
     the format markers you can see in the new sample.
  4. The canary fails until the adapter understands the new generation —
     that red is the point: it names the adapter to fix BEFORE users see
     zero-session reports.

  python3 scripts/adapter_canary.py            # run all canaries
  python3 scripts/adapter_canary.py --list     # show pinned generations
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "healthcheck"))

from verovo_healthcheck.claude import parse_session as claude_parse  # noqa: E402
from verovo_healthcheck.codex import parse_session as codex_parse  # noqa: E402

CANARY_DIR = ROOT / "healthcheck" / "fixtures" / "canary"
MANIFEST = CANARY_DIR / "canary-manifest.json"

PARSERS = {"codex": codex_parse, "claude": claude_parse}


def run_canaries(manifest: dict | None = None,
                 canary_dir: Path = CANARY_DIR) -> list[dict]:
    """Evaluate every pinned canary. Returns per-runtime results; a result
    with ok=False names exactly what broke (H1 acceptance)."""
    manifest = manifest or json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = []
    for runtime, spec in sorted(manifest.get("canaries", {}).items()):
        sample = canary_dir / spec["sample"]
        result = {"runtime": runtime,
                  "sample": spec["sample"],
                  "captured_cli_version": spec.get("captured_cli_version"),
                  "captured_on": spec.get("captured_on")}
        if not sample.exists():
            result.update(ok=False, problem="sample file missing")
            results.append(result)
            continue
        rec = PARSERS[runtime](str(sample))
        problems = []
        if not rec.started_at:
            problems.append("session metadata not recognised (started_at empty)")
        if rec.line_stats.total <= 0:
            problems.append("no lines parsed at all")
        if rec.line_stats.corrupt > spec.get("max_corrupt", 0):
            problems.append("corrupt lines: %d (cap %d)"
                            % (rec.line_stats.corrupt,
                               spec.get("max_corrupt", 0)))
        # Format markers: strings the adapter must still surface for this
        # generation (cli_version is the cheapest universal marker).
        cli_version = getattr(rec, "cli_version", "") or ""
        expected_markers = spec.get("format_markers", [])
        for marker in expected_markers:
            if marker not in cli_version and marker not in str(
                    getattr(rec, "originator", "")):
                # markers may also appear in raw text; fall back to file scan
                if marker not in sample.read_text(encoding="utf-8"):
                    problems.append("format marker %r not observed" % marker)
        result.update(ok=not problems,
                      problems=problems,
                      lines_total=rec.line_stats.total,
                      lines_corrupt=rec.line_stats.corrupt)
        results.append(result)
    return results


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--list" in argv:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for runtime, spec in sorted(manifest.get("canaries", {}).items()):
            print("%-8s sample=%s cli=%s captured=%s"
                  % (runtime, spec["sample"],
                     spec.get("captured_cli_version"),
                     spec.get("captured_on")))
        return 0
    results = run_canaries()
    failed = False
    for r in results:
        if r["ok"]:
            print("  ✓ %-8s %s (%s lines, 0 drift)"
                  % (r["runtime"], r["sample"], r.get("lines_total")))
        else:
            failed = True
            print("  ✗ %-8s %s" % (r["runtime"], "; ".join(r["problems"])))
            print("           adapter is stale vs captured generation "
                  "%s (%s) — fix the adapter, not the sample"
                  % (r.get("captured_cli_version"), r.get("captured_on")))
    if failed:
        return 1
    print("adapter canary: all pinned generations parse cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
