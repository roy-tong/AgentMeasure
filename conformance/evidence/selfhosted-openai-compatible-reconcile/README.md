# Self-hosted OpenAI-compatible server: client surface vs server surface

## Purpose

Pins [standard/known-limits-unprovable-by-surface.md](../../../standard/known-limits-unprovable-by-surface.md)
section 6 with one live capture, so the boundary can be re-checked by running a file
instead of by reading a description. From Discussion #26.

On a self-hosted OpenAI-compatible server, the client surface can be missing two things:

1. **A call's usage.** A stream sent without `stream_options.include_usage` comes back
   with no usage object at all. That is absent, not zero.
2. **The cache split.** vLLM sends `prompt_tokens_details` only when the server is started
   with `--enable-prompt-tokens-details` (off by default), so the client is not told how
   many prompt tokens came from the prefix cache, even when most of them did.

The server surface (`/metrics` counters, two snapshots) recovers the period totals and the
cached count. It cannot split a gap between two or more absent calls.

## Run

From the repository root:

```bash
python3 conformance/evidence/selfhosted-openai-compatible-reconcile/run_case.py
```

Offline, stdlib only.

## Fixture

Live capture, not synthetic. Colab Tesla T4 (driver 580.82.07), vLLM 0.27.1,
torch 2.13.0+cu130, `Qwen/Qwen2.5-0.5B-Instruct --dtype half`, every other server flag
default (prefix caching on, prompt token details off). The same request three times, one
after another ("Name three rivers in Europe.", `max_tokens` 16, `temperature` 0,
`ignore_eos` true), 2026-10-14T17:40Z:

| call | request | usage the client got |
|---|---|---|
| A | plain | 35 prompt / 16 output, `prompt_tokens_details: null` |
| B | stream, no `stream_options` | none |
| C | stream, `include_usage: true` | 35 / 16, `prompt_tokens_details: null` |

Server counters, `/metrics` before A and after C, fresh server:

| counter | before | after |
|---|---|---|
| `vllm:request_success_total` | 0 | 3 |
| `vllm:request_prompt_tokens_sum` | 0 | 105 |
| `vllm:request_generation_tokens_sum` | 0 | 48 |
| `vllm:prompt_tokens_cached_total` | 0 | 64 |

`fixture.jsonl` holds exactly these values. The raw files they were taken from (full
`/metrics` snapshots, the client's usage per call, the server log) are published unedited
at [qaisermehdi3-coder/qvunex@1094fd5](https://github.com/qaisermehdi3-coder/qvunex/tree/1094fd5/benchmarks/data/selfhosted-t4-2026-10-14),
with their sha256 in `expected.json`.

## Required outcomes

| | outcome |
|---|---|
| client | 3 calls, 2 with usage (70 / 32), 1 absent; cache split `UNREPORTED`, cached count `null` |
| server | 3 requests, 105 / 48, 64 cached prompt tokens |
| period total | `PROVABLE`: gap +35 / +16 |
| the absent call's usage | `PROVABLE_BY_ELIMINATION`: with exactly one absent call the whole gap is that call's |
| same fixture, two calls absent | `UNPROVABLE`: the gap (+70 / +32) is a total only |
| cache split per call | `UNPROVABLE` from either surface |

Forbidden: absent usage read as zero; the client total presented as the period total;
a missing `prompt_tokens_details` read as zero cached tokens; per-call attribution of the
gap with two or more calls absent. A missing counter or one that went down (restart) is
unknown, never a zero delta.

## What the runner proves

The runner computes both surfaces from the fixture, reconciles them, and checks the result
against `expected.json`. It then injects five faults (absent usage summed as zero, a missing
cache split read as zero, per-call attribution with two calls absent, a period total claimed
while request counts differ, missing or reset counters) and confirms each is rejected. Each
check was also confirmed to fail when the rule it guards is removed from the runner.

The note on elimination is a small refinement to section 6: per-request attribution is
unprovable from server sums in general, but with exactly one absent call it is forced.

## Claim boundary

One live run of three identical requests on one small model and one card. It pins what each
surface reported in that run. It says nothing about speed or cost, or about other servers'
defaults; SGLang and other engines are not covered by this fixture.

AI-assisted: yes. The runner, fixture extraction and this README were written with an AI
assistant. The run itself was done live, and every fixture value was checked by script
against the raw files.
