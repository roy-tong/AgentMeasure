# v0.4.0 — PyPI, Claude Code adapter, conformance pack, settlement bundle

First release published to **PyPI** — `pipx run agentmeasure` works with no
repo checkout. Healthcheck remains local-only: no network calls at runtime,
no upload, no account.

## Highlights

- **PyPI distribution** (`agentmeasure`): `pipx run agentmeasure demo` /
  `pipx run agentmeasure check` — Claude Code adapter v1 joins the Codex
  rollout reader (HC-01..06 audit checks: duplicate records, retry chains,
  consecutive tool failures, operation-resolution coverage, cache accounting,
  token stability). Missing evidence is **UNPROVABLE**, never silently zero.
- **Embedded conformance pack** (`agentmeasure conformance`, also a
  [GitHub Action](../../action.yml)): run the fixture suite against your own
  parser — plain JSONL + expected totals, no runtime install.
- **OTel / Prometheus exports** and run trends (`agentmeasure trend`).
- **Settlement bundle drafts** for outcome-based billing
  (`agentmeasure settle`) — see
  [proposals/2026-09-18-settlement-bundle-design.md](../proposals/2026-09-18-settlement-bundle-design.md).

## Ecosystem

- **[AMS-1 settlement standard](../standard/SETTLEMENT.md)** (Draft 0.1):
  verdict taxonomy, clauses S-1..S-8 each enforced by a named test,
  machine-readable [clause manifest](../standard/settlement.manifest.json),
  and a one-pager statement generator (`agentmeasure settle --format md`)
  with input-sha256 provenance and a third-party reproduction block.
- **21 verified metering fixes merged upstream** across the ~110-tool audit —
  including langfuse, litellm, and codeburn. Full report:
  [The Token-Accounting Bug Report](../campaigns/audit-report-2026-09.md).

## Checks

`190` healthcheck unit tests · `21/21` metric vectors · `15/15` outcome-audit
vectors · `9/9` delegation vectors · core gate, external fixtures, and pack
selftest all green at this tag.
