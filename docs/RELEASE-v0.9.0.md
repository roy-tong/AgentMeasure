# v0.9.0 — AgentMeasure is now Verovo

CLI release 0.9.0; Provider SDK 0.3.0 (`@verovo/mcp`). Same measure, new name,
new logo.

The project is renamed from **AgentMeasure** to **Verovo**. Nothing about what the
tool claims to do changed in this release: it still re-counts supported billing
exports locally, keeps findings and gaps separate, and reports unknown as unknown.
This release is the rename, plus the compatibility work the rename required.

## What changes for you

| Area | Before | Now |
|---|---|---|
| Install and CLI | `pip install agentmeasure`, `agentmeasure …` | `pip install verovo`, `verovo …` |
| Provider SDK | `@agentmeasure/mcp` | `@verovo/mcp` (0.3.0) |
| Environment variables | `AGENTMEASURE_*`, `AM_*` | `VEROVO_*` (e.g. `VEROVO_EVENTS_DIR`, `VEROVO_LAB_DEBUG`) |
| Local data directory | `~/.agentmeasure/` | `~/.verovo/` |
| Schema namespaces | `agentmeasure.lab/…`, `agentmeasure.commercial/…` | `verovo.lab/…`, `verovo.commercial/…` |
| Settlement standard | AMS-1 | VSS-1 (Verovo Settlement Statement) |
| Repository and site | `roy-tong/AgentMeasure` | `roy-tong/verovo`, `roy-tong.github.io/verovo` |

If you scripted against the old names, this is a breaking rename; pin 0.8.0 if you
need the previous surface for a migration window.

## What does not change

- **Recorded evidence stays valid.** External conformance vectors
  (`conformance/external`, `conformance/vectors/external`) and recorded run logs
  are kept byte-for-byte under the old namespace. The schema accepts
  `agentmeasure.lab/funnel-event` and `agentmeasure.lab/report` as permanent legacy
  aliases, so old fixtures still validate and still reproduce their expected
  metrics.
- **Measurements, verdicts and boundaries** are unchanged. PASS / FAIL /
  UNPROVABLE still mean what they meant; missing evidence still lowers a posture
  instead of filling the gap.
- **No new claim.** A rename is not adoption, not a customer, not a validation of
  the commercial thesis.

## Compatibility notes

- JSON exports keep the tool tag `verovo-healthcheck` (was
  `agentmeasure-healthcheck`); schema version and field names are unchanged.
- The settlement standard keeps its numeric suffix: AMS-1 became VSS-1, so
  references to "VSS-1 S-9" in conformance runners line up again.
- All 511 healthcheck tests, 91 lab tests, 106 buyer-ledger tests, 21 SDK tests and
  the conformance runners pass after the rename.

## Brand

The new wordmark and owl mark live in `assets/` and `website/assets/`; usage rules
are in `docs/brand.md`. The mark is the two eyes that spell the "vo" of the
wordmark — the part that reads evidence, not the part that advertises it.
