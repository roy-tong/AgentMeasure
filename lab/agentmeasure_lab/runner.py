"""Experiment orchestration (LAB-001, LAB-011).

Runs the preregistered plan in deterministic order, enforces the budget
circuit breaker (safe stop, keep collected data, mark run incomplete),
writes funnel events and run metadata, then produces the analysis and both
report renderings (JSON + offline HTML).
"""

import datetime
import hashlib
import json
import os
import time
from typing import Any, Dict, List

from . import FUNNEL_RULES_VERSION, __version__
from . import analysis, matrix, report as report_mod
from .harness import get_runner
from .prereg import canonical_json, load_preregistration, manifest_hash
from .rng import DetRng


def run_experiment(prereg: Dict[str, Any], out_dir: str, manifest_dir: str) -> Dict[str, Any]:
    manifest = prereg["manifest"]
    if manifest_hash(manifest) != prereg["manifest_hash"]:
        raise ValueError("preregistration hash mismatch — refusing to run a modified manifest")

    task_path = matrix.resolve_task_path(manifest["task_set"]["path"], manifest_dir)
    task_set = matrix.load_task_set(task_path)
    tasks = {t["id"]: t for t in task_set["tasks"]}
    plan = matrix.build_plan(manifest, task_set)
    summary = matrix.plan_summary(plan, task_set)

    budget = manifest["budget"]
    runners: Dict[str, Any] = {}
    try:
        for h in manifest["harnesses"]:
            r = get_runner(h["runner"])
            r.setup(h.get("config", {}))
            runners[h["id"]] = r

        events: List[Dict[str, Any]] = []
        spend = {"operations": 0, "cost_units": 0.0}
        started = time.monotonic()
        stopped_reason = None
        variant_levels = {v["id"]: v["levels"] for v in manifest["variants"]}

        for assignment in plan:
            if spend["operations"] >= budget["max_operations"]:
                stopped_reason = "budget:max_operations"
                break
            if spend["cost_units"] >= budget["max_cost_units"]:
                stopped_reason = "budget:max_cost_units"
                break
            elapsed = time.monotonic() - started
            if elapsed >= budget["max_wall_clock_seconds"]:
                stopped_reason = "budget:max_wall_clock_seconds"
                break

            runner = runners[assignment["harness_id"]]
            rng = DetRng(
                manifest["seed"], manifest["experiment_id"],
                assignment["harness_id"], assignment["task_id"],
                assignment["variant_id"], assignment["replicate"],
            )
            episode = runner.run_episode(
                tasks[assignment["task_id"]],
                variant_levels[assignment["variant_id"]],
                assignment,
                rng,
            )
            events.extend(episode)
            spend["operations"] += 1
            spend["cost_units"] += sum(
                ev.get("cost_units", 0.0) for ev in episode if ev["event"] == "attempt"
            )
        wall_clock = time.monotonic() - started
    finally:
        for r in runners.values():
            r.teardown()

    task_set_hash = hashlib.sha256(canonical_json(task_set).encode("utf-8")).hexdigest()
    fingerprint = hashlib.sha256(
        canonical_json(
            {
                "prereg_hash": prereg["manifest_hash"],
                "events": events,
                "plan": plan,
                "engine": __version__,
                "rules": FUNNEL_RULES_VERSION,
            }
        ).encode("utf-8")
    ).hexdigest()

    run_meta = {
        "status": "complete" if stopped_reason is None else "incomplete",
        "stopped_reason": stopped_reason,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "assignments_executed": spend["operations"],
        "assignments_planned": len(plan),
        "budget": {
            "max_operations": budget["max_operations"],
            "max_cost_units": budget["max_cost_units"],
            "max_wall_clock_seconds": budget["max_wall_clock_seconds"],
            "spent_operations": spend["operations"],
            "spent_cost_units": round(spend["cost_units"], 2),
            "spent_wall_clock_seconds": round(wall_clock, 3),
        },
        "plan": summary,
        "task_set": {"path": manifest["task_set"]["path"], "sha256": task_set_hash},
        "harnesses": [runners[h["id"]].describe() for h in manifest["harnesses"]],
        "seed": manifest["seed"],
        "engine_version": __version__,
        "funnel_rules_version": FUNNEL_RULES_VERSION,
        "run_fingerprint": fingerprint,
        "determinism_note": (
            "same seed + same engine + same rules version + same harness versions => same fingerprint"
        ),
    }

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "events.jsonl"), "w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")

    report = analysis.analyze(manifest, prereg["manifest_hash"], events, run_meta)
    if report.get("variants"):
        report["decision"] = _decision_summary(report, stopped_reason)

    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(report_mod.render_html(report))
    with open(os.path.join(out_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(run_meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return report


def _decision_summary(rep: Dict[str, Any], stopped_reason) -> Dict[str, Any]:
    recommendations = []
    for v in rep["variants"]:
        if v.get("baseline"):
            continue
        rec = {"variant_id": v["variant_id"], "verdict": v["verdict"]}
        cmp = v.get("primary_comparison", {})
        margin = (v.get("value") or {}).get("incremental_margin_per_month")
        if margin is not None:
            rec["verified_margin_per_month"] = margin
        if v.get("dominated_by"):
            rec["dominated_by"] = v["dominated_by"]
            rec["recommended_action"] = (
                f"do not pick: dominated by {v['dominated_by']} (no more money, higher cost)"
            )
        elif v["verdict"] == "adopt_candidate":
            rec["recommended_action"] = "ship behind a flag; verify in production via calibration before scaling"
        elif v["verdict"] == "effective_not_qualified":
            rec["recommended_action"] = "do not ship: guardrail breach; iterate on the regressing guardrail"
        elif v["verdict"] == "unverified_growth":
            drop = (v.get("fake_growth") or {}).get("consumption_delta")
            drop_txt = f" ({drop * 100:+.1f}pp)" if drop is not None else ""
            rec["recommended_action"] = (
                "do not ship: growth is not verified margin — consumption fell"
                f"{drop_txt}; fix consumption first; the margin figure already uses the measured (lower) consumption"
            )
        elif v["verdict"] == "regression_reject":
            rec["recommended_action"] = "reject: primary metric significantly regressed"
        elif v["verdict"] == "null_result":
            action = "no action from this experiment; honest null recorded"
            power_note = cmp.get("power_note")
            if power_note:
                action += f"; {power_note}"
            rec["recommended_action"] = action
        else:
            rec["recommended_action"] = "undetermined: more data required before any decision"
        recommendations.append(rec)
    return {
        "recommendations": recommendations,
        "run_incomplete": stopped_reason is not None,
        "note": (
            "This is a recommendation with its evidence chain, not a decision. "
            "continue / scale / stop belongs to the customer (decision owner)."
        ),
    }


def _rebuild_report(run_dir: str, prereg_path: str) -> Dict[str, Any]:
    """Deterministically rebuild a report from a run's stored events."""
    prereg = load_preregistration(prereg_path)
    with open(os.path.join(run_dir, "events.jsonl"), "r", encoding="utf-8") as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    with open(os.path.join(run_dir, "run.json"), "r", encoding="utf-8") as fh:
        run_meta = json.load(fh)
    manifest = prereg["manifest"]
    report = analysis.analyze(manifest, prereg["manifest_hash"], events, run_meta)
    if report.get("variants"):
        report["decision"] = _decision_summary(report, run_meta.get("stopped_reason"))
    return report


def verify_run(run_dir: str, prereg: Dict[str, Any], manifest_dir: str) -> Dict[str, Any]:
    """Re-verify a finished run: prereg hash, event schema, fingerprint."""
    from .prereg import load_schema
    from .schemas import validate

    with open(os.path.join(run_dir, "events.jsonl"), "r", encoding="utf-8") as fh:
        events = [json.loads(line) for line in fh if line.strip()]
    with open(os.path.join(run_dir, "run.json"), "r", encoding="utf-8") as fh:
        run_meta = json.load(fh)

    event_schema = load_schema("funnel-event.schema.json")
    schema_errors = []
    for i, ev in enumerate(events):
        try:
            validate(ev, event_schema)
        except Exception as e:  # noqa: BLE001 - collect, don't abort
            schema_errors.append(f"event[{i}]: {e}")

    recomputed = hashlib.sha256(
        canonical_json(
            {
                "prereg_hash": prereg["manifest_hash"],
                "events": events,
                "plan": matrix.build_plan(
                    prereg["manifest"], matrix.load_task_set(_resolve_task_path(prereg, run_dir, manifest_dir))
                ),
                "engine": run_meta["engine_version"],
                "rules": run_meta["funnel_rules_version"],
            }
        ).encode("utf-8")
    ).hexdigest()
    return {
        "prereg_hash_matches": True,
        "events_schema_valid": not schema_errors,
        "schema_errors": schema_errors[:10],
        "fingerprint_matches": recomputed == run_meta["run_fingerprint"],
        "events": len(events),
        "status": run_meta["status"],
    }


def _resolve_task_path(prereg: Dict[str, Any], run_dir: str, manifest_dir: str) -> str:
    path = prereg["manifest"]["task_set"]["path"]
    if os.path.isabs(path):
        return path
    for base in (manifest_dir, run_dir):
        candidate = os.path.normpath(os.path.join(base, path))
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(f"cannot resolve task set path {path!r} for verification")
