"""Conformance Pack tests — contract C1/C5 acceptance cases as unittest.

The pack must actually read caller files (not wrap fixed sample runners),
distinguish contradictory declarations from missing evidence, and keep
UNPROVABLE as a first-class result.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "conformance" / "pack"
VEC = ROOT / "conformance" / "vectors" / "external" / "urusilla-002"
FIXTURE = VEC / "agentmeasure_urusilla_fixture_002.events.jsonl"


def run_pack(args):
    return subprocess.run(
        [sys.executable, str(PACK / "agentmeasure")] + args,
        capture_output=True, text=True, timeout=120)


class PackSelftest(unittest.TestCase):
    def test_selftest(self):
        r = run_pack(["selftest"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SELFTEST PASS", r.stdout)


class PackCallerInput(unittest.TestCase):
    def test_correct_claims_pass(self):
        with self.subTest():
            r = run_pack(["conformance", "--fixture", str(FIXTURE)])
            self.assertEqual(r.returncode, 0)
            self.assertIn("5 invariants checked: all PASS", r.stdout)
            self.assertIn("NOT-SUPPORTED", r.stdout)  # token/cache honesty

    def test_wrong_claims_fail_exit_1(self):
        claims = Path(self.id().replace("=", "_") + ".json")
        claims.write_text(json.dumps({"median_steps_per_operation": 5.0}))
        try:
            r = run_pack(["conformance", "--fixture", str(FIXTURE), "--claims", str(claims)])
            self.assertEqual(r.returncode, 1)
            self.assertIn("FAIL", r.stdout)
            self.assertIn("operation-grain", r.stdout)
        finally:
            claims.unlink(missing_ok=True)

    def test_missing_evidence_unprovable_exit_0(self):
        evs = [json.loads(l) for l in FIXTURE.read_text().splitlines() if l.strip()]
        no_decl = Path(self.id() + ".jsonl")
        no_decl.write_text("\n".join(json.dumps(e) for e in evs if e.get("event") != "operation_result"))
        try:
            r = run_pack(["conformance", "--fixture", str(no_decl)])
            self.assertEqual(r.returncode, 0)
            self.assertIn("UNPROVABLE", r.stdout)
            self.assertIn("unsafe inference refused", r.stdout)
            self.assertNotIn("all PASS", r.stdout)
        finally:
            no_decl.unlink(missing_ok=True)

    def test_require_unproven_blocks(self):
        evs = [json.loads(l) for l in FIXTURE.read_text().splitlines() if l.strip()]
        no_decl = Path(self.id() + ".jsonl")
        no_decl.write_text("\n".join(json.dumps(e) for e in evs if e.get("event") != "operation_result"))
        try:
            r = run_pack(["conformance", "--fixture", str(no_decl), "--require", "execution-grain"])
            self.assertEqual(r.returncode, 1)
            self.assertIn("not proven", r.stderr)
        finally:
            no_decl.unlink(missing_ok=True)

    def test_invalid_json_exit_2(self):
        bad = Path(self.id() + ".jsonl")
        bad.write_text('{"broken": tru\n')
        try:
            r = run_pack(["conformance", "--fixture", str(bad)])
            self.assertEqual(r.returncode, 2)
            self.assertIn("FMT-002", r.stderr)
        finally:
            bad.unlink(missing_ok=True)

    def test_json_output_written(self):
        out = Path(self.id() + ".json")
        r = run_pack(["conformance", "--fixture", str(FIXTURE), "--json", str(out)])
        self.assertEqual(r.returncode, 0)
        data = json.loads(out.read_text())
        self.assertEqual(data["counts"]["PASS"], 5)
        self.assertFalse(data["claims_mode"])
        out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
