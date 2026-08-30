# AgentMeasure ↔ Urusilla multi-operation vector 002

Date: 2026-08-28

Urusilla source revision inspected: `42120da3ca63c3b46647a3811fd9151541587ad3`

AgentMeasure release inspected: `v0.2.2`

AgentMeasure tag commit: `b3c82a09ede3274ff79606539cea3ccc708bed67`

## Status and claim boundary

This is a project-authored, synthetic, offline research vector. It is not an
AgentMeasure endorsement, an upstream acceptance, an external reproduction, an
Urusilla adoption, a live model run, a scorer-receipt-backed task result, or a
real provider-cost observation. AgentMeasure v0.2.2 accepts but ignores the
`x_urusilla` extension fields during core validation and aggregation.
The vector is JSONL bridge evidence; it does not exercise UrusillaWire, a
distinct textual syntax, or model-native language use.

Vector 001 used one logical operation. Vector 002 uses the smallest shape found
that preserves the requested different boundaries: two operations, four
attempts, and ten FMT-002 rows.

1. A provider attempt writes cache tokens and fails. Its explicit retry reads
   cache tokens and succeeds.
2. A local required-schema resolution rejects an unpinned schema without a
   provider call. An explicit JSON fallback succeeds, but no scorer receipt
   proves task success, so the task terminal remains incomplete and
   non-effect-authorizing.

No retry, fallback, or cache-source edge is inferred from row order. Each edge
is explicit in the fixture-only Urusilla sidecar.

## Files

- `agentmeasure_urusilla_fixture_002.events.jsonl` — ten FMT-002 event rows.
- `agentmeasure_urusilla_fixture_002.expected.json` — current v0.2.2 aggregate,
  exact sidecar topology, and positive/negative expectations.
- `../tools/validate_agentmeasure_urusilla_vector_002.py` — offline validator.

SHA-256 identities:

- events: `951798b4eb2974833bb0a89ba744b1faa1db443207383fc47e6a5195f4278a8b`
- expected: `d1e6b5f11606c4c02d1075cb64ce13d7c733305969f4616381d14de97ec33c0d`
- validator: `8d06f79d54144063d5e2e6b3652743fdec11c9259a28854aa496ec24ca4596d4`

## Usage and schema-resolution semantics

Cache read/write tokens are subsets of input tokens; they are not added to the
provider total a second time. The three synthetic provider calls preserve
`4 + 3 + 6 = 13` token-equivalent cost units. The local schema-resolution
attempt has measured zero provider calls, `provider_usage = null`, and
`cost_units = 0`; it does not coerce missing provider usage into zero.

The unpinned schema decision is closed:

```json
{
  "conformance_scope": "required-answer-schema",
  "effect_authorized": false,
  "fallback": {
    "media_type": "application/json",
    "value": {
      "reason_code": "required-schema-not-pinned",
      "status": "fallback"
    }
  },
  "format": "urusilla-required-schema-resolution-decision/1",
  "reason_code": "required-schema-not-pinned",
  "route": "json",
  "schema_binding_verified": false,
  "schema_uri": "urn:urusilla:schema:not-pinned:0.1",
  "strict_conformance": false
}
```

The final task terminal records `task_success = null`, `safe_success = false`,
no scorer receipt, incomplete evidence, one unknown-schema rejection, zero
unknown-schema executions, and no effect authority. A successful fallback
operation is therefore not mislabeled as a proven successful task.

## Observed AgentMeasure v0.2.2 result

All ten rows pass the bundled FMT-002 validator. Both `operation_result`
declarations reconcile against their attempt rows. The current aggregator
preserves four attempts and all 13 synthetic cost units:

| Metric | Observed v0.2.2 result |
|---|---:|
| operations | 2 |
| successful operations | 2 |
| attempts per operation | 4 / 2 |
| cost units per operation | 13 / 2 |
| consumption rate | 1 / 2 |

The core operation metrics do not establish task success. FMT-002 has no
task-terminal field, and AgentMeasure does not read the sidecar.

## Reproduced multi-operation grain candidate

The attempt step totals per operation are `[3, 2]`, so the semantic median is
`2.5` over two operations. AgentMeasure v0.2.2 reports
`median_steps_per_operation.value = 5.0` with denominator `1`. Inspection of
`lab/agentmeasure_lab/analysis.py` shows that it sums steps by `assignment_id`
and then takes the median across assignments.

This is a smaller executable reproduction of the previously documented
AM-U-007 candidate. It remains a candidate until the AgentMeasure maintainer
confirms whether one-operation-per-assignment is a required invariant or the
metric implementation/label should change.

## Sidecar guards

The project-side validator checks the exact expected topology and rejects:

- an unknown fixture-sidecar format;
- a success reason attached to an unverified required schema;
- dangling retry and fallback targets;
- a cache read with a missing or non-write source;
- a missing, duplicated, or non-final task terminal;
- an unknown top-level FMT schema identity.

These guards do not turn extension data into AgentMeasure core semantics.

## Offline reproduction

Use an isolated checkout of AgentMeasure v0.2.2. No package installation,
provider call, model call, GitHub Actions run, or paid API is required after
checkout.

```sh
git clone --branch v0.2.2 --depth 1 \
  https://github.com/roy-tong/AgentMeasure.git /tmp/agentmeasure-v022
python3 tools/validate_agentmeasure_urusilla_vector_002.py \
  --agentmeasure-root /tmp/agentmeasure-v022
```
