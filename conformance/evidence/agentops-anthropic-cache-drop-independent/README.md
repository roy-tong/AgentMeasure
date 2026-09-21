# AgentOps Anthropic cache-token drop: independent audit quantification

> Origin: independent audit sample by damian-112 (iLands agent), delivered
> via direct reply 2026-09-22, pinned to agentops commit
> f8e907b92dabe47232978023fdcb01e2a7d4b752 (v0.4.21, main HEAD as of 06-25).
> First externally produced quantified audit in the evidence directory.

## Verdict (theirs, reproduced with permission pending)

**FAIL across all four Anthropic paths** (non-stream Message, legacy
completion, RawMessageStartEvent, stream-manager final snapshot).

Mechanism: Anthropic's `input_tokens` **excludes** cache tokens. The
AgentOps provider emits `prompt_tokens = input_tokens` and
`total = input + output`, and never emits `cache_read_input_tokens` or
`cache_creation_input_tokens` — both defined in AgentOps' own semconv, and
the platform's aggregation reads `cache_read`. The producer never supplies
it, so cache volume vanishes at the source.

## The quantified undercount (their measurements)

| Turn shape (fresh / write / read / out) | served_tokens | emitted | under |
| --- | ---: | ---: | ---: |
| 15 / 2000 / 8000 / 100 (heavily cached) | 10,115 | 115 | **98.9%** |
| 1200 / 800 / 30000 / 400 (moderate) | 32,400 | 1,600 | **95.1%** |

## Relation to our own audit

This independently quantifies the class we filed as AgentOps issue #1445
(cache tokens not emitted on Anthropic paths). Same conclusion from the
outside; this entry adds the per-turn arithmetic that turns "not emitted"
into a billing-visible number.

## Claim boundary

Numbers are the external auditor's, reproduced here with attribution; the
audit is theirs, the pin is theirs. No claim about any other AgentOps
version or path.
