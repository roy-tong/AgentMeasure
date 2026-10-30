# Provider Onboarding — one page

> For MCP/API providers joining an external measurement run (issue #6). You
> bring 20–100 anonymized rows (or a public export); we return a measurement
> check. No SDK required, no production traffic, nothing leaves your control
> that you don't choose to send. This page defines the path and what "a
> successful run" means — both sides hold the same yardstick.

## Identify your input first

With CLI 0.7.2+, run `verovo inspect-input your.jsonl`. This is format routing only, not validation or a conformance pass. Path A/B below uses canonical observations; `verovo conformance` uses FMT-002. These are different contracts. A valid canonical file must not be repaired by inventing FMT-002 fields.

## Three entry paths (pick one)

| Path | What you do | Best when |
|---|---|---|
| **A. Raw JSONL** | Map 20–100 rows onto the canonical contract yourself → validate → send | You know your logs well |
| **B. SDK wrap** | Wrap your server with the [Provider SDK](../sdk/) (`sdk/examples/mcp-integration.js`; demo: `./examples/demo-e2e.sh` — mock server → 42 calls → 252 observations → report) | You have a live MCP server |
| **C. assisted mapping** | Send the anonymized sample + your log schema; we draft the mapping, you review it | Fastest start |

Path A/B contract: [`reference/collector-input.md`](../reference/collector-input.md).
Mapping method: [`registry/provider-mapping.md`](../registry/provider-mapping.md).

## The five steps

1. **Answer the five mapping questions** (provider-mapping.md) — in writing,
   one line each.
2. **Produce the sample** — 20–100 rows, anonymized, including at least one
   interesting shape if you have it (a retry, a failure, a multi-step
   operation). Real shapes beat clean shapes.
3. **Validate locally** — `python3 schemas/validate_jsonl.py your.jsonl`
   must exit 0.
4. **Send** — attach to issue #6, or PR the three-piece external fixture if
   you want it preserved (`external/<your-handle>-<seq>/`).
5. **Get the measurement check back** — typically within 48h (first response
   within 24h, house rule).

## What counts as a successful run (the success criteria)

A run is **successful** when all four hold:

1. **Ingestion is clean.** 100% of rows pass the canonical validation — or
   every rejected row has a stated reason in the report (rejects are counted,
   never silently dropped).
2. **Grain is decided, not assumed.** The report states what counts as one
   attempt and one operation on your surface — including "grouping is
   UNPROVABLE on this surface" if that is the honest verdict.
3. **The three sections exist.** What safely counts as attempts vs operations;
   where retries may inflate usage **against your billable unit**; what your
   telemetry cannot prove. A run that returns only happy-path numbers is not
   successful.
4. **Nothing was invented.** No default price, no zero for absence, no
   fabricated identity (missing identity stays unknown — see the mapping
   guide). The report carries UNPROVABLE where your surface is blind, and
   that is a finding about your surface, not a failure of your submission.

## What a run does NOT require

- No production traffic, no 7-day commitment (the older format — a sample
  beats a week).
- No SDK install for Path A/C.
- No customer-identifying data — hash or drop; the mapping guide shows how.
- No endorsement implied: your fixture keeps your claim boundary, stated by
  you (see precedents in the mapping guide).

## After a successful run

- Your fixture can join `conformance/vectors/external/` under your handle —
  reusable evidence your metering has been checked at the shapes you chose.
- Optionally: a conformance pass against the published vectors
  (`conformance/README.md`) — receipt format, counting integrity, outcome
  audit families.

Questions go in [issue #6](https://github.com/roy-tong/verovo/issues/6)
— public, so the next provider reads the answer.
