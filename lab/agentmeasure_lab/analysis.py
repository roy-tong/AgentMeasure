"""Funnel aggregation, comparisons and verdicts (LAB-006..008, ATTR-001..003).

Discipline encoded here (PRD §4.4 / §8.3):
- every rate carries numerator, denominator and a Measurement Label — no
  bare numbers;
- only the preregistered primary metric gets a significance verdict;
  secondary metrics are descriptive only (no metric shopping);
- guardrail breach downgrades "effective" to "effective_not_qualified";
- selection uplift that loses consumption raises a fake-growth warning and
  is excluded from margin claims;
- per-condition (per-harness) effect sizes are reported alongside the
  overall number — never a single pooled effect only (the offline half of
  CAL-003's no-single-global-coefficient rule);
- insufficient sample => "undetermined" + required n, never a guess.
"""

from typing import Any, Dict, List, Optional, Tuple

from . import FUNNEL_RULES_VERSION, __version__
from . import stats
from .prereg import guardrail_metric_names
from .value import compute_margin

DESCRIPTIVE_ONLY_NOTE = (
    "descriptive only — not part of the preregistered analysis plan; "
    "do not read as confirmatory"
)

# Bilingual plain-language verdicts for the decision maker (boss one-pager,
# MCP advice). The enum stays English/stable; humans get the translation.
PLAIN_LABELS = {
    "adopt_candidate": ("Ship it — verified uplift, guardrails pass", "可上线——提升已验证，护栏全部通过"),
    "effective_not_qualified": ("Do not ship — works, but breaches guardrails", "不上线——有效，但突破护栏"),
    "unverified_growth": ("Do not ship — growth is not verified margin", "不上线——增长不是真毛利（消费率下跌）"),
    "regression_reject": ("Reject — significant regression", "拒绝——显著退化"),
    "null_result": ("No measurable difference (honest null)", "无可测差异（诚实零结果）"),
    "undetermined": ("Not enough data to decide", "数据不足，暂无法判定"),
    "baseline": ("Baseline (current)", "基线（现状）"),
}


def _label(grain: str, definition: str) -> Dict[str, str]:
    return {
        "grain": grain,
        "rules_version": FUNNEL_RULES_VERSION,
        "definition": definition,
        "qualification": "controlled experiment environment (not production)",
    }


def _rate(k: int, n: int, grain: str, definition: str) -> Dict[str, Any]:
    ci = stats.wilson_interval(k, n)
    return {
        "numerator": k,
        "denominator": n,
        "value": (k / n) if n else None,
        "ci95": [round(c, 4) for c in ci] if ci else None,
        "measurement_label": _label(grain, definition),
    }


def aggregate(events: List[Dict[str, Any]], key_fields: Tuple[str, ...] = ("variant_id",)) -> Dict[Tuple, Dict[str, Any]]:
    """Aggregate funnel events into per-cell metric bundles."""
    cells: Dict[Tuple, Dict[str, Any]] = {}

    def cell_for(ev: Dict[str, Any]) -> Dict[str, Any]:
        key = tuple(ev[f] for f in key_fields)
        if key not in cells:
            cells[key] = {
                "reach": 0,
                "selected": 0,
                "operations": 0,
                "operations_succeeded": 0,
                "attempts": 0,
                "consumed": 0,
                "cost_units": 0.0,
                # steps are summed per operation key, not per assignment:
                # an assignment may contain several operations (#10 / AM-U-007)
                "steps_by_operation": {},
                # #9 reconciliation state: attempt rows are the facts,
                # operation_result declarations are claims that must reconcile.
                "attempt_outcomes_by_op": {},
                "op_declared_keys": {},
                "op_recon_failures": [],
            }
        return cells[key]

    def _derived_outcome(outcomes: List[str]) -> Optional[str]:
        """Derive operation outcome from attempt rows (rule op-success-any/1)."""
        if any(o == "success" for o in outcomes):
            return "success"
        if any(o == "failure" for o in outcomes):
            return "failure"
        return "unresolved" if outcomes else None

    for ev in events:
        c = cell_for(ev)
        kind = ev["event"]
        if kind == "reach":
            c["reach"] += 1
        elif kind == "choice":
            if ev["selected_subject"]:
                c["selected"] += 1
        elif kind == "attempt":
            aid = ev["assignment_id"]
            op_key = (aid, ev.get("operation_index"))
            c["steps_by_operation"][op_key] = c["steps_by_operation"].get(op_key, 0) + ev["steps"]
            c["cost_units"] += ev["cost_units"]
            c["attempt_outcomes_by_op"].setdefault(op_key, []).append(ev["outcome"])
        elif kind == "operation_result":
            op_key = (ev["assignment_id"], ev.get("operation_index"))
            rows = c["attempt_outcomes_by_op"].get(op_key, [])
            declared_outcome = ev["outcome"]
            declared_attempts = ev["attempts"]
            derived = _derived_outcome(rows)
            last_outcome = rows[-1] if rows else None
            reasons = []
            if op_key in c["op_declared_keys"]:
                reasons.append("duplicate operation_result declaration for this operation")
            c["op_declared_keys"][op_key] = True
            if not rows:
                reasons.append(
                    f"no attempt rows grouped under this operation "
                    f"(declared attempts={declared_attempts})")
            else:
                if declared_attempts != len(rows):
                    reasons.append(
                        f"declared attempts={declared_attempts} but {len(rows)} attempt row(s)")
                if derived is not None and declared_outcome != derived:
                    reasons.append(
                        f"declared outcome={declared_outcome!r} but attempt rows derive "
                        f"{derived!r} (rule op-success-any/1; last attempt outcome={last_outcome!r})")
            # attempts and outcome are taken from measured rows, never from
            # the declaration (#9: never silent trust)
            c["operations"] += 1
            c["attempts"] += len(rows)
            if derived == "success":
                c["operations_succeeded"] += 1
            if reasons:
                rec = {
                    "assignment_id": ev["assignment_id"],
                    "operation_index": ev.get("operation_index"),
                    "reasons": reasons,
                    "declared": {"outcome": declared_outcome, "attempts": declared_attempts},
                    "actual": {"attempt_rows": len(rows),
                               "derived_outcome": derived, "last_outcome": last_outcome},
                }
                # terminal-outcome note per issue #9: last attempt's outcome
                if rows and declared_outcome == "success" and last_outcome != "success":
                    rec["note"] = (
                        f"declared success but last attempt outcome={last_outcome!r}; "
                        "accepted under op-success-any/1, disclosed for diagnosis")
                c["op_recon_failures"].append(rec)
        elif kind == "consumption":
            if ev["consumed"]:
                c["consumed"] += 1

    out: Dict[Tuple, Dict[str, Any]] = {}
    for key, c in cells.items():
        # AM-U-007 (#10): the metric is operation-grain, so the median runs
        # over resolved operations only. Steps of attempts whose operation has
        # no reconciled declaration are dropped (fail-closed), and operations
        # that failed reconciliation do not contribute either.
        failed_keys = {
            (rec["assignment_id"], rec.get("operation_index"))
            for rec in c["op_recon_failures"]
        }
        op_steps = [
            v for k, v in c["steps_by_operation"].items()
            if k in c["op_declared_keys"] and k not in failed_keys
        ]
        med = stats.median(op_steps) if op_steps else None
        declared_ops = len(c["op_declared_keys"])
        recon_failed = len(c["op_recon_failures"])
        out[key] = {
            "reach": c["reach"],
            "selected": c["selected"],
            "operations": c["operations"],
            "operation_reconciliation": {
                "declared_summaries": declared_ops,
                "reconciled": declared_ops - recon_failed,
                "failed": recon_failed,
                "failures": c["op_recon_failures"][:20],
                "status": ("failed" if recon_failed
                           else "passed" if declared_ops
                           else "no_declared_summaries"),
                "note": ("operation_result declarations are reconciled against "
                         "attempt rows; counts/outcomes use measured rows (#9)"),
            },
            "selection_rate": _rate(
                c["selected"], c["reach"], "assignment",
                "subject selected / decision opportunities (reach events)",
            ),
            "operation_success_rate": _rate(
                c["operations_succeeded"], c["operations"], "operation",
                "operations with >=1 successful attempt / subject operations "
                "(rule op-success-any/1)",
            ),
            "consumption_rate": _rate(
                c["consumed"], c["operations_succeeded"], "operation",
                "results consumed by the agent / successful operations",
            ),
            "attempts_per_operation": {
                "numerator": c["attempts"],
                "denominator": c["operations"],
                "value": (c["attempts"] / c["operations"]) if c["operations"] else None,
                "measurement_label": _label(
                    "operation", "total attempts / operations (retries are attempts, not uses)"
                ),
            },
            "median_steps_per_operation": {
                "value": med,
                "numerator": None,
                "denominator": len(op_steps),
                "measurement_label": _label(
                    "operation",
                    "median summed steps across attempts, per resolved operation "
                    "(unresolved operations contribute nothing, fail-closed)"),
            },
            "cost_units_per_operation": {
                "numerator": round(c["cost_units"], 2),
                "denominator": c["operations"],
                "value": (c["cost_units"] / c["operations"]) if c["operations"] else None,
                "measurement_label": _label("operation", "abstract cost units (harness-reported)"),
            },
        }
    return out


def compare(
    control: Dict[str, Any], candidate: Dict[str, Any],
    metric: str, alpha: float, min_n: int,
) -> Dict[str, Any]:
    """Primary-metric comparison with verdict per the preregistered plan."""
    ctrl_m, cand_m = control[metric], candidate[metric]
    n_ctrl, n_cand = ctrl_m["denominator"], cand_m["denominator"]
    result: Dict[str, Any] = {
        "metric": metric,
        "control": {"value": ctrl_m["value"], "n": n_ctrl},
        "candidate": {"value": cand_m["value"], "n": n_cand},
        "alpha": alpha,
        "min_sample_per_arm": min_n,
    }
    if n_ctrl == 0 or n_cand == 0:
        result.update({"verdict": "undetermined", "reason": "empty arm"})
        return result
    test = stats.two_proportion_z_test(ctrl_m["numerator"], n_ctrl, cand_m["numerator"], n_cand)
    ci = stats.newcombe_diff_interval(ctrl_m["numerator"], n_ctrl, cand_m["numerator"], n_cand)
    diff = cand_m["value"] - ctrl_m["value"]
    result.update(
        {
            "difference": round(diff, 4),
            "diff_ci95": [round(x, 4) for x in ci] if ci else None,
            "z": round(test[0], 4) if test else None,
            "p_value": round(test[1], 6) if test else None,
        }
    )
    if n_ctrl < min_n or n_cand < min_n:
        required = None
        if diff != 0:
            try:
                required = stats.required_n_per_arm(
                    ctrl_m["value"] if ctrl_m["value"] else diff / 2 + 0.01,
                    cand_m["value"],
                    alpha=alpha,
                )
            except ValueError:
                required = None
        result.update(
            {
                "verdict": "undetermined",
                "reason": (
                    f"sample below preregistered minimum ({min_n}/arm); "
                    f"indicative required n/arm ≈ {required or 'n/a'}"
                ),
            }
        )
        return result
    significant = test is not None and test[1] < alpha
    if significant:
        result["verdict"] = "significant"
        result["direction"] = "improvement" if diff > 0 else "regression"
    else:
        result["verdict"] = "null_result"
        result["reason"] = (
            f"no significant difference at alpha={alpha} (two-sided, preregistered); "
            "this is an honest null, not evidence of no effect — see CI width"
        )
        # Power guidance (POC finding: a boss reads a bare null as "no effect"
        # and may kill a real, valuable direction). Say what it would take.
        if diff != 0:
            try:
                req = stats.required_n_per_arm(ctrl_m["value"] or 0.02, cand_m["value"], alpha=alpha)
                result["power_note"] = (
                    f"to resolve an effect of the observed size (~{abs(diff) * 100:.1f}pp), "
                    f"plan ≈{req} per arm in the next round"
                )
            except ValueError:
                result["power_note"] = "observed effect is indistinguishable from zero; the CI width is the answer"
    return result


def evaluate_guardrails(
    manifest: Dict[str, Any], arm: Dict[str, Any]
) -> List[Dict[str, Any]]:
    rows = []
    for g in manifest.get("guardrails", []):
        m = arm[g["metric"]]
        value = m["value"]
        if value is None:
            status, note = "unknown", "no data"
        elif "max" in g and value > g["max"]:
            status, note = "breach", f"{value:.4f} > max {g['max']}"
        elif "min" in g and value < g["min"]:
            status, note = "breach", f"{value:.4f} < min {g['min']}"
        else:
            status, note = "pass", "within threshold"
        rows.append({"metric": g["metric"], "value": value, "threshold": g, "status": status, "note": note})
    return rows


def fake_growth_check(control: Dict[str, Any], candidate: Dict[str, Any], primary: str, alpha: float) -> Optional[Dict[str, Any]]:
    """Anti-fake-growth (ATTR-003): selection gain without verified consumption.

    Significance-aware (POC finding: a flat -2pp threshold flagged sampling
    noise and dulled the warning). Flagged only when the consumption drop is
    statistically significant at alpha OR materially large (>5pp). Small
    within-noise dips are not flagged — the margin still uses the candidate's
    measured consumption (conservative), labeled as such.
    """
    if primary == "consumption_rate":
        return None
    cons_ctrl_m, cons_cand_m = control["consumption_rate"], candidate["consumption_rate"]
    cons_ctrl, cons_cand = cons_ctrl_m["value"], cons_cand_m["value"]
    if cons_ctrl is None or cons_cand is None:
        return None
    delta = cons_cand - cons_ctrl
    if delta >= -0.005:
        return None
    significant_drop = False
    test = stats.two_proportion_z_test(
        cons_ctrl_m["numerator"], cons_ctrl_m["denominator"],
        cons_cand_m["numerator"], cons_cand_m["denominator"],
    )
    if test:
        significant_drop = test[1] < alpha
    material_drop = delta < -0.05
    if not (significant_drop or material_drop):
        return {
            "flagged": False,
            "consumption_delta": round(delta, 4),
            "note": "consumption dip is within noise; not flagged — margin still uses the candidate's measured consumption (conservative)",
        }
    kind = "significant" if significant_drop else "material"
    return {
        "flagged": True,
        "kind": kind,
        "consumption_delta": round(delta, 4),
        "message": (
            "Fake-growth warning: consumption rate fell while the primary metric moved. "
            "Uplift is NOT verified margin growth; margin claims must use the measured "
            "(lower) consumption."
        ),
    }


def _annotate_dominance(variants: List[Dict[str, Any]]) -> None:
    """Flag candidates strictly dominated by another candidate (POC finding).

    The boss-facing question is "why would I pick the flashier variant when
    it makes the same money at higher cost?" — the report should say so.
    Conservative rule: B is dominated by A only when both are significant
    improvements, A's monthly margin is not below B's (within 2%), A costs
    less per operation (by >2%), and A's consumption is not lower.
    """
    cands = [
        v for v in variants
        if not v.get("baseline")
        and v.get("primary_comparison", {}).get("verdict") == "significant"
        and v["primary_comparison"].get("direction") == "improvement"
    ]
    for b in cands:
        for a in cands:
            if a["variant_id"] == b["variant_id"]:
                continue
            ma = (a.get("value") or {}).get("incremental_margin_per_month")
            mb = (b.get("value") or {}).get("incremental_margin_per_month")
            if ma is not None and mb is not None:
                better_or_equal_value = ma >= mb * 0.98
            else:
                da = a["primary_comparison"].get("difference") or 0.0
                db = b["primary_comparison"].get("difference") or 0.0
                better_or_equal_value = da >= db * 0.98
            ca = a["metrics"]["cost_units_per_operation"]["value"]
            cb = b["metrics"]["cost_units_per_operation"]["value"]
            consa = a["metrics"]["consumption_rate"]["value"]
            consb = b["metrics"]["consumption_rate"]["value"]
            if (
                better_or_equal_value
                and ca is not None and cb is not None and ca < cb * 0.98
                and consa is not None and consb is not None and consa >= consb
            ):
                b["dominated_by"] = a["variant_id"]
                b["dominance_note"] = (
                    f"{b['variant_id']} makes no more money than {a['variant_id']} "
                    f"while costing more per operation — pick {a['variant_id']}"
                )
                break


def analyze(
    manifest: Dict[str, Any],
    prereg_hash: str,
    events: List[Dict[str, Any]],
    run_meta: Dict[str, Any],
) -> Dict[str, Any]:
    overall = aggregate(events)
    by_harness = aggregate(events, key_fields=("harness_id", "variant_id"))
    analysis_plan = manifest["analysis"]
    alpha = float(analysis_plan["alpha"])
    min_n = int(analysis_plan["min_sample_per_arm"])
    primary = manifest["primary_metric"]
    baseline_id = next(v["id"] for v in manifest["variants"] if v.get("baseline"))
    control = overall[(baseline_id,)]

    variants: List[Dict[str, Any]] = []
    for v in manifest["variants"]:
        vid = v["id"]
        arm = overall.get((vid,))
        if arm is None:
            continue
        entry: Dict[str, Any] = {
            "variant_id": vid,
            "levels": v["levels"],
            "baseline": bool(v.get("baseline")),
            "metrics": arm,
            "guardrails": evaluate_guardrails(manifest, arm) if not v.get("baseline") else [],
        }
        if not v.get("baseline"):
            cmp = compare(control, arm, primary, alpha, min_n)
            entry["primary_comparison"] = cmp
            entry["fake_growth"] = fake_growth_check(control, arm, primary, alpha)
            entry["value"] = compute_margin(
                manifest.get("value_model"), control, arm, entry["fake_growth"]
            )
            entry["per_condition"] = []
            for h in manifest["harnesses"]:
                cell = by_harness.get((h["id"], vid))
                ctrl_cell = by_harness.get((h["id"], baseline_id))
                if cell and ctrl_cell:
                    entry["per_condition"].append(
                        {
                            "condition": h["id"],
                            "comparison": compare(ctrl_cell, cell, primary, alpha, min_n),
                            "note": "per-condition effect size — never summarized by one global coefficient",
                        }
                    )
            guardrail_breach = any(g["status"] == "breach" for g in entry["guardrails"])
            growth_flagged = bool((entry["fake_growth"] or {}).get("flagged"))
            if cmp["verdict"] == "significant" and cmp.get("direction") == "improvement":
                # Decision-exit discipline (POC P3): a selection uplift that
                # loses consumption is not qualified margin growth — the boss
                # must not read "adopt" on top of a fake-growth warning.
                if growth_flagged:
                    entry["verdict"] = "unverified_growth"
                elif guardrail_breach:
                    entry["verdict"] = "effective_not_qualified"
                else:
                    entry["verdict"] = "adopt_candidate"
            elif cmp["verdict"] == "significant":
                entry["verdict"] = "regression_reject"
            else:
                entry["verdict"] = cmp["verdict"]
        else:
            entry["verdict"] = "baseline"
        entry["plain_label"] = PLAIN_LABELS.get(entry["verdict"])
        variants.append(entry)

    _annotate_dominance(variants)

    return {
        "schema": "agentmeasure.lab/report",
        "schema_version": "1.0.0",
        "engine_version": __version__,
        "funnel_rules_version": FUNNEL_RULES_VERSION,
        "experiment_id": manifest["experiment_id"],
        "hypothesis": manifest["hypothesis"],
        "preregistration": {
            "manifest_hash": prereg_hash,
            "primary_metric": primary,
            "alpha": alpha,
            "min_sample_per_arm": min_n,
        },
        "run": run_meta,
        "variants": variants,
        "secondary_metrics_note": DESCRIPTIVE_ONLY_NOTE,
        "limitations": [
            "Controlled synthetic environment; production transfer is NOT claimed here — "
            "production verification requires the commercial calibration loop (Connector + holdout).",
            "Per-condition (per-harness) effects may disagree with the pooled effect; that "
            "disagreement is information, not noise to be averaged away.",
            "Mock harness factor effects are planted simulation parameters, not real-agent claims.",
        ],
    }
