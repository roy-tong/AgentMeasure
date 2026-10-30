# Case note: VibeMirror-coder-001 — what a free measurement check found, and what it could not prove

Published 2026-10-30 with the permission of **HumanMirror / @VibeMirror-coder**
(Jamenbin AUCS, operated for HumanMirror). This note uses only the
already-public synthetic fixture and the independent re-measurement — no
private data, wallet identities, or additional telemetry.

> **Claim boundary (contributor's statement, verbatim): synthetic, provider-side, Base x402.**
> The 56 canonical observations, 15 challenges, 13 validated settlements, and
> 30/30 expected assertions below describe **the synthetic fixture and its
> verification** — not live HumanMirror traffic, external customer payments,
> production integration, certification, or an endorsement. The 0.022 USDC
> sidecar sum is a *synthetic scenario value*, not actual revenue. Buyer-side
> use, retry linkage, and real-world effect remain unprovable from this
> provider surface.

## What the check was

A provider-side x402 gateway surface, submitted 2026-10-21 via the free
measurement lane (issue #6) as a 56-row canonical event file plus a 32-row
provider-native sidecar and the submitter's own expected assertions.
Format gate: `schemas/validate_jsonl.py` → exit 0 (56/56). The independent
re-measurement counted only from the canonical file and priced only from
sidecar settlement rows: **30/30 `must_assert` items matched.**

## What safely counted (from the data)

- 15 challenges presented; 13 validated settlements = 13 billable units
  ("validated x402 call"); 13 attempts, 0 dangling
- outcomes: 11 success / 1 failure (`upstream_timeout`) / 1 unknown
  (`unmapped_termination`)
- 2 challenges abandoned at payment presentation — **0 attempts inflated**
- revenue from sidecar prices only: 0.001 × 4 (`safe_preflight`) +
  0.002 × 9 (`action.release`) = 0.022 USDC on Base *(synthetic scenario value)*

## Where inflation could enter (observed, not claimed)

Two same-payer same-tool settlement pairs inside a 120-second window:
`pay-06 → pay-07` (89s apart; first attempt `upstream_timeout`, then settled
again) and `pay-08 → pay-09` (92s apart; two successes). On a per-call
billable unit, the first shape is the double-billing case — on this surface it
is indistinguishable from two intended calls, so it stays a grouping
observation, never an overcharge claim.

## What could not be proven (UNPROVABLE — absence carried, never converted to zero)

`settlement_grouping`, `retry_linkage`, `operation_resolution`
(operation_id 0/13, retry_of 0/13, coverage 0.0),
`advisory_selection_rate` (2 observed selections is a lower bound; 2/4 not
published as a rate), `decision_authority`, `advice_effect_and_agent_action`;
`result_consumption` UNOBSERVABLE (absent, not zero).

The absence itself was measurable: no field on this surface made a retry
visible, and the check records that as 0/13 presence — not as
`retry_inflation = 0`.

## One correction, by invitation

Under the submitter's negative-results policy, the delivery prose named the
two-successes pair as `exec-req-12/14`; in the data that pair is
`pay-08 → pay-09` (92s, same payer, same tool). `pay-12` and `pay-14` are
different payers, different tools, 45 minutes apart. Every `expected.json`
value was correct as written; only the prose example ids were off — recorded
here because the correction was invited, and because a check that cannot be
corrected is not a check.

## Reproduce it yourself

- Public fixture (unchanged, sha256-guarded): [`conformance/external/VibeMirror-coder-001/`](../../conformance/external/VibeMirror-coder-001/)
- Original check as delivered: [issue #6 comment](https://github.com/roy-tong/AgentMeasure/issues/6#issuecomment-6328758564)
- Method, run-book, and both report templates: [docs/review-method/](./README.md)

Runs like this are free — bring 20–100 sanitized rows to issue #6. If the
check was useful, a star on the repo helps others find it — never required,
never a condition.
