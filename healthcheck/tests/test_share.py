"""Share-summary redaction: the whitelist is the only way out.

Planted strings cover prompts/paths/commands/repo names/session ids/call ids.
If any of them appears in the serialized share output, the whitelist leaked.
"""
import json
import os
import re
import unittest

from _support import fixture, HEALTHCHECK_DIR

from am_healthcheck.checks import run_checks
from am_healthcheck.codex import parse_session
from am_healthcheck.share import (ALLOWED_KEYS, build_share_summary,
                                  share_json, share_markdown)

PLANTED = [
    "secret-project",      # repo-ish path segment
    "Users/tongxiarui",    # local path
    "call_demo_1",         # call id
    "deploy-prod",         # tool name
    "SESSIONUUID",         # session id fragment
    "exec-001",            # exec item id
]


class TestShareRedaction(unittest.TestCase):
    def setUp(self):
        s = parse_session(fixture("codex-ok.jsonl"))
        ov, results, _cov, _top = run_checks([s], "unit")
        self.summary = build_share_summary(ov, results, "synthetic-demo", "unit")

    def test_whitelist_keys_only(self):
        self.assertEqual(set(self.summary.keys()), ALLOWED_KEYS)

    def test_no_planted_strings_in_json(self):
        blob = share_json(self.summary)
        for planted in PLANTED:
            self.assertNotIn(planted, blob)

    def test_no_planted_strings_in_markdown(self):
        blob = share_markdown(self.summary)
        for planted in PLANTED:
            self.assertNotIn(planted, blob)

    def test_checks_list_is_bounded_structure(self):
        for c in self.summary["checks"]:
            self.assertEqual(set(c.keys()), {"check", "name", "status"})

    def test_json_serializable_and_sorted(self):
        blob = share_json(self.summary)
        parsed = json.loads(blob)
        self.assertEqual(parsed["tool"], "AgentMeasure Healthcheck")


class TestNoNetworkCode(unittest.TestCase):
    def test_package_imports_no_network_modules(self):
        banned = ("socket", "http", "urllib", "requests", "ftplib", "smtplib",
                  "xmlrpc", "telnetlib", "asyncio", "subprocess")
        pkg = os.path.join(HEALTHCHECK_DIR, "am_healthcheck")
        for name in os.listdir(pkg):
            if not name.endswith(".py"):
                continue
            with open(os.path.join(pkg, name), encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    match = re.match(
                        r"^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_.]*)", stripped)
                    if not match:
                        continue
                    root = match.group(1).split(".")[0]
                    self.assertNotIn(
                        root, banned,
                        "%s:%d imports %s — healthcheck must stay offline"
                        % (name, lineno, root))


if __name__ == "__main__":
    unittest.main()
