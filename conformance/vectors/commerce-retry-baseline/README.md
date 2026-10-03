# Commerce retry baseline (F2.4) — the canonical agent-commerce case

create_order times out, the agent retries, the retry succeeds. The merchant
receives two requests, books one order, takes one payment — and refunds it
two days later.

Correct metering (AMS-1 semantics, Operation != Attempt):

    1 Operation / 2 Attempts / 1 verified order / net GMV = 0

The naive request-counting dashboard reports 120.00 of GMV that does not
exist — a 100% discrepancy, economically material. The runner recomputes the
receipt from the sandbox fixtures and pins every number in `expected.json`.
