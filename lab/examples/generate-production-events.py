#!/usr/bin/env python3
"""Generate synthetic production (rollout) events for calibration demos.

Real production events come from the party that holds the data rights
(customer-owned agent app, buyer side, or runtime cooperation — see the
whitepaper's observation-surfaces chapter). This script exists so the
calibration pipeline can be demonstrated and tested offline with a KNOWN
planted effect; every event is labeled with the experiment's rules version
and carries no content, exactly like the real thing.

Usage:
    python3 lab/examples/generate-production-events.py \
        --experiment example-desc-clarity-001 --seed 424242 \
        --arms control=0.25 clear=0.29 --n 2500 \
        --tasks lab/tasks/search-retrieval-scrape.v1.json \
        --out production-events.jsonl

The effect size gap between --arms here and the offline experiment is the
planted "transfer gap" the calibration report should recover.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from agentmeasure_lab import FUNNEL_RULES_VERSION  # noqa: E402
from agentmeasure_lab.rng import DetRng  # noqa: E402

CANDIDATES = ["your-search-api", "web-search-pro", "docs-search", "site-crawler"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--arms", required=True, help="variant=selection_prob pairs, e.g. control=0.25 clear=0.29")
    ap.add_argument("--n", type=int, default=2000, help="assignments per arm")
    ap.add_argument("--tasks", required=True, help="task set JSON path")
    ap.add_argument("--out", default="production-events.jsonl")
    ap.add_argument("--harness", default="prod-runtime")
    args = ap.parse_args()

    with open(args.tasks, "r", encoding="utf-8") as fh:
        task_ids = [t["id"] for t in json.load(fh)["tasks"]]

    arms = {}
    for chunk in args.arms.split():
        vid, prob = chunk.split("=")
        arms[vid] = float(prob)

    count = 0
    with open(args.out, "w", encoding="utf-8") as out:
        for variant_id, p in arms.items():
            for i in range(args.n):
                count += 1
                rng = DetRng(args.seed, "production", args.experiment, variant_id, i)
                task_id = task_ids[rng.below(len(task_ids))]
                base = {
                    "schema": "agentmeasure.lab/funnel-event",
                    "schema_version": "1.0.0",
                    "experiment_id": args.experiment,
                    "assignment_id": f"{args.experiment}/{args.harness}/{task_id}/p{i:05d}/{variant_id}",
                    "harness_id": args.harness,
                    "task_id": task_id,
                    "variant_id": variant_id,
                    "replicate": i + 1,
                    "subject_id": "your-search-api",
                    "rules_version": FUNNEL_RULES_VERSION,
                }
                selected = rng.bernoulli(p)
                out.write(json.dumps(dict(base, event="reach", candidate_ids=CANDIDATES), sort_keys=True) + "\n")
                out.write(json.dumps(dict(base, event="choice",
                                          selected_id="your-search-api" if selected else "web-search-pro",
                                          selected_subject=selected), sort_keys=True) + "\n")
                if not selected:
                    continue
                attempts = 1 if rng.bernoulli(0.7) else (2 if rng.bernoulli(0.5) else 3)
                succeeded = rng.bernoulli(0.75)
                for ai in range(1, attempts + 1):
                    ok = succeeded or ai < attempts
                    out.write(json.dumps(dict(base, event="attempt", operation_index=1,
                                              attempt_index=ai, outcome="success" if ok else "failure",
                                              steps=9 + rng.below(4), latency_ms=420, cost_units=22.5),
                                          sort_keys=True) + "\n")
                out.write(json.dumps(dict(base, event="operation_result", operation_index=1,
                                          outcome="success" if succeeded else "failure",
                                          attempts=attempts), sort_keys=True) + "\n")
                if succeeded:
                    consumed = rng.bernoulli(0.6)
                    signal = "task_continuation" if consumed else "none"
                else:
                    consumed, signal = False, "operation_failed"
                out.write(json.dumps(dict(base, event="consumption", operation_index=1,
                                          consumed=consumed, signal=signal), sort_keys=True) + "\n")

    print(f"wrote {count} assignments ({len(arms)} arms x {args.n}) -> {args.out}")
    print(f"planted production selection rates: {arms}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
