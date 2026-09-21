# Rulestack cache-prefix overhead: 436k vs 54,154 tokens (real-world case)

> Origin: surfaced by razzlo (iLands agent) via direct reply, 2026-09-20,
> after the Show HN. First externally reported real-world case mapped to
> the cache-distinction invariant (all prior cases are our own audit).

## The case

Rulestack published "a Claude Code subagent costs ~436k tokens before it
reads a single file", then re-measured and corrected to **54,154**.

Their own stated method error (from the correction post): the 436k was the
cost of spawning **times the number of reviewer iterations**, at face-value
prices — i.e. the same cached prefix was summed across the reviewer's
repeated requests and read as per-spawn fixed overhead.

> "The number was real; the noun attached to it ('fixed overhead') was wrong."

## Mapping to the standard

- The inflation was not the spawn. It was counting a replayed cached prefix
  as fresh per-spawn work — the cache-distinction class one layer up.
- `operation_id` alone would not have prevented it: the repeated reviewer
  requests were multiple attempts whose token totals each replayed the same
  cached prefix. Attempt/cost double-counting survives logical-operation
  grouping; only cache-basis attribution separates replayed volume from
  provider-consumed volume.
- Expected behavior under our invariant: cached replay counts once toward
  served volume, zero toward provider-consumed (hop replay) or cache-invoice
  basis (provider prompt-cache hit), never as fresh per-spawn input.

## Sources (public, cited)

1. Original (2026-08-20, Rulestack):
   https://dev.to/rulestack/a-claude-code-subagent-costs-436k-tokens-before-it-reads-a-single-file-measured-with-the-1ja9
2. Correction (2026-08-29, Vinh Nguyen / Rulestack):
   https://dev.to/rulestack/we-said-a-claude-code-subagent-costs-436k-tokens-a-cleaner-measurement-says-54k-here-is-what-37am

## Claim boundary

External public sources, quoted with attribution; numbers are theirs. This
case documents the failure class in the wild; no claim about any other
implementation.
