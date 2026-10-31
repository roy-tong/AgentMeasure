# Verovo: implementation status

Reviewed 2026-10-31 against the repository implementation. Available means local implementation, not production validation on every platform.

| Feature | Scope | Status |
|---|---|---|
| V01–V02, V05 | Usage adapters, supported bill recounts and charge review | Available for documented formats; no universal billing connector |
| V03–V04 | Invoice extraction and normalization | Optional `invoice-intake` via invoice2data produces source-linked, unreviewed drafts; OCR beyond dependency capability, tax/credit/refund/FX and task allocation remain planned |
| V06–V07 | Task/run linkage and direct/shared allocation | Available with explicit IDs and versioned rules |
| V08–V10 | Business outcomes, verification flags and task costs | Local case ingestion available; source truth requires review |
| ROI | Verified value / cost and cost per verified success | Available; incomplete input remains a coverage limitation |
| Optimization / assurance | Cost-driven workflow changes and risk pricing | Deferred; no causal savings or insurance claims |

Build: reconciliation semantics, task identity, allocation, outcome rules and economics. Reuse: existing telemetry/billing adapters; optional Docling/invoice2data and DuckDB remain integration candidates, not shipped dependencies. Optional invoice2data performs extraction into a non-booked draft; no vendored fork or mandatory core dependency.

The read-only/local `verovo_invoice_intake` MCP tool returns the same unreviewed, unbooked draft as the CLI; it never updates the economics case.

Reliability update: largest-remainder allocation preserves cents and zero weights; explicit `charge_id` deduplicates usage/bill representations; duplicate outcome references do not multiply value; conflicting verified task states abstain; ROI requires a source and literal boolean verification. Zero verified value produces -100% ROI. Confirmed loss totals exclude estimates and duplicates.
