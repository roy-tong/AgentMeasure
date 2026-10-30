# Tool catalog

`tools.json` is the product's machine-readable support matrix for domestic and
overseas agent tools. It is **not** a connector inventory.

## Status fields

- `reader_status`: bill fields and billing dimensions have been cataloged.
- `recipe_status`: a deterministic browser/CDP recipe exists.
- `live_bill_status`: a real customer/vendor bill has been validated.
- `ledger_import_channels`: paths the ledger can ingest today (`file`, `cdp`);
  this does not assert that a provider exposes an API.
- `bill_sources`: where the evidence may exist (`cloud_bill`, `usage_export`,
  `platform_dashboard`, `billing_api`, etc.).
- `audit_capabilities`: checks the engine can perform once evidence exists.

Current version: all providers are `cataloged`; `live_bill_validated` is **0**.
Catalog entries are deliberately conservative. Do not add a provider with
`live_validated` unless a real bill, period and account have been tested and the
evidence is retained.

## Commands

```bash
cd buyer-ledger
python3 -m buyer_ledger catalog summary
python3 -m buyer_ledger catalog list --region cn
python3 -m buyer_ledger catalog list --region global --role seller
python3 -m buyer_ledger catalog show anthropic
python3 -m buyer_ledger catalog coverage --period 2026-10
```

`catalog coverage` maps actual ledger providers to the catalog and reports
unknown providers instead of silently treating them as supported.

## Add a provider

1. Add the provider with aliases, region, category, roles, billing models,
   metering units, bill sources, audit capabilities and official pricing URL.
2. Keep `reader_status=cataloged` until bill fields are actually reviewed.
3. Keep `recipe_status=not_built` until a reviewed recipe exists.
4. Keep `live_bill_status=not_validated` until a real bill has been ingested and
   reconciled.
5. Run `python3 -m unittest discover -s tests -t .`; catalog validation checks
   duplicate IDs/aliases, required dimensions and status enums.
