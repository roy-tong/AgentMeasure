"""Experiment plan: task x harness x variant matrix (LAB-002, LAB-010).

The plan is fully derived from the preregistered manifest, in deterministic
order, so identical manifests produce identical assignments. The plan is
estimated before running (scale + budget preview) and verifiable after
(per-arm reach counts from the emitted events).
"""

import os

from typing import Any, Dict, List

from .rng import DetRng

# Package-shipped task sets (fallback when a manifest's relative path does
# not resolve from the manifest's own directory — POC finding: hand-written
# manifests broke here with a raw traceback).
_PACKAGE_TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks")


def resolve_task_path(path: str, base_dir: str) -> str:
    """Resolve a task-set reference: absolute, relative to the manifest,
    then the bare filename against the package's shipped task corpus."""
    candidates = [path] if os.path.isabs(path) else [
        os.path.normpath(os.path.join(base_dir, path)),
        os.path.join(_PACKAGE_TASKS_DIR, os.path.basename(path)),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        f"task set not found: {path!r} (looked next to the manifest and in {_PACKAGE_TASKS_DIR})"
    )


def load_task_set(path: str) -> Dict[str, Any]:
    import json

    with open(path, "r", encoding="utf-8") as fh:
        corpus = json.load(fh)
    if not isinstance(corpus.get("tasks"), list) or not corpus["tasks"]:
        raise ValueError(f"task set {path} has no tasks")
    ids = [t["id"] for t in corpus["tasks"]]
    if len(set(ids)) != len(ids):
        raise ValueError("task ids must be unique")
    return corpus


def build_plan(manifest: Dict[str, Any], task_set: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build the assignment plan.

    ``replicates_per_task`` counts complete replicate blocks: each block
    assigns every variant to the task exactly once, in deterministic
    shuffled order — balance is structural, not statistical, and is
    verifiable from per-arm reach counts in the emitted events.
    """
    tasks = {t["id"]: t for t in task_set["tasks"]}
    replicates = int(manifest["assignment"]["replicates_per_task"])
    if replicates <= 0:
        raise ValueError("replicates_per_task must be > 0")
    variant_ids = [v["id"] for v in manifest["variants"]]

    plan: List[Dict[str, Any]] = []
    for harness in manifest["harnesses"]:
        for task in task_set["tasks"]:
            block_rng = DetRng("assignment", manifest["experiment_id"], harness["id"], task["id"], manifest["seed"])
            order: List[str] = []
            for _ in range(replicates):
                block = list(variant_ids)
                block_rng.shuffle(block)
                order.extend(block)
            for replicate, variant_id in enumerate(order, start=1):
                plan.append(
                    {
                        "experiment_id": manifest["experiment_id"],
                        "harness_id": harness["id"],
                        "task_id": task["id"],
                        "variant_id": variant_id,
                        "replicate": replicate,
                        "assignment_id": (
                            f"{manifest['experiment_id']}/{harness['id']}/{task['id']}/"
                            f"r{replicate:04d}/{variant_id}"
                        ),
                    }
                )
    return plan


def plan_summary(plan: List[Dict[str, Any]], task_set: Dict[str, Any]) -> Dict[str, Any]:
    per_arm: Dict[str, int] = {}
    per_harness: Dict[str, int] = {}
    for a in plan:
        per_arm[a["variant_id"]] = per_arm.get(a["variant_id"], 0) + 1
        per_harness[a["harness_id"]] = per_harness.get(a["harness_id"], 0) + 1
    return {
        "assignments_total": len(plan),
        "tasks": len(task_set["tasks"]),
        "per_arm": per_arm,
        "per_harness": per_harness,
        "balanced": len(set(per_arm.values())) <= 1 or (max(per_arm.values()) - min(per_arm.values())) <= 1,
    }


def budget_estimate(plan: List[Dict[str, Any]], max_attempts: int, max_steps: int) -> Dict[str, Any]:
    """Upper-bound cost preview (LAB-011 / NFR-COST-001).

    Honest basis: worst case = every assignment selects the subject and
    burns every allowed attempt at max steps. Actual spend is recorded in
    the run metadata and the report.
    """
    assignments = len(plan)
    return {
        "basis": "worst-case upper bound: every assignment selects the subject, max attempts, max steps",
        "max_operations": assignments,
        "max_cost_units": round(assignments * max_attempts * max_steps * 2.5, 2),
    }
