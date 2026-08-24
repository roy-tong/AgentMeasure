"""Regression tests for #8: oneOf/anyOf must not swallow sibling keywords.

Found during the first external conformance pass (Urusilla fixture,
langfuse/langfuse#16383): the validator returned after evaluating oneOf,
so a record that matched one branch but missed root-level required
fields (e.g. funnel-event.schema.json requires experiment_id, task_id,
variant_id at the same level as oneOf) validated successfully.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab.schemas import SchemaError, validate

# Root schema shape mirrors lab/schemas/funnel-event.schema.json:
# oneOf and required are siblings at the same level.
SCHEMA = {
    "type": "object",
    "required": ["event", "experiment_id", "task_id", "variant_id"],
    "properties": {
        "event": {"type": "string"},
        "experiment_id": {"type": "string"},
        "task_id": {"type": "string"},
        "variant_id": {"type": "string"},
        "payload": {"type": "object"},
    },
    "oneOf": [
        {
            "properties": {"payload": {"required": ["tool"]}},
        },
        {
            "properties": {"payload": {"required": ["model"]}},
        },
    ],
}

VALID = {
    "event": "attempt_completed",
    "experiment_id": "exp-1",
    "task_id": "task-1",
    "variant_id": "v1",
    "payload": {"tool": "web.search"},
}


class OneOfSiblingTests(unittest.TestCase):
    def test_valid_record_passes(self):
        validate(VALID, SCHEMA)  # must not raise

    def test_missing_root_required_is_rejected_after_oneof_matches(self):
        # #8 exact scenario: oneOf branch matches, root sibling is missing.
        bad = dict(VALID)
        del bad["experiment_id"]
        with self.assertRaises(SchemaError) as ctx:
            validate(bad, SCHEMA)
        self.assertIn("experiment_id", str(ctx.exception))

    def test_all_root_required_enforced(self):
        for field in ("event", "task_id", "variant_id"):
            bad = dict(VALID)
            del bad[field]
            with self.assertRaises(SchemaError):
                validate(bad, SCHEMA)

    def test_zero_or_multiple_branches_still_fail(self):
        bad = dict(VALID)
        bad["payload"] = {"tool": "web.search", "model": "m1"}  # matches both
        with self.assertRaises(SchemaError) as ctx:
            validate(bad, SCHEMA)
        self.assertIn("matched 2 branches", str(ctx.exception))

    def test_anyof_sibling_enforced(self):
        schema = {
            "type": "object",
            "required": ["experiment_id"],
            "anyOf": [
                {"properties": {"kind": {"const": "a"}}},
                {"properties": {"kind": {"const": "b"}}},
            ],
        }
        ok = {"kind": "a", "experiment_id": "exp-1"}
        validate(ok, schema)  # must not raise
        bad = {"kind": "a"}  # anyOf matches, root sibling missing
        with self.assertRaises(SchemaError):
            validate(bad, schema)

    def test_branch_error_detail_surfaces(self):
        bad = dict(VALID)
        bad["payload"] = {}  # matches no branch
        with self.assertRaises(SchemaError) as ctx:
            validate(bad, SCHEMA)
        self.assertIn("matched 0 branches", str(ctx.exception))
        self.assertIn("first branch error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
