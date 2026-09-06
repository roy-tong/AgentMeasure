# Measurement contributions with inspectable evidence

These are engineering contributions and counterexamples, not product adoption
claims or endorsements. Each case links to its public source and states what
the evidence does not establish.

## Exposing reasoning tokens without adding them twice

[OpenLIT PR #1476](https://github.com/openlit/openlit/pull/1476) was merged on
2026-08-26. The Python/OpenAI change exposes reasoning output tokens for chat
and Responses paths while preserving input/output as the token-usage metric's
categories. The subset invariant is explicit: with output 1,000 and reasoning
700, output usage remains 1,000, not 1,700.

That is a contribution to telemetry and regression protection. It does not
show that OpenLIT adopted AgentMeasure Healthcheck, and does not establish that
every previous OpenLIT path double-counted output.

## An external fixture found defects in our own checker

Urusilla's project-authored synthetic fixtures uncovered our validator's
`oneOf` sibling-constraint gap and declared-operation reconciliation gap:
[issue #8](https://github.com/roy-tong/AgentMeasure/issues/8) and
[issue #9](https://github.com/roy-tong/AgentMeasure/issues/9).
The [first vector](../conformance/vectors/external/urusilla-001/) became a
regression fixture. A [second vector](../conformance/vectors/external/urusilla-002/)
exercised a different operation-grain boundary, tracked in
[issue #12](https://github.com/roy-tong/AgentMeasure/issues/12).

The lesson is useful even if you never install AgentMeasure: preserve attempt
costs while checking declared operation summaries against their underlying
attempts. A successful synthetic fixture is not production usage or a live
provider-cost observation.

[Urusilla PR #15](https://github.com/jaden3824/urusilla/pull/15) proposes running
the generic conformance checks in CI. As checked on 2026-09-06, it is open;
review fixes have been pushed, but upstream workflow approval and merging are
still pending. It complements Urusilla's fixture-specific validators rather
than replacing them.

## Try the local product or contribute a bounded example

For Codex Desktop logs, [try Healthcheck](healthcheck-first-run.md). For generic
FMT-002 event fixtures, use the [conformance pack](../conformance/pack/README.md).
These are different input paths; Healthcheck does not require converting your
logs into FMT-002.

Useful contributions include a minimal synthetic parsing counterexample, a
repeat-run snapshot consumer, or a documentation correction with a versioned
source. Start from a real question and a small reproducer. Do not share private
logs or infer that a missing field means zero. See the
[campaign tracker](30-projects-30-days.md) for existing work before duplicating it.
