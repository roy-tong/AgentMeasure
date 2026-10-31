# Case card: tokendash #37 — one assistant message, billed as three

**Class:** one assistant message ≠ one line (10 confirmed tools in the audit)
**Status of the fix:** merged upstream 2026-09-09
**Evidence:** [tokendash PR #37](https://github.com/zhangferry/tokendash/pull/37)

## What happened

Claude Code writes one JSONL line per content block of an assistant message,
and every line of the same message carries the same `message.id` and the same
`message.usage`. A tool that sums per line bills a message containing text
plus two tool calls three times. In tokendash (49 stars at audit time), a
3-block message produced 3× tokens and cost — a silent overstatement, not a
crash: every individual record looks correct, so dashboards stay green while
the total is wrong.

This was not a one-off. The 2026-09 audit found this exact shape in 10
confirmed tools, with measured real overcounts of 2×–5× across the class.

## What was done

A reproduction built from a synthetic fixture (pinned commit, no private logs)
was filed as [PR #37](https://github.com/zhangferry/tokendash/pull/37). The
maintainer merged it on 2026-09-09; the reconciled counting follows the
message identity rather than the line count. The public claims index records
the entry as **Fixed · Re-verified**, meaning the fix was re-verified after it
landed.

## What this case does not establish

The majority of the ~110 audited repositories passed clean — this card is not
a claim that usage tools are broken in general. A merged fix is engineering
evidence that the defect existed at a pinned commit and that the method finds
real accounting errors; it is not an endorsement of Verovo by tokendash or
its maintainer, and not evidence of product adoption.

## Sources (all in this repository)

| Claim | Source | Date |
|---|---|---|
| 3-block message → 3× tokens and cost; 49★; merged | [campaigns/audit-report-2026-09.md](../../campaigns/audit-report-2026-09.md), class 1 | 2026-09-06 → 09-09 |
| Class has 10 confirmed tools; measured overcounts 2×–5× | [campaigns/audit-report-2026-09.md](../../campaigns/audit-report-2026-09.md) | 2026-09 |
| Per-block re-summation, 2×–3× inflation instances | [campaigns/measurement-casebook.md](../../campaigns/measurement-casebook.md) | 2026-09-06/07 |
| Fixed · Re-verified; PR #37 merged 2026-09-09 | [website/claims.html](https://roy-tong.github.io/Verovo/claims.html) | published index |
| Fix reconciles cumulative Claude usage snapshots | [campaigns/audit-report-2026-09.md](../../campaigns/audit-report-2026-09.md), fixes section | merged 09-09 |
