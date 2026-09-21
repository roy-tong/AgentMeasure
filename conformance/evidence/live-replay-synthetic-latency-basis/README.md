# Live / replay / synthetic latency basis (mixed-aggregate failure)

> Origin: contributed by Chandan Kumar (@modelpath-dev), 2026-09-21, via
> direct reply after the counting-grain / provenance discussion with Roy Tong.
> Evidence-directory entry for the live-only vs mixed-basis aggregate rule.

## What it pins

One `operation_id` carries three invocation rows with different latency:

| Row | provenance | latency_ms | role |
| --- | --- | ---: | --- |
| live | live | 100 | observed production attempt |
| replay | replay | 20 | derived from a stored prior result |
| synthetic | synthetic | 300 | declared synthetic; not production |

A schema that tags provenance can enforce:

- `operation_id` = one user intent
- each try stays its own row
- production averages draw from **live** rows only
- **replay** rows sit in their own view
- **synthetic** rows are excluded from production aggregates entirely

## The number pair that matters

| View | Mean latency_ms | How |
| --- | ---: | --- |
| **live-only (correct)** | **100** | mean of live rows only |
| **all-rows (wrong)** | **140** | mean of live + replay + synthetic = (100+20+300)/3 |

That pair is the mixed-basis failure in one look: the wrong mean looks
decisive, but it mixes measurement bases.

## Expected behavior

- Live view mean latency = 100
- Replay view mean latency = 20
- Synthetic excluded from production aggregates
- Do not emit 140 as a measured production latency

## Claim boundary

Synthetic conformance fixture; no real provider traffic is described.
