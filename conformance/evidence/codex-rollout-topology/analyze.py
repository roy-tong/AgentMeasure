#!/usr/bin/env python3
"""Recompute the codex-rollout-topology numbers from a set of rollout JSONL files.

Usage: python3 analyze.py <dir-containing-*.jsonl>

Corpus used for the published numbers: the `baseline/` rollout files of
https://github.com/codeset-ai/codeset-release-evals (53 files, public).
"""
import glob
import json
import sys
from collections import Counter


def main(dirpath: str) -> None:
    agg = Counter()
    files_with_tc = 0
    byte_identical_repeats = 0
    for f in sorted(glob.glob(f"{dirpath}/*.jsonl")):
        prev_info = None
        prev_total_in = None
        had_tc = False
        for line in open(f, errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                agg["corrupt_lines"] += 1
                continue
            p = d.get("payload") or {}
            if d.get("type") != "event_msg" or p.get("type") != "token_count":
                continue
            had_tc = True
            info = p.get("info") or {}
            t = info.get("total_token_usage")
            if t is None or not isinstance(t.get("total_tokens"), (int, float)):
                agg["no_cumulative_events"] += 1
            else:
                agg["with_cumulative"] += 1
                tin = t.get("input_tokens")
                if prev_total_in is not None and tin is not None and tin < prev_total_in:
                    agg["mono_violations"] += 1
                if tin is not None:
                    prev_total_in = tin
            if prev_info is not None and json.dumps(info) == prev_info:
                byte_identical_repeats += 1
            prev_info = json.dumps(info)
            agg["tc_events"] += 1
        files_with_tc += 1 if had_tc else 0

    print(f"files with token_count events: {files_with_tc}")
    print(f"token_count events: {agg['tc_events']}")
    print(f"byte-identical repeats of predecessor: {byte_identical_repeats}"
          f" ({100.0 * byte_identical_repeats / max(1, agg['tc_events']):.0f}%)")
    print(f"cumulative monotonicity violations: {agg['mono_violations']}")
    print(f"events without usable total_token_usage: {agg['no_cumulative_events']}")
    print(f"corrupt lines: {agg['corrupt_lines']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
