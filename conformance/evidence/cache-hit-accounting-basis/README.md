# Cache-Hit Accounting-Basis Fixture (LiteLLM #39057)

> Origin: the enforcement case raised by @renezander030 in
> [BerriAI/litellm#39057](https://github.com/BerriAI/litellm/issues/39057) —
> a third-party report that a token budget drawing on the same column a cache
> hit replays can throttle a well-cached agent that spends nothing.
>
> This fixture is **synthetic, offline research evidence**. It asserts
> arithmetic relations between declared quantities only. It is not an
> endorsement, an integration, or a statement about any specific
> implementation's current behavior.

## The invariant

Four quantities are routinely conflated under one "tokens" column:

```text
served_tokens            what the caller received (cache or not)
provider_consumed_tokens what the provider actually metered
billable_tokens          what the invoice counts
budget_consumed_tokens   what enforcement draws down
```

None may be silently assumed equal to another. The checkable invariant is:

> **An enforcement path must declare its accounting basis; a cache hit that
> replays served volume while costing zero provider consumption draws down the
> budget if and only if the declared basis is served volume.**

## The fixture (FMT-002 event rows)

```text
request 1 (cache miss):
  attempts            1
  provider_tokens     100
  served_tokens       100
  cost                > 0

request 2 (cache hit):
  attempts            1        (served from cache; no provider call)
  provider_tokens     0
  served_tokens       100      (replayed)
  cost                = 0
```

## Expected outcomes per declared basis

| Budget basis | Draws on request 1 | Draws on request 2 | Total drawn |
| --- | --- | --- | --- |
| provider-consumption | 100 | **0** | 100 |
| served-volume | 100 | **100** | 200 |
| dollar | cost | **0** | cost |

All three bases are legitimate policies. The invariant is that the basis is
explicit — a control system acting on an unstated convention is the failure
mode, not the choice of convention.

## Verdict semantics

- `PASS` — the enforcement path declares a basis and the drawn amount matches it
- `FAIL` — the drawn amount contradicts the declared basis (e.g. declared
  provider-consumption but cache hits still draw down)
- `UNPROVABLE` — no basis is declared and cannot be inferred from the evidence
  present

## Attribution

The enforcement framing and the real-world throttle case come from
[@renezander030](https://github.com/renezander030)'s thread (with his
per-step token-budget gist linked there). If anonymous attribution is
preferred, this section will be updated.
