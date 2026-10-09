# AgentMeasure availability certification ↔ FMT-002 mapping (chenhz01-001)

Date: 2026-10-08

Status: synthetic conformance fixture authored for issue #11; no external run.

AgentMeasure commit inspected: `67c276b7d17d5a00dc2fa89681eae97f29eeda06`

## Bottom line

M4.1's `consumption` event carries a single `consumed` boolean. That boolean
cannot represent what issue #11 established: availability (the result entered
the next model request) and influence (the result changed behavior) are
different facts, and "reference" is a weak estimator between them, not a state.

This fixture is one trace whose four tool results each meet a different
certification outcome, so a compaction-aware implementation can be tested
against all four at once:

| op | outcome | what happened | State A | observability (AGENTS.md §2) |
|---|---|---|---|---|
| 1 | `verbatim` | the result's canonical content is in the next request | yes | TRUE |
| 2 | `summary-embed` | only a lossy summary reached the request | no | FALSE for A, weak influence |
| 3 | `absent` | a request left, the result is nowhere in it | no | FALSE |
| 4 | `unreachable` | no request left the framework at all | no | UNOBSERVABLE |

The core aggregator scores this trace at `consumption_rate = 1/4 = 0.25`. That
number is wrong in two ways the four-value axis fixes: it counts the
`unreachable` result (UNOBSERVABLE) in the denominator, and it gives the
`summary-embed` result no bucket of its own. The corrected State-A rate is
`1/3 = 0.333`, with the unreachable result excluded, never counted FALSE
(invariant 17).

## Why `summary-embed` is its own bucket

A summary embed means the content did reach inference, just lossily. That is
weak evidence of influence (the State-B axis) with no verbatim availability. It
is a different row from use-without-cite: there the result was present but
uncited; here a projection of it was present and the original was not.

Folding `summary-embed` into an availability miss looks harmless until you
notice where it lands. Compaction-heavy sessions are the common case in long
agent runs, not the edge case, so an implementation that reports
availability-failed on every compacted result will under-report exactly on the
runtimes where the distinction pays for itself. The bucket has to exist.

## Why the certifier canonicalizes the field, not the bytes

`op1` is the re-serialization trap. The result is embedded in the next request
as a serialized JSON string, so re-serializing the whole request escapes it. A
raw byte or substring certifier misses it and reports `absent` — a false
negative. The runner keeps both certifiers to pin the contrast:

```
op1  raw-substring -> absent      (false negative: re-serialization)
op1  canonical     -> verbatim    (parse the field value, hash the content)
```

So the certifier canonicalizes each field value and compares content hashes,
and it records the field path where the match was found (`messages[1].content`
for op1 and op2). The path is what lets a summary embed certify a weaker state
instead of State A: same field, different `embed_form`.

## The four outcomes ↔ FMT-002

FMT-002 has no field for the certification outcome, so it rides in an
`x_availability` extension on each `consumption` event, the same way the
Urusilla fixture carries its ledger in `x_urusilla`. The boolean `consumed` is
set to State A only (verbatim), which is what a correct verbatim certifier
would emit today; everything the boolean drops is in the extension.

| certification | `consumed` | `signal` | `x_availability.observability_state` | in State-A denominator? |
|---|---|---|---|---|
| `verbatim` | `true` | `task_continuation` | TRUE | yes (numerator) |
| `summary-embed` | `false` | `unknown` | FALSE | yes |
| `absent` | `false` | `none` | FALSE | yes |
| `unreachable` | `false` | `unknown` | UNOBSERVABLE | no — excluded |

`unreachable` is the invariant-17 case. The request never left, so the surface
could not judge availability at all. Counting it as not-consumed is the
UNOBSERVABLE→FALSE collapse the standard forbids. Guard 6 in the runner shows
that mislabeling it as `absent` moves the denominator from 3 to 4, so the
collapse is detectable rather than silent.

## Boundaries this vector does not cross

Two limits, flagged in review (chenhz01, #32), that a real-trace certifier has
to close and this synthetic fixture deliberately does not:

- **`summary-embed` is declared, not inferred.** Here the summary bucket is
  read from the sidecar's `embed_form`, which is ground truth for a synthetic
  fixture. On a real trace the summary has to be established by a content-level
  criterion the runtime cannot silently fail to compute — a hash prefix,
  sub-sequence coverage, or an edit-distance threshold — or the classifier
  reintroduces the "looks wired, silently isn't" failure this vector exists to
  catch.
- **The field-walk is single-layer exact match.** It checks whether a
  `messages[i].content` value parses and hashes equal to the result content.
  Nested embeddings (content parts, tool-call arguments) and partial embeddings
  are out of scope. This is a pinned exact-match certifier, not a general
  substring or deep search.

## Files

- `agentmeasure_chenhz01_fixture_001.events.jsonl` — 14 FMT-002 events (reach,
  choice, then attempt/operation_result/consumption per operation).
- `agentmeasure_chenhz01_fixture_001.trace_context.json` — the raw inputs (the
  four results and the next request each faced), so certification is recomputed
  from scratch, not trusted from the extension.
- `agentmeasure_chenhz01_fixture_001.expected.json` — core metrics, the
  four-bucket breakdown, the State-A rate, and the forbid list.
- `../../../runners/run_external_fixture_003.py` — the six guards.

## Attribution

- Two-state ontology (availability vs influence) and the compaction boundary:
  Gunjan Jaswal (@gunjanjaswal), issue #11.
- Trace-side hash certification (`certify_availability`): @chenhz01.
- Canonicalized content, field-path recording, and the four-value axis:
  @roy-tong.
- Fixture author: Gunjan Jaswal (@gunjanjaswal).

## Claim boundary

Synthetic conformance fixture authored for AgentMeasure issue #11. It is not an
endorsement, an external reproduction, or a real provider or agent-runtime
observation. The certification inputs are constructed to exercise the four
outcomes, not sampled from a live trace.
