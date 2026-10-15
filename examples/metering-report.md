# Free conformance baseline — synthetic, not a paid-value demonstration

Scope: sample-internal accounting of a scaffolded single-operation fixture.
Input: metering-sample.jsonl, created with conformance --new-vector; one attempt,
one declared successful operation, one step, zero declared cost units.

## Evidence boundary
This sample demonstrates format and reproduction only. Placeholder identities
must be replaced with real provenance for a customer sample. It does not prove
production correctness, invoice amounts, unit prices or customer value.

## Reproduce locally
agentmeasure conformance --fixture metering-sample.jsonl --json metering-result.json

Use CLI 0.7.1 or later. Version 0.7.0 omitted a required module from the wheel.
Expected for this zero-cost example: 4 PASS, 1 UNPROVABLE (cost preservation); token/cache checks are NOT-SUPPORTED. Zero declared cost is not proof of missing cost fields.
Read the per-invariant verdicts; no --claims file means this checks the sample's
own consistency, not an implementation's reported numbers. Token/cache rules
are not supported by core FMT-002. A PASS is limited to the supplied evidence.

## What a paid review would need to add
The confirmed source-field mapping, actual evidence and supported verdicts,
any discrepancy against the customer's declared metric, reproduction command,
unsupported fields and next verification steps. No discrepancy is invented.

Running the above command alone is free. Additional mapping or applicability review must be agreed before payment; a formatted copy of this output is not the intended paid deliverable.
