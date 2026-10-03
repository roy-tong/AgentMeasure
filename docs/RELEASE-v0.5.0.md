# v0.5.0 — the buyer-side verification system, complete

Everything since v0.4.1 lands in one release: the buyer-side verification
pipeline taken from "tools" to "a system a normal user can operate", plus a
full agent-commerce measurement family, plus the console that ties both
together. 450 tests hold the line (248 at v0.4.1). Zero runtime
dependencies; no network code (an import guard covers every new module);
judgement stays 100% rule-based; no message text is ever read.

## The buyer-side review pipeline

`prepare` maps a native Intercom/Zendesk export onto the canonical columns —
judgement columns stay empty for human review, native signals travel as
`hint_*` leads, every value carries `prov_*` provenance, and `--inspect`
aligns before any number exists. `recount` applies the vendor's own
published rules line by line, findings in both directions, `UNPROVABLE`
never guessed — with an optional `--contract` overlay whose outcome-standard
findings are a separate lane, never netted into the claim. `dispute` builds
the negotiable pack; `recovery` records what the vendor actually conceded;
`crosscheck` puts the buyer's billing ledger beside the export and names
every disagreement without resolving it; `crm-join` fills empty judgement
cells from the buyer's own business records and names conflicts. `verify`
composes all lanes into one Verified Ledger; `rules-diff` gates material
vendor-rule changes for the monthly ritual.

## Agent Commerce Measurement

The chain where the click disappears, measured from the merchant side:
`commerce-ledger` produces the measurement receipt (metric + value +
evidence, materiality vs the naive dashboard in currency AND percent), with
live/replay/synthetic segregated at the schema level and a canonical retry
vector pinned in CI (1 Operation / 2 Attempts / 1 verified order /
net GMV = 0). The operating layer on top: `pnl-trees` (Organic and Paid,
never blended), `cm-ledger` (the seven-line contribution margin),
`demand-audit` (channel potential vs operator performance), `intent-taxonomy`
(Operating Cell = cluster × surface × proposition), `decision-audit`
(auto/approval/forbidden with the policy citation on every execution), and
`benchmark-export` (cross-brand aggregates only — customer data cannot
structurally enter the shared pool).

## The console

`agentmeasure console` renders the verification documents as one offline
app: sidebar navigation over two user journeys (vendor bill review; agent
channel operations), an overview workbench whose stage states are derived
from the documents, hash-routed views, a print mode that flattens every
view, and a test-enforced copy discipline that refuses draft or internal
language. Single file, no network, escaped values. Design checked with the
impeccable Operate-mode playbook and its detector (zero findings).

## Also in this release

`outcomes` — the outcome-unit verification engine (fail-closed: counted +
criteria_unproven is an inconsistency, refused); outcome-unit schema v0.2
covering qualified_lead, completed_case, action (allowance-aware), and
usage_aggregate — one evidence plane across the billing stages;
`period-compare` for the monthly delta; `template` for appendix-E reuse;
`certify` grading artifacts on the Stage 0..3 adoption ladder with a
deterministic digest; `incrementality` producing treatment-vs-holdout
statistics that never masquerade as a verdict.

## Channels

- GitHub Release (this page) — ships on tag push.
- npm `@agentmeasure/mcp` — published by the same workflow when the token
  is present.
- PyPI `agentmeasure` — the workflow attempts trusted publishing; the
  PyPI-side publisher configuration is a project-owner setting. If this
  release's publish job fails the same way v0.4.1's did, configure the
  pending publisher on pypi.org and re-run the failed job — no rebuild
  needed.
