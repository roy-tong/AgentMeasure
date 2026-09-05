#!/usr/bin/env python3
"""External integration example: trend table over saved snapshots.

This script is what a third-party integration looks like: it consumes the
versioned snapshot documents (`agentmeasure check --save-snapshot`) through
their public schema only — it does NOT import am_healthcheck internals, so it
keeps working as long as the snapshot schema stays on v1.

Usage:
    python3 examples/track-weekly.py snapshot-a.json snapshot-b.json [...]

Snapshot files are personal artifacts (they carry project names). This example
prints aggregates only, but the files themselves still never leave the machine
unless you choose to move them.

Python 3.9+ standard library only.
"""
import argparse
import json
import sys

SUPPORTED_SCHEMA = 1
KNOW_SNAPSHOTS = "snapshot-v1"


def load_snapshot(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    # A real consumer must refuse schema versions it does not speak.
    if data.get("tool") != "agentmeasure-healthcheck":
        raise ValueError("%s is not an AgentMeasure snapshot" % path)
    if data.get("schema") != SUPPORTED_SCHEMA:
        raise ValueError("%s uses snapshot schema %r; this reader speaks %s — "
                         "update the reader before reading newer files"
                         % (path, data.get("schema"), KNOW_SNAPSHOTS))
    return data


def verdict_line(checks):
    return " ".join("%s=%s" % (c["check_id"], c["status"]) for c in checks)


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("snapshots", nargs="+", metavar="SNAPSHOT.json")
    args = parser.parse_args(argv)

    rows = []
    failures = 0
    for path in args.snapshots:
        try:
            snap = load_snapshot(path)
        except (OSError, ValueError, KeyError) as exc:
            print("error: %s" % exc, file=sys.stderr)
            failures += 1
            continue
        ov = snap["overview"]
        token = ov.get("token") or {}
        rows.append({
            "label": "%s · %s" % (path, snap.get("window_label", "?")),
            "sessions": ov["sessions"],
            "exec": ov["exec_total"],
            "failed": ov["exec_failed"],
            "chains": ov["retry_chains"],
            "unresolved": ov["unresolved_chains"],
            "input": token.get("input", "?") if ov.get("token_provable") else "UNPROVABLE",
            "verdicts": verdict_line(snap.get("checks", [])),
        })

    if rows:
        print("%-46s %9s %7s %7s %7s %6s %13s"
              % ("snapshot", "sessions", "exec", "failed", "chains", "unres", "input tokens"))
        for row in rows:
            print("%-46s %9s %7s %7s %7s %6s %13s"
                  % (row["label"][:46], row["sessions"], row["exec"],
                     row["failed"], row["chains"], row["unresolved"], row["input"]))
        print()
        print("verdicts (newest): %s" % (rows[-1]["verdicts"] if rows else "—"))
        print("Verdicts: ok | finding | unprovable | info. UNPROVABLE token "
              "totals are shown as such, never as zero.")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
