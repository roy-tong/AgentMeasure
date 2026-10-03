#!/usr/bin/env python3
"""Commerce retry baseline vector (F2.4) — the canonical agent-commerce case.

1 Operation / 2 Attempts / 1 verified order / net GMV = 0. The runner
recomputes the receipt from the sandbox fixtures and pins every number in
expected.json, including the materiality line: the naive dashboard claims
120.00 that does not exist (100% discrepancy). A drift in the retry
semantics, the refund deduction, or the evidence grading fails CI.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "healthcheck"))

from am_healthcheck import commerce as commerce_mod  # noqa: E402


def main() -> int:
    fixtures = ROOT / "healthcheck" / "am_healthcheck" / "fixtures" / "commerce"
    schema = json.loads(
        (ROOT / "schemas" / "commerce-profile.schema.json").read_text(encoding="utf-8"))
    expected = json.loads(
        (ROOT / "conformance" / "vectors" / "commerce-retry-baseline" /
         "expected.json").read_text(encoding="utf-8"))["expected"]

    events = commerce_mod.load_events(
        str(fixtures / "agent-events.jsonl"), schema)
    orders = commerce_mod.load_orders(str(fixtures / "merchant-orders.csv"))
    payments = commerce_mod.load_payments(
        str(fixtures / "merchant-payments.csv"))
    receipt = commerce_mod.reconcile(
        events, orders, payments, policy_version="1.0.0",
        inputs={"agent-events.jsonl": commerce_mod._sha256_of(
                    str(fixtures / "agent-events.jsonl")),
                "merchant-orders.csv": commerce_mod._sha256_of(
                    str(fixtures / "merchant-orders.csv")),
                "merchant-payments.csv": commerce_mod._sha256_of(
                    str(fixtures / "merchant-payments.csv"))})

    m = receipt["materiality"]
    actual = {
        "operations": receipt["operations"],
        "attempts_by_operation": receipt["attempts_by_operation"],
        "verified_orders": (receipt["verified_orders"]
                            - len([l for l in receipt["links"]
                                   if l["evidence_level"] in ("correlated",
                                                              "inferred")])),
        "duplicate_rows": len(receipt["duplicate_rows"]),
        "gross": dict((x["metric"], x["value"]) for x in receipt["metrics"]
                      )["observed_gross_gmv"],
        "refunded": dict((x["metric"], x["value"]) for x in receipt["metrics"]
                         )["observed_refunded_total"],
        "net": dict((x["metric"], x["value"]) for x in receipt["metrics"]
                    )["net_gmv_strong"],
        "incremental_value": None,
        "naive_net": m["naive_net"],
        "discrepancy": m["discrepancy"],
        "discrepancy_pct": m["discrepancy_pct"],
    }

    failures = []
    for key, want in expected.items():
        got = actual.get(key)
        if got != want:
            failures.append("  %s: expected %r, got %r" % (key, want, got))
    if failures:
        print("commerce-retry-baseline FAILED:")
        print("\n".join(failures))
        return 1
    print("commerce-retry-baseline: 1 Operation / 2 Attempts / 1 verified "
          "order / net GMV = 0 — reproduced")
    print("materiality: naive %s vs verified %s (%.0f%% discrepancy, "
          "economically material)" % (m["naive_net"], m["verified_net"],
                                      abs(m["discrepancy_pct"]) * 100))
    return 0


if __name__ == "__main__":
    sys.exit(main())
