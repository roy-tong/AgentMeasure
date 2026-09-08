# Usage-claim Comparison Template

> For auditing provider / subscription usage claims (e.g. "3-4x less usage on
> the long tail") against local receipts. Same task mix, before and after, one
> counting rule. Fill the blanks; ship the filled version as the audit.

## 0. Claim under test

- Claim (quote verbatim):
- Vendor / product / plan:
- Claimed metric & magnitude:
- Date claimed:

## 1. Boundary of the comparison

- Task class(es) covered (what is "a task" here):
- Harness / client + version:
- Same prompts & same task mix on both sides? (y/n, attach list)
- Window: start / end (same wall-clock span both sides)

## 2. Counting rule (pick ONE and state it)

- [ ] Count exactly one stream (state which: response_item vs item_completed)
- [ ] Mirror ratio disclosed: ______ (dual-recorded fraction of sessions)
- [ ] Reasoning tokens: included in output total, surfaced as facet only (never summed)
- [ ] Cache: read/write tokens kept in separate buckets; input total is exclusive after subtraction
- [ ] Compaction: aggregate from last cumulative snapshot per session; sessions lacking one are UNPROVABLE
- [ ] Attempts vs operations: ledger is append-only attempts; operations are derived (never "corrected")

## 3. Evidence files

- Local log root(s): e.g. `~/.codex/sessions`, `~/.claude/projects`, Pi exports
- Export method + version (exact tool/commit)
- Sanitization performed (no prompts / auth / personal data included)

## 4. Numbers

| metric | before | after | delta | basis |
| --- | --- | --- | --- | --- |
| total tokens (per counting rule) | | | | |
| fresh input tokens | | | | |
| cache read tokens | | | | |
| cache write tokens | | | | |
| output tokens (incl. reasoning) | | | | |
| reasoning facet | | | | |
| attempts | | | | |
| resolved operations | | | | |
| tokens per completed task | | | | |
| attempts per completed task | | | | |
| claimed vendor % (for reference only) | | | | |

## 5. Verdict

- [ ] PASS — numbers reproducible from attached logs under the stated rule
- [ ] FAIL — number does not reproduce / rule ambiguous (say where)
- [ ] UNPROVABLE — logs cannot decide (say which field and why)
- If UNPROVABLE, list exactly what evidence would upgrade it.

## 6. Disclosure

- This is an independent read of local logs, not an official vendor statement.
- Local token totals are not billed credits; billing claims need the vendor's
  own accounting as the source of truth, and this template only checks that a
  claimed delta is *locally reproducible under a stated counting rule*.
