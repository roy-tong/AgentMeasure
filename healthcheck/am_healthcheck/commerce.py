"""Agent Commerce Measurement — where the click disappears (F2.1-F2.9).

Traditional attribution starts at the click. Agent commerce has no click: the
agent calls a tool, creates an order, retries on timeout, pays, refunds. This
module measures that chain from the MERCHANT side (M1A — our own observation
surface; platform-side M1B is accepted as input when present, never required).

What it enforces, per the requirements pool (Agent-Commerce-Measurement
2026-10-03):

- F2.1  live / replay / synthetic are segregated at aggregation time: one
        mixed-mode call is an ERROR, not a blend. Synthetic lab probes never
        touch production aggregates.
- F2.2  decision observations carry observed_merchants — never a candidate_set
        (the schema forbids the fiction).
- F2.3  every attribution link gets one of four evidence levels, assigned by
        named rules: observed / correlated / inferred / UNPROVABLE.
- F2.4  retries reconcile: N attempts under ONE operation produce ONE verified
        order; the merchant's request log that says otherwise is the naive
        view, quantified in materiality.
- F2.5  the receipt: metric + value + evidence per row — invocations
        (merchant-observed), verified orders (direct mapping), net GMV
        (strong), assisted orders (correlated), incremental (UNPROVABLE, and
        the only honest value for it is null).
- F2.6  metric names carry their strength as a prefix; a name whose claimed
        strength exceeds its evidence is a lint failure.
- F2.7  governance: policy version required on every record (mixed versions
        refused); the receipt anchors the exact input bytes by sha256 — the
        raw evidence this receipt describes cannot be silently swapped.
- F2.8  merchant-side connector: documented generic CSV shapes for order and
        payment/refund logs (sandbox fixtures ship with the package).
- F2.9  materiality: the naive dashboard view vs the verified ledger, the
        discrepancy in currency AND percent, split by named category. Below
        ~0.3% the honest line prints: measurement error this small is nobody's
        business.
"""
from __future__ import annotations

import csv
import hashlib
import json
from typing import Any, Dict, List, Optional

from .outcomes import validate_schema

RECEIPT_SCHEMA = "agentmeasure.commerce/measurement-receipt"
RECEIPT_VERSION = "0.1.0"

EVIDENCE_STRENGTH = {"UNPROVABLE": 0, "inferred": 1, "correlated": 2,
                     "observed": 3}
NAME_STRENGTH = {"incremental": 0, "inferred": 1, "correlated": 2,
                 "observed": 3, "strong": 3}
MATERIALITY_FLOOR = 0.003  # below this, measurement is nobody's business


class CommerceError(ValueError):
    """Refusals: mixed observation modes, mixed policy versions, bad input."""


def _sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Loaders (F2.8 merchant-side connector: documented generic shapes)
# ---------------------------------------------------------------------------
def load_events(path: str, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                raise CommerceError("line %d of %s is not valid JSONL"
                                    % (i + 1, path)) from None
            errors = validate_schema(rec, schema)
            if errors:
                raise CommerceError("line %d fails the commerce profile "
                                    "schema: %s" % (i + 1, "; ".join(errors[:3])))
            events.append(rec)
    return events


def load_orders(path: str) -> List[Dict[str, Any]]:
    """Merchant order log: order_id, agent_operation_id, amount, currency,
    status, created_at[, idempotency_key]."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        for required in ("order_id", "amount", "status"):
            if required not in fields:
                raise CommerceError("order log needs a %r column; got: %s"
                                    % (required,
                                       ", ".join(reader.fieldnames or [])))
        rows = []
        for i, row in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            try:
                amount = round(float(row.get("amount", "")), 2)
            except ValueError:
                raise CommerceError("order line %d: amount %r is not a number"
                                    % (i + 2, row.get("amount"))) from None
            rows.append({
                "line": i + 2,
                "order_id": row.get("order_id"),
                "agent_operation_id": row.get("agent_operation_id", ""),
                "amount": amount,
                "currency": row.get("currency", ""),
                "status": row.get("status", ""),
                "created_at": row.get("created_at", ""),
                "idempotency_key": row.get("idempotency_key", ""),
            })
    return rows


def load_payments(path: str) -> List[Dict[str, Any]]:
    """Merchant payment log: payment_id, order_id, amount, type(charge|refund),
    created_at."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        for required in ("order_id", "amount", "type"):
            if required not in fields:
                raise CommerceError("payment log needs a %r column; got: %s"
                                    % (required,
                                       ", ".join(reader.fieldnames or [])))
        rows = []
        for i, row in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            try:
                amount = round(float(row.get("amount", "")), 2)
            except ValueError:
                raise CommerceError("payment line %d: amount %r is not a number"
                                    % (i + 2, row.get("amount"))) from None
            ptype = row.get("type", "")
            if ptype not in ("charge", "refund"):
                raise CommerceError(
                    "payment line %d: type %r must be charge or refund"
                    % (i + 2, ptype))
            rows.append({
                "line": i + 2,
                "payment_id": row.get("payment_id", ""),
                "order_id": row.get("order_id"),
                "amount": amount,
                "type": ptype,
                "created_at": row.get("created_at", ""),
            })
    return rows


# ---------------------------------------------------------------------------
# Governance gates (F2.7) and mode segregation (F2.1)
# ---------------------------------------------------------------------------
def _check_governance(events: List[Dict[str, Any]],
                      policy_version: str) -> Dict[str, Any]:
    modes = sorted({e["observation_mode"] for e in events})
    versions = sorted({e["measurement_policy_version"] for e in events})
    if len(modes) > 1:
        raise CommerceError(
            "mixed observation modes in one aggregation: %s — synthetic "
            "records never enter a production aggregate; split the input"
            % ", ".join(modes))
    if versions and versions != [policy_version]:
        raise CommerceError(
            "measurement_policy_version mismatch: records carry %s, this "
            "receipt is issued under %s — different methodologies are "
            "different receipts" % (versions, policy_version))
    return {"observation_mode": modes[0] if modes else None,
            "measurement_policy_version": policy_version,
            "metric_definitions_frozen": "definitions are frozen under the "
                                         "policy version above; a changed "
                                         "definition is a new version"}


# ---------------------------------------------------------------------------
# Attribution link evidence rules (F2.3) — named rules, attributable grades
# ---------------------------------------------------------------------------
def _grade_invocation_to_order(order: Dict[str, Any],
                               operation_ids: set) -> Dict[str, str]:
    op = (order.get("agent_operation_id") or "").strip()
    if op and op in operation_ids:
        return {"evidence_level": "observed",
                "rule_basis": "order carries an agent_operation_id present in "
                              "the invocation records (direct mapping)"}
    if op:
        return {"evidence_level": "inferred",
                "rule_basis": "order claims an operation id the invocation "
                              "records do not contain"}
    return {"evidence_level": "UNPROVABLE",
            "rule_basis": "no agent origin on the order; the link is assumed "
                          "by nobody"}


# ---------------------------------------------------------------------------
# The reconciliation and the receipt (F2.4/F2.5/F2.9)
# ---------------------------------------------------------------------------
def reconcile(events: List[Dict[str, Any]], orders: List[Dict[str, Any]],
              payments: List[Dict[str, Any]], policy_version: str,
              inputs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    governance = _check_governance(events, policy_version)
    mode = governance["observation_mode"]
    prefix = "synthetic_" if mode == "synthetic" else "observed_"

    operations = {e["operation_id"] for e in events
                  if e.get("operation_id")}
    attempts_by_op: Dict[str, int] = {}
    for e in events:
        if e.get("record_type") == "attempt_event" and e.get("operation_id"):
            attempts_by_op[e["operation_id"]] = \
                attempts_by_op.get(e["operation_id"], 0) + 1
    decisions = [e for e in events if e.get("record_type") == "decision_observation"]

    # Orders: dedupe by idempotency key first, then by order_id. A repeated
    # row is named, not silently summed.
    orders_confirmed = [o for o in orders if o["status"] == "confirmed"]
    seen_keys: Dict[str, Dict[str, Any]] = {}
    duplicate_rows: List[Dict[str, Any]] = []
    verified: List[Dict[str, Any]] = []
    for o in orders_confirmed:
        key = o.get("idempotency_key") or "id:" + str(o["order_id"])
        if key in seen_keys:
            duplicate_rows.append({
                "order_id": o["order_id"],
                "line": o["line"],
                "collapsed_into": seen_keys[key]["order_id"],
                "amount": o["amount"],
                "reason": "duplicate order row (same idempotency key)"
                          if o.get("idempotency_key")
                          else "duplicate order_id in the merchant log"})
            continue
        seen_keys[key] = o
        grade = _grade_invocation_to_order(o, operations)
        o = dict(o)
        o.update(grade)
        verified.append(o)

    charges: Dict[str, List[Dict[str, Any]]] = {}
    refunds: Dict[str, List[Dict[str, Any]]] = {}
    for p in payments:
        bucket = charges if p["type"] == "charge" else refunds
        bucket.setdefault(str(p["order_id"]), []).append(p)
    double_charges: List[Dict[str, Any]] = []
    for oid, plist in sorted(charges.items()):
        if len(plist) > 1:
            double_charges.append({
                "order_id": oid,
                "charges": len(plist),
                "amount": round(sum(p["amount"] for p in plist[1:]), 2),
                "reason": "multiple charges on one verified order"})

    gross = round(sum(o["amount"] for o in verified), 2)
    refunded = round(sum(p["amount"] for plist in refunds.values()
                         for p in plist), 2)
    net = round(gross - refunded, 2)
    assisted = [o for o in verified if o["evidence_level"] in ("correlated",
                                                               "inferred")]

    # Naive dashboard view (F2.9): every confirmed row summed, refunds and
    # duplicates included — what a request-counting dashboard reports.
    naive_gross = round(sum(o["amount"] for o in orders_confirmed), 2)
    naive_net = naive_gross  # the naive view does not deduct refunds
    discrepancy = round(naive_net - net, 2)
    discrepancy_pct = round(discrepancy / naive_net, 4) if naive_net else None
    categories: List[Dict[str, Any]] = []
    if duplicate_rows:
        categories.append({"category": "duplicate_orders",
                           "amount": round(sum(d["amount"] for d in duplicate_rows), 2),
                           "rows": len(duplicate_rows)})
    if double_charges:
        categories.append({"category": "cross_agent_or_retry_double_credit",
                           "amount": round(sum(d["amount"] for d in double_charges), 2),
                           "rows": len(double_charges)})
    if refunded:
        categories.append({"category": "refund_not_deducted",
                           "amount": refunded, "rows": len(refunds)})
    unmapped = [o for o in verified if o["evidence_level"] == "UNPROVABLE"]
    if unmapped:
        categories.append({"category": "invocation_mapping_error",
                           "amount": round(sum(o["amount"] for o in unmapped), 2),
                           "rows": len(unmapped)})

    materiality = {
        "naive_net": naive_net,
        "verified_net": net,
        "discrepancy": discrepancy,
        "discrepancy_pct": discrepancy_pct,
        "denominator": "the naive view — the error is expressed as a share "
                       "of what the dashboard claims",
        "categories": categories,
    }
    if discrepancy_pct is None:
        materiality["reading"] = "no naive revenue to compare against"
    elif abs(discrepancy_pct) < MATERIALITY_FLOOR:
        materiality["reading"] = ("discrepancy %.2f%% is below the 0.3%% "
                                  "materiality floor — measurement error this "
                                  "small is nobody's business; say so"
                                  % (abs(discrepancy_pct) * 100))
    else:
        materiality["reading"] = ("discrepancy %.2f%% is economically "
                                  "material — measurement changes the number "
                                  "the business acts on"
                                  % (abs(discrepancy_pct) * 100))

    # The receipt (F2.5): metric + value + evidence, names linted (F2.6).
    metrics = [
        {"metric": prefix + "invocations", "value": len(operations),
         "evidence": "merchant-observed"},
        {"metric": prefix + "verified_orders",
         "value": len(verified) - len(assisted),
         "evidence": "direct mapping"},
        {"metric": prefix + "gross_gmv", "value": gross,
         "evidence": "observed"},
        {"metric": prefix + "refunded_total", "value": refunded,
         "evidence": "observed"},
        {"metric": "net_gmv_strong", "value": net, "evidence": "strong"},
        {"metric": "assisted_orders_correlated",
         "value": len(assisted), "evidence": "correlated"},
        {"metric": "incremental_gmv_UNPROVABLE", "value": None,
         "evidence": "UNPROVABLE"},
    ]
    for m in metrics:
        problem = lint_metric(m["metric"], m["evidence"])
        if problem:
            raise CommerceError("receipt metric failed the naming lint: %s (%s)"
                                % (m["metric"], problem))

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": RECEIPT_VERSION,
        "governance": governance,
        "input_digests": inputs or {},
        "operations": len(operations),
        "attempts_by_operation": attempts_by_op,
        "decision_observations": len(decisions),
        "verified_orders": len(verified),
        "duplicate_rows": duplicate_rows,
        "double_charges": double_charges,
        "metrics": metrics,
        "links": [
            dict({"link_type": "invocation_to_order",
                  "order_id": o["order_id"]},
                 **{k: o[k] for k in ("evidence_level", "rule_basis")})
            for o in verified],
        "materiality": materiality,
        "claim_rule": "incremental is UNPROVABLE here by construction: this "
                      "receipt has no holdout. Metric strength never exceeds "
                      "evidence strength.",
    }
    return receipt


# ---------------------------------------------------------------------------
# F2.6 — the naming lint
# ---------------------------------------------------------------------------
def lint_metric(name: str, evidence: str) -> Optional[str]:
    """Return a reason string when the metric name claims more strength than
    its evidence carries; None when the name is honest.

    A `synthetic_` mode prefix is its own grade (M0 synthetic observation):
    mode-labelled metrics are honest by construction and skip the strength
    ladder, which exists to stop PRODUCTION metrics overclaiming.
    """
    if evidence not in EVIDENCE_STRENGTH and evidence not in (
            "merchant-observed", "direct mapping", "strong"):
        return "unknown evidence level %r" % evidence
    if name.startswith("synthetic_"):
        return None
    strength = EVIDENCE_STRENGTH.get(
        evidence, EVIDENCE_STRENGTH["observed"])  # merchant-observed/strong
    tokens = [t for t in name.split("_") if t in NAME_STRENGTH]
    if evidence == "UNPROVABLE" and "incremental" not in tokens and "inferred" not in tokens:
        return "UNPROVABLE evidence may only feed incremental_* / inferred_* metrics"
    if not tokens:
        return "metric name carries no strength prefix (observed/correlated/inferred/incremental)"
    claimed = min(NAME_STRENGTH[t] for t in tokens)
    if claimed > strength:
        return ("name claims %r strength but the evidence is %r"
                % (max((t for t in tokens if NAME_STRENGTH[t] == claimed),
                       key=lambda t: NAME_STRENGTH[t]),
                   evidence))
    return None


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def receipt_markdown(receipt: Dict[str, Any]) -> str:
    g = receipt["governance"]
    out = ["# Measurement receipt — agent commerce (M1A merchant-side)", ""]
    out.append("mode: %s · policy v%s · metric definitions frozen under it"
               % (g["observation_mode"], g["measurement_policy_version"]))
    out.append("")
    out.append("| metric | value | evidence |")
    out.append("|---|---:|---|")
    for m in receipt["metrics"]:
        out.append("| `%s` | %s | %s |"
                   % (m["metric"],
                      "—" if m["value"] is None else m["value"],
                      m["evidence"]))
    out.append("")
    out.append("operations: %d · attempts: %s · verified orders: %d"
               % (receipt["operations"],
                  json.dumps(receipt["attempts_by_operation"])
                  if receipt["attempts_by_operation"] else "0",
                  receipt["verified_orders"]))
    if receipt["duplicate_rows"]:
        out.append("")
        out.append("Collapsed duplicate rows: %s"
                   % ", ".join("%s(line %d)" % (d["order_id"], d["line"])
                               for d in receipt["duplicate_rows"][:8]))
    m = receipt["materiality"]
    out.append("")
    out.append("## Materiality — naive dashboard vs verified ledger")
    out.append("")
    out.append("naive net %s vs verified net %s → discrepancy %s (%.2f%%)"
               % (m["naive_net"], m["verified_net"], m["discrepancy"],
                  abs(m["discrepancy_pct"] or 0) * 100))
    for c in m["categories"]:
        out.append("- %s: %s over %d row(s)"
                   % (c["category"], c["amount"], c["rows"]))
    out.append("")
    out.append(m["reading"])
    out.append("")
    out.append(receipt["claim_rule"])
    if receipt["input_digests"]:
        out.append("")
        out.append("Evidence anchors (sha256, immutable inputs):")
        for name, digest in sorted(receipt["input_digests"].items()):
            out.append("- %s `%s…`" % (name, digest[:16]))
    return "\n".join(out)
