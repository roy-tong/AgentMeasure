"""History command tests (G6 local half: experiment / hypothesis library)."""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentmeasure_lab.cli import main as cli_main
from tests._support import LabWorkspace, base_manifest


class TestHistory(unittest.TestCase):
    def test_history_lists_runs_with_verdicts_and_hashes(self):
        ws = LabWorkspace()
        cwd = os.getcwd()
        try:
            os.chdir(ws.tmp)
            # two experiments: one adoptable, one honest null
            ws.run(base_manifest(experiment_id="hist-uplift", seed=20260822, replicates=40))
            null_manifest = base_manifest(
                experiment_id="hist-null",
                seed=20260822,
                replicates=8,
                variants=[
                    {"id": "control", "baseline": True,
                     "levels": {"description_clarity": "control", "version_label": "a"}},
                    {"id": "label-b", "baseline": False,
                     "levels": {"description_clarity": "control", "version_label": "b"}},
                ],
            )
            null_manifest["analysis"]["min_sample_per_arm"] = 2
            ws.run(null_manifest)

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli_main(["lab", "history", "--runs", ws.tmp])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn("hist-uplift", text)
            self.assertIn("hist-null", text)
            self.assertIn("adopt_candidate", text)
            self.assertIn("prereg", text)
            self.assertIn("fingerprint", text)
            self.assertIn("2 run(s)", text)
        finally:
            os.chdir(cwd)
            ws.close()

    def test_history_empty_is_friendly(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            cwd = os.getcwd()
            try:
                os.chdir(td)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = cli_main(["lab", "history"])
                self.assertEqual(code, 0)
                self.assertIn("no runs found", out.getvalue())
            finally:
                os.chdir(cwd)

    def test_run_json_has_created_at(self):
        import json

        ws = LabWorkspace()
        try:
            _, run_dir, _ = ws.run(base_manifest(experiment_id="hist-ts", seed=1, replicates=2))
            with open(os.path.join(run_dir, "run.json"), encoding="utf-8") as fh:
                meta = json.load(fh)
            self.assertIn("created_at", meta)
            self.assertIn("T", meta["created_at"])
        finally:
            ws.close()


if __name__ == "__main__":
    unittest.main()
