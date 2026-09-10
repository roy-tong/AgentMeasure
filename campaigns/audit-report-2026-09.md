# The Token-Accounting Bug Report: ~110 AI usage tools audited, 45+ verified billing bugs

*2026-09-06 → 09-09. Method: read the code, build a synthetic fixture, run the
tool's own parser against it. Every finding below links to a public, evidence-
backed filing with a pinned commit and a runnable or quoted-static argument.*

## TL;DR

If a tool tells you what your AI coding agents cost, there is a real chance it
is wrong in a systematic direction. We audited ~110 repositories across the
Claude Code / Codex / gateway / eval / observability ecosystems and filed
65+ evidence-backed findings; **10 have already been merged or accepted by
maintainers**, several with public credit. The majority of audited tools
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

## Honesty notes

- Counts are of *filings with pinned evidence*, as of 2026-09-10; merges
  happen as maintainers get to them (10 accepted so far).
- Most audited repos passed. We name the clean ones because that matters.
- All reproductions are synthetic; no private logs anywhere.
- This audit was performed with the methods and fixtures of this repository —
  that is the demo. No audited project endorses AgentMeasure.
