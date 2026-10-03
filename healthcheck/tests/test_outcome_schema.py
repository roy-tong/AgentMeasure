"""Outcome-unit schema tests (BP r28 p14 Emerging row — schema before engine).

The BP's own sequencing for outcome pricing: "先做 schema". These tests pin
the v1 schema with a compact draft-07 subset validator (type / required /
enum / properties / items / minLength / pattern / minima — the features the
schema actually uses), so the two examples always validate and the negative
example always fails. The schema is the contract; the validator here is its
conformance proof.
"""
import json
import os
import re
import unittest

from _support import REPO_ROOT

SCHEMA_PATH = os.path.join(REPO_ROOT, "schemas", "outcome-unit.schema.json")
EXAMPLES_DIR = os.path.join(REPO_ROOT, "schemas", "examples", "outcome-units")

DATE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def validate(instance, schema, path="$"):
    """Draft-07 subset: the keywords outcome-unit.schema.json uses."""
    errors = []
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) \
            else [schema["type"]]
        checks = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float))
                                and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
        }
        if not any(checks[t](instance) for t in types):
            return ["%s: expected type %s" % (path, "/".join(types))]

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: shorter than minLength %d"
                          % (path, schema["minLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: does not match pattern %s"
                          % (path, schema["pattern"]))
        if schema.get("format") == "date-time" \
                and not DATE_TIME_RE.match(instance):
            errors.append("%s: not an ISO date-time" % path)

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: below minimum" % path)
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append("%s: not above exclusiveMinimum" % path)
        if "maxLength" in schema and instance > schema["maxLength"]:
            errors.append("%s: above maxLength" % path)

    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r not in enum %s" % (path, instance, schema["enum"]))

    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                errors.append("%s: missing required %r" % (path, name))
        for name, sub in schema.get("properties", {}).items():
            if name in instance:
                errors += validate(instance[name], sub,
                                   "%s.%s" % (path, name))

    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errors += validate(item, schema["items"], "%s[%d]" % (path, i))

    return errors


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class TestOutcomeUnitSchema(unittest.TestCase):
    def test_schema_itself_is_valid_json(self):
        schema = load(SCHEMA_PATH)
        self.assertEqual(schema["$schema"],
                         "http://json-schema.org/draft-07/schema#")

    def test_example_qualified_lead_validates(self):
        errors = validate(load(os.path.join(EXAMPLES_DIR,
                                            "qualified-lead.json")),
                          load(SCHEMA_PATH))
        self.assertEqual(errors, [])

    def test_example_completed_case_validates(self):
        errors = validate(load(os.path.join(EXAMPLES_DIR,
                                            "completed-case.json")),
                          load(SCHEMA_PATH))
        self.assertEqual(errors, [])

    def test_invalid_example_fails_on_missing_contract_ref(self):
        errors = validate(load(os.path.join(
            EXAMPLES_DIR, "invalid-missing-contract-ref.json")),
            load(SCHEMA_PATH))
        self.assertTrue(any("contract_ref" in e for e in errors))

    def test_unproven_unit_is_representable(self):
        # A criterion that cannot be evidenced must be expressible without
        # failing the schema — UNPROVABLE is a first-class state here too.
        unit = load(os.path.join(EXAMPLES_DIR, "qualified-lead.json"))
        self.assertEqual(unit["status"], "unproven")
        self.assertTrue(unit["qualification"]["criteria_unproven"])

    def test_schema_discipline_matches_settlement_grades(self):
        # observer_grade must stay aligned with AMS-1's ladder.
        schema = load(SCHEMA_PATH)
        grades = schema["properties"]["observer_grade"]["enum"]
        self.assertEqual(
            grades, ["self_attested", "affected_party", "third_party_corroborated"])


if __name__ == "__main__":
    unittest.main()
