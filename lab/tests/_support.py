"""Shared test fixtures: manifest factory + in-memory experiment runs."""

import copy
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab.prereg import (  # noqa: E402
    create_preregistration,
    load_preregistration,
    save_preregistration,
)
from agentmeasure_lab.runner import run_experiment  # noqa: E402

LAB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASK_SET_NAME = "search-retrieval-scrape.v1.json"


def base_manifest(experiment_id="test-exp", variants=None, seed=7, replicates=40,
                  min_n=100, budget=None, primary="selection_rate"):
    if variants is None:
        variants = [
            {"id": "control", "baseline": True,
             "levels": {"description_clarity": "control", "version_label": "a"}},
            {"id": "clear", "baseline": False,
             "levels": {"description_clarity": "clear", "version_label": "a"}},
        ]
    return {
        "schema": "agentmeasure.lab/experiment-manifest",
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "hypothesis": "test hypothesis long enough to validate",
        "task_set": {"path": TASK_SET_NAME},
        "harnesses": [
            {
                "id": "mock-v1",
                "runner": "mock",
                # explicit amplitude keeps engine tests deterministic across
                # default-config changes
                "config": {
                    "factor_effects": {
                        "attraction": {"description_clarity": {"control": 0.0, "clear": 0.02}}
                    }
                },
            }
        ],
        "factors": [
            {"name": "description_clarity", "levels": ["control", "clear"]},
            {"name": "version_label", "levels": ["a", "b"]},
        ],
        "variants": variants,
        "assignment": {"mode": "within-task-balanced", "replicates_per_task": replicates},
        "primary_metric": primary,
        "guardrails": [
            {"metric": "consumption_rate", "min": 0.45},
            {"metric": "median_steps_per_operation", "max": 14},
            {"metric": "attempts_per_operation", "max": 1.5},
        ],
        "analysis": {
            "method": "two_proportion_z_test",
            "alpha": 0.05,
            "min_sample_per_arm": min_n,
            "report_per_condition": ["harness"],
        },
        "budget": budget or {
            "max_operations": 100000,
            "max_cost_units": 1000000,
            "max_wall_clock_seconds": 300,
        },
        "value_model": {
            "opportunity_per_month": 20000000,
            "pay_conversion": 0.30,
            "margin_per_billed_event": 0.04,
            "serving_cost_per_month": 0,
            "capture_rate_assumption": None,
        },
        "seed": seed,
    }


class LabWorkspace:
    """Temp workspace with the shipped task set copied in."""

    def __init__(self):
        self.tmp = tempfile.mkdtemp(prefix="am-lab-test-")
        shutil.copyfile(
            os.path.join(LAB_DIR, "tasks", TASK_SET_NAME),
            os.path.join(self.tmp, TASK_SET_NAME),
        )

    def run(self, manifest):
        mpath = os.path.join(self.tmp, f"{manifest['experiment_id']}.json")
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2)
        return run_manifest_file(mpath, self.tmp)

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


def run_manifest_file(mpath, manifest_dir):
    with open(mpath, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    prereg = create_preregistration(manifest)
    ppath = save_preregistration(
        prereg, os.path.splitext(mpath)[0] + ".prereg.json"
    )
    out_dir = os.path.join(os.path.dirname(mpath), f"run-{manifest['experiment_id']}")
    report = run_experiment(load_preregistration(ppath), out_dir, manifest_dir)
    return report, out_dir, ppath


def load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def generate_production_events(
    path,
    experiment_id,
    seed,
    arm_selection_probs,
    n_per_arm,
    task_ids,
    subject_id="your-search-api",
    harness_id="prod-runtime",
    operation_success_prob=0.75,
    consumption_prob=0.6,
):
    """Synthetic production (rollout) events in FMT-002 form.

    arm_selection_probs: {variant_id: P(subject selected)} — the planted
    production effect the calibration analysis must recover.
    """
    from agentmeasure_lab import FUNNEL_RULES_VERSION
    from agentmeasure_lab.rng import DetRng

    lines = []
    counter = 0
    for variant_id, p in arm_selection_probs.items():
        for i in range(n_per_arm):
            counter += 1
            rng = DetRng(seed, "production", experiment_id, variant_id, i)
            task_id = task_ids[rng.below(len(task_ids))]
            assignment_id = f"{experiment_id}/{harness_id}/{task_id}/p{i:05d}/{variant_id}"
            base = {
                "schema": "agentmeasure.lab/funnel-event",
                "schema_version": "1.0.0",
                "experiment_id": experiment_id,
                "assignment_id": assignment_id,
                "harness_id": harness_id,
                "task_id": task_id,
                "variant_id": variant_id,
                "replicate": i + 1,
                "subject_id": subject_id,
                "rules_version": FUNNEL_RULES_VERSION,
            }
            reach = dict(base, event="reach", candidate_ids=[subject_id, "web-search-pro", "docs-search", "site-crawler"])
            selected = rng.bernoulli(p)
            choice = dict(base, event="choice", selected_id=subject_id if selected else "web-search-pro",
                          selected_subject=selected)
            lines.append(reach)
            lines.append(choice)
            if not selected:
                continue
            attempts = 1 if rng.bernoulli(0.7) else (2 if rng.bernoulli(0.5) else 3)
            succeeded = rng.bernoulli(operation_success_prob)
            for ai in range(1, attempts + 1):
                ok = succeeded or ai < attempts
                lines.append(dict(base, event="attempt", operation_index=1, attempt_index=ai,
                                  outcome="success" if ok else "failure", steps=9 + rng.below(4),
                                  latency_ms=400, cost_units=22.5))
            lines.append(dict(base, event="operation_result", operation_index=1,
                              outcome="success" if succeeded else "failure", attempts=attempts))
            if succeeded:
                consumed = rng.bernoulli(consumption_prob)
                lines.append(dict(base, event="consumption", operation_index=1, consumed=consumed,
                                  signal="task_continuation" if consumed else "none"))
            else:
                lines.append(dict(base, event="consumption", operation_index=1, consumed=False,
                                  signal="operation_failed"))
    with open(path, "w", encoding="utf-8") as fh:
        for ev in lines:
            fh.write(json.dumps(ev, sort_keys=True) + "\n")
    return path
