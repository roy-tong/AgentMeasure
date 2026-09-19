#!/usr/bin/env python3
"""Generate website/vendor-rules.js from registry/vendor-rules.json.

The registry file is the single source of truth. The browser-local recount needs
the rules with no network request after load, so they are inlined into a JS
global. This script is the only thing that writes that global.

  python3 scripts/gen_web_rules.py --build   # regenerate
  python3 scripts/gen_web_rules.py --check   # CI: fail if out of date

The parity test (conformance/runners/parity_recount.js) then checks that the
browser implementation and the Python implementation agree on the same fixture,
so an out-of-date rules file cannot silently ship.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "registry" / "vendor-rules.json"
DST = ROOT / "website" / "vendor-rules.js"

BANNER = """/* GENERATED FILE — do not edit.
 * Source: registry/vendor-rules.json (the single source of truth).
 * Regenerate with: python3 scripts/gen_web_rules.py --build
 * CI runs --check and fails if this file is out of date.
 */
"""


def render() -> str:
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    body = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True)
    # UMD-safe: the browser gets a global, node gets module.exports, so the
    # parity test can load the same file the page loads.
    return (BANNER
            + "(function (root, factory) {\n"
            + "  if (typeof module === \"object\" && module.exports) {\n"
            + "    module.exports = factory();\n"
            + "  } else {\n"
            + "    root.AGENTMEASURE_VENDOR_RULES = factory();\n"
            + "  }\n"
            + "})(typeof self !== \"undefined\" ? self : this, function () {\n"
            + "  return " + body + ";\n"
            + "});\n")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in argv
    expected = render()
    if check:
        actual = DST.read_text(encoding="utf-8") if DST.exists() else ""
        if actual != expected:
            print("  ✗ website/vendor-rules.js is out of date with "
                  "registry/vendor-rules.json")
            print("    run: python3 scripts/gen_web_rules.py --build")
            return 1
        print("  ✓ website/vendor-rules.js in sync with the registry")
        return 0
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(expected, encoding="utf-8")
    print("  wrote %s (%d bytes)" % (DST.relative_to(ROOT), len(expected)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
