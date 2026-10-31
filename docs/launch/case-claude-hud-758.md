# Case card: claude-hud #758 — one-hour cache writes priced at the 5-minute rate

**Class:** cache-pricing semantics (9 confirmed tools in the audit)
**Status of the fix:** merged upstream
**Evidence:** [claude-hud PR #758](https://github.com/jarrodwatts/claude-hud/pull/758)

## What happened

Cache pricing has exact multipliers: 5-minute cache writes cost 1.25× input,
1-hour writes cost 2×, reads 0.1×. claude-hud (27.9k stars at audit time)
priced 1-hour writes at the 5-minute rate of 1.25×, which understates that
component by 37.5%. Understatement is the dangerous direction for a buyer:
the dashboard reads cheaper than reality while the invoice keeps the correct
number, and the gap surfaces at reconciliation time, not before.

The audit found 9 confirmed tools in this class. The semantics are genuinely
easy to get wrong — Anthropic's `input_tokens` excludes cache tokens while
OpenAI's includes them — but "easy to get wrong" is exactly why the rule needs
to be pinned somewhere checkable instead of re-derived in every dashboard.

## What was done

The finding was filed with a reproduction against a pinned commit and merged
upstream as [PR #758](https://github.com/jarrodwatts/claude-hud/pull/758).
The public claims index records it as **Fixed · Re-verified**.

## What this case does not establish

A 37.5% understatement on one component is not a statement about any user's
actual bill — it depends entirely on how much of a workload hits 1-hour cache
writes. This card is engineering evidence about a defect at a pinned commit
and its fix, not an adoption or endorsement claim, and not a claim that large
projects are careless: most audited repositories, including some of the
largest, passed clean.

## Sources (all in this repository)

| Claim | Source | Date |
|---|---|---|
| 1h writes at 1.25× — 37.5% understated on that component; 27.9k★ | [campaigns/audit-report-2026-09.md](../../campaigns/audit-report-2026-09.md), class 3 | 2026-09-06 → 09-09 |
| 5-min writes 1.25×, 1-hour writes 2×, reads 0.1×; class = 9 tools | [campaigns/audit-report-2026-09.md](../../campaigns/audit-report-2026-09.md) | 2026-09 |
| Fixed · Re-verified; PR #758 merged (27.9k★) | [website/claims.html](https://roy-tong.github.io/verovo/claims.html) | published index |
| Cache-pricing class listing incl. claude-hud #758 | [campaigns/measurement-casebook.md](../../campaigns/measurement-casebook.md) | 2026-09-06/07 |
