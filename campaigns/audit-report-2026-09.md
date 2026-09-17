# The Token-Accounting Bug Report: ~110 AI usage tools audited, 45+ verified billing bugs

*2026-09-06 → 09-09. Method: read the code, build a synthetic fixture, run the
tool's own parser against it. Every finding below links to a public, evidence-
backed filing with a pinned commit and a runnable or quoted-static argument.*

## TL;DR

If a tool tells you what your AI coding agents cost, there is a real chance it
is wrong in a systematic direction. We audited ~110 repositories across the
Claude Code / Codex / gateway / eval / observability ecosystems and filed
65+ evidence-backed findings; **15 have already been merged or accepted by
maintainers** (10 at publication, 10 more in the six days since), several
with public credit. The majority of audited tools
passed clean — including some of the largest (promptfoo, Portkey's model
data, TokenTracker) — so this is not "everything is broken"; it is "five
specific, findable bug classes, one of which your tool probably hasn't
tested".

## The five classes that keep appearing

### 1. One assistant message ≠ one line (10 confirmed tools)

Claude Code writes **one JSONL line per content block** of an assistant
message, and every line carries the same `message.id` and the same
`message.usage`. Sum per line and a message with text + two tool calls is
billed 3×. Real overcounts we measured: 2×–5×.

- [tokendash #37](https://github.com/zhangferry/tokendash/pull/37) (49★, merged): 3-block message → 3× tokens and cost
- [ccem #12](https://github.com/Genuifx/ccem/issues/12): same shape, first-wins variant undercounts instead
- [samewrite #1](https://github.com/ipeterpetrus/samewrite/issues/1): a *research project's* headline numbers rested on it

### 2. Re-emitted events (5 tools)

Codex re-emits `token_count` events with identical totals after compaction,
settings changes, and rate-limit refreshes. Naive per-event accumulation
double-counts. Measured on real corpora: +0.5% to +15% per session file.

- [token-vision #1](https://github.com/extrei/token-vision/issues/1): one real rollout, +14.97%
- [tokenscope #6](https://github.com/stealthsrc/tokenscope/pull/6) (merged), [coding-agent-usage-tracker #1](https://github.com/avihut/coding-agent-usage-tracker/pull/1) (merged)

### 3. Cache-pricing semantics (9 tools)

Anthropic's `input_tokens` **excludes** cache tokens; OpenAI's includes them.
5-minute cache writes cost 1.25× input, 1-hour writes 2×, reads 0.1×. Tools
that apply one convention to both providers clamp input to $0, double-charge
cache, or price 1h writes as 1.25×.

- [claude-hud #758](https://github.com/jarrodwatts/claude-hud/pull/758) (27.9k★): 1h writes at 1.25× — 37.5% understated on that component
- [one-api-pro #13](https://github.com/modelbus/one-api-pro/issues/13): streaming `+=` double-counts input (+50.7% with no cache) **and** the billing formula re-subtracts cache

### 4. Price-table drift (7 tools, including the source)

Embedded price snapshots diverge from published rates by 1.2×–5× — including
in vendored copies of **LiteLLM's price file**, the industry's source of
record ([litellm #40360](https://github.com/BerriAI/litellm/issues/40360):
Bedrock CRIS Claude-3-Haiku cache rates were ratio-generated instead of using
Anthropic's non-round published values; [llmcost #25](https://github.com/prassoai/llmcost/issues/25)
inherited the same values in a vendored snapshot).

### 5. Resume/fork history loss (4 tools)

Codex resume writes a new rollout file whose `session_meta.id` is the
*original* session id. Stores that replace-per-session wipe everything before
the resume; fork re-plays the parent prefix and double-counts it.

- [ai-usage-inspector #1](https://github.com/Kud0o/ai-usage-inspector/issues/1): 86% of a session's tokens vanish (real pair measured)
- [swarm #145](https://github.com/ra3orblade/swarm/issues/145) → [fixed in #146](https://github.com/ra3orblade/swarm/pull/146) with maintainer credit: *"reported and diagnosed by @roy-tong, who also supplied the patch this follows"*

## Why you should care even if you don't use these tools

Your billing dashboards, your FinOps exports, and every "how much did this
agent cost" number downstream inherit these errors. The bugs are findable
with **synthetic fixtures in minutes** — most tools' own tests never model
these shapes (single-line messages, monotonically growing counters).

## Audit your own tool in 10 minutes

The fixture corpus is open data — plain JSONL + expected totals, no runtime:

```bash
git clone --depth 1 https://github.com/roy-tong/AgentMeasure
# point your parser at conformance/pack fixtures like at real logs
python3 conformance/pack/agentmeasure selftest   # see the expected-totals style
```

Full method and per-class pointers: [tool-authors.md](tool-authors.md).
Full case list: [measurement-casebook.md](measurement-casebook.md).

## Fixes landed since publication (2026-09-11 → 09-14)

- [candor #8](https://github.com/auswm85/candor/pull/8) — OpenAI gpt-4o cached input restored 0.3125 → 1.25 per 1M with a pinned-table regression guard (merged 09-14, maintainer-invited)
- [langfuse #17117](https://github.com/langfuse/langfuse/issues/17117) — OTel cache_write alias missing from the extractor's cache-creation list: fixed on main (34k★; the flagship cache-accounting finding of this audit)
- [tokenfuse #267](https://github.com/TAIPANBOX/tokenfuse/issues/267) — OpenAI cached tokens no longer priced on both sides of input (closed completed 09-14)
- [openlit #1543](https://github.com/openlit/openlit/pull/1543) — measured-zero reasoning tokens no longer conflated with unknown (merged 09-15)
- [codeburn #1264](https://github.com/getagentseal/codeburn/pull/1264) — three-layer token_count dedup with measured re-emission behavior (merged 09-16 after three review rounds; the re-review's 136k-event corpus check corrected our own analysis and is now a methodology rule)

- [tokscale #1306](https://github.com/junhoyeo/tokscale/issues/1306) — forked/continued Pi sessions no longer double-count (fix via #1323, closed completed)
- [claude-usage-widget #1](https://github.com/everssauro/claude-usage-widget/issues/1) — first-wins dedup no longer drops 25% of output tokens (maintainer independently reproduced on a 2,694-file archive before merging)
- [token-monitor #627](https://github.com/Javis603/token-monitor/issues/627) — cross-session fork dedup anchored on stable response identity (closed completed)
- [snip #186](https://github.com/edouard-claude/snip/issues/186) — the two contradictory hardcoded price tables were unified (closed completed via #189)
- [openusage #360](https://github.com/janekbaraniewski/openusage/issues/360) — Codex cached tokens no longer billed twice (closed completed via #365)

Five further fixes landed on or just before the publication cut and were not
part of the original count: [trulens #2766](https://github.com/truera/trulens/pull/2766)
(mixed-currency aggregation, by a third-party contributor from this report),
[cc-enhanced #24](https://github.com/camjac251/cc-enhanced/pull/24),
[gortex #784](https://github.com/zzet/gortex/issues/784) (via #786),
[one-api-pro #13](https://github.com/modelbus/one-api-pro/issues/13),
[trace-mcp #1175](https://github.com/nikolai-vysotskyi/trace-mcp/issues/1175).
The headline count stays criteria-consistent (publication baseline + strictly
post-publication); the overall verified total is at least 20.

## Methodology notes (added 2026-09-14)

Two rules this audit learned the hard way, now part of the checklist for
every future finding:

1. **Real data decides.** A synthetic fixture can *propose* a bug, but when a
   maintainer's existing behavior and our fixture disagree, only a real log
   settles which side is wrong. Example: our codeburn PR initially asserted
   that three identical consecutive `token_count` events must be three calls;
   scanning 53 public Codex rollouts (1,313 events) showed 603 are byte-identical
   re-emissions of the previous event — the maintainer's dedup behavior was
   correct and our assertion was wrong
   ([codeburn #1264](https://github.com/getagentseal/codeburn/pull/1264)).
   Filings now carry a real-data check wherever a public corpus exists.
2. **A consumer contract must exist before an emission shape is a bug.** If a
   tool emits two records for one logical call but no consumer aggregates
   them unguarded, the emission is an intended contract, not a defect —
   file it as a semantics question, not a billing bug
   ([pydantic-ai #7975](https://github.com/pydantic-ai/pydantic-ai/issues/7975),
   closed not-actionable; correctly).

## Honesty notes

- Counts are of *filings with pinned evidence*, as of 2026-09-17 morning;
  merges happen as maintainers get to them (20 accepted so far; see the dated
  subsection below for what landed after publication).
- Most audited repos passed. We name the clean ones because that matters.
- All reproductions are synthetic; no private logs anywhere.
- This audit was performed with the methods and fixtures of this repository —
  that is the demo. No audited project endorses AgentMeasure.
