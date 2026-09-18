# Inference-boundary: aggregation replay ambiguity (fixture family)

> Origin: contributed by David Turner (@atomicdjt), 2026-09-17, via direct
> reply after the DR-005 attribution of the provider-inference boundary.
> First inference-boundary entry in the evidence directory.

## What it pins

A provider reports an aggregate tool-call count whose source pointer resolves
to **two equally plausible records**: a measured counter and a replayed cache,
identical in window and count, with no measurement-basis marker to tell them
apart.

The fixture grades every field with an evidence status:

- `observed` — value returned verbatim by the provider;
- `derived` — concluded from the two candidate records (the ambiguity itself);
- `inferred` — aggregation basis: consistent with either measured or replayed,
  not established by the available evidence.

## Expected behavior

`preserve_uncertainty`. The reported count stays `observed` with the
qualification "provider-reported; not independently established as measured";
the aggregation basis stays unresolved with both candidates preserved; the
forbid list blocks labeling the count as measured, collapsing the candidates,
or substituting a default basis.

## Why it matters

This is the confident-gap failure mode in miniature: a consumer that cannot
distinguish measured from replayed aggregation will fill the gap with a number
that looks measured. The fixture asserts the honest alternative: keep the
uncertainty, name it, and never let it silently become a claim.

## Claim boundary

Synthetic conformance fixture; no real provider behavior is described.
