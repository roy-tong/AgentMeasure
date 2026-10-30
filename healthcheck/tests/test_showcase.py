"""Showcase freeze tests: the public reproducible cases cannot silently drift.

examples/showcase/ publishes three cases with frozen expected outputs; these
tests re-run each case through the same code path the CLI uses and compare
the rendered reports to the frozen files. If behaviour changes on purpose,
regenerate the expected files in the same commit and say so in the changelog.
"""
import io
import json
import os
import unittest
from contextlib import redirect_stdout

from verovo_healthcheck import vendors
from verovo_healthcheck.cli import main

SHOWCASE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "examples", "showcase")

CASES = [
    ("case-a-overcharge-zendesk", ["--vendor", "zendesk"], False),
    ("case-b-both-directions-intercom", ["--vendor", "intercom"], False),
    ("case-c-contract-lane-intercom", ["--vendor", "intercom"], True),
]


class TestShowcaseFreeze(unittest.TestCase):
    def _run_case(self, name, extra, has_contract):
        csv_path = os.path.join(SHOWCASE, name + ".csv")
        expected_path = os.path.join(SHOWCASE, name + ".expected.txt")
        with open(expected_path, encoding="utf-8") as fh:
            expected = fh.read()

        argv = ["recount", "--export", csv_path] + extra
        if has_contract:
            argv += ["--contract", os.path.join(SHOWCASE, name + ".contract.json")]
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue().strip(), expected.strip(),
                         "showcase output drifted from the frozen file: %s" % name)

    def test_all_showcase_outputs_match_frozen_files(self):
        for name, extra, has_contract in CASES:
            self._run_case(name, extra, has_contract)

    def test_case_c_contract_json_is_valid_overlay(self):
        # load via the public loader to assert the shipped file stays valid
        loaded = vendors.load_contract(os.path.join(
            SHOWCASE, "case-c-contract-lane-intercom.contract.json"))
        self.assertEqual(loaded["reopen_window_hours"], 72)
        self.assertTrue(loaded["human_takeover_disqualifies"])

    def test_case_a_sample_matches_bundled_demo_export(self):
        bundled = os.path.join(os.path.dirname(os.path.abspath(vendors.__file__)),
                               "demo", "sample-recount-export.csv")
        with open(bundled, encoding="utf-8") as fh:
            bundled_text = fh.read()
        with open(os.path.join(SHOWCASE, "case-a-overcharge-zendesk.csv"),
                  encoding="utf-8") as fh:
            showcase_text = fh.read()
        self.assertEqual(bundled_text, showcase_text,
                         "README sample (--sample) and showcase case A must "
                         "stay the same file content")


if __name__ == "__main__":
    unittest.main()
