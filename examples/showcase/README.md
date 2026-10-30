# Reproducible bill-recount showcase

Three synthetic cases (not customer recoveries). Each case is an input CSV (synthetic data), the one command
that runs it, and a frozen expected output. If the tool in your hand produces
a different report, first confirm you are running the same source revision.
These snapshots match CLI 0.8.0; older releases have an older report header.

The pattern is borrowed from projects that earn trust by being reproducible:
the showcase is not a claim, it is a runnable expectation.

## Case A — overcharge, and the rows we refuse to guess

```bash
verovo recount --export case-a-overcharge-zendesk.csv --vendor zendesk
```

One conversation a human agent finished was still billed (`$2.00` overcharge).
Four of five rows land in `cannot settle` because a counts-only export cannot
carry Zendesk's LLM verdict — those rows are removed from the claim, not
zeroed. Read: [expected output](case-a-overcharge-zendesk.expected.txt).

## Case B — findings run both directions

```bash
verovo recount --export case-b-both-directions-intercom.csv --vendor intercom
```

Two overcharged lines (a reopen inside the documented window, a human
takeover), one line the vendor under-billed in your favour. Undercharge is
netted before any dollar is claimed: `$1.98 − $0.99 = $0.99`. Read:
[expected output](case-b-both-directions-intercom.expected.txt).

## Case C — the contract lane is leverage, never netted into the claim

```bash
verovo recount --export case-c-contract-lane-intercom.csv --vendor intercom \
  --contract case-c-contract-lane-intercom.contract.json
```

The buyer's contract (72h reopen window, human takeover disqualifies) is a
second lane: its findings are renewal leverage, listed separately and never
netted into the Tier 1 billing claim. Rows without timestamps stay
`unprovable` — a missing recontact time is never read as "no recontact".
Read: [expected output](case-c-contract-lane-intercom.expected.txt).

## Guarantees

- All data is synthetic. No customer data appears here.
- The vendor rule sets and their sources are printed in every report
  (`verovo recount --list-vendors` for the full registry).
- The frozen expected outputs are compared by CI on every change
  (`healthcheck/tests/test_showcase.py`), so the showcase cannot silently
  drift from the shipped behaviour.
