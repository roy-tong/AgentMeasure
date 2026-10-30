# The monthly review (subscription SOP)

One period, one ritual, four commands — now wrapped in
[`scripts/monthly_review.py`](../scripts/monthly_review.py) so the order and
the gates are mechanical, not tribal.

## The ritual

| Step | Command | Question it answers | Gate |
|---|---|---|---|
| 1 | `rules-diff <last-snapshot>` | did the vendor's rules change since last month? | **material change = exit 1**: re-verify under the new rule and disclose; never mix rules in one claim |
| 2 | `verify --export … --vendor …` | this month's ledger, all lanes in one artifact | produces `verified-ledger.json` (inputs sha256-anchored) |
| 3 | `period-compare <prev> <current>` | the honest delta — three-state movement, new/cleared findings, recovery progress | rules-version change is flagged, periods stay separate |
| 4 | `decisions` / `delivery` | the value books: decisions made differently, hours spent | printed for the review meeting |

Close with the console for the person reading it:

```bash
verovo console --ledger monthly-review/verified-ledger.json --out console.html
```

## Real usage

```bash
python3 scripts/monthly_review.py \
  --vendor intercom --export august.csv --contract msa.json \
  --prev-ledger july/verified-ledger.json \
  --rules-snapshot july/vendor-rules.json \
  --period 2026-08-01 --out august-review
```

Keep per-month directories (`july/`, `august-review/`): `period-compare`
consumes last month's ledger; `rules-diff` consumes last month's registry
snapshot (`curl` the pinned
[registry/vendor-rules.json](../registry/vendor-rules.json) at the version
you verified against, or copy it from the repo at that tag).

## Sandbox acceptance

```bash
python3 scripts/monthly_review.py --demo
```

runs the recount plus both journals on the bundled fixtures — the ritual's
shape, no data needed.

## Discipline reminders

- A finding is not money: `recovery` tracks concessions; `decisions` tracks
  what the buyer decided; the two are never summed.
- The buyer's own standard (`--contract`) is leverage, never a claim line.
- UNPROVABLE rows stay out of the amounts; the export tells you which
  evidence to bring next month.
