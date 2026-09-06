# Try Healthcheck on your own Codex logs

We are looking for the first five non-author testers to help verify installation
and whether the report is understandable. This is an engineering preview, not a
claim that five testers have already completed it. No account, star, issue, or
data upload is required to use it.

## Run

Requires Python 3.9+, Git and pipx. Installation downloads the package; analysis
is local and has zero runtime dependencies. Supported samples currently come
from Codex Desktop; standalone Codex CLI remains unverified and Claude Code is
not supported.

```bash
pipx install "git+https://github.com/roy-tong/AgentMeasure#subdirectory=healthcheck"
agentmeasure demo
agentmeasure check --json report.json
```

Without pipx, install into a Python virtual environment using pip and the same
Git URL. See [the full guide](../healthcheck/README.md).

Note separately how long installation and the first own-data report take.
An empty or unsupported directory is useful feedback, but is not a successful
own-data run. The demo is synthetic and never counts as an own-data run.

Try answering: **What did the report establish, and what would you do next?**
Finding no issue can be useful too, provided coverage supports that conclusion.
These are log checks, not a verdict on overall agent quality or task success.

## Optional feedback, with a preview

The HTML report, full `report.json`, and snapshots are personal artifacts. Do
not attach them to a public issue: they may contain local paths and identifiers.

```bash
agentmeasure share report.json                  # preview; writes nothing
agentmeasure share report.json --out summary.md # export aggregate summary
```

Open `summary.md` yourself before sharing. It contains aggregate counts, without
prompts, commands, paths, project names, or session IDs. You can also omit the
summary and describe only the installation problem or confusing result.

[**Open a first-run feedback issue**](https://github.com/roy-tong/AgentMeasure/issues/new?template=6-healthcheck-first-run.yml)

Please include OS, Python and tool version, whether the data is your own or the
demo, and what was useful or blocked you. How you first found us and what made
you try it are optional, separate questions. Feedback is not an endorsement and
opening an issue does not automatically count as successful use.

## Come back after a change

```bash
agentmeasure check --save-snapshot before.json
# Make an actual change and run your agent again.
agentmeasure check --save-snapshot after.json
agentmeasure compare before.json after.json
```

Describe the change and whether the comparison informed a decision. Different
windows or workloads limit comparisons; metric deltas alone do not prove the
change caused an improvement. Keep the snapshots local.
