"""对账引擎：按账户/币种隔离，审查不完整或估算不完整时不出确定性差额。"""

import datetime
from decimal import Decimal
from typing import List

from .model import LedgerError, VERIFIED
from .store import LedgerStore

CLS_MATCHED = "matched"
CLS_OVERCHARGE_SUSPECTED = "overcharge_suspected"
CLS_UNDERCHARGE = "undercharge_observed"
CLS_ESTIMATE_ONLY = "estimate_only"
CLS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
CLS_UNPRICED_USAGE = "usage_unpriced"
CLS_ESTIMATE_INCOMPLETE = "estimate_incomplete"
CLS_REVIEW_REQUIRED = "review_required"

DEFAULT_TOLERANCE_ABS = "0.01"
DEFAULT_TOLERANCE_REL = "0.005"


def _d(value) -> Decimal:
    return Decimal(str(value)) if value not in (None, "") else Decimal("0")


def _validate_period(period):
    try:
        datetime.date.fromisoformat(period + "-01")
    except (ValueError, TypeError):
        raise LedgerError("period must be YYYY-MM; cross-period reconciliation is not allowed")
    if len(period) != 7:
        raise LedgerError("period must be YYYY-MM")


def classify(bill_total, recount_total, tolerance_abs, tolerance_rel):
    if bill_total is None and recount_total is None:
        return CLS_INSUFFICIENT_EVIDENCE, None
    if bill_total is None:
        return CLS_ESTIMATE_ONLY, None
    if recount_total is None:
        return CLS_INSUFFICIENT_EVIDENCE, None
    variance = bill_total - recount_total
    tol = max(tolerance_abs, abs(recount_total) * tolerance_rel)
    if abs(variance) <= tol:
        return CLS_MATCHED, variance
    return (CLS_OVERCHARGE_SUSPECTED, variance) if variance > 0 \
        else (CLS_UNDERCHARGE, variance)


def link_lines_to_usage(charge_lines: List[dict], usage_events: List[dict]):
    """只在同一账户/币种分组内做保守关联；无法关联的项显式披露。"""
    by_key = {}
    for ue in usage_events:
        key = (ue.get("tool") or ue.get("capability") or "", ue.get("billable_unit"))
        by_key.setdefault(key, []).append(ue)
    linked_charges, unlinked_charges = [], []
    for cl in charge_lines:
        if not cl.get("tool"):
            unlinked_charges.append(cl)
            continue
        key = (cl["tool"], cl.get("unit") or "")
        if key in by_key or (cl["tool"], "") in by_key:
            linked_charges.append(cl)
        else:
            unlinked_charges.append(cl)
    linked_usage_ids = set()
    for cl in linked_charges:
        for key in ((cl["tool"], cl.get("unit") or ""), (cl["tool"], "")):
            for ue in by_key.get(key, []):
                linked_usage_ids.add(ue["id"])
    unlinked_usage = [ue for ue in usage_events if ue["id"] not in linked_usage_ids]
    return linked_charges, unlinked_charges, unlinked_usage


def _pricing_provenance_valid(store, event):
    ref = event.get("pricing_policy_id") or ""
    if not ref or event.get("computed_charge") in (None, ""):
        return False
    policy = store.find_policy(
        event["provider"], event.get("capability") or event.get("tool") or "",
        at=event.get("occurred_at") or event["period"])
    if not policy or ref != policy.policy_id + "@" + policy.version:
        return False
    if policy.currency != event.get("currency"):
        return False
    if policy.model == "per_unit":
        expected, _ = policy.charge_for(Decimal(event["quantity"]))
        return expected == Decimal(event["computed_charge"])
    # quota/tier 的金额由周期聚合管线分配；这里核验政策链， flat/subscription 不接受。
    return policy.model in ("free_quota", "volume_tiered")


def reconcile(store: LedgerStore, period: str,
              tolerance_abs=DEFAULT_TOLERANCE_ABS,
              tolerance_rel=DEFAULT_TOLERANCE_REL):
    """按 provider+account+currency 原子替换一个账期的完整对账快照。"""
    _validate_period(period)
    tol_abs, tol_rel = _d(tolerance_abs), _d(tolerance_rel)
    charge_lines = store.effective_charge_lines(period=period)
    usage_events = store.effective_usage_events(period=period)
    documents = {d["id"]: d for d in store.list_documents()}

    groups = {}
    charge_currencies = {}
    for line in charge_lines:
        account = documents[line["document_id"]]["account_ref"]
        scope = (line["provider"], account)
        charge_currencies.setdefault(scope, set()).add(line["currency"])
        key = scope + (line["currency"],)
        groups.setdefault(key, {"charges": [], "usage": []})["charges"].append(line)
    for event in usage_events:
        account = event.get("account_ref") or documents[event["document_id"]]["account_ref"]
        scope = (event["provider"], account)
        currencies = charge_currencies.get(scope, set())
        currency = event.get("currency") or (
            next(iter(currencies)) if len(currencies) == 1 else "")
        key = scope + (currency,)
        groups.setdefault(key, {"charges": [], "usage": []})["usage"].append(event)

    # 已登记但尚未形成账本行的材料同样是覆盖缺口，不能让旧数据继续 matched。
    unparsed_by_scope = {}
    for doc in store.list_documents(period=period):
        if doc["tier"] not in ("bill_fact", "platform_usage"):
            continue
        if store.count_rows_for_document(doc["id"]) == 0:
            scope = (doc["provider"], doc["account_ref"])
            unparsed_by_scope.setdefault(scope, []).append(doc)
    for scope in unparsed_by_scope:
        if not any(key[:2] == scope for key in groups):
            groups[scope + ("",)] = {"charges": [], "usage": []}

    results = []
    try:
        # 旧快照只在完整新快照成功后一并替换；失败则整体回滚。
        store.conn.execute("DELETE FROM reconciliation WHERE period=?", (period,))
        for key in sorted(groups):
            provider, account_ref, currency = key
            p_lines = groups[key]["charges"]
            p_usage = groups[key]["usage"]
            bill_total = sum((Decimal(c["amount"]) for c in p_lines), Decimal("0")) \
                if p_lines else None
            candidates = [u for u in p_usage if u.get("computed_charge") not in (None, "")]
            priced = [u for u in candidates if _pricing_provenance_valid(store, u)]
            invalid_pricing = [u for u in candidates if u not in priced]
            recount_total = sum((Decimal(u["computed_charge"]) for u in priced), Decimal("0")) \
                if priced else None
            unpriced = [u for u in p_usage if u.get("computed_charge") in (None, "")]
            by_unit = {}
            for event in unpriced:
                unit = event["billable_unit"]
                by_unit[unit] = by_unit.get(unit, Decimal("0")) + Decimal(event["quantity"])
            unpriced_qty = None
            if len(by_unit) == 1:
                unpriced_qty = str(next(iter(by_unit.values())))
            elif not by_unit:
                unpriced_qty = "0"

            pending_charges = [c for c in p_lines if c["review_status"] != VERIFIED]
            pending_usage = [u for u in p_usage if u["review_status"] != VERIFIED]
            unparsed_docs = unparsed_by_scope.get((provider, account_ref), [])
            review_required = bool(
                pending_charges or pending_usage or unparsed_docs or invalid_pricing)
            recount_complete = not unpriced and not invalid_pricing and not any(
                d["tier"] == "platform_usage" for d in unparsed_docs)
            if review_required:
                variance_class, variance = CLS_REVIEW_REQUIRED, None
            elif priced and unpriced:
                # 已计价小计可以展示，但绝不能与完整账单形成正式差额。
                variance_class, variance = CLS_ESTIMATE_INCOMPLETE, None
            else:
                variance_class, variance = classify(
                    bill_total, recount_total, tol_abs, tol_rel)
                if variance_class == CLS_INSUFFICIENT_EVIDENCE and unpriced:
                    variance_class = CLS_UNPRICED_USAGE

            linked_c, unlinked_c, unlinked_u = link_lines_to_usage(p_lines, p_usage)
            detail = {
                "bill_fact_lines": len(p_lines),
                "usage_events": len(p_usage),
                "priced_usage_events": len(priced),
                "unpriced_usage_qty": unpriced_qty,
                "unpriced_usage_by_unit": {k: str(v) for k, v in sorted(by_unit.items())},
                "recount_complete": recount_complete,
                "linked_charge_lines": len(linked_c),
                "unlinked_charge_lines": [
                    {"id": c["id"], "description": c["description"], "amount": c["amount"]}
                    for c in unlinked_c],
                "unlinked_usage_events": [
                    {"id": u["id"], "tool": u["tool"], "quantity": u["quantity"],
                     "unit": u["billable_unit"]}
                    for u in unlinked_u],
                "review_pending_lines": sum(
                    1 for c in p_lines if c["review_status"] == "pending"),
                "undeterminable_lines": sum(
                    1 for c in p_lines if c["review_status"] == "undeterminable"),
                "review_pending_usage": sum(
                    1 for u in p_usage if u["review_status"] != VERIFIED),
                "unparsed_documents": [
                    {"id": d["id"], "tier": d["tier"], "file_name": d["file_name"]}
                    for d in unparsed_docs],
                "invalid_pricing_events": [u["id"] for u in invalid_pricing],
                "tiers_present": {
                    "bill_fact": bool(p_lines), "platform_usage": bool(p_usage),
                    "recount": recount_total is not None,
                },
            }
            store.put_reconciliation(
                period, provider, account_ref=account_ref, bill_total=bill_total,
                recount_total=recount_total, variance=variance,
                variance_class=variance_class, detail=detail, currency=currency,
                commit=False)
            results.append({
                "period": period, "provider": provider, "account_ref": account_ref,
                "currency": currency,
                "bill_total": None if bill_total is None else str(bill_total),
                "recount_total": None if recount_total is None else str(recount_total),
                "recount_complete": recount_complete,
                "variance": None if variance is None else str(variance),
                "variance_class": variance_class,
                "detail": detail,
            })
        store.conn.commit()
    except Exception:
        store.conn.rollback()
        raise
    return results


def apply_pricing(store: LedgerStore, provider: str, period: str):
    """按事件日选择唯一有效政策；quota/tier 在同一计费作用域内按账期聚合。"""
    _validate_period(period)
    documents = {d["id"]: d for d in store.list_documents()}
    resolved, skipped = [], 0
    stale_ids = set()
    for event in store.effective_usage_events(period=period, provider=provider):
        at = event.get("occurred_at") or period
        policy = store.find_policy(
            provider, event.get("capability") or event.get("tool") or "", at=at)
        if policy is None:
            skipped += 1
            if event.get("computed_charge") not in (None, "") or event.get("pricing_policy_id"):
                stale_ids.add(event["id"])
            continue
        resolved.append((event, policy))

    aggregate_groups = {}
    for event, policy in resolved:
        if policy.model not in ("free_quota", "volume_tiered"):
            continue
        account = event.get("account_ref") or documents[event["document_id"]]["account_ref"]
        key = (policy.policy_id, policy.version, policy.capability, account,
               event["billable_unit"], policy.currency)
        aggregate_groups.setdefault(key, []).append((event, policy))

    aggregate_charges = {}
    aggregate_blocked = set()
    for key, items in aggregate_groups.items():
        quantities = [Decimal(e["quantity"]) for e, _ in items]
        if any(q < 0 for q in quantities):
            # 聚合政策与冲销的交互尚需独立分配规则，不能用猜测金额覆盖历史。
            aggregate_blocked.add(key)
            continue
        policy = items[0][1]
        if policy.model == "volume_tiered":
            total = sum(quantities, Decimal("0"))
            rate = policy.tier_unit_price(total)
            for event, _ in items:
                charge = None if rate is None else Decimal(event["quantity"]) * rate
                aggregate_charges[event["id"]] = (
                    charge, rate, "volume tier on period total %s" % total)
        else:
            remaining = Decimal(policy.free_quota)
            for event, _ in sorted(items, key=lambda x: (x[0]["occurred_at"], x[0]["id"])):
                quantity = Decimal(event["quantity"])
                free = min(quantity, remaining)
                remaining -= free
                overage = quantity - free
                if overage and not policy.unit_price:
                    charge = None
                else:
                    charge = overage * Decimal(policy.unit_price or "0")
                aggregate_charges[event["id"]] = (
                    charge, policy.unit_price if overage else "",
                    "period free quota; overage quantity %s" % overage)

    updated = 0
    try:
        for event_id in stale_ids:
            store.conn.execute(
                "UPDATE usage_event SET computed_charge=NULL, unit_price_applied='', "
                "currency='', pricing_policy_id='', "
                "note='no unique applicable policy; previous estimate withdrawn' WHERE id=?",
                (event_id,))
        for event, policy in resolved:
            account = event.get("account_ref") or documents[event["document_id"]]["account_ref"]
            key = (policy.policy_id, policy.version, policy.capability, account,
                   event["billable_unit"], policy.currency)
            if key in aggregate_blocked:
                skipped += 1
                if event.get("computed_charge") not in (None, "") or event.get("pricing_policy_id"):
                    stale_ids.add(event["id"])
                continue
            if policy.model in ("free_quota", "volume_tiered"):
                charge, applied_rate, note = aggregate_charges[event["id"]]
            else:
                charge, note = policy.charge_for(Decimal(event["quantity"]))
                applied_rate = policy.unit_price if policy.model in ("per_unit", "flat") else ""
            if charge is None:
                skipped += 1
                if event.get("computed_charge") not in (None, "") or event.get("pricing_policy_id"):
                    stale_ids.add(event["id"])
                continue
            store.conn.execute(
                "UPDATE usage_event SET computed_charge=?, unit_price_applied=?, "
                "currency=?, pricing_policy_id=?, note=? WHERE id=?",
                (str(charge), str(applied_rate) if applied_rate not in (None, "") else "",
                 policy.currency,
                 policy.policy_id + "@" + policy.version, note, event["id"]))
            updated += 1
        store.conn.commit()
    except Exception:
        store.conn.rollback()
        raise
    return {"updated": updated, "skipped_no_policy_or_rule": skipped,
            "withdrawn_stale_estimates": len(stale_ids)}
