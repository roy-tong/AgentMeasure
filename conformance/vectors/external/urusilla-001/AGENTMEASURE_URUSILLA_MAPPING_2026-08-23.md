# AgentMeasure FMT-001/002/003 ↔ Urusilla event mapping

Date: 2026-08-23 (Asia/Seoul)

Status: project-authored interoperability analysis and synthetic fixture; no external run

AgentMeasure release inspected: `v0.2.1`

AgentMeasure annotated tag object: `09e19243f69be850afded3153796c5aee8918498`

AgentMeasure tag target commit: `20807ad39483a6b78d2db056d78af6e4c7196bf4`

Urusilla source baseline inspected: `ee480d1d4a249ea1c104761ee8d63a5557773137`

## Bottom line

AgentMeasure FMT-002 is close enough to carry a **lossy projection** of an
Urusilla attempt/operation ledger, and its v0.2.1 aggregator correctly keeps
the fixture's four attempt costs in the numerator rather than deduplicating
them. It is not currently an isomorphism. Stable operation and attempt IDs,
explicit retry and fallback edges, cache roles, provider-usage components,
billed-cost units, measurement-boundary provenance, and a task terminal are
not represented by the released FMT-002 vocabulary.

The released schema and bundled validator also expose testable gaps. Most
importantly, the bundled validator returns after evaluating `oneOf`, so it does
not evaluate the root schema's sibling `required`, `properties`, and type
constraints. Separately, the aggregator trusts the declared
`operation_result.attempts` and `operation_result.outcome` without reconciling
them against attempt rows. These are **candidate AgentMeasure defects for Roy
Tong to confirm**, not claims that Langfuse has a defect.

This work responds to Roy Tong's public collaboration offer. It is not a
Langfuse decision, endorsement, adoption, or official integration.

## 1. Primary sources and evidence boundary

### 1.1 Public discussion

- [Langfuse Discussion #16383](https://github.com/orgs/langfuse/discussions/16383)
  was opened by `roy-tong`, not by the Langfuse team.
- [Roy's operation/attempt response](https://github.com/langfuse/langfuse/discussions/16383#discussioncomment-18114026)
  says that AgentMeasure treats retry chains as first-class and encourages
  producers to declare `operation_id`.
- [Roy's mapping offer](https://github.com/langfuse/langfuse/discussions/16383#discussioncomment-18115059)
  says that FMT-001/002/003 carry `operation_id`, `attempt_id`, `retry_of`,
  outcome, and usage-with-absent-allowed. The released files below do not
  literally contain all of those fields; this document records that divergence
  rather than silently normalizing it away.
- [The Urusilla maintainer's source event-row proposal](https://github.com/langfuse/langfuse/discussions/16383#discussioncomment-18109190)
  is the source of the conceptual fields mapped here.

### 1.2 AgentMeasure v0.2.1 materials

All repository links in this section are pinned to commit
`20807ad39483a6b78d2db056d78af6e4c7196bf4`.

| Artifact | Exact path | Git blob | File SHA-256 | What it establishes |
|---|---|---:|---:|---|
| [FMT-001](https://github.com/roy-tong/AgentMeasure/blob/20807ad39483a6b78d2db056d78af6e4c7196bf4/lab/schemas/experiment-manifest.schema.json) | `lab/schemas/experiment-manifest.schema.json` | `f47f002a255c873974580033f5523ed0028c0db1` | `057ff406ce3a65402b4c4ae4eb510e7030ec60b90bdedf5e929e4b00faa30d6e` | Preregistered experiment design, assignment, metric, guardrails, budget, and seed |
| [FMT-002](https://github.com/roy-tong/AgentMeasure/blob/20807ad39483a6b78d2db056d78af6e4c7196bf4/lab/schemas/funnel-event.schema.json) | `lab/schemas/funnel-event.schema.json` | `9e13a6db01fef1e21c89d576493d6bf5dc038a83` | `f4ba3a97e803bbb605a0d228c49c68702e73ce1b2bddfbf8ed0ed392500d0bc7` | Event rows for reach, choice, attempt, operation result, and consumption |
| [FMT-003](https://github.com/roy-tong/AgentMeasure/blob/20807ad39483a6b78d2db056d78af6e4c7196bf4/lab/schemas/report.schema.json) | `lab/schemas/report.schema.json` | `89033fe831bd6d1698df04c5a1c48444a989c0f3` | `3cad76afacbe7147897427a4087c06c62b956a99f4bb275b9ea907acd6198cc0` | Derived report envelope |
| [Event constructors](https://github.com/roy-tong/AgentMeasure/blob/20807ad39483a6b78d2db056d78af6e4c7196bf4/lab/agentmeasure_lab/funnel.py) | `lab/agentmeasure_lab/funnel.py` | `20b7f6a8b069afdac07d6c95565e289b289c8b98` | `b61608806e7296097ecd6d511f4e169864dea8bb3a3c035292f74d7eea70d145` | Intended operation-success-any rule and event construction |
| [Aggregator](https://github.com/roy-tong/AgentMeasure/blob/20807ad39483a6b78d2db056d78af6e4c7196bf4/lab/agentmeasure_lab/analysis.py#L62-L146) | `lab/agentmeasure_lab/analysis.py` | `4385245ad58eac1dad9e78276688e788551e9161` | `1239423d3f83a871b7369e34ff8e2b6964ab701b254a4df95baa41b089181985` | Exact aggregate equations used below |
| [Bundled validator](https://github.com/roy-tong/AgentMeasure/blob/20807ad39483a6b78d2db056d78af6e4c7196bf4/lab/agentmeasure_lab/schemas.py#L31-L108) | `lab/agentmeasure_lab/schemas.py` | `1ff08afcabff838e50637cc05d7864f4eff88389` | `ac2564a3ce435e313594f76fea87f5d22ee5258ae0deb0abeee8816b4ba6e7f5` | Zero-dependency schema-subset implementation |
| [Codex adapter](https://github.com/roy-tong/AgentMeasure/blob/20807ad39483a6b78d2db056d78af6e4c7196bf4/lab/agentmeasure_lab/harness_cli.py#L220-L272) | `lab/agentmeasure_lab/harness_cli.py` | `063dfcc2dc1c404b7b10a799390d9e5ee144ad9d` | `3238c72273659df6af80249d7616213d413a20d53b11a26bdcb2d61c7183192e` | v0.2.1 maps episode tokens to attempt `cost_units` and derives one operation |

The [v0.2.1 release](https://github.com/roy-tong/AgentMeasure/releases/tag/v0.2.1)
reports a live Codex A/B run (four tasks × two variants), 188,520 versus
215,021 tokens per operation, and an honest null at `n=4` per arm. The release
API exposed one attached asset when inspected on 2026-08-23:
`agentmeasure-mcp-0.1.1.tgz` with published digest
`sha256:d3b83a1d62ca438465767773636a7a7e7e4dda2429bd055ac3ce6162e61baeae`.
The tag tree and attached assets did not expose the live run's preregistration,
`events.jsonl`, `run.json`, or `report.json`. Therefore the A/B numbers are
recorded here as **maintainer-reported release results**, not independently
recomputed evidence. The schemas and engine source *were* independently
inspected at the pinned tag.

### 1.3 Urusilla implementation surface

The public Discussion row is a proposed interoperability row, not the exact
current Urusilla result-event object. At source baseline
`ee480d1d4a249ea1c104761ee8d63a5557773137`:

- [`initial_goal_eval/verifier.py`](https://github.com/jaden3824/urusilla/blob/ee480d1d4a249ea1c104761ee8d63a5557773137/initial_goal_eval/verifier.py#L74-L206)
  requires each result event to have exactly `sequence`, `phase`, `task_id`,
  input/output digests, a usage-receipt digest, and a structured `usage` object.
- [`initial_goal_eval/provider_artifact_store.py`](https://github.com/jaden3824/urusilla/blob/ee480d1d4a249ea1c104761ee8d63a5557773137/initial_goal_eval/provider_artifact_store.py#L177-L289)
  binds a provider call to `episode_id`, `turn_index`, `attempt_index`,
  `purpose`, an idempotency key, and a digest-derived `call_id`. This attempt
  identity is not currently projected as a top-level result-event
  `operation_id`/`attempt_id`/`retry_of` triple.
- [`initial_goal_eval/contract.py`](https://github.com/jaden3824/urusilla/blob/ee480d1d4a249ea1c104761ee8d63a5557773137/initial_goal_eval/contract.py#L36-L73)
  defines setup, sender, router, receiver, repair, fallback, tool, safety, and
  judge phases. These are accounting phases, not automatically AgentMeasure
  attempts.
- [`initial_goal_eval/statistics.py`](https://github.com/jaden3824/urusilla/blob/ee480d1d4a249ea1c104761ee8d63a5557773137/initial_goal_eval/statistics.py#L88-L116)
  computes whole-session task success and complete token cost across all arms.

Consequently, the mapping below has two layers: the public conceptual row and
the fields actually backed by the current Urusilla evidence implementation.

## 2. Field-by-field mapping

Classification vocabulary:

- **direct** — same information and compatible grain;
- **lossy** — a projection exists but drops identity or meaning;
- **absent** — no released FMT-002 field carries the information;
- **ambiguous** — more than one defensible projection exists;
- **extension-only** — FMT-002 currently accepts an extra property, but the
  AgentMeasure schema and aggregator assign it no meaning.

| Urusilla conceptual field | Current Urusilla backing | AgentMeasure v0.2.1 projection | Class | Finding |
|---|---|---|---|---|
| `task_id` | Result events and task results bind a frozen task | `task_id` | direct | Same label grain. FMT-002 does not define a task-terminal event or validate one task outcome. |
| `operation_id` | No top-level result-event field; route/task structure can delimit work | `operation_index` | lossy | A stable ID becomes a positive integer. Its scope and global uniqueness are not specified or enforced. |
| `attempt_id` | Provider `call_id` plus `attempt_index`; result event has `sequence` | `attempt_index` | lossy | The stable identity and receipt binding disappear; index uniqueness is not enforced. |
| `retry_of_attempt_id` | Not yet a top-level result-event field | none | absent | Ordering must not be treated as proof of a retry edge. This field named in Roy's comment is absent from released FMT-002. |
| `kind` | `phase` distinguishes receiver, repair, fallback, tool, and other accounting work | `event` distinguishes attempt/result/consumption | lossy | `event=attempt` gives grain, not whether the attempt was primary, repair, fallback, or tool work. |
| `cache_role` | Proposed row; provider-specific usage can be retained in receipts | none | absent | Cache write/read attribution cannot survive the core FMT projection. |
| `provider_usage` | Nullable input/output/reasoning/unclassified/provider-total/total plus accounting status and receipt digest | `cost_units` | lossy | FMT-002 has one required non-negative number, no component categories, receipt, unit, or unknown/null state. |
| `billed_cost` | Proposed row; current result ledger focuses on token usage | `cost_units` | ambiguous | `cost_units` is abstract. The v0.2.1 Codex adapter happens to use one unit per token, not currency. Billed currency must not be inferred. |
| `outcome` | Task result, disposition, safety result, and provider terminal evidence live at distinct grains | `outcome` on attempt and operation result | direct in vocabulary, ambiguous in derivation | Both use success/failure/unresolved-like states, but FMT does not reconcile operation outcome with its attempts. |
| `fallback_of` | `fallback_from` and fallback-phase evidence exist in the route/result surface | none | absent/ambiguous | A fallback may be projected as another attempt of one intent or a new operation. The released format cannot preserve the declared edge. |
| `boundary_source` | Proposed row; current evidence binds operator, source kind, digests, and receipts | none | absent | `harness_id` identifies a producer and `rules_version` identifies rules; neither expresses runtime-declared versus SDK/trace-inferred confidence. |
| `sequence` | Strictly increasing and unique within an arm | none | absent | File order is observable, but FMT-002 has no normative append-only sequence. |
| `usage_receipt_sha256` | Required when measured usage is present | none | absent | FMT cost has no receipt-level integrity binding. |
| `task_outcome` | Scored and safety-qualified task result | no task-terminal event | absent | `operation_result` and `consumption` are not equivalent to safe task completion. |

### 2.1 What FMT-001 and FMT-003 add

FMT-001 usefully preregisters the task set, harnesses, factors, variants,
balanced assignment, primary metric, guardrails, analysis, budget, and seed.
It does not carry attempt rows or the retry graph. FMT-003 carries the report
envelope and an open `metrics` object, but it does not normatively define the
event-level fields missing from FMT-002. Therefore FMT-001/003 strengthen the
experimental discipline around a projection; they do not make the event
projection lossless.

## 3. Differences, ambiguities, and candidate defects

### 3.1 Legitimate model differences

1. AgentMeasure Lab measures a controlled Reach → Choice → Success →
   Consumption funnel. Urusilla's ledger additionally needs replayable
   communication, safety, fallback, and total-task-cost evidence.
2. FMT-002 intentionally omits timestamps for deterministic replay. Urusilla
   also does not need wall-clock timestamps to map the proposed row.
3. Urusilla input/output and usage-receipt digests have no FMT counterpart.
   This is a narrower AgentMeasure evidence surface, not automatically a bug.
4. `latency_ms` is an FMT attempt observation while current Urusilla aggregate
   claims focus on token cost and safe task completion. No direct claim should
   be inferred in either direction.

### 3.2 Semantics requiring an explicit bridge policy

1. Define whether a fallback preserves one logical intent (`attempt`) or begins
   a new intent (`operation`) before projection.
2. Define the scope of `operation_index` and `attempt_index` as at least
   `(experiment_id, assignment_id, operation_index[, attempt_index])`.
3. Declare the unit and observation state of `cost_units`. Provider tokens,
   billed currency, latency cost, and a synthetic score are not interchangeable.
4. Keep missing usage unknown. Do not encode unknown as `0` merely to satisfy
   FMT-002.
5. Keep task success in an Urusilla sidecar until AgentMeasure defines a task
   terminal and its relationship to operations.

### 3.3 Candidate AgentMeasure spec or implementation defects

These findings should be proposed upstream as small reproducible tests, not as
accusations.

#### AM-U-001 — comment/schema vocabulary divergence

Roy's public offer names `operation_id`, `attempt_id`, `retry_of`, and
usage-with-absent-allowed. Released FMT-002 instead defines
`operation_index`, `attempt_index`, and required numeric `cost_units`; it has no
`retry_of`. Resolution may be a newer uncommitted design, shorthand in the
comment, or missing schema fields.

#### AM-U-002 — unknown usage cannot be represented normatively

For an `attempt`, FMT-002 requires `cost_units`, whose root property schema is a
non-negative number. `null` is not valid under Draft 2020-12. Using `0` for an
unobserved value makes unknown usage indistinguishable from a measured zero and
can understate cost.

#### AM-U-003 — bundled `oneOf` validator skips sibling constraints

The bundled validator checks `oneOf` first and returns immediately after one
branch matches. Draft 2020-12 requires sibling keywords to apply as well. A
minimal `attempt` object containing only the branch-required fields passed the
bundled validator even though it omitted root-required `schema`,
`experiment_id`, `assignment_id`, and the other base fields. A second mutation
with `operation_index="one"`, `cost_units=null`, and `replicate=0` also passed
the bundled validator. This is an implementation defect independent of whether
FMT-002 remains permissive to extensions.

#### AM-U-004 — operation summaries are not reconciled to attempts

The schema and aggregator accept an `operation_result` declaring
`attempts=999` and `outcome=failure` next to the fixture's four attempts,
including a successful fourth attempt. The aggregate then reports 999 attempts
and zero successful operations. The stated `op-success-any/1` rule exists in
constructor documentation and measurement labels, but it is not enforced at
the event-set boundary.

#### AM-U-005 — duplicate and relationship integrity is unspecified

No event identifier, append-only sequence, or uniqueness constraint prevents
duplicate `attempt`, `operation_result`, or `consumption` rows. FMT-002 shape
validation alone cannot enforce cross-row uniqueness, but a conformance runner
can and should.

#### AM-U-006 — extensions are accepted but semantically unowned

FMT-002 omits `additionalProperties: false`, so the fixture's `x_urusilla`
sidecar is valid under the JSON Schema. The official aggregator ignores it.
This is useful for experimentation but must not be described as AgentMeasure
support for retry/cache/fallback semantics.

#### AM-U-007 — multi-operation step grain may be mislabeled

The aggregator groups attempt steps by `assignment_id`, then labels the median
as `median_steps_per_operation`. This is equivalent only when an assignment has
exactly one operation, as the current bundled runner emits. FMT-002 itself
allows multiple `operation_index` values per assignment, so either the invariant
or the aggregation key should be made explicit.

#### AM-U-008 — release evidence packaging gap

Roy's public follow-up says that v0.2.1 has the full report, and the tagged
changelog says that the report passed `am lab verify`. The inspected tag and
release assets do not expose the raw preregistration/events/run/report bundle
needed to independently recompute its reported A/B numbers. This does not show
that the reported numbers are wrong; it limits their reproducibility from the
public release artifact.

## 4. Minimum conformance fixture

### 4.1 Files

- [`outputs/agentmeasure_urusilla_fixture_001.events.jsonl`](agentmeasure_urusilla_fixture_001.events.jsonl)
  — eight project-authored synthetic FMT-002 event rows.
- [`outputs/agentmeasure_urusilla_fixture_001.expected.json`](agentmeasure_urusilla_fixture_001.expected.json)
  — expected aggregate and the Urusilla-only semantics that must not be inferred
  from AgentMeasure core fields.

The fixture represents one task, one declared logical operation, four attempts,
one cache write, one cache read, a fallback transition, a terminal success, and
task continuation. `cost_units` are synthetic token-equivalent test units, not
provider-billed currency. `billed_cost` remains `null`. The `x_urusilla`
properties exercise the current extension tolerance; AgentMeasure does not
validate or aggregate their meaning.

Fixture SHA-256 before the parent integration commit:

- events JSONL: `675f544fe8cc3c16be20534b6516a04dd924e754ace88e0743fd7d0638a1e88f`
- expected JSON: `aec24faf99329ce3ee9698bbc9f396f314e7a67342d486f74872b6c1c560edba`

### 4.2 Verifiable expected aggregate

Running the events through the exact v0.2.1 `analysis.aggregate` function at
commit `20807ad39483a6b78d2db056d78af6e4c7196bf4` produced:

| Metric | Expected numerator | Expected denominator | Expected value |
|---|---:|---:|---:|
| Reach | — | — | 1 |
| Selected | — | — | 1 |
| Operations | — | — | 1 |
| Selection rate | 1 | 1 | 1.0 |
| Operation success rate | 1 | 1 | 1.0 |
| Consumption rate | 1 | 1 | 1.0 |
| Attempts per operation | 4 | 1 | 4.0 |
| Median summed steps | — | 1 assignment | 5.0 |
| Cost units per operation | 25.0 | 1 | 25.0 |

The unreduced 25 cost units are the key positive interoperability property.
The retry edges, cache roles, fallback edges, provider-usage components,
receipt bindings, and task outcome are only in `x_urusilla` and the expected
sidecar. They are not reconstructed from FMT core fields.

### 4.3 Reproduction procedure

Use an isolated checkout; no provider call or package installation is needed:

```sh
git clone --branch v0.2.1 --depth 1 \
  https://github.com/roy-tong/AgentMeasure.git /tmp/agentmeasure-v021
test "$(git -C /tmp/agentmeasure-v021 rev-parse HEAD)" = \
  20807ad39483a6b78d2db056d78af6e4c7196bf4
PYTHONPATH=/tmp/agentmeasure-v021/lab python3 - <<'PY'
import json
from pathlib import Path
from agentmeasure_lab import analysis
from agentmeasure_lab.prereg import load_schema
from agentmeasure_lab.schemas import validate

events = [
    json.loads(line)
    for line in Path("outputs/agentmeasure_urusilla_fixture_001.events.jsonl")
        .read_text(encoding="utf-8").splitlines()
    if line.strip()
]
schema = load_schema("funnel-event.schema.json")
for event in events:
    validate(event, schema)
print(json.dumps(analysis.aggregate(events)[("urusilla-projection",)],
                 indent=2, sort_keys=True))
PY
```

### 4.4 What was actually verified

Verified locally on 2026-08-23:

1. all eight fixture rows passed the **bundled AgentMeasure v0.2.1 validator**;
2. the exact v0.2.1 aggregator produced the metrics in the table above;
3. a missing-base-fields mutation passed the bundled validator;
4. an invalid-root-types mutation passed the bundled validator;
5. a contradictory `attempts=999`, failed-operation mutation passed shape
   validation and changed the aggregate to 999 attempts and zero successful
   operations.

Not verified or not performed:

- no standards-complete Draft 2020-12 validator was installed or run in this
  workspace; the normative conclusions above follow directly from the schema
  keywords and should be added to an upstream test with a full validator;
- no AgentMeasure maintainer reviewed or accepted this mapping;
- no AgentMeasure live harness, model, provider, or paid API was invoked;
- no Urusilla general-dialogue/competitive evaluation was rerun;
- no external reproduction, organic adoption, Langfuse integration, comment,
  issue, or pull request was created by this task;
- this fixture is synthetic format/aggregation evidence only and cannot improve
  Urusilla's currently unproven general unfamiliar-agent token-savings result.

## 5. Recommended next exchange with AgentMeasure

1. Ask Roy whether the comment describes an upcoming FMT revision or intended
   extension vocabulary.
2. Offer the eight-event fixture plus three mutations as a small upstream
   conformance test, preserving Roy's authorship of AgentMeasure and Urusilla's
   authorship of the bridge fixture.
3. Request a released representation for unknown cost and a relational
   validator that derives operation outcome/attempt count from attempt rows.
4. Decide jointly whether fallback is an attempt relationship or an operation
   relationship; do not infer it from order.
5. Only after those points are frozen, preregister and run a matched external
   cross-check. Keep all setup, retry, repair, fallback, and failed-attempt cost
   in the task total.

## 6. Reply-ready public summary (7 sentences)

Thanks, Roy — I mapped our proposed Urusilla attempt/operation/task row against the exact AgentMeasure v0.2.1 FMT-001/002/003 files at commit `20807ad39483a6b78d2db056d78af6e4c7196bf4`.

FMT-002 is the closest layer: `task_id` and `outcome` map directly, while our stable operation/attempt identities collapse to `operation_index` and `attempt_index`.

The released schema does not yet carry `retry_of`, fallback edges, cache roles, provider-usage components, billed-cost units, boundary provenance, or a task terminal, so the current projection is intentionally lossy.

I built an eight-event synthetic fixture with four attempts and one operation; it passes the bundled v0.2.1 validator, and the official aggregator reports 4 attempts/operation and the unreduced total of 25 synthetic cost units.

The same probe found two concrete conformance questions: the bundled validator returns after `oneOf` and accepts records missing root constraints, while the aggregator trusts a declared operation attempt count/outcome without reconciling the attempt rows.

I also could not find the live v0.2.1 run's preregistration/events/run/report bundle in the tagged tree or release assets, so I treat those A/B numbers as maintainer-reported rather than independently recomputed.

No live model run, external reproduction, Langfuse adoption, issue, comment, or PR occurred in this mapping task; if these boundaries match your intent, the next useful step would be a small attributed conformance fixture upstream.
