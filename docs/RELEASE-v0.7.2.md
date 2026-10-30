# v0.7.2 — Route user inputs to the right checker

Canonical provider observations and FMT-002 are different contracts. A valid provider submission previously produced unrelated FMT-002 missing-field errors when passed to conformance.

`verovo inspect-input sample.jsonl --json routing.json` now identifies the input shape and explains the next step. Recognition never claims schema validation or a measurement verdict: both are explicitly NOT-RUN. Mixed, invalid, ambiguous, empty and unsupported inputs return exit 2. No source rows are included in the report, and no fields are invented or converted.

Conformance now intercepts recognized incompatible inputs with a targeted recovery path. Existing FMT-002 validation remains mandatory. Canonical semantic analysis still uses the provider workflow; this release does not claim universal input support, token/cache cost verification or live quota monitoring.

Upgrade: `python -m pip install --upgrade verovo`.

Validation: 487 Healthcheck tests; installed-wheel smoke with input routing; required repository checks. SDK remains 0.2.0. Research feedback and test results do not establish payment or PMF.
