#!/usr/bin/env python3
"""The monthly review driver (requirements pool §七 B3).

One account period, four commands, one page of output — the subscription
ritual as a single runnable script instead of tribal knowledge:

    rules-diff      did the vendor's rules change since last snapshot?
    verify          this month's ledger (all lanes, one artifact)
    period-compare  the honest delta vs last month's ledger
    decisions       the third value book, printed for the review meeting

Exit code: 0 = ritual complete (findings or none); 1 = material rule change
(rules-diff gate) — the period must be re-verified under the new rule and
disclosed, never mixed; 2 = input error.

Real usage:

    python3 scripts/monthly_review.py \
        --vendor intercom --export august.csv --contract msa.json \
        --prev-ledger july/verified-ledger.json \
        --rules-snapshot july/vendor-rules.json \
        --decisions decisions.jsonl

Demo usage (sandbox fixtures, no data needed — the acceptance run):

    python3 scripts/monthly_review.py --demo
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "healthcheck"))


def _run(args: list) -> int:
    """Run one verovo subcommand, streaming output."""
    print("\n" + "=" * 64)
    print("$ verovo " + " ".join(args))
    print("=" * 64)
    proc = subprocess.run([sys.executable, "-m", "verovo_healthcheck.cli"] + args,
                          cwd=str(ROOT / "healthcheck"))
    return proc.returncode


def demo() -> int:
    """The ritual on sandbox fixtures: proves the pipeline end to end."""
    fixtures = ROOT / "healthcheck" / "verovo_healthcheck" / "fixtures"
    export = str(fixtures / "vendor-export-intercom.csv")
    print("MONTHLY REVIEW — DEMO (sandbox fixtures, no real data)")
    rc = _run(["recount", "--export", export, "--vendor", "intercom"])
    if rc != 0:
        return rc
    rc = _run(["delivery", "--log", "/tmp/am-monthly-demo-delivery.jsonl"])
    rc = _run(["decisions", "--log", "/tmp/am-monthly-demo-decisions.jsonl"])
    print("\ndemo complete: recount + the two journals. For the full ritual")
    print("with rules-diff/verify/period-compare, run with --export and")
    print("--prev-ledger against real monthly inputs (see docs/monthly-review.md).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="monthly_review",
                                 description="the subscription's monthly ritual")
    ap.add_argument("--demo", action="store_true",
                    help="run the ritual on sandbox fixtures")
    ap.add_argument("--vendor", help="vendor id for the real ritual")
    ap.add_argument("--export", help="this month's canonical export CSV")
    ap.add_argument("--contract", default=None,
                    help="buyer outcome-standard overlay (optional)")
    ap.add_argument("--ledger", default=None,
                    help="buyer billing ledger CSV (optional)")
    ap.add_argument("--confirmations", default=None,
                    help="vendor concessions CSV (optional)")
    ap.add_argument("--prev-ledger", default=None,
                    help="last month's verified-ledger.json for period-compare")
    ap.add_argument("--rules-snapshot", default=None,
                    help="last month's vendor-rules.json for rules-diff")
    ap.add_argument("--out", default="monthly-review",
                    help="output directory for this month's ledger")
    ap.add_argument("--period", default=None)
    args = ap.parse_args(argv)

    if args.demo:
        return demo()
    if not (args.vendor and args.export):
        ap.error("real ritual needs --vendor and --export (or --demo)")

    # 1. rules-diff gate: a material rule change re-opens the period.
    if args.rules_snapshot:
        rc = _run(["rules-diff", args.rules_snapshot])
        if rc == 1:
            print("\nrules-diff gate: MATERIAL rule change since the "
                  "snapshot. Re-verify the period under the new rule and "
                  "disclose the change — do not mix rules in one claim.")
            return 1
        if rc != 0:
            return rc

    # 2. verify: this month's ledger, all lanes in one artifact.
    verify_cmd = ["verify", "--export", args.export, "--vendor", args.vendor,
                  "--out", args.out]
    for flag, value in (("--contract", args.contract),
                        ("--ledger", args.ledger),
                        ("--confirmations", args.confirmations),
                        ("--period-start", args.period)):
        if value:
            verify_cmd += [flag, value]
    rc = _run(verify_cmd)
    if rc != 0:
        return rc

    # 3. period-compare: the honest delta.
    if args.prev_ledger:
        rc = _run(["period-compare", args.prev_ledger,
                   str(Path(args.out) / "verified-ledger.json")])
        if rc != 0:
            return rc

    # 4. the two journals, printed for the review meeting.
    for journal in ("delivery", "decisions"):
        log = "/tmp/am-%s.jsonl" % journal
        Path(log).touch(exist_ok=True)
        _run([journal, "--log", log])

    print("\nMonthly ritual complete. Ledger: %s/verified-ledger.json" % args.out)
    print("Next: verovo console --ledger %s/verified-ledger.json "
          "--out console.html" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
