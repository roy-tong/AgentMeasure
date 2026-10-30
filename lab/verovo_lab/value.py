"""Margin value formula (ATTR-002) — the bridge from measurement to economics.

    incremental_margin / month
        = opportunity_per_month
        x selection_rate_delta
        x P(operation succeeds | selected)          [measured]
        x P(result consumed | succeeded)            [measured]
        x pay_conversion
        x margin_per_billed_event
        - serving_cost_per_month

Every measured factor comes from the experiment with its label; every
business parameter must be supplied (and labeled) by the customer. Missing
parameters => no absolute number: the report falls back to relative uplift
only. Capture-rate assumptions are displayed separately and are never
silently baked into the formula. Anti-fake-growth rule (ATTR-003): if the
variant's consumption fell (fake-growth flag), margin is computed with the
variant's measured consumption, not the control's.
"""

from typing import Any, Dict, Optional


def compute_margin(
    value_model: Dict[str, Any],
    baseline_arm: Dict[str, Any],
    candidate_arm: Dict[str, Any],
    fake_growth: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    vm = value_model or {}
    required = ("opportunity_per_month", "pay_conversion", "margin_per_billed_event")
    missing = [k for k in required if vm.get(k) is None]
    out: Dict[str, Any] = {
        "formula": (
            "opportunity x dSelection x P(success|selected) x P(consumed|success) "
            "x conversion x margin - serving_cost"
        ),
        "parameters_supplied": {k: vm.get(k) for k in list(required) + ["serving_cost_per_month", "capture_rate_assumption"]},
    }
    if missing:
        out.update(
            {
                "computable": False,
                "missing_parameters": missing,
                "note": "relative uplift only — no absolute margin claimed without customer parameters",
            }
        )
        return out

    sel_delta = candidate_arm["selection_rate"]["value"] - baseline_arm["selection_rate"]["value"]
    success = candidate_arm["operation_success_rate"]["value"] or 0.0
    consumption = candidate_arm["consumption_rate"]["value"] or 0.0
    monthly = (
        vm["opportunity_per_month"]
        * sel_delta
        * success
        * consumption
        * vm["pay_conversion"]
        * vm["margin_per_billed_event"]
    )
    monthly -= vm.get("serving_cost_per_month") or 0.0
    out.update(
        {
            "computable": True,
            "selection_rate_delta": round(sel_delta, 4),
            "measured_factors": {
                "P_success_given_selected": {"value": round(success, 4), "source": "experiment"},
                "P_consumed_given_success": {"value": round(consumption, 4), "source": "experiment"},
            },
            "consumption_basis": "candidate arm (measured) — the candidate's own consumption, never the control's",
            "incremental_margin_per_month": round(monthly, 2),
            "fake_growth_adjusted": bool(fake_growth and fake_growth.get("flagged")),
        }
    )
    if vm.get("capture_rate_assumption") is not None:
        out["capture_at_assumption"] = round(monthly * vm["capture_rate_assumption"], 2)
        out["capture_note"] = "capture rate is a business assumption, shown separately, not part of the measurement"
    return out
