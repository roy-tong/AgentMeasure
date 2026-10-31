# Case note: razzlo-001 — thirteen explicit-zero cache-write prices, one truthiness idiom, and the fix that followed

Published 2026-10-31. This note records a contributor report and its outcome.
The contributor — **Razzlo (iLands broker)**, a pseudonymous email correspondent
with no GitHub account (registration blocked from their network since 2026-09-20)
— is credited by their specified line in the frozen vector:
*"Razzlo (iLands broker) — vectors and row counts provided by direct reply,
2026-10-26. Archived by Verovo."*

> **Claim boundary (contributor recount + our verification, kept separate).**
> The row counts below come from two different instruments. Razzlo's numbers
> (4,244-row and 4,307-row table scans, the 44-row class count) are **his own
> self-built cache-price checker**, reported by email 2026-10-23 and 2026-10-26.
> What we verified ourselves is narrower: the 13 `tencent/*` rows read directly
> from litellm's `model_prices_and_context_window.json` (2026-10-26 for
> [issue #48390](https://github.com/BerriAI/litellm/issues/48390), re-read
> 2026-10-31 for this note). Nothing here is a bill, an observed overcharge, or
> a claim that litellm mispriced anything internally as of 2026-10-26 — that
> scope note was in the issue, and where it turned out incomplete this note says
> so.

## What the report was

A recurring recount of litellm's model-price table, not a delivery through the
free lane. The 2026-10-23 recount (4,244 rows; the contributor's five check
classes stable across recounts, OpenRouter block fully absorbed) flagged one
block: **all 13
`tencent/*` price rows publish `cache_creation_input_token_cost: 0.0` — an
explicit zero — next to a nonzero `cache_read_input_token_cost`**. Re-read
2026-10-31 against `main` (now 4,551 models, 16 `tencent/*` rows — three new
image-model rows carry no cache fields): the 13 rows are still there, unchanged
in shape. Examples, prices straight from the file:

```
tencent/glm-5.3:          input 1.4e-06   cache_write 0.0    cache_read 2.6e-07
tencent/deepseek-v4-pro:  input 1.74e-06  cache_write 0.0    cache_read 1.45e-07
tencent/kimi-k3:          input 3e-06     cache_write 0.0    cache_read 3e-07
```

Tencent may genuinely bill cache writes at zero. That is a question for the
vendor doc URLs those rows point at, not for us — the explicit `0.0` is a
legitimate value either way.

## The trap (a shape, not a charge)

In Python, `0.0` is falsy. A consumer writing
`row.get("cache_creation_input_token_cost") or fallback` discards the explicit
zero and silently **reprices a free cache write at the fallback rate** (the
shape seen in the wild: `1.25 × input`). The price is present in the source of
record and thrown away by a truthiness idiom. The same absent-vs-zero shape was
already fixed once on the usage side
([openlit#1543](https://github.com/openlit/openlit/pull/1543), merged).

Razzlo's 2026-10-27 class note: 44 of his 4,307 rows share the shape, and all
13 `tencent/*` rows point at tencent-cloud doc URLs — **the class is the
finding; tencent is its local instance.** We did not independently recount his
44: reading the live table ourselves on 2026-10-31 finds 40 such rows among
4,551 — five days of table drift, recorded as drift, not as contradiction.

## What we did with it

1. **Upstream bug report, honestly scoped**
   ([BerriAI/litellm#48390](https://github.com/BerriAI/litellm/issues/48390),
   2026-10-26): 13/13 tencent rows verified by direct file read; we stated we
   had *not* found an internal litellm mispricing path and asked for a decision
   — a one-line doc note that `0.0` is meaningful, and/or an in-check guard
   helper. Bug report, no marketing.
2. **Defensive regression frozen as a conformance vector**
   ([`conformance/vectors/pricing-explicit-zero.json`](../../conformance/vectors/pricing-explicit-zero.json),
   commit `4d9f975`; credit line recorded in `1bc6db1`). `PRICING-ZERO-001`
   pins the principle — **fallback only on absence, never on explicit zero** —
   in three cases: or-fallback repricing 1.25× → FAIL; in-check guard keeps
   `0.0` free → PASS; absent field falls back but must be marked `inferred` →
   PASS. Wired into CI (`conformance.yml` → `run_pricing_zero.py`), so neither
   we nor a downstream contributor can reintroduce the idiom silently.

## The fix, and one correction to ourselves

The loop closed faster than the ask. litellm maintainer **tin-berri** merged
[PR #49294](https://github.com/BerriAI/litellm/pull/49294)
(*"fix(cost): preserve zero prices across batch, speech and search"*,
2026-10-30, "Fixes #48390"), and closed the issue with thanks. The diff shows
the idiom was not hypothetical inside litellm either: the batch calculator had
literally `model_info.get("cache_creation_input_token_cost") or
input_cost_per_token`; Perplexity search rates and the speech character/token
metric selection had the same truthiness reads. All became `is None` checks,
with regression tests, and `CONTRIBUTING.md` gained a "Preserve zero prices"
rule that names the exact idiom.

**Correction, by our own policy:** our issue said "no internal litellm path
found." That was true for the calculators we read and incomplete as a claim —
the batch/speech/Perplexity arms carried the idiom. Recorded here because a
check that cannot be corrected is not a check; the frozen vector needed no
change (it pins the shape, not the inventory).

## What could not be proven (UNPROVABLE — absence carried, never converted)

- **No mispriced bill anywhere in this case.** The 1.25× repricing is the
  consumer idiom's shape, frozen in a vector — no real overcharge was observed
  or claimed, by razzlo or by us.
- **Whether the vendor's economics match the table** (is a cache write really
  free?) — the tencent-cloud doc URLs are the source of record; we did not
  verify vendor docs.
- **The 44-row class count** is the contributor's recount; our 40-row count is
  a different day's table. Neither audits the other.

## Reproduce it yourself

- Frozen vector + credit line:
  [`conformance/vectors/pricing-explicit-zero.json`](../../conformance/vectors/pricing-explicit-zero.json)
- Runner (3/3 vectors, exit 0):
  `python3 conformance/runners/run_pricing_zero.py`
- The report that started it:
  [litellm#48390](https://github.com/BerriAI/litellm/issues/48390) · the fix:
  [litellm#49294](https://github.com/BerriAI/litellm/pull/49294) · the earlier
  usage-side fix of the same shape:
  [openlit#1543](https://github.com/openlit/openlit/pull/1543)
- Method, run-book, and report templates: [docs/review-method/](./README.md)

Contributions like this one arrive by email too — a recurring recount from
someone who reads price tables for a living is exactly the 20–100-row shape the
free lane exists for. Credit stays with the contributor, in their own words.
