# v0.7.1 — Fix installed conformance and first-run friction

A clean PyPI install of 0.7.0 could run Healthcheck but failed on conformance
with `No module named verovo_healthcheck.lab.analysis`. This patch includes that
subpackage in the wheel and exercises it in the installed-artifact smoke test.

- `conformance --new-vector` defaults to the caller's working directory, not the Python installation.
- `conformance` without a fixture returns a useful input error and a sample-generation command.
- `share --out` says the file was saved locally and should be inspected; it no longer claims the user already reviewed it.
- Zero-cost fixtures retain their conservative UNPROVABLE verdict, with an accurate reason rather than claiming that cost fields are absent.
- Website first-run guidance, illustrative reports and email templates cover no-mail-client, missing-input and checkout-pending paths.

## Upgrade

```bash
python -m pip install --upgrade verovo
verovo conformance --new-vector my-sample --out ./vectors
verovo conformance --fixture ./vectors/my-sample-001/verovo_my_sample_fixture_001.events.jsonl
```

The generated fixture is synthetic: 4 PASS, 1 UNPROVABLE for zero-cost preservation;
token/cache rules remain NOT-SUPPORTED. Replace placeholders with real evidence
before interpreting your own data. SDK version remains 0.2.0.

Validation: 479 Healthcheck unit tests, installed-wheel smoke including sample
generation and conformance, and the repository's required checks. User-journey
simulations are not customer adoption or payment evidence. Online checkout is
still being configured; no purchase or refund was simulated as a real transaction.
