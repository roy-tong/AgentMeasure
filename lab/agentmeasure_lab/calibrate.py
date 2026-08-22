"""Production calibration analysis (CAL-002, CAL-003, CAL-004 offline half).

The Verify step of the loop: compare a preregistered offline experiment
against production re-measurement events, and quantify the transfer honestly.

Discipline encoded (PRD §4.4 / BP §8 G1):
- production uplift is computed per the SAME preregistered plan (primary
  metric, alpha, min sample) — never re-chosen after seeing the data;
- transfer effects are reported per condition (harness x task stratum),
  each with an interval — never one global "transfer coefficient";
- when a side lacks the events a comparison needs, the comparison is
  `not_comparable` with the gap named — offline numbers never impersonate
  production;
- production events may lack attempt-level detail; steps guardrails then
  report `unknown`, they are not guessed from offline data.

Production events use the same open funnel-event schema (FMT-002): a
gradual-rollout arm is a variant_id; reach = live opportunities for that arm.
"""

import json
import os
from typing import Any, Dict, List, Optional

from . import FUNNEL_RULES_VERSION, __version__
from . import analysis, matrix, report as report_mod
from .analysis import compare
from .prereg import load_preregistration
from .schemas import validate
from .prereg import load_schema

CALIBRATION_SCHEMA_ID = "agentmeasure.lab/calibration-report"


def load_events(path: str) -> List[Dict[str, Any]]:
    events = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    schema = load_schema("funnel-event.schema.json")
    for i, ev in enumerate(events):
        try:
            validate(ev, schema)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"production event[{i}] fails FMT-002: {e}") from e
    return events


def _task_strata(task_set_path: Optional[str]) -> Dict[str, str]:
    if not task_set_path or not os.path.exists(task_set_path):
        return {}
    corpus = matrix.load_task_set(task_set_path)
    return {t["id"]: f"{t.get('category', 'unknown')}/{t.get('tier', 'unknown')}" for t in corpus["tasks"]}


def _annotate_strata(events: List[Dict[str, Any]], strata: Dict[str, str]) -> List[Dict[str, Any]]:
    out = []
    for ev in events:
        copy_ev = dict(ev)
        copy_ev["_stratum"] = strata.get(ev.get("task_id", ""), "unknown/unknown")
        copy_ev["_harness"] = ev.get("harness_id", "unknown")
        out.append(copy_ev)
    return out


def _arm_cells(events: List[Dict[str, Any]], key_field: str):
    """Aggregate funnel per (key, variant) using the shared funnel rules."""
    return analysis.aggregate(events, key_fields=(key_field, "variant_id"))


def _transfer(offline_cmp: Dict[str, Any], production_cmp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Offline-minus-production effect, with a quadrature-approximated CI.

    Honest note: the interval combines two independent Newcombe intervals
    (half-widths in quadrature); it is an approximation, labeled as such.
    """
    if offline_cmp.get("difference") is None or production_cmp.get("difference") is None:
        return None
    d = offline_cmp["difference"] - production_cmp["difference"]
    hw = 0.0
    for cmp in (offline_cmp, production_cmp):
        ci = cmp.get("diff_ci95")
        if ci:
            hw += ((ci[1] - ci[0]) / 2.0) ** 2
    hw = hw ** 0.5
    return {
        "offline_minus_production": round(d, 4),
        "ci95_approx": [round(d - hw, 4), round(d + hw, 4)] if hw else None,
        "method": "difference of independent diff estimates; CI via quadrature of Newcombe half-widths (approximation)",
    }


def _calibration_verdict(offline_cmp: Dict[str, Any], production_cmp: Dict[str, Any]) -> Dict[str, str]:
    if production_cmp.get("verdict") == "undetermined":
        return {"calibration": "undetermined", "reason": production_cmp.get("reason", "insufficient production sample")}
    off_d = offline_cmp.get("difference") or 0.0
    prod_d = production_cmp.get("difference") or 0.0
    if production_cmp["verdict"] == "significant" and off_d * prod_d > 0:
        return {
            "calibration": "production_confirmed",
            "reason": f"production effect {prod_d:+.4f} is significant and direction-consistent with offline {off_d:+.4f}",
        }
    if production_cmp["verdict"] == "significant" and off_d * prod_d < 0:
        return {
            "calibration": "direction_mismatch",
            "reason": f"production effect {prod_d:+.4f} is significant but opposite to offline {off_d:+.4f}; do not scale on offline evidence",
        }
    if production_cmp["verdict"] == "null_result":
        return {
            "calibration": "transfer_not_established",
            "reason": "offline effect did not reach significance in production (honest null); see production CI width before concluding 'no effect'",
        }
    return {"calibration": "not_comparable", "reason": production_cmp.get("reason", "gap")}


def _reweighting_suggestions(condition_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """CAL-004 (minimal): where to spend the next experiment's replicates.

    Ranks conditions by |transfer| (offline-vs-production disagreement) and
    offline CI width — the two signals that more targeted replicates would
    actually shrink. Suggestions flow back into LAB-002's matrix design.
    """
    scored = []
    for row in condition_rows:
        cmp = row.get("comparison")
        if not cmp:
            continue
        tr = _transfer_from_row(row)
        if tr is None:
            continue
        scored.append(
            {
                "condition": row["condition"],
                "transfer": tr["offline_minus_production"],
                "offline_ci_width": _ci_width(cmp),
                "suggestion": "add replicates for this condition in the next preregistered experiment",
            }
        )
    scored.sort(key=lambda s: (abs(s["transfer"]), s["offline_ci_width"]), reverse=True)
    return scored[:3]


def _transfer_from_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return row.get("transfer")


def _ci_width(cmp: Dict[str, Any]) -> float:
    ci = cmp.get("diff_ci95")
    return (ci[1] - ci[0]) if ci else 0.0


def calibrate(
    run_dir: str,
    prereg_path: str,
    production_events_path: str,
    task_set_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the calibration report: offline vs production, per condition."""
    prereg = load_preregistration(prereg_path)
    manifest = prereg["manifest"]
    primary = manifest["primary_metric"]
    alpha = float(manifest["analysis"]["alpha"])
    min_n = int(manifest["analysis"]["min_sample_per_arm"])
    baseline_id = next(v["id"] for v in manifest["variants"] if v.get("baseline"))
    treatment_ids = [v["id"] for v in manifest["variants"] if not v.get("baseline")]

    offline_events = load_events(os.path.join(run_dir, "events.jsonl"))
    production_events = load_events(production_events_path)

    if task_set_path is None:
        task_set_path = matrix.resolve_task_path(
            manifest["task_set"]["path"], os.path.dirname(os.path.abspath(prereg_path))
        )
    strata = _task_strata(task_set_path)

    offline_ann = _annotate_strata(offline_events, strata)
    production_ann = _annotate_strata(production_events, strata)

    offline_overall = analysis.aggregate(offline_events)
    production_overall = analysis.aggregate(production_events)

    variants_out = []
    for vid in treatment_ids:
        ctrl_p = production_overall.get((baseline_id,))
        cand_p = production_overall.get((vid,))
        if not ctrl_p or not cand_p:
            variants_out.append(
                {
                    "variant_id": vid,
                    "calibration": {
                        "calibration": "not_comparable",
                        "reason": "production events missing for at least one arm (check rollout coverage / data-rights scope)",
                    },
                }
            )
            continue

        production_cmp = compare(ctrl_p, cand_p, primary, alpha, min_n)
        offline_cmp = compare(
            offline_overall[(baseline_id,)], offline_overall[(vid,)], primary, alpha, min_n
        )

        condition_rows = []
        for field, label in (("_harness", "harness"), ("_stratum", "stratum")):
            off_cells = _arm_cells(offline_ann, field)
            prod_cells = _arm_cells(production_ann, field)
            for key in sorted({k[0] for k in off_cells} | {k[0] for k in prod_cells}):
                ctrl_o, cand_o = off_cells.get((key, baseline_id)), off_cells.get((key, vid))
                ctrl_q, cand_q = prod_cells.get((key, baseline_id)), prod_cells.get((key, vid))
                if not (ctrl_o and cand_o and ctrl_q and cand_q):
                    condition_rows.append(
                        {
                            "condition": f"{label}:{key}",
                            "status": "not_comparable",
                            "gap": "one side lacks events for this condition",
                        }
                    )
                    continue
                off_c = compare(ctrl_o, cand_o, primary, alpha, min_n)
                prod_c = compare(ctrl_q, cand_q, primary, alpha, min_n)
                row = {"condition": f"{label}:{key}", "comparison": prod_c, "offline": off_c}
                tr = _transfer(off_c, prod_c)
                if tr:
                    row["transfer"] = tr
                condition_rows.append(row)

        verdict = _calibration_verdict(offline_cmp, production_cmp)
        variants_out.append(
            {
                "variant_id": vid,
                "offline_comparison": offline_cmp,
                "production_comparison": production_cmp,
                "calibration": verdict,
                "transfer_overall": _transfer(offline_cmp, production_cmp),
                "per_condition": condition_rows,
                "reweighting_suggestions": _reweighting_suggestions(condition_rows),
                "production_guardrails": analysis.evaluate_guardrails(manifest, cand_p),
            }
        )

    with open(os.path.join(run_dir, "run.json"), "r", encoding="utf-8") as fh:
        run_meta = json.load(fh)

    return {
        "schema": CALIBRATION_SCHEMA_ID,
        "schema_version": "1.0.0",
        "engine_version": __version__,
        "funnel_rules_version": FUNNEL_RULES_VERSION,
        "experiment_id": manifest["experiment_id"],
        "preregistration": {"manifest_hash": prereg["manifest_hash"], "primary_metric": primary},
        "offline_run": {
            "run_fingerprint": run_meta.get("run_fingerprint"),
            "assignments": run_meta.get("assignments_executed"),
            "environment": "controlled (offline experiment)",
        },
        "production_source": {
            "events_file": os.path.basename(production_events_path),
            "environment": "production (gradual rollout; treatment arms vs holdout)",
            "note": "production events follow the same open FMT-002 schema; aggregation rules identical — same ruler, different data",
        },
        "variants": variants_out,
        "limitations": [
            "Transfer intervals are approximations (quadrature of independent Newcombe intervals).",
            "Per-condition production samples are usually smaller than offline; undetermined conditions are reported as such, never pooled away.",
            "Calibration requires cross-side data rights (BP G0); this report only exists for sides whose events were actually provided.",
        ],
    }


def write_calibration_report(cal: Dict[str, Any], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "calibration-report.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(cal, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    html_path = os.path.join(out_dir, "calibration-report.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(report_mod.render_calibration_html(cal))
    return json_path
