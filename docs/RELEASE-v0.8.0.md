# v0.8.0 — Evidence-qualified recounts and repeatable reviews

CLI release 0.8.0; Provider SDK version remains 0.2.0.

`verovo recount --sample` runs a bundled five-row synthetic export. Three
showcase cases cover findings in both directions, missing evidence and a separate
buyer contract lane. They are demonstrations, not customer recovery results.

The report headline distinguishes published-price estimates from verified invoice
totals, displays unsettled rows, and labels signed net variance without implying
refunds. Zero identified variance does not clear an incomplete bill.

The optional monthly workflow requires an independent private repository and
uploads data to GitHub. It installs the reviewed source revision, checks the
billing period and input hash, and stops stale scheduled input. Optional issues
track unresolved or offsetting findings per vendor and period. Each new period
still needs a reviewed export; see RECONCILE.md. Local CLI handling remains available.

The website routes developers to local checks and $10/$20 bounded help, and buyers
to separate free feasibility review. A PDF total alone cannot support recount.
Vendor rule sources remain inspectable; no payment or PMF is established by tests.

Validation: 511 Healthcheck tests, including 21 new regressions for report evidence
boundaries, stale input, path confinement and unresolved/offsetting findings.
Upgrade: `python -m pip install --upgrade verovo`.

`verovo response-audit FILE.jsonl [FILE.jsonl ...]` adds a read-only Claude
cross-file evidence view: response identity reuse, usage conflicts and missing
fields. It never rewrites logs, selects first/last/max usage or adds cache subsets
to totals. Session and invoice totals remain unknown. Ten regressions cover
missing IDs, conflicting snapshots, bad input and output overwrite protection.
