# v0.4.1 — CLI regression fix

Fixes the PyPI 0.4.0 first-command crash reported by a real user (morpheus): `_run_check` read an unbound `args` for `audit_mode` / `sdk_events_path` (NameError on `demo` / `check` / `compare`). Main already passed the values as parameters; this release ships that fix to PyPI.

- `fix(cli)`: 717c2d3 — release 0.4.1 (regression shipped in 0.4.0)
- `docs`: e4d287d — README warns PyPI served crashing 0.4.0; git install as the working door

Install: `pip install agentmeasure==0.4.1` (or `pipx upgrade agentmeasure`).
