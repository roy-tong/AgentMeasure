"""Read-only JSONL routing. Recognition is not schema or metric validation."""
import json
from collections import Counter


def family(row):
    if not isinstance(row, dict):
        return "unknown"
    canonical = "observation_type" in row and "spec_version" in row
    # The agentmeasure.lab namespace is a permanent legacy alias for evidence
    # recorded before the 2026-10-30 Verovo rename.
    funnel = row.get("schema") in ("verovo.lab/funnel-event", "agentmeasure.lab/funnel-event")
    if canonical and funnel:
        return "ambiguous"
    if canonical:
        return "canonical-observations"
    if funnel:
        return "fmt002"
    if row.get("type") in ("session_meta", "turn_context", "event_msg", "response_item", "compacted"):
        return "codex-rollout"
    return "unknown"


def _reject_constant(value):
    raise ValueError("non-finite JSON number")


def inspect(path):
    counts = Counter()
    errors = []
    rows = 0
    with open(path, encoding="utf-8-sig") as fh:
        for line_number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            rows += 1
            try:
                row = json.loads(line, parse_constant=_reject_constant)
            except ValueError:
                counts["invalid-json"] += 1
                # Never echo a raw line: it may contain prompts or credentials.
                if len(errors) < 10:
                    errors.append({"line": line_number, "reason": "invalid JSON"})
                continue
            counts[family(row)] += 1
    detected = next(iter(counts)) if len(counts) == 1 else "mixed"
    if not rows:
        detected = "empty"
    actions = {
        "canonical-observations": [
            "This is the provider canonical observation shape, not FMT-002.",
            "In a repository checkout: python3 schemas/validate_jsonl.py <your-file>",
            "Then use docs/provider-onboarding.md for a measurement check; do not invent missing identities or convert request groups into logical operations.",
        ],
        "fmt002": ["Run verovo conformance --fixture <your-file> for schema and invariant checks."],
        "codex-rollout": ["Run verovo check --dir <directory-containing-your-logs> --all; verovo check --help for filters."],
    }
    return {
        "kind": "input-routing", "format": detected, "nonempty_rows": rows,
        "row_formats": dict(sorted(counts.items())), "errors": errors,
        "invalid_json_rows": counts["invalid-json"],
        "schema_validation": "NOT-RUN", "measurement_verdict": "NOT-RUN",
        "next_steps": actions.get(detected, [
            "Keep the original file. Separate mixed formats or correct invalid JSON before checking.",
            "For an unsupported format, provide a redacted sample and its schema for a fit review; do not fabricate fields to pass a validator.",
        ]),
        "limits": "Format recognition only. No rows are repaired, dropped, mapped, or treated as a conformance pass. No source content is included in this report.",
    }


def render(report):
    return "\n".join([
        "Input format: " + report["format"],
        "Nonempty rows: " + str(report["nonempty_rows"]),
        "Schema validation: NOT-RUN; measurement verdict: NOT-RUN",
    ] + report["next_steps"] + [report["limits"]])
