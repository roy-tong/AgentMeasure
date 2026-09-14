# Codex rollout topology — what real sessions actually emit

A reference for anyone parsing Codex CLI/desktop rollout JSONL: the event
mix, the token_count semantics, and the re-emission behavior that dedup
logic must survive. Written after a reviewer asked the decisive question —
"does Codex ever repeat a `token_count` event for the same request?" — and
the answer turned out to shape a fix
([codeburn #1264](https://github.com/getagentseal/codeburn/pull/1264)).

## Corpus

53 public rollout sessions from
[codeset-ai/codeset-release-evals](https://github.com/codeset-ai/codeset-release-evals)
(`gpt54_*` / `sonnet_*` / `haiku_*` / `opus_*` families, `baseline/`
directories), 1,313 `token_count` events total. No private logs. Reproduce
with `analyze.py` below against your own checkout of that repo.

## Event types observed

| Line `type` | `payload.type` | Notes |
| --- | --- | --- |
| `session_meta` | — | one per file; session id, model, cwd |
| `event_msg` | `task_started` | marks turn boundaries for active-time windows |
| `event_msg` | `token_count` | usage snapshots; see below |
| `event_msg` | `user_message` | |
| `response_item` | `message` / `function_call` / `reasoning` | conversation items |

A minority of eval-family files (`codeset/` variants) contain no
`token_count` events at all — parsers must tolerate event-poor sessions.

## token_count semantics (the part that bites parsers)

Each `event_msg/token_count` carries `payload.info` with:

- `total_token_usage` — **cumulative across the session** (input, cached,
  output, reasoning, total). Monotone non-decreasing within a session.
- `last_token_usage` — the delta attributable to the most recent response.
- `model_context_window`.

Measured facts (53 sessions / 1,313 events):

1. **603 events (46%) are byte-identical repeats of their immediate
   predecessor** — same cumulative AND same delta, typically 0.5–3 s apart.
   Codex re-emits snapshots unchanged within a response; a parser that
   counts each event as a request over-counts by ~2x.
2. **0 monotonicity violations** — cumulative totals never regress within a
   session. A regression means you are reading a fork or a new session.
3. **54 events (4%) carry no usable `total_token_usage`** — sessions exist
   that emit only `last_token_usage`. Parsers need a path for these, but it
   must not treat byte-identical re-emissions as distinct requests.
4. In the corpus, `rate_limits` mutate between re-emitted events (credits
   drain) — identity for dedup purposes must be computed on `info`, not on
   the whole line.

## Recommended dedup ladder

1. Collapse an event whose `info` payload is byte-identical to the previous
   event's (with or without cumulative present).
2. With cumulative present, also collapse on equal `total_tokens` against
   the predecessor (covers same-total, different-delta shapes).
3. Key cross-file replay protection (fork/resume) on cumulative identity
   where available; without it, do not guess — and document the trade-off.

## Files

- `analyze.py` — recomputes every number above from a directory of rollout
  JSONL files. `python3 analyze.py <dir-with-*.jsonl>`
