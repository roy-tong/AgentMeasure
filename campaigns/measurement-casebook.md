# Measurement contributions with inspectable evidence

These are engineering contributions and counterexamples, not product adoption
claims or endorsements. Each case links to its public source and states what
the evidence does not establish.

## Ecosystem audit: 33 verified usage-accounting findings (2026-09-06/07)

Over two days we deep-read 71 repositories across the Claude/Codex usage-tool
long tail, LLM observability platforms, eval frameworks, gateways, and
upstream pricing-data sources, and filed 33 evidence-backed findings — every
one pinned to a commit SHA, verified by a runnable reproduction or a quoted
static argument, and checked against the target's issue history for
duplicates. The method is the product demo: the same hazard taxonomy and
synthetic-fixture discipline that drive the AgentMeasure conformance pack
were applied to other people's code.

What this establishes: these specific defects exist at these commits, and the
audit method finds real, quantified accounting errors that the projects' own
test suites missed. What it does not establish: that any of these projects
endorses or uses AgentMeasure, that the maintainers will accept the fixes, or
that every tool in the space has these defects (the majority of audited
repos — including promptfoo, Portkey's model data, and tokscale — passed
clean).

The hazard classes (with the number of confirmed instances found):

- **Per-block re-summation** — Claude Code writes one JSONL line per content
  block, each carrying the same `message.id` and the same `message.usage`;
  summing per line multiplies usage by block count. 9 confirmed instances,
  2×–3× inflation (e.g. [tokendash #37](https://github.com/zhangferry/tokendash/pull/37),
  [agent-bill #1](https://github.com/yange0793-dot/agent-bill/pull/1),
  [ccem #12](https://github.com/Genuifx/ccem/issues/12),
  [samewrite #1](https://github.com/ipeterpetrus/samewrite/issues/1)).
- **Re-emitted event re-summation** — Codex re-emits `token_count` events with
  identical totals after compaction/settings/rate-limit refreshes; naive
  per-event accumulation double-counts them. Verified on real corpora and
  fixed in 4 tools (e.g. [tokenscope #6](https://github.com/stealthsrc/tokenscope/pull/6),
  [token-vision #1](https://github.com/extrei/token-vision/issues/1),
  [coding-agent-usage-tracker #1](https://github.com/avihut/coding-agent-usage-tracker/pull/1)).
- **Cache pricing semantics** — Anthropic `input_tokens` excludes cache while
  OpenAI's includes it; conflating the two clamps input to zero or double-
  charges cache. 1h-TTL writes are 2× input, not 1.25×
  ([claude-hud #758](https://github.com/jarrodwatts/claude-hud/pull/758),
  [tokenguard analysis](https://github.com/QQSHI13/tokenguard) — repo
  archived before filing, [one-api-pro #13](https://github.com/modelbus/one-api-pro/issues/13)).
- **Pricing-table drift** — embedded price tables diverging from published
  rates, 1.2×–3× per model ([switchXprovider #1](https://github.com/shaheer-00/switchXprovider/pull/1),
  [Tokdash #75](https://github.com/JingbiaoMei/Tokdash/pull/75),
  [iris-eval #478](https://github.com/iris-eval/mcp-server/pull/478),
  [litellm #40360](https://github.com/BerriAI/litellm/issues/40360) — in
  the industry's pricing source of record).
- **Loss on resume/fork** — sessions re-opened or forked lose or duplicate
  their history ([ai-usage-inspector #1](https://github.com/Kud0o/ai-usage-inspector/issues/1),
  [swarm #145](https://github.com/ra3orblade/swarm/issues/145)).

**Accepted so far: 1.** The swarm maintainer merged the fix in
[swarm PR #146](https://github.com/ra3orblade/swarm/pull/146), crediting the
report: *"reported and diagnosed by @roy-tong, who also supplied the patch
this follows."* Everything else is open and unreviewed at the time of
writing; several maintainers approved CI runs on our PRs
([claude-hud](https://github.com/jarrodwatts/claude-hud/pull/757),
[Claude-Code-Agent-Monitor
#328](https://github.com/hoangsonww/Claude-Code-Agent-Monitor/pull/328)).
Reproductions use fully synthetic fixtures derived from this project's
reference corpus — no private logs were shared anywhere.

The full audit log, per-finding evidence, and the honest no-gap list (most
audited projects passed) are maintained internally; the public trail is the
linked PRs and issues above. If you want the fixture shapes that expose these
classes in your own tool, they are in the
[conformance pack](../conformance/pack/README.md) — no AgentMeasure runtime
required.

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
