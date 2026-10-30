# Collector Input Contract (canonical observations, JSONL)

> What an external provider sends for a measurement run: one JSONL file, one
> canonical observation per line. This is the same contract the Provider SDK
> emits and the same validation the collector ingests — there is exactly one
> input format (single canonical surface; no second dialect).

## Validate before sending

```bash
python3 schemas/validate_jsonl.py your-observations.jsonl
```

Exit 0 = every line is a valid canonical observation. This is the same
validation the collector runs on ingest (`reference/collector/ingest.py ::
validate_canonical`), so a file that passes here will not be rejected there.

## Envelope (every line)

| Field | Required | Notes |
|---|---|---|
| `spec_version` | yes | `"verovo-0.4"` |
| `observation_id` | yes | Unique within the file |
| `observation_type` | yes | One of the payload types below |
| `observer` | yes | `{principal, trust_domain, side}` — `side` is `client` or `provider` |
| `observed_at` | yes | RFC 3339 timestamp |
| `deployment_context` | yes | At minimum `{project_id}` — a stable pseudonymous id is fine |
| `surface` | yes | `{surface_id, surface_namespace}` — e.g. `mcp_tool:bar.search` / `io.github.foo` |
| `provenance` | yes | How the row was produced: `sdk`, `otel`, `log_replay`, `manual` … |
| `usage_context` / `validity` | yes | `unknown` is a legal, honest value — prefer it over guessing |
| `context_source` / `validity_source` | yes | `none` when the two fields above are `unknown` |
| `caller` / `client_key` / `sampling` / `collection_health` | no | Omit rather than invent |

Full schema: [`schemas/observation.schema.json`](../schemas/observation.schema.json).
Worked examples: [`schemas/examples/observations.json`](../schemas/examples/observations.json).

## Payload types (one per `observation_type`)

Providers onboarding for a measurement run typically send a subset — the
minimum useful shape is **presentation → selection → attempt_started →
attempt_completed**, plus `effect_confirmed` if your surface can see outcomes.

| Type | Key payload fields | What it records |
|---|---|---|
| `presentation` | `decision_id`, `candidate_set_id`, `choice_mode` | A decision point with N candidates shown |
| `selection` | `decision_id`, `decision_authority`, `selection_constraint` | Which candidate was taken, under what authority |
| `attempt_started` | `tool_call_id`, `operation_id?`, `retry_of?` | One execution attempt begins |
| `attempt_completed` | `tool_call_id`, `outcome` (`success`/`failure`/`retry`/`denied`/`unknown`), `duration_ms?` | How that attempt ended |
| `effect_confirmed` | `effect_id`, `operation_id`, `outcome_class` (`resolved`/`assumed_resolved`/`escalated`/`abandoned`/`reopened`/`not_outcome`) | An externally observable outcome of an operation |
| `delegation_observed` | see schema | Work handed to another agent layer |
| `result_consumed` | see schema | A tool result entering a later model call |
| `task_outcome` | see schema | Task-grain outcome |

Payload schemas live in [`schemas/payloads/`](../schemas/payloads/) — each
`observation_type` has exactly one payload schema and unknown types are
rejected.

## Rules that reject the file (not warn)

1. Unknown `observation_type`, or a payload that fails its typed schema.
2. `caller.type` contradicting `caller.identity_strength`
   (`claimed_agent`→`declared`, `correlated_agent`→`correlated`,
   `platform_attested`→`attested`).
3. Duplicate `observation_id` within one file.

## Honest-absence discipline

A field you cannot observe is **absent or `unknown` — never zero and never a
default**. If your surface cannot see retries, emit no `retry_of`; the
measurement report will carry those attempts as UNPROVABLE, which is the
correct verdict, not a gap in your submission. See
[known-limits-unprovable-by-surface](../standard/known-limits-unprovable-by-surface.md).

Next: how to map your native events onto this shape →
[`registry/provider-mapping.md`](../registry/provider-mapping.md).
