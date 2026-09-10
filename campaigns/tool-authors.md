# Audit your usage/cost tool in 10 minutes

If you maintain a tool that reads Claude Code, Codex, Gemini CLI, OpenCode, or
gateway/proxy usage events — this page is for you. Between 2026-09-06 and
09-09 we audited ~110 such repositories and filed 45+ evidence-backed
findings; most tools hit at least one of eight hazard classes below, usually
in code their own tests cover happily.

## The eight classes (with real confirmed instances)

| # | Class | Typical symptom | Confirmed |
|---|---|---|---|
| H1 | Claude per-block re-summation | one assistant message = one JSONL line **per content block**, each with the same `message.id` and same `usage`; summing per line inflates 2–5× | 10 tools |
| H2 | Codex re-emitted events | `token_count` re-emits identical totals after compaction/settings/rate-limit refresh; per-event accumulation double-counts (real corpora: +0.5–15% per file) | 5 tools |
| H3 | Cumulative misuse | summing `total_token_usage` across events instead of diffing | 3 tools |
| H4 | Limit-window mixups | 5h vs weekly `used_percentage`/`resets_at` crossed | 2 tools |
| H5 | Cache-price semantics | Anthropic `input_tokens` **excludes** cache (OpenAI's includes it); 5m write=1.25×, 1h write=2×, read=0.1× — conflations clamp input to $0 or double-charge | 9 tools |
| H6 | Resume/fork loss or duplication | child rollout re-plays parent prefix; store keyed by session id wipes history | 4 tools |
| H7 | Embedded price-table drift | stale snapshot prices (observed 1.2×–5× off, incl. in vendored LiteLLM copies) | 7 tools |
| H8 | SSE usage extraction | Anthropic `message_start` carries input usage, `message_delta` carries **cumulative** usage — `+=` double-counts; early-exit drops the usage-only OpenAI chunk | 5 tools |

## The 10-minute self-audit

1. Take the fixture files from the
   [conformance pack](../conformance/pack/README.md) (plain JSONL + expected
   totals — no AgentMeasure runtime, no install).
2. Point your parser at them the way you point it at real logs.
3. Compare your totals against the expected values in each fixture.

If the numbers match: you're clean, and you now have regression inputs most
tools in this space lacked. If they don't: the fixture name tells you the
class; each class above links to a public, real-world instance you can
compare fixes against (see the
[measurement casebook](measurement-casebook.md#ecosystem-audit-33-verified-usage-accounting-findings-2026-09-0607)).

## What we ask in return

Nothing mandatory. If the fixtures saved you a bug, a star or a "fixtures
from AgentMeasure" line in your README both help others find them — and a
link back to your fixed issue grows the shared casebook. That's the whole
loop.

## Scope notes

- The audit's per-finding evidence lives in the public PRs/issues it filed;
  the internal ledger (which repos passed clean — the majority — and which
  are pending) is not published to avoid implying endorsement.
- Fixtures are synthetic. No private logs are shared anywhere.
- Not affiliated with Anthropic, OpenAI, or any audited project.
