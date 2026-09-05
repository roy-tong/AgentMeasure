# AgentMeasure Healthcheck (pre-release)

**A local check-up report for your coding agent runs.**
Point it at the logs your agent runtime already writes. It answers three
questions with evidence — *which records are duplicated, where did the agent
pay retries for one logical operation, and where did the same tool fail over
and over* — and writes a terminal summary plus a local HTML report.

Same honesty rules as the [conformance pack](../conformance/pack/README.md):
every verdict is `OK / FINDING / UNPROVABLE`, and UNPROVABLE is a first-class
result — when the logs cannot decide, that is disclosed, never zeroed.

> Status: engineering preview (v0.3.0). First adapter: **Codex rollout logs**.
> Distribution name decided: **`agentmeasure`** on PyPI (command of the same
> name). PyPI publish is armed and goes live with tag `v0.3.0` once the PyPI
> account/trusted publisher is configured — until then use the git install.

## Install

```bash
# 1) once v0.3.0 is published (planned this week)
pipx install agentmeasure

# 2) today, from git (no account, no PyPI needed)
pipx install "git+https://github.com/roy-tong/AgentMeasure#subdirectory=healthcheck"
# without pipx: python3 -m pip install --user "git+https://github.com/roy-tong/AgentMeasure#subdirectory=healthcheck"

# 3) zero install, straight from a repository checkout
python3 healthcheck/agentmeasure demo
```

Python 3.9+ standard library only; zero runtime dependencies; no network code
(a test enforces both).

## Quick start

```bash
agentmeasure demo      # synthetic session — see it work, no data needed
agentmeasure check     # your Codex logs, last 7 days
agentmeasure check --all           # every local session
agentmeasure check --dir ~/.codex/sessions/2026/09/05
agentmeasure selftest  # adapters + checks on bundled fixtures
agentmeasure validate export.json  # check an export against its schema
agentmeasure --version
```

(Without installing, prefix the commands with `python3 healthcheck/agentmeasure`.)

Options for `check` / `demo`: `--html PATH` (default `agentmeasure-report.html`),
`--json PATH` (full machine-readable export), `--share PATH` (sanitized summary,
`.md` or `.json`), `--days N`, `--save-snapshot [PATH]`, `--no-history`.
`demo` accepts the same output paths and `--no-history`.

Input filters for `check` and `compare`:

```bash
--since 2026-09-01 --until 2026-09-05   # date range (overrides --days)
--project myrepo                        # keep sessions whose project matches
                                        # (project = cwd basename, case-insensitive)
```

## Snapshots & compare — did the change help?

The re-run preview: save a snapshot, change something (a prompt, a Skill, a
dependency), run the agent again, compare.

```bash
python3 healthcheck/agentmeasure check --save-snapshot before.json
# …make your change and run the agent…
python3 healthcheck/agentmeasure check --save-snapshot after.json
python3 healthcheck/agentmeasure compare before.json after.json
# or skip the second snapshot: compare runs a fresh check as side B
python3 healthcheck/agentmeasure compare --all before.json
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
`agentmeasure validate FILE…` checks any export against its schema, and
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
| run number | local run history at `~/.agentmeasure/history.jsonl` distinguishes first vs repeated runs; delete the file to reset |

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
- **Run history** (`~/.agentmeasure/history.jsonl`) stays on the machine and is
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
python3 -m unittest discover -s healthcheck/tests   # 101 tests
python3 healthcheck/agentmeasure selftest           # fixtures + redaction + compare + schemas
bash healthcheck/scripts/smoke_install.sh           # clean-venv install smoke (packaged artifact)
```

The install smoke is also a CI job (Python 3.9/3.11): it builds the package,
installs it into a fresh venv, and runs `selftest`, `demo`, `validate`, and the
external example from the installed artifact — the repository checkout is not
used.

Python 3.9+ standard library only. Zero dependencies, by policy: if any step
asks you to register, connect to a network, or pay — that is a bug.

## Feedback

- [Open an issue](https://github.com/roy-tong/AgentMeasure/issues) — include
  the `--json` export (it contains local paths; strip them first if the log
  location is sensitive).
- [Email](mailto:tongroy18@gmail.com?subject=AgentMeasure%20Healthcheck%20feedback)
