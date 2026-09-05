#!/usr/bin/env bash
# Install smoke test (R3/R6 acceptance: "发布产物冒烟通过").
# Default: install from the source tree the way a user would.
# `--wheel`: build the wheel first and install that — verifies the exact
# artifact shape that PyPI will serve.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

python3 -m venv "$tmp/venv"
# A fresh venv bundles pip+setuptools; make sure setuptools is present before
# building with --no-build-isolation, which keeps the build fully offline.
"$tmp/venv/bin/pip" install --quiet --no-build-isolation --upgrade setuptools

if [[ "${1:-}" == "--wheel" ]]; then
  "$tmp/venv/bin/pip" install --quiet --no-build-isolation wheel
  "$tmp/venv/bin/pip" wheel --quiet --no-deps --no-build-isolation \
      -w "$tmp/wheels" "$here"
  ls "$tmp/wheels"
  "$tmp/venv/bin/pip" install --quiet --no-deps "$tmp/wheels"/agentmeasure-*.whl
else
  "$tmp/venv/bin/pip" install --quiet --no-build-isolation --no-deps "$here"
fi

cd "$tmp"
"$tmp/venv/bin/agentmeasure" --version
"$tmp/venv/bin/agentmeasure" selftest
"$tmp/venv/bin/agentmeasure" demo --html "$tmp/demo.html" --json "$tmp/demo.json" \
    --save-snapshot "$tmp/demo-snap.json" --no-history >/dev/null
"$tmp/venv/bin/agentmeasure" validate "$tmp/demo.json" "$tmp/demo-snap.json"
"$tmp/venv/bin/python" "$here/examples/track-weekly.py" "$tmp/demo-snap.json" >/dev/null

echo "smoke: install + demo + selftest + validate + external example ALL OK"
