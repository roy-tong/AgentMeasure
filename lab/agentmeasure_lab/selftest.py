"""Built-in end-to-end sanity check: one planted uplift + one honest null.

`python3 lab/am lab selftest` runs two small preregistered experiments on
the synthetic harness and asserts the engine recovers the planted effect
and reports the null honestly. This is the engine validating itself against
known ground truth — the same discipline the standard asks of any claim.
"""

import json
import os
import shutil
import tempfile
from typing import Any, Dict

from .prereg import create_preregistration, load_preregistration, save_preregistration
from .runner import run_experiment

_TASK_SET = "search-retrieval-scrape.v1.json"


def _manifest(experiment_id: str, variants: list, seed: int, replicates: int = 40) -> Dict[str, Any]:
    return {
        "schema": "agentmeasure.lab/experiment-manifest",
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "hypothesis": "selftest hypothesis: planted uplift recovered, null reported honestly",
        "task_set": {"path": _TASK_SET},
        "harnesses": [
            {
                "id": "mock-v1",
                "runner": "mock",
                # explicit amplitude so the selftest's pass/fail is deterministic
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
        "primary_metric": "selection_rate",
        "guardrails": [
            {"metric": "consumption_rate", "min": 0.45},
            {"metric": "median_steps_per_operation", "max": 40},
        ],
        "analysis": {
            "method": "two_proportion_z_test",
            "alpha": 0.05,
            "min_sample_per_arm": 100,
            "report_per_condition": ["harness"],
        },
        "budget": {
            "max_operations": 100000,
            "max_cost_units": 1000000,
            "max_wall_clock_seconds": 120,
        },
        "seed": seed,
    }


def run_selftest() -> bool:
    lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tasks_src = os.path.join(lab_dir, "tasks", _TASK_SET)
    tmp = tempfile.mkdtemp(prefix="am-lab-selftest-")
    ok = False
    try:
        shutil.copyfile(tasks_src, os.path.join(tmp, _TASK_SET))

        # 1. Planted uplift: description_clarity=clear has +3pp-ish attraction in the mock model.
        uplift = _manifest(
            "selftest-uplift",
            [
                {"id": "control", "baseline": True, "levels": {"description_clarity": "control", "version_label": "a"}},
                {"id": "clear", "baseline": False, "levels": {"description_clarity": "clear", "version_label": "a"}},
            ],
            seed=20260822,
            replicates=40,
        )
        rep1 = _run_one(uplift, tmp)
        v1 = next(v for v in rep1["variants"] if not v.get("baseline"))

        # 2. Honest null: version_label has exactly zero planted effect.
        null = _manifest(
            "selftest-null",
            [
                {"id": "control", "baseline": True, "levels": {"description_clarity": "control", "version_label": "a"}},
                {"id": "label-b", "baseline": False, "levels": {"description_clarity": "control", "version_label": "b"}},
            ],
            seed=20260822,
            replicates=40,
        )
        rep2 = _run_one(null, tmp)
        v2 = next(v for v in rep2["variants"] if not v.get("baseline"))

        uplift_ok = v1["verdict"] in ("adopt_candidate", "effective_not_qualified") and (
            v1["primary_comparison"].get("direction") == "improvement"
        )
        null_ok = v2["verdict"] in ("null_result", "undetermined")

        print(f"uplift experiment: {v1['verdict']} "
              f"(Δ {v1['primary_comparison']['difference']*100:+.1f}pp, "
              f"p={v1['primary_comparison'].get('p_value')}) — expected significant improvement")
        print(f"null experiment  : {v2['verdict']} "
              f"(Δ {v2['primary_comparison']['difference']*100:+.1f}pp, "
              f"p={v2['primary_comparison'].get('p_value')}) — expected honest null")
        ok = uplift_ok and null_ok
        print(f"selftest: {'PASS' if ok else 'FAIL'}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ok


def _run_one(manifest: Dict[str, Any], tmp: str) -> Dict[str, Any]:
    # Task path is relative to the manifest's directory in this scratch space.
    manifest["task_set"]["path"] = _TASK_SET
    mpath = os.path.join(tmp, f"{manifest['experiment_id']}.json")
    with open(mpath, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    prereg = create_preregistration(manifest)
    ppath = save_preregistration(prereg, os.path.join(tmp, f"{manifest['experiment_id']}.prereg.json"))
    out = os.path.join(tmp, f"run-{manifest['experiment_id']}")
    return run_experiment(load_preregistration(ppath), out, tmp)
