# AgentMeasure lab schema ↔ iwasinnam hop-replay ledger mapping

Date: 2026-09-23

Status: external worked example contributed in BerriAI/litellm#39057 by
iwasinnam2 (Ivan), sanitized (request id redacted, numbers a worked example
against the real formulae). Project-authored projection into the
`agentmeasure.lab/funnel-event` schema; no external run executed.

## Provenance

- Upstream thread: BerriAI/litellm#39057 (comment by iwasinnam2, 2026-09-22)
- Contributor offered the vector for use as fixture + PR ("Happy for you to
  take it as the fixture + PR")

## Semantics being pinned

1. **Three-column non-collapse**: served_tokens / provider_consumed_tokens /
   billable_units are independent. On the hop replay (request-2, cache hit)
   provider_consumed is 0 while served stays 2347 and billable stays
   ceil(2347/1000) = 3.
2. **pipe_usd is the billed rail**: > 0 on the hit (0.006 = 3 × $0.002 hit
   rate). Zeroing "spend" wholesale would zero the one column actually billed.
3. **estimated_provider_usd is a hit-only counterfactual**: structurally > 0
   on every hit, exactly 0 on the miss. Asserting 0 on the miss catches the
   tempting-but-wrong implementation that fills the column on every row.
4. **Upstream prompt-cache discount sits on a separate rail** (request-3
   shape: nonzero upstream-cache leg AND discounted billable) and must never
   be summed with the hop-replay figure.

## litellm-side follow-up

A PR against litellm's cost-tracking path mapping these assertions onto
`litellm` proxy cost tests is tracked in the upstream thread; the vector here
is the implementation-independent record of the agreed semantics.
