import os
import tempfile
import unittest

from buyer_ledger import ingest, parsing, presets
from buyer_ledger.store import LedgerStore


def write_tmp(content, name):
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class ProviderPresetTest(unittest.TestCase):
    def setUp(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db_path = db_path
        self.store = LedgerStore(db_path)
        self.paths = []

    def tearDown(self):
        self.store.close()
        os.unlink(self.db_path)
        for p in self.paths:
            os.unlink(p)

    def _import_fixture(self, name):
        preset = presets.PRESETS[name]
        path = write_tmp(preset["fixture"], preset["file_name"])
        self.paths.append(path)
        return ingest.import_file(
            self.store, path, provider=preset["provider"],
            tier=preset["tier"], doc_type=preset["doc_type"],
            period="2026-10")

    def test_every_preset_spec_is_valid_against_its_fixture_header(self):
        for name, preset in presets.PRESETS.items():
            header = preset["fixture"].splitlines()[0].split(",")
            errors = parsing.validate_spec(preset["spec"], header=header)
            self.assertEqual(errors, [], "preset %s invalid: %s" % (name, errors))

    def test_apply_then_import_replays_and_counts_usage_events(self):
        for name in presets.PRESETS:
            with self.subTest(preset=name):
                preset = presets.PRESETS[name]
                fingerprint = presets.apply_preset(self.store, name)
                rule = self.store.get_parse_rule(
                    fingerprint, provider=preset["provider"],
                    doc_type=preset["doc_type"], tier=preset["tier"])
                self.assertIsNotNone(rule)
                self.assertTrue(rule["approved"])
                self.assertEqual(rule["created_via"], "preset")

                r1 = self._import_fixture(name)
                self.assertFalse(r1["duplicate"])
                self.assertEqual(r1["usage_events"], 2)
                self.assertEqual(r1["charge_lines"], 0)
                self.assertEqual(r1["spec_source"], "replay")

                # 幂等：同内容重复导入不重复计费
                r2 = self._import_fixture(name)
                self.assertTrue(r2["duplicate"])

    def test_unmatched_header_falls_back_to_agent_hint_not_wrong_parse(self):
        # 表头与预设不一致（多了一列）→ 不得套用预设，应提示走 agent 草案
        presets.apply_preset(self.store, "openai/usage_csv")
        path = write_tmp(
            "Date,Requests,Input tokens,Cached input tokens,Output tokens,"
            "Total tokens,Cost (USD),Workspace\n2026-10-02,1,10,0,5,15,0.01,acme\n",
            "openai-usage-variant.csv")
        self.paths.append(path)
        r = ingest.import_file(self.store, path, provider="openai",
                               tier="platform_usage", doc_type="usage",
                               period="2026-10")
        self.assertEqual(r["usage_events"], 0)
        self.assertTrue(any("parse --agent" in n for n in r["notes"]))

    def test_preset_fingerprint_matches_same_header_different_values(self):
        # 指纹只取表头形状：真实导出（同表头、不同数值）应命中同一规则
        presets.apply_preset(self.store, "anthropic/usage_csv")
        path = write_tmp(
            "Date,Model,Input tokens,Output tokens,Cache creation tokens,"
            "Cache read tokens,Cost (USD)\n"
            "2026-10-09,claude-opus-4-5,999,99,9,9,0.09\n",
            "anthropic-usage.csv")
        self.paths.append(path)
        r = ingest.import_file(self.store, path, provider="anthropic",
                               tier="platform_usage", doc_type="usage",
                               period="2026-10")
        self.assertFalse(r["duplicate"])
        self.assertEqual(r["usage_events"], 1)
        self.assertEqual(r["spec_source"], "replay")


if __name__ == "__main__":
    unittest.main()
