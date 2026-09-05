# v0.3.0 — Healthcheck: installable CLI + versioned export schemas

> Released automatically from `docs/RELEASE-v0.3.0.md` by
> `.github/workflows/release.yml` (tag `v0.3.0`).
> First PyPI release of the `agentmeasure` command.

---

## What's in this release

**AgentMeasure Healthcheck** — a local check-up report for coding agent runs.
Reads the logs your agent runtime already writes (Codex rollout first), checks
them for duplicate records, retry amplification, and tool-error runs, and
writes a terminal summary plus a local HTML report. Same honesty rules as the
conformance pack: `OK / FINDING / UNPROVABLE`, and UNPROVABLE is a first-class
result. Python 3.9+ standard library only; zero runtime dependencies; no
network code (tests enforce both).

### Install

```bash
pipx install agentmeasure
# or: python3 -m pip install --user agentmeasure
agentmeasure demo    # synthetic session, no data needed
agentmeasure check   # your Codex logs, last 7 days
```

### Headlines

- **Checks with evidence.** HC-01 duplicate records (including the format's
  by-design dual-stream recording, disclosed as a ratio), HC-02 retry
  amplification (attempts vs logical operations), HC-03 tool-error runs — each
  finding carries file, line, and exit codes, plus a concrete next step.
- **Honest numbers.** Token subsets never summed into totals; token aggregates
  UNPROVABLE unless every logical session contributes a valid cumulative
  snapshot; corrupt/truncated input reported as lower bounds, never dropped.
- **Snapshots & compare.** `check --save-snapshot` + `compare` show what
  actually changed between two runs (verdict transitions, metric deltas,
  caveats on version/window mismatches).
- **Project breakdown & filters.** cwd-basename project aggregates;
  `--project`, `--since/--until`, `--days`, `--all`.
- **Versioned export schemas (report-v1 / snapshot-v1 / compare-v1).**
  Fields are only added within a version; `agentmeasure validate` checks any
  export; `examples/track-weekly.py` is a complete external consumer that
  imports no package internals.
- **Share-safe by construction.** `--share` exports a whitelist-only summary
  (no prompts, paths, commands, repo names, session ids) — planted-string
  tests enforce it.

### Verification

- 101 unit tests + selftest (fixture verdicts, redaction, compare, schemas)
- Clean-venv install smoke in CI (Python 3.9/3.11): build → install →
  selftest → demo → validate → external example, all from the packaged
  artifact
- Verified against 55 local Codex rollout files (cli 0.142.3–0.153.0);
  snapshot-vs-fresh compare is fully deterministic

### Boundaries (stated, not hidden)

- Supported runtime: Codex rollout (Desktop). Claude Code is detected but not
  yet supported — its adapter ships after validation against real samples.
- Engineering preview: quiet publish, no launch marketing yet. The GitHub
  entry points and naming follow the v4 launch plan.
