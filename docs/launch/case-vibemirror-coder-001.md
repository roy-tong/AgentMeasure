# Case card: VibeMirror-coder-001 — an independent re-measurement, and what it could not prove

**What it is:** a third-party measurement check delivered through the free lane
(issue #6), published as a case note on 2026-10-30 with the submitter's
permission (HumanMirror / @VibeMirror-coder, Jamenbin AUCS, operated for
HumanMirror).
**Full case note:** [docs/review-method/case-note-VibeMirror-coder-001.md](../review-method/case-note-VibeMirror-coder-001.md)
**Reproduce it:** [conformance/external/VibeMirror-coder-001/](../../conformance/external/VibeMirror-coder-001/) (public, sha256-guarded fixture)

> **Claim boundary (contributor's statement, verbatim): synthetic, provider-side, Base x402.**
> The numbers below describe the synthetic fixture and its verification — not
> live traffic, external customer payments, production integration,
> certification, or an endorsement.

## What was submitted and checked

A provider-side x402 gateway surface arrived 2026-10-21 via issue #6 as a
56-row canonical event file plus a 32-row provider-native sidecar and the
submitter's own expected assertions. The format gate
(`schemas/validate_jsonl.py`) passed 56/56 rows. The independent
re-measurement counted only from the canonical file and priced only from
sidecar settlement rows: **30 of 30 `must_assert` items matched.**

Counted safely from the data: 15 challenges presented; 13 validated
settlements, each one a billable unit ("validated x402 call"); 13 attempts
with 0 dangling; outcomes 11 success / 1 failure (`upstream_timeout`) / 1
unknown (`unmapped_termination`); 2 challenges abandoned at payment
presentation, inflating nothing. Settlement prices sum to 0.022 USDC on Base —
a synthetic scenario value, not revenue.

## The two findings that matter more than the totals

**Absence stayed absence.** `settlement_grouping`, `retry_linkage` and
`operation_resolution` could not be judged (operation_id 0/13, retry_of 0/13,
coverage 0.0), so they stayed UNPROVABLE — recorded as "no field on this
surface makes a retry visible," never converted to `retry_inflation = 0`.
`result_consumption` was UNOBSERVABLE, which is a fact about the surface, not
a zero.

**The check was corrected, by invitation.** The delivery prose originally
named the two-successes pair as `exec-12/14`; in the data that pair is
`pay-08 → pay-09` (92 seconds apart, same payer, same tool). Every expected
value was correct as written; only the prose example ids were off. A check
that cannot be corrected is not a check.

## What this case does not establish

No live traffic, no external customer payments, no production integration, no
certification, no endorsement, and no buyer-side effect — buyer-side use,
retry linkage and real-world effect remain unprovable from this provider
surface. This card is evidence that the method runs end to end on
third-party data and reports its own limits, nothing further.

## Sources (all in this repository)

| Claim | Source | Date |
|---|---|---|
| 56-row canonical file; 56/56 format gate; 30/30 `must_assert` matched | [case note](../review-method/case-note-VibeMirror-coder-001.md) | published 2026-10-30 |
| 15 challenges; 13 validated settlements; 13 attempts, 0 dangling; 11/1/1 outcomes; 2 abandoned; 0.022 USDC (synthetic) | [case note](../review-method/case-note-VibeMirror-coder-001.md) | 2026-10-30 |
| UNPROVABLE / UNOBSERVABLE list; prose-id correction `pay-08 → pay-09` | [case note](../review-method/case-note-VibeMirror-coder-001.md) | 2026-10-30 |
| Public sha256-guarded fixture | [conformance/external/VibeMirror-coder-001/](../../conformance/external/VibeMirror-coder-001/) | submitted 2026-10-21 |
| Free lane: 20–100 sanitized rows via issue #6 | [case note](../review-method/case-note-VibeMirror-coder-001.md), closing note | 2026-10-30 |
