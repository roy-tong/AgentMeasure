# AgentMeasure Lab

**Open experiment engine for the agent channel** — preregistered, offline, zero dependencies, no registration.

```text
task set × harness matrix × factor variants
  → Reach → Choice → Success → Consumption funnel
  → honest statistics (effect size + CI + guardrails + nulls)
  → local HTML/JSON report with a decision summary
```

> Python 3.9+ standard library only. If any step below asks you to register,
> connect to a cloud service, or pay — that is a product defect; please open an issue.

## Quickstart (under 5 minutes)

```bash
git clone https://github.com/roy-tong/AgentMeasure && cd AgentMeasure

# 1. sanity: planted uplift must be recovered, a zero-effect factor must report an honest null
python3 lab/am lab selftest

# 2. init a workspace with an example experiment
python3 lab/am lab init

# 3. lock the preregistration (hypothesis, primary metric, guardrails, analysis plan — hashed)
python3 lab/am lab preregister am-lab/experiments/example-manifest.json

# 4. run it (fully local)
python3 lab/am lab run am-lab/experiments/example-manifest.prereg.json

# 5. re-verify the run any time (prereg hash, event schema, determinism fingerprint)
python3 lab/am lab verify am-lab/runs/example-desc-clarity-001 am-lab/experiments/example-manifest.prereg.json
```

Open `am-lab/runs/example-desc-clarity-001/report.html`. The report opens with a
bilingual **decision-maker one-pager** (conclusion / uplift / monthly margin /
certainty / recommended action — no statistics vocabulary required), then the
evidence. The shipped example deliberately contains two candidate variants:

- `clear` — description rewritten for clarity: selection +5.9pp (p<0.001),
  guardrails pass → **adopt candidate**;
- `clear-verbose` — same rewrite plus verbose output: selection up but
  consumption fell (fake growth) and the steps guardrail breached, and it is
  **dominated by `clear`** (less money at higher cost) → **do not ship**.

That second row is the point of this engine: **an uplift that is not verified
margin is not a shippable improvement**, and the report says so at the decision
exit — not in a footnote. `preregister` also prints a scale / power / budget
preview before anything is locked (per-arm n, the n needed to detect +2/+3/+5/+8pp,
budget caps), so an underpowered plan is visible before it wastes a run.

## The full loop: Test → Ship → Verify (calibration)

The offline experiment is only half the loop. Once a variant ships behind a gradual
rollout (the customer's own release process), the Verify step compares production
against the preregistered offline result:

```bash
# 1. demo only: synthesize production rollout events with a KNOWN planted effect
python3 lab/examples/generate-production-events.py \
  --experiment example-desc-clarity-001 --arms "control=0.25 clear=0.29" --n 2500 \
  --tasks lab/tasks/search-retrieval-scrape.v1.json --out prod-events.jsonl

# 2. production re-test + per-condition transfer effects (CAL-002/003)
python3 lab/am lab calibrate am-lab/runs/example-desc-clarity-001 \
  am-lab/experiments/example-manifest.prereg.json --production-events prod-events.jsonl
```

The calibration report computes production uplift under the **same preregistered plan**
(primary metric, alpha, min sample — never re-chosen), the **transfer effect**
(offline − production) per condition (harness × task stratum) with intervals — never a
single global transfer coefficient — and verdicts that say the hard things out loud:
`production_confirmed`, `direction_mismatch` (do not scale), `transfer_not_established`
(honest production null), `not_comparable` (data gap named, never filled by assumption).
It also emits matrix-reweighting suggestions for the next experiment (CAL-004).

Real production events come from the party that holds the data rights (customer-owned
agent app / buyer side / runtime cooperation). The **connector** is the local-first data
plane for that handoff:

```bash
python3 lab/am connector init --config connector.json --experiment <id>
python3 lab/am connector set choice export --config connector.json   # tiers: off | local | export
python3 lab/am connector export prod-events.jsonl --config connector.json --out export.json
python3 lab/am connector verify export.json --key connector.key
python3 lab/am connector revoke --config connector.json              # immediate; exports refuse
```

Exports are aggregate counts only (schema-level: no per-assignment rows, no content),
HMAC-signed, and exclude any class not authorized at `export` tier. The module never
transmits anything — moving an export to a counterparty is a data-rights decision made
under contract (G0), outside this code.

## Query results over MCP (read-only)

Agents and CI are first-class users (LAB-009):

```bash
python3 lab/am mcp serve
```

Tools: `get_run_summary`, `get_presentation_advice` (variant recommendations with
evidence grades, guardrails, fake-growth flags, and production-verification status
pulled from the calibration report when present), `get_funnel_metrics` (rates with
numerators, denominators, intervals, labels). Read-only; no rankings; no competitor
data; no cross-customer baselines.

## Experiment history (local hypothesis library)

Experiments are a repeating need — channels drift, models change. After runs
accumulate:

```bash
python3 lab/am lab history          # every run: date, experiment, verdicts, prereg + fingerprint
```

This is the local half of the hypothesis library (the hosted/monitored half is
a later, commercial-layer step): what was tested, what it said, and the hashes
that make each claim replayable.

## Why preregistration is not optional

The engine refuses to run a manifest whose hash does not match its locked preregistration,
and the report only draws confirmatory conclusions from the preregistered primary metric.
Everything else is labeled descriptive. If a result is not significant, you get an honest
`null_result` with the CI width — not a nudge to try another metric. Changing the plan means
starting a **new** experiment. This is the difference between an experiment engine and a
conclusion generator.

## What the funnel measures

| Stage | Definition | Denominator |
| --- | --- | --- |
| Reach | the candidate set actually presented for a decision | assignments |
| Choice | the subject capability was selected | reach |
| Success | the operation succeeded (≥1 successful attempt; retries are attempts, not uses) | selections |
| Consumption | the agent actually used the delivered result | successful operations |

Every rate in the report carries numerator, denominator, a 95% Wilson interval and a
[Measurement Label](../standard/QUALITY.md) (grain, rules version, definition). No bare numbers.

Comparisons are two-sided two-proportion tests with Newcombe intervals, evaluated per
condition (per harness) as well as overall — never a single pooled effect alone. Guardrails
can downgrade a significant improvement to `effective_not_qualified`. If selection rises
while consumption falls, the report raises a **fake-growth warning** and the value formula
uses the measured (lower) consumption.

## The synthetic harness and real harnesses

Two kinds of runner ship in this repository:

1. **`mock`** — a deterministic **simulation** with planted factor effects, so the
   pipeline runs offline with known ground truth (validates the engine, not real
   agents; every report says so).
2. **Real harness adapters** (`claude-code`, `codex`) — run the *actual* harness
   headless against a **controlled candidate set**: the runner exposes your
   capability plus competitors through a per-episode local MCP tool server
   ([`toolserver.py`](agentmeasure_lab/toolserver.py), pure stdlib), varies the
   presentation per variant (descriptions, output verbosity), executes
   `claude -p --output-format stream-json --mcp-config …` / `codex exec --json`,
   and parses the transcript into funnel events.

```json
"harnesses": [
  { "id": "claude-code-1.x", "runner": "claude-code",
    "config": { "timeout_seconds": 120, "max_turns": 8 } }
]
```

Honest status of the adapters (also disclosed inside every report):

- `codex`: **live-validated** against codex-cli 0.149.0-alpha (2026-08-22): candidate
  injection via `-c mcp_servers.*`, MCP calls auto-approved with `--approve-for-me`,
  ephemeral sessions, token usage metered as cost units (1 unit = 1 token). Transcript
  shapes are from an alpha CLI and may change upstream; the App Server surface remains
  the better observation plane (profiles/codex.md §4).
- `claude-code`: implemented against the documented headless interface and
  **integration-tested against scripted transcripts** (tests/fake_claude.py) —
  live-CLI validation is the next step; treat first live runs as validation runs.
- Observability limits disclosed per episode: candidate set controlled (and the prompt
  closes it — the agent is instructed to use only the injected tools, since a real
  harness will otherwise reasonably prefer its built-in search); choice from the
  transcript; success from the tool-call status; consumption = continuation proxy;
  steps = action-item count (proxy); latency not observed headless (labeled placeholder).

Community runners still follow the plugin interface
(`module.path:ClassName`); harness profiles live in [`profiles/`](../profiles/).

## Files

| Path | Purpose |
| --- | --- |
| `am` | CLI entry (`am lab …` / `am connector …` / `am mcp serve`) |
| `agentmeasure_lab/` | engine: rng, prereg, matrix, runner, funnel, stats, analysis, report, value, calibrate, connector, mcp_server, harness_cli, toolserver |
| `schemas/` | open formats: experiment manifest (FMT-001), funnel events (FMT-002), report (FMT-003), calibration report |
| `docs/CORE-MAPPING.md` | FMT-004: Core 0.4.4 ↔ experiment formats mapping + reference scenarios |
| `tasks/search-retrieval-scrape.v1.json` | synthetic vertical corpus v1 — 36 tasks, 3 tiers (LAB-005) |
| `examples/example-manifest.json` | three-arm demo: clean uplift + guardrail breach |
| `examples/generate-production-events.py` | demo-only synthetic rollout events with planted transfer |
| `tests/` | `python3 -m unittest discover -s tests -t .` (from `lab/`) |

## Honest status (2026-08)

- Implemented and tested (74 tests + selftest): preregistration lock (+ scale/power/budget
  preview), balanced assignment, seed determinism, budget circuit breaker, funnel capture,
  honest statistics (intervals, honest nulls with next-round sizing, guardrails,
  fake-growth rejection at the decision exit, dominance callouts), bilingual decision-maker
  one-pager, value formula, offline HTML/JSON report, schema conformance (`verify`);
  calibration analysis (production re-test, per-condition transfer, not_comparable,
  reweighting suggestions); connector data plane (three-tier authorization, immediate
  revocation, signed aggregate-only export); read-only MCP query interface; local
  experiment history (`am lab history`); **real harness adapters** (`claude-code` full,
  `codex` experimental) with candidate injection via a local MCP tool server.
- **Not yet done**: live-CLI validation of the adapters (implemented + scripted-transcript
  integration-tested; first live runs should be treated as validation); real production
  event ingestion from an actual rollout (needs a G0 data-rights agreement); hosted
  history/monitoring (commercial layer, later).
- The mock harness's factor effects are simulation parameters, disclosed in every report
  that uses it. Results on `mock` validate the **engine**, not any real-world claim.

## Non-goals

No registration wall, no cloud dependency, no telemetry (not even opt-in yet — undecided,
see OD-009), no ranking of capabilities or providers, no payment features. Lab reports are
openly shareable; the commercial layer adds data and delivery on top of the same formats —
never a different ruler.
