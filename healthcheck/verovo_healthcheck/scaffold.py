"""Conformance-vector scaffolding — one command from "I want to contribute"
to a CI-valid vector directory (requirements pool §七 C1).

External contributions have outgrown fixtures: PR #32 shipped the first
availability-certification vector. The friction left is the blank page —
which files, which schema, which claim boundary. `verovo conformance
--new-vector <name>` generates the directory external contributors actually
ship (FMT-002 fixture + metadata + expected + README with the claim-boundary
template), valid as generated: the fixture passes the pack's FMT-002
validation, the metadata satisfies its required fields, and the README
starts from the honest sentences instead of from marketing.

The contributor fills in real events and expectations; the structure never
has to be reverse-engineered from an existing vector.
"""
from __future__ import annotations

import json
import os
import re
from typing import Dict, List

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")

_EVENT_BASE = {
    "schema": "verovo.lab/funnel-event",
    "schema_version": "1.0.0",
}


def _event(kind: str, name: str, extra: Dict = None) -> Dict:
    ev = dict(_EVENT_BASE)
    ev.update({
        "event": kind,
        "experiment_id": "%s-001" % name,
        "assignment_id": "assignment-001",
        "harness_id": "fill-me-harness",
        "task_id": "fill-me-task",
        "variant_id": "fill-me-variant",
        "replicate": 1,
        "subject_id": "fill-me-subject",
        "rules_version": "fill-me-rules/1.0.0",
    })
    if extra:
        ev.update(extra)
    return ev


def validate_name(name: str) -> str:
    if not NAME_RE.match(name or ""):
        raise ValueError(
            "vector name must be lowercase letters/digits/hyphens, 3-40 "
            "chars (e.g. 'acme-cache-retry'); got %r" % name)
    return name


def scaffold(name: str, out_root: str,
             contributed_by: str = "") -> Dict[str, str]:
    """Generate a CI-valid external vector directory. Returns paths written."""
    name = validate_name(name)
    slug = "%s-001" % name
    directory = os.path.join(out_root, slug)
    if os.path.exists(directory):
        raise ValueError("%s already exists — pick a new name or -002 suffix"
                         % directory)
    os.makedirs(directory)

    # A complete minimal funnel: reach → choice → attempt → operation_result
    # → consumption. Valid FMT-002 as generated; contributors replace the
    # fill-me values with real observations.
    # Per-type required fields follow the FMT-002 oneOf branches exactly.
    events: List[Dict] = [
        _event("reach", name, {"candidate_ids": ["fill-me-candidate-a",
                                                 "fill-me-candidate-b"]}),
        _event("choice", name, {"selected_id": "fill-me-candidate-a",
                                "selected_subject": True}),
        _event("attempt", name, {"operation_index": 1, "attempt_index": 1,
                                 "outcome": "success",
                                 "steps": 1, "latency_ms": 1, "cost_units": 0}),
        _event("operation_result", name, {"operation_index": 1,
                                          "outcome": "success",
                                          "attempts": 1}),
        _event("consumption", name, {"operation_index": 1, "consumed": True,
                                     "signal": "task_continuation"}),
    ]
    fixture_name = "verovo_%s_fixture_001.events.jsonl" % name.replace("-", "_")
    fixture_path = os.path.join(directory, fixture_name)
    with open(fixture_path, "w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    metadata_path = os.path.join(directory, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as fh:
        json.dump({
            "source": "TODO: repo @ commit / URL of the corpus",
            "time_window": "TODO: e.g. 2026-10-01..2026-10-07",
            "observation_surface": "TODO: e.g. server wrapper logs",
            "data_class": "synthetic",
            "_note": "data_class must be production or synthetic; say "
                     "synthetic unless the corpus is real",
        }, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    expected_path = os.path.join(directory, "expected.json")
    with open(expected_path, "w", encoding="utf-8") as fh:
        json.dump({
            "case": "%s-001: one sentence on what this vector pins" % name,
            "expected": {
                "TODO": "replace with the pinned values your runner asserts",
                "example_metric": None,
            },
            "claim_boundary": "what this vector IS (schema + computation on "
                              "these events) and IS NOT (no endorsement, no "
                              "production claim beyond the pinned corpus)",
        }, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    readme_path = os.path.join(directory, "README.md")
    credit = contributed_by or "TODO your handle / org"
    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write("""# {slug} — one-line description of the boundary this vector pins

Contributed by **{credit}**. Pinned source: fill in repo @ commit.

## What this vector is

The FMT-002 fixture (`{fixture}`) carries N events of {name}'s
measurement path; `expected.json` pins the values a correct implementation
must produce on exactly these events. The pack validates the fixture
schema as generated:

    verovo conformance --fixture {fixture} --metadata metadata.json

## What this vector is not

- Not an endorsement by, or verification of, any product.
- Not a production claim beyond the pinned corpus in `metadata.json`.
- Not a benchmark of anything except the computation it pins.

Fill in the TODOs, replace fill-me values with real observations, open a
pull request — the directory layout is already CI-shaped.
""".format(slug=slug, credit=credit, fixture=fixture_name, name=name))

    return {"directory": directory, "fixture": fixture_path,
            "metadata": metadata_path, "expected": expected_path,
            "readme": readme_path}
