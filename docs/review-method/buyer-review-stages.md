# Buyer review stages — Intake → Source Check → Rule Resolution → Reconciliation → Delivery Assessment → Buyer Decision

> The six stages a buyer review walks through, which command serves each stage,
> and what stays human. The staging is a map over existing commands, not a new
> pipeline: every stage either runs a shipped command or records a decision.
> Conclusion levels (rule consistency / evidence credibility / buyer decision)
> are defined in `verovo_healthcheck/review.py` and rendered in every review
> report; this page is their operating procedure.

## Stage map

| Stage | Question | Tool (deterministic) | Human part |
| --- | --- | --- | --- |
| 1. Intake | What is being reviewed, for whom, by when, to what decision? | `verovo review --init <task.json>` writes the deliberately incomplete task template | Fill `scope` (buyer, service, account/task, period, **decision**, owner, due date); an empty scope is not a review |
| 2. Source Check | Are the inputs complete, local and attributable? | `review` reads each evidence file once, records SHA-256, turns missing/null/wrong-type observations into per-criterion `UNPROVABLE` | Obtain authorized exports (invoice JSON, usage records, delivery logs); a gap stays a gap — never fill it |
| 3. Rule Resolution | Which pricing/delivery rules apply, at which version? | `basis {kind, ref, version}` is required per criterion; `kind` must be `billing_rule` (charges) or `buyer_requirement` (delivery) | Supply the rule reference from the contract; optionally record `confirmed_by/confirmed_at` when a human has confirmed applicability — the report echoes it, never infers it |
| 4. Reconciliation | Does the bill/usage match the rules on independent recount? | `verovo recount` (Tier 1: the vendor's own published rules on your counts-only export), `verovo crosscheck` (export vs billing ledger, disagreements named not resolved), `buyer-ledger/` for multi-platform tool bills | Choose the rule version; interpret disagreement lists |
| 5. Delivery Assessment | Did the service meet the buyer's stated requirements? | `review` delivery lane: each `buyer_requirement` criterion vs local observations, PASS/FAIL/UNPROVABLE per criterion | Write requirements as measurable criteria before looking at observations; a passing charge lane never masks a failing delivery lane |
| 6. Buyer Decision | Pay / pay under protest / demand evidence / dispute / remediate? | **No command decides this.** `verovo decisions` records what the buyer actually decided, next to the review result | The buyer (or named owner from `scope.decision`) decides; Level 3 in the report's conclusion levels points here explicitly |

## Reading the output

- Per-criterion verdicts and per-lane rollups (charges / delivery stay separate;
  an unselected lane is `NOT_REVIEWED`, an evidence gap makes a lane `UNPROVABLE`,
  never `PASS`).
- **Conclusion levels**: the run establishes Level 1 (rule consistency) only.
  Level 2 (evidence credibility — rule applicability confirmations, third-party
  corroboration, coverage) is reported as not established, with the count of
  human-confirmed criteria. Level 3 (the buyer business decision) is outside
  the tool.
- The `boundary` line travels with every report: verdicts apply only to supplied
  criteria and local observations; delivery failure is not proof of incorrect
  billing or a refund; no money is summed, recovered or approved.

## Related

- Input guide: `docs/buyer-review.md`
- Free-run procedure for provider-side checks: `docs/review-method/run-book.md`
- Dispute & Recovery Pack: `verovo dispute` (negotiable deliverable; Tier 1 vendor
  rules / Tier 2 Verovo settlement standard), realized corrections via `verovo recovery`
