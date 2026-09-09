# Emission finality: designated-record fixture

> Shapes to pin the "which copy is the response" problem from
> pydantic/pydantic-ai#7975 and open-telemetry/semantic-conventions-genai#487.
> Purpose: a rule that is a **fixed assertion on a single record** (a
> designated-record / finality marker), not a sampled rate over a corpus.

## Scenario

One model response `R` is emitted across N content blocks. Each block may carry
a usage object that is a **snapshot of an in-progress accumulator** or the
**final** one. Nothing in the shape below says which is which, except the
optional marker.

## Records (usage objects for response R)

```json
[
  { "message_id": "r1", "usage": { "output_tokens": 7,  "reasoning": 7 }, "complete": false },
  { "message_id": "r1", "usage": { "output_tokens": 317, "reasoning": 300 }, "complete": true },
  { "message_id": "r1", "usage": { "output_tokens": 0,  "reasoning": 0 }, "complete": false }
]
```

- Copy 1 is an early snapshot (7 output).
- Copy 2 is the **designated final** record (`complete: true`) carrying 317.
- Copy 3 is a **zeroed-after-populated** record (written after 2).

## Assertions

| Rule | Result on this group | Verdict |
| --- | --- | --- |
| Sum all copies | 324 | FAIL (double/extra counting of snapshots) |
| Last-write-wins | 0 (copy 3) | FAIL — reads a free response |
| Dedup by id + take max | 317 | PASS **by luck of ordering**; monotonicity assumed |
| Sum designated records only (`complete: true`) | 317 | PASS — locally checkable, ordering-independent |

## Why not heuristics (the shape that breaks them)

```json
[
  { "message_id": "r2", "usage": { "output_tokens": 300, "reasoning": 200 }, "complete": false },
  { "message_id": "r2", "usage": { "output_tokens": 250, "reasoning": 150 }, "complete": true }
]
```

Copy 2 **diverges downward** from copy 1 (final is smaller). `max-per-id`
returns 300 (copy 1); the designated record says 250. A monotone-only fixture
would let both `last-wins` and `max-per-id` pass identically, so fixtures must
include downward-diverging copies to distinguish the rules.

Corpus statistics (2.28x, 2.10x) are measurements of a moving corpus — they are
not constants and must not be quoted as such. The mechanism is the claim:
**usage is scoped per response, emission is scoped per block, and the record
must mark which copy is the response** (or carry an explicit partial/share
marker on the others).

## Verdict format (AgentMeasure)

- designated-record rule on this fixture: **PASS** (fixed assertion on one
  record).
- last-wins / max-per-id on the downward case: **FAIL** as a contract (they can
  only be validated as sampled rates).
