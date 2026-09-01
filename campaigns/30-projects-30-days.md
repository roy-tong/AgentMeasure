# 30 Projects / 30 Days — Agent Measurement Conformance Sprint

> Checking how open-source AI infrastructure measures retries, cache hits, token
> subsets, cost grouping, and eval reruns — one project a day.
>
> No rankings. No composite scores. No "who is best."
>
> Every finding is **PASS / FAIL / UNPROVABLE / NOT APPLICABLE**, and every
> claim links to code or a reproducible fixture.

## Why

Labels like `requests`, `tokens`, and `cost` hide different accounting grains.
A retry is one logical operation but two provider calls. A reasoning-token
subset must not be added into its output total. A cache hit is not a new
measurement. Most dashboards cannot tell you which convention their numbers
follow — and two correct numbers under different conventions can disagree by
2–3×.

This sprint asks each project one question:

> **Does your metric mean what its label says — and can your telemetry prove it?**

## Tracker

| # | Project | Surface checked | Invariant | Status | Upstream artifact |
| --- | --- | --- | --- | --- | --- |
| 1 | [OpenLIT](https://github.com/openlit/openlit) | token accounting | token subset (reasoning ⊂ output) | **FAIL → fixed** | [PR #1476 merged](https://github.com/openlit/openlit/pull/1476) |
| 2 | [Urusilla](https://github.com/jaden3824/urusilla) | operation aggregation (checked AgentMeasure itself) | execution / reconciliation / operation grain | **3 FAILs → fixed** | vectors [001](../conformance/vectors/external/urusilla-001/) · [002](../conformance/vectors/external/urusilla-002/) · issues [#8](https://github.com/roy-tong/AgentMeasure/issues/8) [#9](https://github.com/roy-tong/AgentMeasure/issues/9) [#12](https://github.com/roy-tong/AgentMeasure/issues/12) · CI integration [PR jaden3824/urusilla#15](https://github.com/jaden3824/urusilla/pull/15) |
| 3 | [pydantic-ai](https://github.com/pydantic/pydantic-ai) | OTel usage attributes | token subset emission | **intended / consumer-contract gap** | [issue #7975](https://github.com/pydantic/pydantic-ai/issues/7975) — emission confirmed intended; the consumer subset contract is unstated; routing to semconv |
| 4 | [LiteLLM](https://github.com/BerriAI/litellm) | cache-hit usage logging | cache accounting | **confirmed by third party** | [issue #39057](https://github.com/BerriAI/litellm/issues/39057) — independent dev confirmed the ambiguity changes budget enforcement, not just reports |
| 5 | [Phoenix](https://github.com/Arize-ai/phoenix) | token aggregation | leaf-span counting | reviewing | [issue #15793](https://github.com/Arize-ai/phoenix/issues/15793) |
| 6 | [DeepEval](https://github.com/confident-ai/deepeval) | eval rerun semantics | repeated measurement | **contributor PR proposed** | [issue #3110](https://github.com/confident-ai/deepeval/issues/3110) — tests/docs to pin cache replay ≠ new judge sample |
| 7 | [SigNoz](https://github.com/SigNoz/signoz) | cost pipeline ↔ dashboard | cost source linkage | reviewing | [issue #12738](https://github.com/SigNoz/signoz/issues/12738) |
| 8 | [AgentOps](https://github.com/AgentOps-AI/agentops) | Anthropic usage extraction | cache token emission | reviewing | [issue #1445](https://github.com/AgentOps-AI/agentops/issues/1445) |
| 9 | [OpenLLMetry](https://github.com/traceloop/openllmetry) | anthropic vs bedrock packages | cache accounting | reviewing | [issue #4449](https://github.com/traceloop/openllmetry/issues/4449) |
| 10 | [Ragas](https://github.com/vibrantlabsai/ragas) | metric aggregation | failure denominator | reviewing | [issue #2980](https://github.com/vibrantlabsai/ragas/issues/2980) |
| 11 | [Promptfoo](https://github.com/promptfoo/promptfoo) | cached-run reporting | replayed measurement | reviewing | [issue #10595](https://github.com/promptfoo/promptfoo/issues/10595) |
| 12 | [Langfuse](https://github.com/langfuse/langfuse) | OTel vs REST ingestion | cache normalization | reviewing | [issue #16884](https://github.com/langfuse/langfuse/issues/16884) |

*(Rows update as checks complete. Status meanings: checking = audit in
progress; reviewing = upstream issue open; discussing = public thread active;
PASS/FAIL/UNPROVABLE = invariant verdict recorded; fixed = upstream accepted
a change.)*

## The seven invariants

| id | question |
| --- | --- |
| execution grain | are attempts mixed into operations? |
| retry accounting | do retries inflate request / usage counts? |
| cache replay | is a cached replay counted as a new measurement? |
| token accounting | is a subset (reasoning) added into its total? |
| cost preservation | does grouping remove or duplicate real attempt cost? |
| evidence boundary | are returned / available / influential conflated? |
| eval repeatability | are n runs n measurements, or retries of one verdict? |

## Discipline

- Every row links to code or a fixture. No vibes.
- Findings are framed as contract questions, not gotchas; maintainers get the
  reproducible case and an offer of a regression-test PR before anything is
  published as a FAIL.
- UNPROVABLE is a valid and important result: "your telemetry cannot decide
  this" is itself the finding.
- The checker checks itself: AgentMeasure's own three externally found defects
  (row 2) stay at the top of this table on purpose.

## Follow along

Repo → [conformance pack](../conformance/pack/README.md) (run the same checks
on your own fixture) · X → [@elliwoodtong](https://x.com/elliwoodtong)
