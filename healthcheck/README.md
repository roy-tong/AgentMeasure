# Verovo Healthcheck

**A local check-up report for your coding agent runs.**
Point it at the logs your agent runtime already writes. It answers three
questions with evidence — *which records are duplicated, where did the agent
pay retries for one logical operation, and where did the same tool fail over
and over* — and writes a terminal summary plus a local HTML report.

Same honesty rules as the [conformance pack](../conformance/pack/README.md):
every verdict is `OK / FINDING / UNPROVABLE`, and UNPROVABLE is a first-class
result — when the logs cannot decide, that is disclosed, never zeroed.

> Status 2026-10-30: CLI **v0.9.0** is tagged on GitHub; the PyPI project `verovo`
> is not published yet, so `pip install verovo` fails until the first upload (the
> previous `agentmeasure` project stays at 0.8.0). Use the pinned Git install below
> in the meantime. Provider SDK is **v0.3.0** (`@verovo/mcp`). 511 Healthcheck tests
> passed locally. See [release notes](https://roy-tong.github.io/verovo/releases.html).

## Install

```bash
# Pinned Git install of 0.9.0 (works today; the PyPI project `verovo` is not published yet).
pipx install "git+https://github.com/roy-tong/verovo@v0.9.0#subdirectory=healthcheck"
verovo demo

# Once `verovo` is on PyPI this is the normal path.
pip install verovo            # or: pipx install verovo

# Or run from a repository checkout (use a release tag for reproducibility).
python3 healthcheck/verovo demo
```

Historical note: the 0.4.0 wheel (2026-09) had a known first-command crash.
Since v0.5.0 the release pipeline builds and smoke-tests the packaged wheel in
a fresh environment before every push; PyPI is again the recommended path.

Python 3.9+ standard library only; zero runtime dependencies; no network code
(a test enforces both).

The 0.7.0 wheel's conformance command is broken because a bundled dependency was
omitted. **Upgrade to 0.7.2 or later** for `conformance`; Healthcheck itself was unaffected.
[Installed conformance quickstart](../conformance/pack/README.md#first-run-from-an-installed-cli).

[Installation and error recovery](https://roy-tong.github.io/verovo/#install-help)
includes Windows and virtual environments. The report path is printed after a
successful check. Keep full JSON/HTML local; only share an inspected summary.

## Quick start

```bash
verovo demo      # synthetic session — see it work, no data needed
verovo check     # your agent logs, last 7 days (Codex or Claude Code)
verovo check --all           # every local session
verovo check --runtime claude   # force the Claude Code adapter
verovo check --dir ~/.codex/sessions/2026/09/05
verovo selftest  # adapters + checks on bundled fixtures
verovo validate export.json  # check an export against its schema
verovo share run.json        # PREVIEW the sanitized summary (writes nothing)
verovo share run.json --out summary.md   # export after review
verovo --version
```

(Without installing, prefix the commands with `python3 healthcheck/verovo`.)

Options for `check` / `demo`: `--html PATH` (default `verovo-report.html`),
`--json PATH` (full machine-readable export), `--share PATH` (sanitized summary,
`.md` or `.json`), `--days N`, `--save-snapshot [PATH]`, `--no-history`.
`demo` accepts the same output paths and `--no-history`.

Input filters for `check` and `compare`:

```bash
--since 2026-09-01 --until 2026-09-05   # date range (overrides --days)
--project myrepo                        # keep sessions whose project matches
                                        # (project = cwd basename, case-insensitive)
```

## Outcome-billing verification: prepare → recount → dispute → recovery

For a hands-on first run, I walk through two reproducible synthetic examples in
[Check an Intercom Fin bill locally in 10 minutes](../docs/intercom-bill-walkthrough.md):
a CSV recount and a separate confirmed-versus-assumed settlement statement.

The buyer-side bill check for per-resolution vendors (Intercom Fin, Zendesk AI
Agents, …). Rules live in the [vendor-rules registry](../registry/vendor-rules.json)
(single source of truth, each rule cited and confidence-graded). Four commands,
one pipeline:

```bash
verovo prepare --export native-export.csv --vendor zendesk --inspect
verovo prepare --export native-export.csv --vendor zendesk --out prepared.csv
#   native Intercom/Zendesk export -> canonical skeleton. Judgement columns
#   stay EMPTY for human review; native signal columns travel as hint_*
#   cells; prov_* cells record where every value came from. No verdicts.

verovo recount --export prepared.csv --vendor zendesk --inspect
verovo recount --export prepared.csv --vendor zendesk --json recount.json
verovo recount --export prepared.csv --vendor zendesk --contract contract.json
#   Tier 1: the vendor's own published rules, line by line. Findings in BOTH
#   directions; absent evidence is UNPROVABLE, never guessed. --contract adds
#   the buyer's outcome standard (e.g. reopen_window_hours: 72) as a separate
#   outcome lane — renewal leverage, never netted into the claim.

verovo dispute --export prepared.csv --vendor zendesk --contract contract.json
#   the negotiable pack: cover letter citing the vendor's own rule per
#   finding + appendix + (optionally) Tier 2 under the VSS-1 standard.

verovo recovery --pack pack/dispute-pack.json --confirmations confirmations.csv
#   what the vendor actually conceded: credited/paid per disputed line, with
#   confirmation dates and evidence refs. Realized value is counted
#   separately from the claim — an argument won is not cash.
```

`verovo recount --list-vendors` shows the registry with each rule's
source and confidence (P = primary/official, S = secondary, U = unverified).
The browser-local recount at [the website](../website/) runs the same Tier 1
with no upload; a cross-language parity test keeps the two from drifting.

Before a client review, confirm the contract version and outcome subtype.
Current public Intercom terms include Procedure outcomes and handoffs. Uncovered
terms must remain unresolved rather than be automatically marked unbillable.
CRM enrichment also has two reproduced input-boundary issues (missing or aliased
columns, and multi-record ordering) awaiting fixes; verify enriched values before
using them as client evidence.

### The whole story in one artifact

```bash
verovo crosscheck --export prepared.csv --vendor zendesk --ledger billing.csv
#   your billing ledger (计费流水) against the export: charges the export
#   doesn't flag, billed flags the ledger doesn't confirm, amounts off the
#   published price. Disagreements are named, never resolved.

verovo verify --export prepared.csv --vendor zendesk --contract contract.json \
    --ledger billing.csv --confirmations confirmations.csv --out vledger
#   the Verified Ledger: Tier 1 + outcome lane + ledger cross-check +
#   realized recovery in ONE document (json + md), each lane labelled
#   claim / leverage / realized and never summed across.

verovo dashboard --pack vledger/verified-ledger.json --out dashboard.html
#   offline single-file HTML: cards, tables, recovery bar. No JS, no
#   network, printable — renders, never recomputes.

verovo rules-diff last-month-registry.json
#   the monthly ritual: diff last period's rules snapshot against the
#   packaged registry. Exit 1 = a material change (trigger, price, reopen
#   rule) — re-verify the period under the new rule and disclose it.

verovo narrative --pack pack/dispute-pack.json --audience vendor \
    --emit-prompt prompt.txt
#   step 1 of two: the drafting prompt, built from the pack. Run YOUR OWN
#   model on it, then:
verovo narrative --pack pack/dispute-pack.json --check-draft draft.txt --out letter.md
#   step 2: every number in the draft is checked against the pack; any
#   invented or rounded number refuses the draft and the rule-based
#   template ships. The model never touches the numbers. No model? The
#   template is the default.

verovo delivery --log delivery.jsonl --log-event \
    --engagement ACME --vendor zendesk --period-index 1 --phase mapping --minutes 45
verovo delivery --log delivery.jsonl
#   appendix-E metrics from logged phases: first look ≤10h, third period
#   ≤1h, repeat-period reuse ≥70%. Use the mapping fingerprint `prepare`
#   prints to track which engagements share the reusable mapping.
```

Outcome pricing beyond per-resolution support (qualified lead, completed
case) is defined — schema first, per the BP — at
[schemas/outcome-unit.schema.json](../schemas/outcome-unit.schema.json) with
worked examples. The outcome **engine** now ships too:
`verovo outcomes --units units.jsonl` verifies them fail-closed, and the
schema covers action and usage-aggregate units — an engineering extension beyond the current support-billing sales scope.

```bash
verovo crm-join --export prepared.csv --crm crm.csv --out joined.csv
verovo outcomes --units outcome-units.jsonl --json outcome-ledger.json
verovo period-compare last-month/verified-ledger.json vledger/verified-ledger.json
verovo template --export --vendor intercom --fingerprint <fp> --contract contract.json
verovo certify --pack vledger/verified-ledger.json --digest-out digest.txt
verovo incrementality --events treatment-holdout.csv
```

### Agent commerce: existing engineering reference

Commercial development of this line is paused in the October buyer-review plan.
The following documents existing commands, not a current sales offer.

Traditional attribution starts at the click; agent commerce has none. The
merchant-side measurement receipt (F2.1-F2.9):

```bash
verovo commerce-ledger \
    --events agent-events.jsonl --orders merchant-orders.csv \
    --payments merchant-payments.csv --policy-version 1.0.0
#   metric + value + evidence table; retries reconcile to 1 Operation /
#   2 Attempts / 1 verified order; net GMV is strong; incremental is
#   UNPROVABLE (no holdout, no claim); materiality prints the discrepancy
#   vs the naive dashboard in currency AND percent.
```

live / replay / synthetic never mix inside one aggregation (error, not a
blend); metric names carry their strength prefix and are linted against the
evidence that backs them; every input is sha256-anchored. The operating layer on top:

```bash
verovo pnl-trees --orders orders.csv --campaigns campaigns.csv   # Organic / Paid, ROAS in Paid only
verovo cm-ledger --orders orders.csv --costs costs.csv --period 2026-09
verovo demand-audit --measurements m.csv --thresholds t.json     # Launch / Watch / Not ready
verovo intent-taxonomy --file clusters.json                      # Operating Cell health
verovo decision-audit --policy policy.json --executions log.jsonl
verovo benchmark-export --rows brand-rows.csv --min-brands 5     # aggregates only, ever
```

 Schema:
[schemas/commerce-profile.schema.json](../schemas/commerce-profile.schema.json);
canonical retry vector pinned in CI at
`conformance/vectors/commerce-retry-baseline/`.

`certify` grades the artifact on the VSS-1 adoption ladder (Stage 0..3) and
emits the deterministic digest; hand the digest to your own signing tool —
this package never runs one. `incrementality` produces statistics about a
difference, never a verdict: the BP's line between rule judgement and causal
inference stays visible in the output itself.

## Sharing results: preview first, export second

The recommended flow never writes a shareable file until you have read it:

```bash
verovo check --json run.json          # the report export embeds the summary
verovo share run.json                 # terminal PREVIEW — nothing is written
verovo share run.json --out summary.md  # export only after you reviewed it
```

`share` re-checks the summary against its whitelist before showing or writing
anything, so a tampered or future-format export is refused rather than leaked.
`check --share PATH` remains available as the one-step explicit alternative.

## Snapshots & compare — did the change help?

The re-run preview: save a snapshot, change something (a prompt, a Skill, a
dependency), run the agent again, compare.

```bash
python3 healthcheck/verovo check --save-snapshot before.json
# …make your change and run the agent…
python3 healthcheck/verovo check --save-snapshot after.json
python3 healthcheck/verovo compare before.json after.json
# or skip the second snapshot: compare runs a fresh check as side B
python3 healthcheck/verovo compare --all before.json
```

`compare` prints metric deltas (failed executions, retry chains, …), check
verdict transitions (`HC-02 OK → FINDING`), and honest caveats: token totals
are differenced only when **both** sides are provable, and version / window /
mode mismatches are disclosed because they change what a delta is allowed to
mean. Snapshots are local artifacts (they contain project names and session
short-ids); the snapshot schema is versioned and validated on load.

## Versioned export schemas — how other tools integrate (R8)

Everything a third party needs is a JSON document with a version on it:

| document | written by | schema |
| --- | --- | --- |
| report export | `check --json PATH` / `demo --json PATH` | `report-v1` |
| snapshot | `--save-snapshot PATH` | `snapshot-v1` (schema field = 1) |
| comparison | `compare --json PATH` | `compare-v1` |

Reference schemas live in [`schemas/`](schemas/). Compatibility policy:
**within a schema version, fields are only added — never renamed, retyped, or
removed**; a consumer that meets an unknown newer version must stop and say so.
`verovo validate FILE…` checks any export against its schema, and
[`examples/track-weekly.py`](examples/track-weekly.py) is a complete external
consumer: it reads snapshots through the schema only, imports nothing from the
package, and refuses future schema versions. MCP-style servers can wrap the
same exports later; the exports, not internal modules, are the integration
surface.

## What it checks

| id | check | question it answers | verdict basis |
| --- | --- | --- | --- |
| HC-01 | Duplicate records | byte-identical lines, repeated call/execution ids, sessions split across files, and the format's **by-design dual recording** when model-side calls and command events are both present | exact line hashes, id counts |
| HC-02 | Retry amplification | same command failed then re-run: how many executions carried one logical operation | consecutive same-command blocks whose first attempt failed |
| HC-03 | Tool error runs | ≥3 back-to-back failures of the same tool with no success between | consecutive failed executions, same tool kind |

Plus a coverage overview: sessions, turns, executions by outcome, token
consumption (with subset discipline), compactions, sub-agent activity, corrupt
lines, and a **per-project breakdown** (project = cwd basename, canonical
deduplicated counts). Every finding carries evidence — file, line number, exit
codes — and a concrete next step.

## Honest-number rules (the part most tools get wrong)

- **Executions are counted from exactly one stream.** Codex Desktop can write a
  tool call as both a `response_item` record and an `item_completed` event.
  Summing both — or grepping the file — double-counts when both are present.
  HC-01 discloses the observed ratio instead of hiding it.
- **Token subsets are never added into totals.** `cached_input` ⊆ input,
  `reasoning_output` ⊆ output in Codex logs. The report shows subsets
  alongside, never inside, totals.
- **Token totals use the last cumulative snapshot per session**, not sums of
  per-event deltas (which double-count after context compaction). The aggregate
  is marked UNPROVABLE unless every logical session has one valid snapshot;
  missing or malformed snapshots are reported separately.
- **Corrupt or truncated input lowers every count.** All numbers are lower bounds
  where lines failed to parse or a file hit the safety cap; the limitation is
  reported, never dropped.
- **UNPROVABLE, not zero.** Sessions whose format lacks outcome events make
  HC-02/HC-03 UNPROVABLE for that part — reported as such.

## Statistics definitions (for support and accounting)

| term | definition |
| --- | --- |
| execution | one `CommandExecution` / `McpToolCall` event; its outcome is `ok`, `failed`, or `unknown` |
| retry chain | a maximal block of consecutive executions of the same command whose first attempt failed; one chain = one logical operation executed N times |
| resolved chain | a chain whose last attempt succeeded |
| tool error run | ≥3 consecutive failed executions of the same tool kind with no success or unknown in between |
| token total | last cumulative `total_token_usage` snapshot per session, summed only when every session has a valid snapshot; otherwise UNPROVABLE |
| project | basename of the session's recorded working directory (`session_meta.cwd`); used for the breakdown, `--project` filtering, and snapshots — never included in the share summary |
| snapshot | versioned JSON record of one run's window, verdicts, and aggregate counters (schema 1); local artifact |
| comparison delta | `B − A` per metric; tokens are differenced only when provable on both sides, and version/window/mode mismatches are disclosed as caveats |
| demo run | executed on the bundled synthetic session; counted separately (`synthetic-demo`) |
| own-data run | executed on real local logs (`own-data`) |
| run number | local run history at `~/.verovo/history.jsonl` distinguishes first vs repeated runs; delete the file to reset |

## Privacy

- **No network.** The package contains no network code; a test enforces this by
  scanning every module for network imports.
- **Raw data stays local.** Prompts, message text, and reasoning content are
  never read into the model (only envelope types, ids, exit codes, durations,
  and token counters).
- **Two artifacts, two levels.** The HTML report is personal (local paths and
  evidence metadata — raw commands are represented by hashes, and the banner
  says so). The `--share` summary
  is built from a fixed whitelist of aggregate counts: no prompts, paths,
  commands, repo names, or session ids can appear in it, and a planted-string
  test enforces this.
- **Run history** (`~/.verovo/history.jsonl`) stays on the machine and is
  deletable.

## Verified runtime support

| runtime | status | verified against |
| --- | --- | --- |
| Codex rollout JSONL (Desktop originator) | supported | cli 0.142.3 – 0.153.0; review snapshot 54 local files, 48 sessions, ~83k lines (2026-06-30 → 2026-09-05). Sessions without `CommandExecution` events (older format) run with HC-02/HC-03 UNPROVABLE, disclosed. |
| Codex CLI (`codex_cli_rs` originator) | expected compatible, **not yet verified** — no local samples | pending real samples |
| Claude Code (`~/.claude/projects`) | detected, **not yet supported** | adapter ships after validation against real samples |

New cli versions are handled defensively: unknown event types are accounted
(`unknown type` counts), never silently dropped.

## Exit codes

| code | meaning |
| --- | --- |
| 0 | the check ran and produced a report (findings or not) |
| 1 | selftest fixture mismatch (development only) |
| 2 | input/output error: no readable logs in the window, bad `--dir`/arguments, or an output path cannot be written |

## Development

```bash
python3 -m unittest discover -s healthcheck/tests   # 511 tests verified 2026-10-15
python3 healthcheck/verovo selftest           # fixtures + redaction + compare + schemas
bash healthcheck/scripts/smoke_install.sh           # clean-venv install smoke (packaged artifact)
```

The install smoke is also a CI job (Python 3.9/3.11): it builds the package,
installs it into a fresh venv, and runs `selftest`, `demo`, `validate`, and the
external example from the installed artifact — the repository checkout is not
used.

Python 3.9+ standard library only. Zero dependencies, by policy: if any step
asks you to register, connect to a network, or pay — that is a bug.

## Feedback

- [Open an issue](https://github.com/roy-tong/verovo/issues) — include
  the `--json` export (it contains local paths; strip them first if the log
  location is sensitive).
- [Email](mailto:tongroy18@gmail.com?subject=Verovo%20Healthcheck%20feedback)

## Identify an input before checking it

```bash
verovo inspect-input sample.jsonl --json input-routing.json
```

This reads every nonempty JSONL row and identifies canonical provider observations, FMT-002, or Codex rollout shapes. Mixed, invalid and unknown inputs exit 2 with next steps. Exit 0 means a format was recognized, **not** that the schema or measurement passed. The report includes no source rows. Canonical observations use the repository validator and provider onboarding path; do not invent fields to force them into FMT-002.

## Compare Claude response snapshots (0.8.0)

`verovo response-audit session.jsonl fork.jsonl --json responses.json` compares explicit inputs without rewriting logs or claiming invoice totals. See [scope and next steps](../docs/response-audit.md).
