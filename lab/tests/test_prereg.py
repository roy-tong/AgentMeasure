import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab.prereg import (
    canonical_json,
    create_preregistration,
    load_manifest,
    manifest_hash,
)
from tests._support import LAB_DIR, base_manifest


class TestPrereg(unittest.TestCase):
    def test_canonical_json_key_order_independent(self):
        a = {"x": 1, "y": {"b": 2, "a": 3}}
        b = {"y": {"a": 3, "b": 2}, "x": 1}
        self.assertEqual(canonical_json(a), canonical_json(b))

    def test_hash_changes_when_hypothesis_changes(self):
        m = base_manifest()
        m2 = copy.deepcopy(m)
        m2["hypothesis"] = "a different hypothesis entirely"
        self.assertNotEqual(manifest_hash(m), manifest_hash(m2))

    def test_example_manifest_validates(self):
        path = os.path.join(LAB_DIR, "examples", "example-manifest.json")
        manifest = load_manifest(path)
        self.assertEqual(manifest["experiment_id"], "example-desc-clarity-001")

    def test_manifest_requires_single_baseline(self):
        m = base_manifest()
        m["variants"].append({"id": "b2", "baseline": True, "levels": {"description_clarity": "control", "version_label": "a"}})
        from agentmeasure_lab.prereg import validate_manifest
        with self.assertRaises(ValueError):
            validate_manifest(m)

    def test_unknown_factor_level_rejected(self):
        m = base_manifest()
        m["variants"][1]["levels"]["description_clarity"] = "nonexistent"
        from agentmeasure_lab.prereg import validate_manifest
        with self.assertRaises(ValueError):
            validate_manifest(m)

    def test_prereg_detects_tampering(self):
        import json
        import tempfile

        m = base_manifest(experiment_id="tamper-check")
        record = create_preregistration(m)
        with tempfile.NamedTemporaryFile("w", suffix=".prereg.json", delete=False) as fh:
            json.dump(record, fh)
            path = fh.name
        try:
            from agentmeasure_lab.prereg import load_preregistration
            load_preregistration(path)  # untouched: fine

            record["manifest"]["analysis"]["alpha"] = 0.01  # post-hoc plan change
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(record, fh)
            with self.assertRaises(ValueError):
                load_preregistration(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
