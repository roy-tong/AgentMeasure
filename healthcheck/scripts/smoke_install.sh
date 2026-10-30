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
  "$tmp/venv/bin/pip" install --quiet --no-deps "$tmp/wheels"/verovo-*.whl
else
  "$tmp/venv/bin/pip" install --quiet --no-build-isolation --no-deps "$here"
fi

cd "$tmp"
"$tmp/venv/bin/verovo" --version
"$tmp/venv/bin/verovo" selftest
"$tmp/venv/bin/verovo" demo --html "$tmp/demo.html" --json "$tmp/demo.json" \
    --save-snapshot "$tmp/demo-snap.json" --no-history >/dev/null
"$tmp/venv/bin/verovo" validate "$tmp/demo.json" "$tmp/demo-snap.json"
"$tmp/venv/bin/python" "$here/examples/track-weekly.py" "$tmp/demo-snap.json" >/dev/null

# Settlement surface. `recount --list-vendors` reads the packaged
# vendor-rules.json, so a data file missing from the wheel fails here rather
# than only in a user's install. The recount and dispute runs then exercise the
# rules and the pack writer against the shipped fixture.
"$tmp/venv/bin/verovo" review --sample --html "$tmp/buyer.html" --json "$tmp/buyer.json" >/dev/null
"$tmp/venv/bin/verovo" recount --list-vendors >/dev/null
"$tmp/venv/bin/verovo" recount --sample --json "$tmp/sample.json" >/dev/null
printf '%s\n' '{"type":"assistant","message":{"id":"smoke"}}' > "$tmp/response.jsonl"
"$tmp/venv/bin/verovo" response-audit "$tmp/response.jsonl" --json "$tmp/response-audit.json" >/dev/null
"$tmp/venv/bin/verovo" recount \
    --export "$here/verovo_healthcheck/fixtures/vendor-export-intercom.csv" \
    --vendor intercom --json "$tmp/recount.json" >/dev/null
"$tmp/venv/bin/verovo" recount \
    --export "$here/verovo_healthcheck/fixtures/vendor-export-intercom.csv" \
    --vendor intercom --inspect >/dev/null
"$tmp/venv/bin/verovo" dispute \
    --export "$here/verovo_healthcheck/fixtures/vendor-export-intercom.csv" \
    --vendor intercom --price 0.99 --out "$tmp/pack" --buyer "smoke" >/dev/null
test -f "$tmp/pack/dispute-pack.md"
test -f "$tmp/pack/dispute-pack.json"

"$tmp/venv/bin/verovo" conformance --new-vector smoke-case --out "$tmp/vectors"
"$tmp/venv/bin/verovo" inspect-input "$tmp/vectors/smoke-case-001/verovo_smoke_case_fixture_001.events.jsonl"
"$tmp/venv/bin/verovo" conformance --fixture "$tmp/vectors/smoke-case-001/verovo_smoke_case_fixture_001.events.jsonl"

echo "smoke: conformance + install + demo + selftest + validate + settlement surface ALL OK"
