# Verovo

<p align="left"><img src="assets/verovo-logo-card.png" alt="Verovo" width="300"></p>


**Verify AI service charges and delivery with evidence your team can check.**

Verovo helps AI service buyers connect applicable billing rules with
event records and business requirements. Start with a specific AI support bill
or an upcoming acceptance or renewal decision.

Today, the open-source CLI re-counts supported billing exports, organizes
findings and records follow-up outcomes. Broader buyer review services are
being validated case by case; this is not a universal contract or quality checker.
Local CLI commands do not upload data.

| Your task | Start here |
|---|---|
| A specific AI support billing question | [Describe the task and check fit](https://roy-tong.github.io/verovo/first-look.html#contact), or run the free recount below |
| An upcoming acceptance or renewal decision | [Discuss the decision and evidence needed](https://roy-tong.github.io/verovo/first-look.html); project scope is exploratory |
| A local log anomaly or one metering sample | [Free measurement runs](https://roy-tong.github.io/verovo/services.html) — bring a sanitized sample, we run the check |
| Contribute a rule, counterexample or adapter | [Maintainer resources](#for-tool-maintainers-and-providers) |

[Website](https://roy-tong.github.io/verovo/) · [中文](README.zh-CN.md) · [Healthcheck guide](healthcheck/README.md) · [Release notes](https://roy-tong.github.io/verovo/releases.html)

## Two questions, different next steps

- **Does the charge follow the applicable agreement?** A supported difference
  can inform a vendor review. A finding is not an accepted claim or a refund.
- **Does delivery meet your business requirements?** This can inform acceptance,
  remediation or renewal. A stricter buyer requirement does not by itself make
  an existing charge incorrect.

Support operations supply the business facts; finance or procurement owns the
spend decision. Missing evidence stays unknown. We separate findings in both
directions, evidence gaps, vendor acceptance and actual refunds or used credits.

Since 2026-10-21 the project is entirely free and open source — the paid
diagnostics and the commercial fee explorations have been retired. Free
measurement runs do not cover enterprise invoice or delivery reviews.

Read the [buyer scope](docs/product-scope.md) and
[commercial and open-source boundaries](docs/commercial-narrative.md).

## Re-count a bill in 60 seconds

Save this five-line sample as `export.csv` (synthetic data, real command):

```csv
conversation_id,human_agent_participated,issue_addressed,customer_recontacted_within_window,vendor_billed
c-001,N,Y,N,Y
c-002,N,Y,N,Y
c-003,N,Y,N,Y
c-004,Y,Y,N,Y
c-005,N,Y,Y,Y
```

```bash
# 0.9.0 is tagged on GitHub; the PyPI project `verovo` is pending its first publish.
pip install "git+https://github.com/roy-tong/verovo@v0.9.0#subdirectory=healthcheck"
# once published: pip install verovo
verovo recount --export export.csv --vendor zendesk
```

The output prints the vendor's rule with its public source, findings in both
directions, then the dollars:

```
Dollars (at USD 2.0 per resolution)
overcharge identified       2.00
undercharge (vendor favour) 0.00
net variance                2.00
```

No CSV at hand? `verovo recount --sample` runs the same bundled synthetic export in CLI 0.8.0.
In this synthetic example, four rows remain unsettled; $8 is not a verified
billable total. The $2 is a rule-priced finding, not recovered money.

Three reproducible showcase cases (overcharge with refused guesses, findings
in both directions, the contract lane) live in
[examples/showcase](examples/showcase/README.md) with frozen expected outputs
that CI compares on every change.

## Review domestic and overseas tool bills (research preview)

Buyer Ledger extends the same evidence discipline to agent-tool spending: model
tokens, search calls, credits, browser hours, sandbox seconds, OCR pages, voice
characters, generated outputs and seats. The product separates invoice facts,
platform usage and rule-based recomputation; a tool is not marked “supported”
merely because its logo is in a table.

- **Buyer view:** check platform, direct and cloud-marketplace charges, including
  free quota, prepaid packs, credits and third-party cash.
- **Seller view:** audit whether metered usage is represented in billing; keep
  unpriced or unlinked usage as an evidence gap, not “leakage revenue.”
- **Catalog:** 26 domestic and overseas tools, with billing models, metering
  units, bill sources, audit capabilities and validation status. See
  [catalog/tools.json](buyer-ledger/catalog/tools.json).
- **No-API bill portals:** attach a user-started Chrome over a loopback CDP
  endpoint, replay a reviewed recipe, download the bill and ingest it through
  the same audit pipeline. Credentials are never handed to the tool.
- **Boundary:** tools are **cataloged**, not live-connected. No tool has a live
  customer-bill validation yet, and generic CSV/TSV plus CDP plumbing are tested
  with synthetic fixtures. Read [Buyer Ledger](buyer-ledger/README.md) and its
  [review limits](buyer-ledger/REVIEW-20261029.md).
- **Complaint evidence (exploratory):** SURE 1.6 study of 1,949 public discovery
  records → 150 reads → **66 strict evidence records**. Prepaid-credit expiry,
  unexpected charges, auto-recharge and metering mismatch dominate; price
  increases are only 2/66. Audit fails 3/12 gates (3/18 vendors, one region,
  7 counterexamples); it is not a complaint rate or market validation. See the
  [bounded case summary](buyer-ledger/COMPLAINTS-20261029.md).
- **50k discovery expansion:** the public discovery corpus now holds **50,000**
  unique records (HN 49,090 + six existing source families). Strict evidence
  remains **66**, full reads remain **150**, and the audit remains 9/12 and
  exploratory. Fifty thousand records are not fifty thousand users or evidence.
- **Hypothesis stress test:** on the 50k layer, H1's evidence shape is supported
  (manual core rate: credits 30% vs price 6%) but raw mentions are near parity;
  H2 is **not supported** (the credit/subscription difference reverses within
  HN); H3 supports only English-source invisibility; H4's keyword-screen
  downgrade rate is **71.6%** (95% CI 66.2–76.4); H5 remains suggestive. No
  hypothesis was promoted to validated.
- **CDP discovery, phase 1:** a local Chrome CDP pass captured 2,734 public
  discussions → **2,437 curated discovery records** (1,708 direct-vendor,
  729 generic AI/API billing) plus 26 official pricing pages. This is a discovery
  corpus, not strict evidence or customer invoices.

```bash
python3 -m buyer_ledger catalog summary
python3 -m buyer_ledger catalog list --region global --role buyer
python3 -m buyer_ledger catalog coverage --period 2026-10
python3 -m buyer_ledger report --period 2026-10 --perspective seller --out seller.md
python3 -m buyer_ledger fetch --recipe recipe.json --period 2026-10 \
  --cdp http://127.0.0.1:9222 --analyze --out report.md
```

The support matrix and case notes are in
[website/tools.html](website/tools.html); the Pages URL becomes available after
the normal website deployment.

## Repeat a billing review

For local-only handling, run the CLI on each new period's export. The optional
[GitHub Actions workflow](RECONCILE.md) requires a separate private repository
and uploads data and reports to GitHub. Public forks are not private storage.
Each period needs a fresh, reviewed export; no vendor data is fetched automatically.

Six vendor rule sets ship today — Intercom Fin, Zendesk AI Agents, HubSpot
Breeze, Salesforce Agentforce, Ada and a generic per-resolution baseline —
each citing its source and confidence grade
(`verovo recount --list-vendors`). When a recount disagrees with the
invoice: `verovo prepare` maps a native Intercom or Zendesk export onto
the canonical columns, `verovo dispute` builds the Dispute & Recovery
Pack, and `verovo recovery` records what the vendor actually conceded,
counted separately from the claim.

A recount is arithmetic, not a verdict: rows without enough evidence land in
`cannot settle` and are removed from the claim, never zeroed. "No finding" is
a valid outcome. Vendor recounting is a free CLI capability, not one of the
two paid services below.

## Start with your own machine (free)

`verovo check` inspects your local Codex / Claude Code sessions for
duplicate records, retry amplification and token anomalies — the same evidence
discipline pointed at your own logs. `verovo demo` runs a bundled
synthetic session with no account and no upload. Missing evidence stays
unknown; a retry is not automatically a second logical operation.

Python 3.9+. CLI **0.8.0** on [PyPI](https://pypi.org/project/verovo/);
Provider SDK **0.2.0** on [npm](https://www.npmjs.com/package/@verovo/mcp),
verified 2026-10-15. These packages have separate version numbers.
On macOS/Linux use `python3 -m pip` if needed; on Windows use `py -m pip`.
For permission or
“externally managed” errors, use the [virtual-environment instructions](https://roy-tong.github.io/verovo/#install-help).
With both runtimes present, auto-discovery prefers Codex; use
`verovo check --runtime claude` for Claude Code. No logs in the default
seven-day window? Try `--all` or an explicit `--dir` and `--runtime`. A missing
input is not a passing check. [More recovery steps](https://roy-tong.github.io/verovo/#how).

### Compare Claude response evidence across files

```bash
verovo response-audit first-session.jsonl fork-session.jsonl --json responses.json
```

This read-only command groups supplied response IDs and shows repeated usage
snapshots, conflicts and missing fields. It does not rewrite logs, choose a
winning snapshot or compute a session/invoice total. See the
[response-audit guide](docs/response-audit.md).

## Free measurement runs

The tools are free and local. If you want a human-run check on your own data,
that is free too: bring 20–100 sanitized rows (or a public export) and we run a
measurement check, usually within 48 hours of a clean sample. Findings are
stated as checkable claims; where your surface cannot prove something, the
report says UNPROVABLE instead of guessing.

What we ask — never required: permission to publish the fixture under your
handle with the claim boundary you state (nothing customer-identifying; hash or
drop identifiers), and if the check was useful, a star on the repo — never a
condition.

- Start in [issue #6](https://github.com/roy-tong/verovo/issues/6) (public, so the next reader learns from your run), or email tongroy18@gmail.com
- Guide: [docs/provider-onboarding.md]
- Run the same review yourself: [docs/review-method/](docs/review-method/README.md) — intake checks, mapping, commands and report templates behind every free run(docs/provider-onboarding.md) — three entry paths, five steps, and what counts as a successful run

The previously offered $10/$20 paid diagnostics were removed on 2026-10-21; the
project is now entirely free and open source.

To prepare a summary locally:

```bash
verovo check --json report.json
verovo share report.json --out summary.json
verovo validate summary.json
```

`--out` writes immediately on your machine. Inspect the file before you choose to
send it. Nothing is automatically uploaded. "No finding" and "not enough
evidence" are valid outcomes. Tool bugs can be reported in
[Issues](https://github.com/roy-tong/verovo/issues/new), with a redacted
reproduction.

## For tool maintainers and providers

| Resource | Use it for |
|---|---|
| [Conformance pack](conformance/pack/README.md) | Check fixtures and reported metrics; PASS / FAIL / UNPROVABLE |
| [Provider SDK](sdk/README.md) | Capture canonical observations from MCP tool handlers: `npm install @verovo/mcp` |
| [Core specification](standard/CORE.md) and [VSS-1](standard/SETTLEMENT.md) | Define measurement grains and the evidence needed for claims |
| [Claims index](https://roy-tong.github.io/verovo/claims.html) | Inspect dated findings, reproductions and upstream responses |
| [Lab](lab/README.md) | Existing experimental tooling; no hosted product commitment |

The buyer tools above (`recount`, `prepare`, `dispute`, `recovery`) share one
[end-to-end walkthrough](https://roy-tong.github.io/verovo/first-look.html).
They are free CLI capabilities, not one of the two current fixed-price
services. Current development priorities are in the [roadmap](ROADMAP.md).

## Evidence and limits

The [September audit report](campaigns/audit-report-2026-09.md) documents the
110-tool review. Individual findings and subsequent corrections are linked in
the claims index. Engineering evidence does not establish paid demand, customer
savings or a right to a refund. Customer value and repeat purchase remain under validation.

511 Healthcheck unit tests passed on 2026-10-15. See [CI](https://github.com/roy-tong/verovo/actions/workflows/conformance.yml)
for current results and [v0.8.0](https://github.com/roy-tong/verovo/releases/tag/v0.8.0)
for the release scope. Example fixtures are not production customer data.

## Open-source commitments

- MIT-licensed tools and public rules remain free. Paying does not change a verdict.
- Analysis runs locally. Sharing a sanitized sample is your explicit choice.
- No paid rankings or recommendation slots; no payment custody.

[Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Governance](GOVERNANCE.md) · [Agent instructions](AGENTS.md) · [Whitepaper](whitepaper/measuring-software-used-by-ai-agents.md)

[Task scope and validation priorities](docs/product-scope.md) · [Developer guide](docs/developer-guide.md)

## Why optional paid help?

The public cases and free explanations stay free. A paid review is agreed human
work on a remaining decision, not a secret scanner or automatic certification.
If existing output answers the question, we recommend self-service. See the
[paid review scope](docs/paid-review-scope.md).
