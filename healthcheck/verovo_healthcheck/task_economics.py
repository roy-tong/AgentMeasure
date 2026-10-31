"""Task economics: connect technical usage, financial cost and business outcome.

This module deliberately does not parse contracts, call providers or decide what a
business "should" value. It computes a reproducible ledger from an explicit local
case file:

    BusinessTask <- AgentRun <- UsageEvent (financialized only)
    BusinessTask <- CostItem (direct or allocated shared)
    BusinessTask <- BusinessOutcome (verified only for success/value)

Rules that are intentionally strict:
- currencies are never added together;
- a usage row is not a monetary cost unless it is explicitly financialized and
  carries a cost/currency/source reference;
- duplicate cost rows are reported, not silently summed;
- missing task linkage stays unallocated (no timestamp guessing);
- shared cost requires an allocation rule with a version;
- unverified outcomes never enter the "cost per verified success" denominator;
- ROI is null unless verified business value exists in the case currency.
"""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class EconomicsError(ValueError):
    """Invalid case structure or an unsafe financial assumption."""


def _dec(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise EconomicsError("%s must be a monetary/quantity value" % field)
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise EconomicsError("%s is not a valid number: %r" % (field, value))
    if not number.is_finite():
        raise EconomicsError("%s must be finite" % field)
    return number


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise EconomicsError("%s must be a non-empty string" % field)
    return text


def _list(case: Dict[str, Any], field: str) -> List[Any]:
    value = case.get(field)
    if value is None:
        return []
    if not isinstance(value, list):
        raise EconomicsError("%s must be an array" % field)
    return value


def _index(items: List[Any], field: str, label: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise EconomicsError("%s[%d] must be an object" % (label, index))
        key = _text(item.get(field), "%s[%d].%s" % (label, index, field))
        if key in out:
            raise EconomicsError("duplicate %s %r" % (label, key))
        out[key] = item
    return out


def _amount(item: Dict[str, Any], field: str, label: str) -> Decimal:
    return _dec(item.get(field), "%s.%s" % (label, field))


def _currency(item: Dict[str, Any], label: str, case_currency: str) -> str:
    currency = str(item.get("currency") or case_currency).strip().upper()
    if currency != case_currency:
        raise EconomicsError(
            "%s currency %s differs from case currency %s; cross-currency "
            "aggregation is forbidden" % (label, currency, case_currency))
    return currency


def _allocate(total: Decimal, tasks: List[str], rule: Dict[str, Any]) -> Dict[str, Decimal]:
    """Allocate a shared cost without losing cents; remainder stays explicit.

    equal       equal split across tasks
    headcount   basis.weights task_id -> non-negative weight
    revenue     basis.values task_id -> non-negative verified revenue
    """
    method = str(rule.get("method") or "")
    basis = rule.get("basis") if isinstance(rule.get("basis"), dict) else {}
    if not tasks:
        return {}
    if method == "equal":
        weights = {task: Decimal("1") for task in tasks}
    elif method in ("headcount", "revenue"):
        source = basis.get("weights" if method == "headcount" else "values")
        if not isinstance(source, dict):
            raise EconomicsError("allocation rule %s needs basis.%s" % (
                rule.get("id"), "weights" if method == "headcount" else "values"))
        weights = {}
        for task in tasks:
            value = source.get(task, 0)
            weight = _dec(value, "allocation weight %s" % task)
            if weight < 0:
                raise EconomicsError("allocation weight cannot be negative: %s" % task)
            weights[task] = weight
    else:
        raise EconomicsError("unsupported allocation method: %r" % method)
    denominator = sum(weights.values(), Decimal("0"))
    if denominator <= 0:
        raise EconomicsError("allocation weights sum to zero")
    total = _money(total)
    allocated: Dict[str, Decimal] = {}
    running = Decimal("0")
    for index, task in enumerate(tasks):
        if index == len(tasks) - 1:
            share = total - running
        else:
            share = _money(total * weights[task] / denominator)
            running += share
        allocated[task] = share
    return allocated


def evaluate(case: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(case, dict):
        raise EconomicsError("case must be an object")
    if case.get("schema_version") not in (None, "1.0"):
        raise EconomicsError("unsupported task-economics schema_version")
    case_id = _text(case.get("case_id"), "case_id")
    currency = _text(case.get("currency"), "currency").upper()
    period = case.get("period")
    if not isinstance(period, dict) or not period.get("start") or not period.get("end"):
        raise EconomicsError("period.start and period.end are required")

    tasks_raw = _list(case, "tasks")
    if not tasks_raw:
        raise EconomicsError("at least one task is required")
    tasks = _index(tasks_raw, "task_id", "tasks")
    task_ids = list(tasks)
    runs = _index(_list(case, "runs"), "run_id", "runs")
    usage = _index(_list(case, "usage"), "usage_id", "usage")
    documents = _index(_list(case, "documents"), "document_id", "documents")
    cost_items = _list(case, "cost_items")
    outcomes = _list(case, "outcomes")
    loss_events = _list(case, "loss_events")
    rules_raw = _list(case, "allocation_rules")
    rules: Dict[str, Dict[str, Any]] = {}
    for index, rule in enumerate(rules_raw):
        if not isinstance(rule, dict):
            raise EconomicsError("allocation_rules[%d] must be an object" % index)
        rid = _text(rule.get("id"), "allocation_rules[%d].id" % index)
        if rid in rules:
            raise EconomicsError("duplicate allocation rule %r" % rid)
        _text(rule.get("version"), "allocation_rules[%d].version" % index)
        if str(rule.get("method") or "") not in ("equal", "headcount", "revenue"):
            raise EconomicsError("allocation rule %s has unsupported method" % rid)
        rules[rid] = rule

    findings: List[Dict[str, Any]] = []
    direct: Dict[str, Decimal] = {task_id: Decimal("0") for task_id in task_ids}
    shared_items: List[Tuple[Decimal, str, str]] = []  # amount, rule_id, cost_id
    unallocated: List[Dict[str, Any]] = []
    seen_cost = set()

    # Technical usage is not a financial cost unless explicitly financialized.
    for usage_id, item in usage.items():
        run_id = str(item.get("run_id") or "").strip()
        run = runs.get(run_id)
        if run is None:
            unallocated.append({"kind": "usage", "id": usage_id,
                                "reason": "run_id is unknown"})
            continue
        task_id = str(run.get("task_id") or "").strip()
        if not task_id or task_id not in tasks:
            unallocated.append({"kind": "usage", "id": usage_id,
                                "reason": "run has no known task_id"})
            continue
        if not item.get("financialized"):
            continue
        source_ref = str(item.get("source_ref") or "").strip()
        if not source_ref:
            unallocated.append({"kind": "usage", "id": usage_id,
                                "reason": "financialized usage needs source_ref"})
            continue
        _currency(item, "usage %s" % usage_id, currency)
        amount = _amount(item, "cost", "usage %s" % usage_id)
        if amount < 0:
            raise EconomicsError("usage cost cannot be negative: %s" % usage_id)
        direct[task_id] += amount

    # Direct and shared cost items. Duplicate financial rows are findings, not sums.
    for index, item in enumerate(cost_items):
        if not isinstance(item, dict):
            raise EconomicsError("cost_items[%d] must be an object" % index)
        cost_id = _text(item.get("cost_id"), "cost_items[%d].cost_id" % index)
        source_ref = _text(item.get("source_ref"), "cost_items[%d].source_ref" % index)
        amount = _amount(item, "amount", "cost_items[%d]" % index)
        if amount < 0:
            raise EconomicsError("cost item amount cannot be negative: %s" % cost_id)
        _currency(item, "cost item %s" % cost_id, currency)
        dedupe = (
            source_ref,
            str(_money(amount)),
            currency,
            str(item.get("period") or "%s..%s" % (period["start"], period["end"])),
            str(item.get("vendor") or ""),
        )
        if cost_id in seen_cost or dedupe in seen_cost:
            findings.append({"code": "duplicate_cost_item", "severity": "review",
                             "id": cost_id, "source_ref": source_ref,
                             "message": "duplicate financial row was not added twice"})
            continue
        seen_cost.add(cost_id)
        seen_cost.add(dedupe)
        task_id = str(item.get("task_id") or "").strip()
        if task_id:
            if task_id not in tasks:
                unallocated.append({"kind": "cost_item", "id": cost_id,
                                    "reason": "unknown task_id %s" % task_id})
                continue
            direct[task_id] += amount
            continue
        rule_id = str(item.get("allocation_rule") or "").strip()
        if not rule_id or rule_id not in rules:
            unallocated.append({"kind": "cost_item", "id": cost_id,
                                "reason": "shared cost needs a known allocation_rule"})
            continue
        shared_items.append((amount, rule_id, cost_id))

    allocated: Dict[str, Decimal] = {task_id: Decimal("0") for task_id in task_ids}
    allocation_details: List[Dict[str, Any]] = []
    for amount, rule_id, cost_id in shared_items:
        rule = rules[rule_id]
        shares = _allocate(amount, task_ids, rule)
        for task_id, share in shares.items():
            allocated[task_id] += share
        allocation_details.append({
            "cost_id": cost_id, "amount": str(_money(amount)),
            "rule_id": rule_id, "rule_version": rule.get("version"),
            "method": rule.get("method"), "shares": {k: str(v) for k, v in shares.items()},
        })

    # Outcomes are separate evidence. Only verified success enters success/value.
    outcome_rows: List[Dict[str, Any]] = []
    verified_success = set()
    verified_value: Dict[str, Decimal] = {}
    for index, item in enumerate(outcomes):
        if not isinstance(item, dict):
            raise EconomicsError("outcomes[%d] must be an object" % index)
        task_id = _text(item.get("task_id"), "outcomes[%d].task_id" % index)
        if task_id not in tasks:
            raise EconomicsError("outcome references unknown task: %s" % task_id)
        status = str(item.get("status") or "")
        verified = bool(item.get("verified"))
        source_ref = str(item.get("source_ref") or "").strip()
        row = {"task_id": task_id, "status": status, "verified": verified,
               "source_ref": source_ref}
        if status == "success" and verified and source_ref:
            verified_success.add(task_id)
        else:
            findings.append({"code": "unverified_outcome", "severity": "review",
                             "task_id": task_id,
                             "message": "outcome is not verified success; excluded from success denominator"})
        if item.get("value") is not None:
            if _currency(item, "outcome %s" % task_id, currency) and item.get("value_verified") and verified and status == "success":
                value = _dec(item.get("value"), "outcome value %s" % task_id)
                if value < 0:
                    raise EconomicsError("outcome value cannot be negative: %s" % task_id)
                verified_value[task_id] = verified_value.get(task_id, Decimal("0")) + value
            else:
                findings.append({"code": "unverified_value", "severity": "review",
                                 "task_id": task_id,
                                 "message": "business value is not verified and is excluded from ROI"})
        outcome_rows.append(row)

    rows: List[Dict[str, Any]] = []
    total_cost = Decimal("0")
    for task_id, task in tasks.items():
        direct_cost = _money(direct[task_id])
        shared_cost = _money(allocated[task_id])
        total = _money(direct_cost + shared_cost)
        total_cost += total
        rows.append({
            "task_id": task_id, "type": task.get("type", ""),
            "direct_cost": str(direct_cost), "allocated_cost": str(shared_cost),
            "fully_loaded_cost": str(total),
            "verified_success": task_id in verified_success,
            "verified_value": str(_money(verified_value.get(task_id, Decimal("0"))))
            if task_id in verified_value else None,
        })

    success_count = len(verified_success)
    successful_cost = total_cost if success_count else None
    cost_per_success = (
        _money(total_cost / Decimal(success_count)) if success_count else None
    )
    verified_value_total = sum(verified_value.values(), Decimal("0"))
    roi = None
    roi_reason = "no verified business value in the case currency"
    if verified_value_total > 0 and total_cost > 0:
        roi = str(((verified_value_total - total_cost) / total_cost).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP))
        roi_reason = "verified value and fully loaded cost in the same currency/period"

    loss_total = sum(
        (_dec(item.get("amount"), "loss event amount")
         for item in loss_events if isinstance(item, dict) and item.get("amount") is not None),
        Decimal("0"),
    )
    loss_rows = []
    for index, item in enumerate(loss_events):
        if not isinstance(item, dict):
            raise EconomicsError("loss_events[%d] must be an object" % index)
        _currency(item, "loss event %d" % index, currency)
        loss_rows.append({
            "loss_id": item.get("loss_id", ""), "task_id": item.get("task_id", ""),
            "amount": str(_money(_dec(item.get("amount", 0), "loss amount"))),
            "status": item.get("status", ""), "source_ref": item.get("source_ref", ""),
        })

    coverage = {
        "tasks": len(tasks), "runs": len(runs), "usage": len(usage),
        "financial_documents": len(documents), "cost_items": len(cost_items),
        "outcomes": len(outcomes),
        "verified_success_tasks": success_count,
        "unallocated_items": len(unallocated),
    }
    result = {
        "schema_version": "1.0", "kind": "verovo.task-economics",
        "case_id": case_id, "currency": currency, "period": period,
        "coverage": coverage,
        "totals": {
            "fully_loaded_cost": str(_money(total_cost)),
            "verified_success_tasks": success_count,
            "cost_per_verified_success": str(cost_per_success) if cost_per_success is not None else None,
            "verified_business_value": str(_money(verified_value_total)),
            "roi": roi, "roi_reason": roi_reason,
            "loss_events": str(_money(loss_total)),
        },
        "tasks": rows,
        "allocation": allocation_details,
        "unallocated": unallocated,
        "findings": findings,
        "outcomes": outcome_rows,
        "loss_events": loss_rows,
        "boundary": (
            "Local deterministic calculation only. Costs are attributable only when "
            "task/run linkage and financial source are explicit; unallocated items are "
            "not zero. ROI requires verified value in the same currency and period. "
            "Simulated savings and estimated value are not realized benefits."
        ),
    }
    return result


def load_case(path: str) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EconomicsError("case file must contain an object")
    return data


def report_text(result: Dict[str, Any]) -> str:
    total = result["totals"]
    lines = [
        "Verovo task economics",
        "case: %s | currency: %s | period: %s..%s" % (
            result["case_id"], result["currency"],
            result["period"].get("start"), result["period"].get("end")),
        "",
        "Coverage: %s" % json.dumps(result["coverage"], ensure_ascii=False, sort_keys=True),
        "Fully loaded cost: %s %s" % (result["currency"], total["fully_loaded_cost"]),
        "Verified successful tasks: %s" % total["verified_success_tasks"],
        "Cost per verified success: %s" % (
            ("%s %s" % (result["currency"], total["cost_per_verified_success"]))
            if total["cost_per_verified_success"] is not None else "unavailable (no verified success)"),
        "ROI: %s" % (total["roi"] if total["roi"] is not None else "null (%s)" % total["roi_reason"]),
        "Loss events: %s %s" % (result["currency"], total["loss_events"]),
        "",
        "Tasks:",
        "task_id\ttype\tdirect\tallocated\tfully_loaded\tverified_success\tverified_value",
    ]
    for row in result["tasks"]:
        lines.append("%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
            row["task_id"], row["type"], row["direct_cost"], row["allocated_cost"],
            row["fully_loaded_cost"], row["verified_success"],
            row["verified_value"] if row["verified_value"] is not None else "unknown"))
    if result["unallocated"]:
        lines += ["", "Unallocated (not zero):"]
        for row in result["unallocated"]:
            lines.append("- %s %s: %s" % (row["kind"], row["id"], row["reason"]))
    if result["findings"]:
        lines += ["", "Findings:"]
        for row in result["findings"]:
            lines.append("- [%s] %s" % (row["code"], row["message"]))
    lines += ["", result["boundary"]]
    return "\n".join(lines)


def report_markdown(result: Dict[str, Any]) -> str:
    total = result["totals"]
    lines = [
        "# Task economics — %s" % result["case_id"], "",
        "- Currency: `%s`" % result["currency"],
        "- Period: `%s..%s`" % (result["period"].get("start"), result["period"].get("end")),
        "- Fully loaded cost: **%s %s**" % (result["currency"], total["fully_loaded_cost"]),
        "- Verified success tasks: **%s**" % total["verified_success_tasks"],
        "- Cost per verified success: **%s**" % (
            ("%s %s" % (result["currency"], total["cost_per_verified_success"]))
            if total["cost_per_verified_success"] is not None else "unavailable"),
        "- ROI: **%s**" % (total["roi"] if total["roi"] is not None else "null"),
        "- Loss events: **%s %s**" % (result["currency"], total["loss_events"]),
        "", "## Coverage", "", "| Item | Count |", "|---|---|",
    ]
    for key, value in result["coverage"].items():
        lines.append("| %s | %s |" % (key, value))
    lines += ["", "## Tasks", "",
              "| Task | Type | Direct | Allocated | Fully loaded | Verified success | Verified value |",
              "|---|---|---|---|---|---|---|"]
    for row in result["tasks"]:
        lines.append("| {task} | {type} | {direct} | {alloc} | {full} | {ok} | {value} |".format(
            task=row["task_id"], type=row["type"], direct=row["direct_cost"],
            alloc=row["allocated_cost"], full=row["fully_loaded_cost"],
            ok=row["verified_success"], value=row["verified_value"] or "unknown"))
    if result["unallocated"]:
        lines += ["", "## Unallocated (not zero)", ""]
        for row in result["unallocated"]:
            lines.append("- `%s/%s`: %s" % (row["kind"], row["id"], row["reason"]))
    if result["findings"]:
        lines += ["", "## Findings", ""]
        for row in result["findings"]:
            lines.append("- `%s`: %s" % (row["code"], row["message"]))
    lines += ["", "## Boundary", "", result["boundary"], ""]
    return "\n".join(lines)
