# Langfuse cache-write alias normalization (fixture family)

> Origin: langfuse/langfuse#17117 and #17118 (extractor alias gap raised by
> AgentMeasure; fixture shapes posted in-thread 2026-09-09). Canonical home:
> the thread, pending upstream landing of the test set.

## The three cases

1. **Inclusive emitter (spec-shaped)**: input_tokens=300 (inclusive),
   cache_read=40, cache_write=25. Extractor stores them as-is.
2. **Exclusive emitter**: input_tokens=235 (exclusive), cache_read=40,
   cache_write=25. Extractor must normalize to the inclusive shape
   (input=300) so downstream consumers see one convention.
3. **Alias duplicates**: the same logical usage arriving through multiple
   OTel alias names. The guard classifies once across aliases; it never
   re-derives the classification from each alias's view of the row.

## Wire-ambiguity property (pinned 2026-09-14, from the #17117 review)

In case 2 the correct output is defined by the **emitter's exclusivity**, so
the extractor cannot verify it from the payload alone: `input_tokens=235`
with `cache_read=40` is indistinguishable on the wire from an inclusive
`input=235` whose un-cached portion happens to be 195. Consequences:

- any assertion claiming to validate case 2 from payload shape alone asserts
  something the wire cannot support;
- the declared basis is a fixture **input**, not something the extractor
  recovers;
- future aliases added to the extractor inherit this caveat by construction,
  which is why the case-3 guard classifies once instead of re-deriving.

## Claim boundary

Synthetic shapes only, documenting the proposed test set; no statement about
Langfuse's current behavior beyond what the linked issues state.
