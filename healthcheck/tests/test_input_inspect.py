"""Input routing must not turn shape recognition into a conformance pass."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

from _support import HEALTHCHECK_DIR
from verovo_healthcheck import cli, input_inspect


class InputRoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "input.jsonl"

    def write(self, rows):
        self.path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    def run_cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_provider_shape_routes_without_claiming_validation(self):
        self.write([{"spec_version": "verovo-0.4", "observation_type": "attempt_started"}])
        result = input_inspect.inspect(self.path)
        self.assertEqual(result["format"], "canonical-observations")
        self.assertEqual(result["schema_validation"], "NOT-RUN")
        code, _, err = self.run_cli(["conformance", "--fixture", str(self.path)])
        self.assertEqual(code, 2)
        self.assertIn("schemas/validate_jsonl.py", err)
        self.assertNotIn("missing required property 'candidate_ids'", err)

    def test_mixed_input_never_silently_drops_other_rows(self):
        self.write([{"schema": "verovo.lab/funnel-event"}, {"spec_version": "verovo-0.4", "observation_type": "selection"}])
        r = input_inspect.inspect(self.path)
        self.assertEqual(r["format"], "mixed")
        self.assertEqual(r["nonempty_rows"], 2)
        self.assertEqual(self.run_cli(["inspect-input", str(self.path)])[0], 2)

    def test_invalid_json_retains_count_without_echoing_private_data(self):
        self.path.write_text('SECRET-PROMPT\n{"x": NaN}\n', encoding="utf-8")
        r = input_inspect.inspect(self.path)
        self.assertEqual(r["invalid_json_rows"], 2)
        self.assertNotIn("SECRET", json.dumps(r))

    def test_shape_recognition_does_not_bypass_fmt_validation(self):
        self.write([{"schema": "verovo.lab/funnel-event"}])
        self.assertEqual(self.run_cli(["inspect-input", str(self.path)])[0], 0)
        self.assertEqual(self.run_cli(["conformance", "--fixture", str(self.path)])[0], 2)

    def test_no_input_overwrite(self):
        self.write([{"type": "session_meta"}])
        before = self.path.read_bytes()
        self.assertEqual(self.run_cli(["inspect-input", str(self.path), "--json", str(self.path)])[0], 2)
        self.assertEqual(before, self.path.read_bytes())
        alias = Path(self.tmp.name) / "hardlink.jsonl"
        os.link(self.path, alias)
        self.assertEqual(self.run_cli(["inspect-input", str(self.path), "--json", str(alias)])[0], 2)
        self.assertEqual(before, self.path.read_bytes())

    def test_empty_unknown_and_ambiguous_are_not_success(self):
        for rows in ([], [{}], [42], [{"schema": "verovo.lab/funnel-event", "spec_version": "verovo-0.4", "observation_type": "selection"}]):
            self.write(rows)
            self.assertEqual(self.run_cli(["inspect-input", str(self.path)])[0], 2)

    def test_report_export_and_utf8_bom(self):
        self.path.write_text('\ufeff{"type":"session_meta"}\n', encoding="utf-8")
        output = Path(self.tmp.name) / "routing.json"
        self.assertEqual(self.run_cli(["inspect-input", str(self.path), "--json", str(output)])[0], 0)
        self.assertEqual(json.loads(output.read_text())["measurement_verdict"], "NOT-RUN")

    def test_missing_file_returns_input_error(self):
        self.assertEqual(self.run_cli(["inspect-input", str(self.path)])[0], 2)
        self.assertEqual(self.run_cli(["conformance", "--fixture", str(self.path)])[0], 2)
