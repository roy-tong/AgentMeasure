# Check an Intercom Fin bill locally in 10 minutes

I use two small, synthetic examples below to show what I would check before
challenging a per-resolution bill. No customer messages, account credentials,
or AMS-1 background are needed. The first example checks a CSV against the
packaged Intercom rules; the second shows confirmed versus assumed outcomes
in a one-page statement. They are **different datasets**, not two views of the
same invoice, and their dollar figures must not be added together.

## 1. Get the local checker

Python 3.9+ and Git are required. Run these commands in a terminal:

```bash
git clone https://github.com/roy-tong/AgentMeasure.git
cd AgentMeasure
python3 healthcheck/agentmeasure --version
mkdir -p walkthrough-output
```

The commands below all run from this repository root. The source-tree launcher
needs no package installation or account. Cloning needs internet access; the
checks themselves run locally. Keep `walkthrough-output/` outside version
control, especially when replacing the examples with private exports.

## 2. Inspect the CSV before trusting any number

The bundled [Intercom CSV](../healthcheck/am_healthcheck/fixtures/vendor-export-intercom.csv)
is a **synthetic, already reviewed canonical export**, not a native Intercom
report. It contains ten conversations, eight marked billed, and deliberately
leaves two evidence cells empty.

```bash
python3 healthcheck/agentmeasure prepare \
  --export healthcheck/am_healthcheck/fixtures/vendor-export-intercom.csv \
  --vendor intercom --inspect
python3 healthcheck/agentmeasure prepare \
  --export healthcheck/am_healthcheck/fixtures/vendor-export-intercom.csv \
  --vendor intercom --out walkthrough-output/prepared.csv
python3 healthcheck/agentmeasure recount \
  --export walkthrough-output/prepared.csv --vendor intercom --inspect
```

The preparation report shows `Rows: 10`. It lists one row needing
`human_agent_participated` and one needing
`customer_recontacted_within_window`. The recount inspection says
`all required columns matched`: that means **headers** matched, not that every
cell contains evidence. The two empty cells must remain unknown in this demo.

### When I use my own monthly export

I first export conversation data for the invoice's date range from Intercom
Reports, following [Intercom's reporting export instructions](https://www.intercom.com/help/en/articles/2046229-export-your-conversations-data).
I preserve the original file locally and check the reporting timezone, date
filters, and which conversations the export includes. A partial export cannot
prove a whole invoice. I run the same `prepare` commands with the native CSV
path instead of the bundled fixture, inspect the mapping, then review the
prepared CSV in a spreadsheet before recounting.

The canonical columns are:

| Column | Evidence I need |
| --- | --- |
| `conversation_id` | Stable conversation identifier, not a row number. |
| `opened_at`, `closed_at` | Exported timestamps with a known timezone. |
| `human_agent_participated` | Whether a human actually participated; assignment alone is not proof. |
| `issue_addressed` | Evidence that the question was addressed, not just a closed status. |
| `customer_recontacted_within_window` | Recontact checked against the applicable window, not any historical reply. |
| `vendor_billed` | Billing ledger/invoice evidence for this conversation. |

`prepare` copies mapped fields and adds `prov_*` provenance cells. Missing
judgements stay empty; `hint_*` columns are leads, never decisions. I retain
those columns and record the source of any reviewed value in `prov_*`.
Intercom's `Has user reply` does not establish post-close recontact, and the
conversation export may not say which conversations were billed. I do not turn
missing data into `no` to make a report look complete.

## 3. Recount under the vendor's rules

```bash
python3 healthcheck/agentmeasure recount \
  --export walkthrough-output/prepared.csv --vendor intercom \
  --json walkthrough-output/recount.json
```

Expected terminal excerpts:

```text
Conversations:        10
Billed by vendor:     8
billed but not billable     4
billable but not billed     2
net                         +2
cannot settle               2 (20.0%)
agrees with the vendor      2
three-state: PASS 2 / FAIL 6 / UNPROVABLE 2
```

At the packaged USD 0.99 per-resolution price, the report shows:

| Recount field | USD |
| --- | ---: |
| `overcharge_amount` | 3.96 |
| `undercharge_amount` | 1.98 |
| `variance` | 1.98 |
| `cannot_settle_amount` | 1.98 |

Four disputed charges minus two unbilled eligible resolutions leaves a net
two-unit variance. The two unknown conversations are **excluded**, not treated
as a refund or as zero. `recount.json` preserves the conversation IDs and
line-level verdicts so I can trace every finding back to a row.

For a real bill, I check the price, rule version, and applicable terms against
the invoice rather than assuming that the packaged price is my contract.
`recount --list-vendors` lists the rule sources and confidence; the
[registry](../registry/vendor-rules.json) records the implementation's rules.
This is evidence for review, not a vendor credit or a legal determination.

## 4. Read confirmed versus assumed outcomes on one page

`settle` accepts effect-record JSONL, **not the prepared CSV**. For this part I
use the separate [synthetic outcome fixture](../conformance/evidence/assumed-resolution/fixture.jsonl).
It already labels four outcomes as customer-confirmed, three as assumed,
two as escalated, and one as abandoned. A native CSV must not be renamed to
JSONL or silently converted into customer-confirmed outcomes.

```bash
python3 healthcheck/agentmeasure settle \
  --effects conformance/evidence/assumed-resolution/fixture.jsonl \
  --output walkthrough-output/settlement.json \
  --provider intercom --offering fin \
  --period-start 2025-03-01 --period-end 2025-03-31 \
  --statement --format md --price 0.99 --verbose
```

The command writes `walkthrough-output/settlement.json` and
`walkthrough-output/settlement-statement.md`. Open the Markdown file in a text
editor or Markdown viewer. Its reproducible anchors are:

| Statement line | Value |
| --- | --- |
| Tier 1: resolved + assumed | 7 / 10 |
| Tier 2: affected-party confirmed | 4 / 10 |
| Disputed class | 3 |
| Tier 1 amount | $6.93 |
| Tier 2 amount | $3.96 |
| Variance | $2.97 |
| Removed as UNPROVABLE | 10 (100.0%) |

The $2.97 is a **difference between outcome definitions**, not the $1.98
vendor-rule recount above and not a proven refund. Assumed outcomes can count
under vendor terms without being customer-confirmed. This fixture has no
incrementality evidence, so the statement explicitly removes all ten lines
from an outcome claim. It also says `Billable but not billed: cannot determine
from this input`: effect records alone cannot establish the other direction.
The generation time and absolute output paths will differ between runs; the
counts and amounts should not.

For a real statement I need separately reviewed effect records with outcome
class, observer grade, confirmation time, and traceable conversation IDs.
I do not infer those fields from the CSV's `issue_addressed` flag. If that
evidence is unavailable, I stop at the vendor-rule recount and list what is
missing rather than manufacturing a statement.

## 5. Keep the evidence; share only after review

I keep the source export, reviewed CSV, billing evidence, applicable terms,
`recount.json`, and any independently supported outcome records together
locally. I review IDs and provenance before sharing even a generated report.
The synthetic walkthrough is safe to reproduce, but real exports and output
files can contain sensitive identifiers and are not automatically anonymized.

For a browser-only vendor-rule check, use the
[local recount page](https://roy-tong.github.io/AgentMeasure/recount.html).
For the broader pipeline, including billing-ledger crosschecks and realized
credits, see the [buyer-side commands](../healthcheck/README.md#outcome-billing-verification-prepare--recount--dispute--recovery).
