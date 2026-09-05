#!/usr/bin/env bash
# Install smoke test (R3/R6 acceptance: "发布产物冒烟通过").
# Builds the package the way a user would install it, then runs the installed
# console command against the bundled fixtures — not the repository checkout.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

python3 -m venv "$tmp/venv"
# A fresh venv bundles pip+setuptools; make sure setuptools is present before
# building with --no-build-isolation, which keeps the build fully offline.
"$tmp/venv/bin/pip" install --quiet --no-build-isolation --upgrade setuptools
"$tmp/venv/bin/pip" install --quiet --no-build-isolation --no-deps "$here"

cd "$tmp"
"$tmp/venv/bin/agentmeasure" --version
"$tmp/venv/bin/agentmeasure" selftest
"$tmp/venv/bin/agentmeasure" demo --html "$tmp/demo.html" --json "$tmp/demo.json" \
    --save-snapshot "$tmp/demo-snap.json" --no-history >/dev/null
"$tmp/venv/bin/agentmeasure" validate "$tmp/demo.json" "$tmp/demo-snap.json"
"$tmp/venv/bin/python" "$here/examples/track-weekly.py" "$tmp/demo-snap.json" >/dev/null

echo "smoke: install + demo + selftest + validate + external example ALL OK"
