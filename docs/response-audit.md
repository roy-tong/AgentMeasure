# Compare Claude response evidence across files

Use this when a fork/resumed session appears to repeat the same response usage,
or two copies of a response disagree. Requires CLI 0.8.0.

```bash
verovo response-audit original.jsonl fork.jsonl --json response-evidence.json
```

Inputs are explicit JSONL files; nothing is auto-uploaded or rewritten. Each
assistant `message.id` joins its observed usage snapshots. Reports use a SHA256
of that ID, not prompts, responses or tool arguments. An ID hash can still link
records across reports: review it before sharing. Duplicate input files are read
once. Files over 400 MiB are rejected rather than silently truncated.

- **OBSERVED**: the observed complete usage snapshots agree. This is not proof of
  complete coverage, final usage, a second execution, or correct billing.
- **CONFLICT**: usage, model or request identities disagree for the same response.
  Preserve both source versions; do not choose first, last or maximum usage.
- **INCOMPLETE**: one or more usage rows lack nonnegative integer values for input,
  output, cache-read or cache-creation tokens. Missing cache values are not zero.
- Missing response IDs and malformed rows are counted separately. They are not
  merged into a fabricated response or silently dropped from the coverage story.

`session_token_total` and `invoice_total` are always null; the measurement verdict
is UNPROVABLE. Cache fields are not added to input totals. Exit zero means the
inspection ran, not that the evidence passed. Input/output failures exit 2.

## What to do next

For repeated snapshots, inspect how your exporter copies a response across files
before changing the counter. For conflicts, retain source records and request
identities; additional fields may be needed to establish which usage is final.
For billing questions, obtain applicable provider billing evidence. This command
does not replace that evidence or broaden the $20 QA service into invoice/token
auditing. CLI bugs and unsupported formats can be reported free with a minimal
redacted reproduction; do not post raw private logs in a public issue.

This is an evidence-inspection capability validated on synthetic regressions.
Real customer adoption, session-total reconciliation and savings are not claimed.
