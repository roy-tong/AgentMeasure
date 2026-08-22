"""`am lab` command-line interface (LAB-001).

Zero-friction contract (PRD §4.1): no registration, no network, no cloud —
any step that would require one is a product defect.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, List, Optional

from . import __version__
from .prereg import (
    create_preregistration,
    load_manifest,
    load_preregistration,
    save_preregistration,
)


def _repo_lab_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def cmd_init(args) -> int:
    workdir = args.dir
    exp_dir = os.path.join(workdir, "experiments")
    os.makedirs(exp_dir, exist_ok=True)
    src_manifest = os.path.join(_repo_lab_dir(), "examples", "example-manifest.json")
    dst_manifest = os.path.join(exp_dir, "example-manifest.json")
    shutil.copyfile(src_manifest, dst_manifest)

    # Task set ships with the repo; rewrite the reference relative to the
    # manifest's new location so quickstart works from the repo root.
    manifest = load_manifest(dst_manifest)
    task_abs = os.path.normpath(os.path.join(_repo_lab_dir(), "tasks", os.path.basename(manifest["task_set"]["path"])))
    manifest["task_set"]["path"] = os.path.relpath(task_abs, exp_dir)
    with open(dst_manifest, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"initialized {workdir}/")
    print(f"  experiment manifest : {dst_manifest}")
    print(f"  task set            : {os.path.normpath(manifest['task_set']['path'])} (shipped, synthetic)")
    print("next steps:")
    print(f"  python3 lab/am lab preregister {dst_manifest}")
    print(f"  python3 lab/am lab run <preregistration-file>")
    return 0


def _prereg_preview(manifest: Dict[str, Any], manifest_dir: str) -> None:
    """Scale / power / budget preview before anything is locked or run
    (PRD LAB-002 acceptance + NFR-COST-001: cost is estimated up front)."""
    from . import matrix, stats

    try:
        task_path = matrix.resolve_task_path(manifest["task_set"]["path"], manifest_dir)
        task_set = matrix.load_task_set(task_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"  scale preview unavailable: {e}")
        return
    plan = matrix.build_plan(manifest, task_set)
    summary = matrix.plan_summary(plan, task_set)
    min_n = int(manifest["analysis"]["min_sample_per_arm"])
    per_arm = summary["per_arm"]
    print(f"  plan: {summary['assignments_total']} assignments · {summary['tasks']} tasks · per-arm n={per_arm}")
    smallest = min(per_arm.values())
    if smallest < min_n:
        print(f"  WARNING: smallest arm n={smallest} < preregistered minimum {min_n} (undetermined verdicts likely)")
    # Planning-aid power table (assumed 25% baseline; the point is the order
    # of magnitude, not a promise).
    row = []
    for delta in (0.02, 0.03, 0.05, 0.08):
        n = stats.required_n_per_arm(0.25, 0.25 + delta)
        row.append(f"+{int(delta * 100)}pp≈{n:,}/arm")
    print(f"  power planning aid (at an assumed 25% baseline): {' · '.join(row)}")
    budget = manifest["budget"]
    worst = matrix.budget_estimate(plan, 3, 20)
    print(f"  budget caps: {budget['max_operations']:,} ops · {budget['max_cost_units']:,} cost units · "
          f"{budget['max_wall_clock_seconds']}s wall clock (worst-case spend ≈ {worst['max_cost_units']:,.0f} cost units)")


def cmd_preregister(args) -> int:
    manifest = load_manifest(args.manifest)
    record = create_preregistration(manifest)
    out = args.out or (
        os.path.splitext(args.manifest)[0] + ".prereg.json"
    )
    save_preregistration(record, out)
    print(f"preregistration locked: {out}")
    print(f"  experiment   : {record['experiment_id']}")
    print(f"  manifest hash: {record['manifest_hash']}")
    _prereg_preview(manifest, os.path.dirname(os.path.abspath(args.manifest)))
    print("  the hypothesis, primary metric, guardrails and analysis plan are now immutable;")
    print("  changing them means starting a NEW experiment, not editing this file.")
    return 0


def cmd_run(args) -> int:
    prereg = load_preregistration(args.prereg)
    manifest_dir = os.path.dirname(os.path.abspath(args.prereg))
    runs_root = args.out
    if runs_root is None:
        # Predictable, cwd-relative default (POC finding: the old
        # manifest-parent heuristic wrote runs to surprising locations).
        runs_root = os.path.join("am-lab", "runs") if os.path.isdir("am-lab") else "runs"
    out_dir = os.path.join(runs_root, prereg["experiment_id"])
    if os.path.exists(out_dir):
        n = 2
        while os.path.exists(f"{out_dir}-{n}"):
            n += 1
        out_dir = f"{out_dir}-{n}"

    from .runner import run_experiment

    report = run_experiment(prereg, out_dir, manifest_dir)
    run = report["run"]
    print(f"run {'complete' if run['status'] == 'complete' else 'INCOMPLETE (' + str(run['stopped_reason']) + ')'}")
    print(f"  assignments : {run['assignments_executed']}/{run['assignments_planned']}")
    print(f"  fingerprint : {run['run_fingerprint']}")
    for v in report.get("variants", []):
        if v.get("baseline"):
            continue
        line = f"  {v['variant_id']}: {v['verdict']}"
        cmp = v.get("primary_comparison", {})
        if cmp.get("difference") is not None:
            line += f" (Δ {cmp['difference']*100:+.1f}pp, p={cmp.get('p_value')})"
        print(line)
    print(f"  report      : {os.path.join(out_dir, 'report.html')}")
    print(f"               {os.path.join(out_dir, 'report.json')}")
    return 0


def cmd_report(args) -> int:
    from . import analysis, report as report_mod
    from .runner import _rebuild_report

    report = _rebuild_report(args.run_dir, args.prereg)
    with open(os.path.join(args.run_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    with open(os.path.join(args.run_dir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(report_mod.render_html(report))
    print(f"report regenerated (deterministic) in {args.run_dir}")
    return 0


def cmd_verify(args) -> int:
    from .runner import verify_run

    prereg = load_preregistration(args.prereg)
    manifest_dir = os.path.dirname(os.path.abspath(args.prereg))
    result = verify_run(args.run_dir, prereg, manifest_dir)
    ok = result["prereg_hash_matches"] and result["events_schema_valid"] and result["fingerprint_matches"]
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("verify:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_selftest(args) -> int:
    """Built-in end-to-end sanity: one planted uplift + one honest null."""
    from .selftest import run_selftest

    ok = run_selftest()
    return 0 if ok else 1


def cmd_history(args) -> int:
    """Local experiment history / hypothesis library (G6, local half).

    Experiments are a repeating need; this lists every run in the workspace
    with its preregistration hash, verdicts and fingerprint — the local
    evidence trail behind 'what did we already test, and what did it say'.
    """
    import glob

    candidates = [args.runs] if args.runs else ["am-lab/runs", "runs"]
    rows = []
    for root in candidates:
        for report_path in sorted(glob.glob(os.path.join(root, "*", "report.json"))):
            run_dir = os.path.dirname(report_path)
            try:
                with open(report_path, "r", encoding="utf-8") as fh:
                    report = json.load(fh)
                meta_path = os.path.join(run_dir, "run.json")
                created = ""
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as fh:
                        meta = json.load(fh)
                    created = (meta.get("created_at") or "")[:10]
                if not created:
                    created = datetime.date.fromtimestamp(
                        os.path.getmtime(report_path)
                    ).isoformat()
                verdicts = ", ".join(
                    f"{v['variant_id']}={v['verdict']}"
                    for v in report["variants"]
                    if not v.get("baseline")
                )
                rows.append(
                    {
                        "created": created,
                        "experiment": report["experiment_id"],
                        "status": report["run"]["status"],
                        "verdicts": verdicts,
                        "prereg": report["preregistration"]["manifest_hash"][:10],
                        "fingerprint": report["run"]["run_fingerprint"][:10],
                        "dir": run_dir,
                    }
                )
            except (OSError, ValueError, KeyError):
                continue
    if not rows:
        print("no runs found (looked in " + ", ".join(candidates) + ") — run an experiment first")
        return 0
    rows.sort(key=lambda r: (r["created"], r["experiment"]))
    width = max(len(r["experiment"]) for r in rows)
    print(f"{'date':<10}  {'experiment':<{width}}  {'status':<10}  verdicts")
    print("-" * (34 + width))
    for r in rows:
        print(f"{r['created']:<10}  {r['experiment']:<{width}}  {r['status']:<10}  {r['verdicts']}")
        print(f"{'':<10}  prereg {r['prereg']}… · fingerprint {r['fingerprint']}… · {r['dir']}")
    print(f"\n{len(rows)} run(s). Iterating on the same hypothesis? Open a NEW experiment —")
    print("preregistered plans are immutable by design.")
    return 0


def cmd_calibrate(args) -> int:
    """Offline-vs-production calibration (CAL-002/003)."""
    from .calibrate import calibrate, write_calibration_report

    cal = calibrate(args.run_dir, args.prereg, args.production_events, args.task_set)
    out_dir = args.out or args.run_dir
    json_path = write_calibration_report(cal, out_dir)
    for v in cal["variants"]:
        verdict = v.get("calibration", {})
        print(f"  {v['variant_id']}: {verdict.get('calibration')} — {verdict.get('reason', '')}")
        tr = v.get("transfer_overall")
        if tr:
            print(f"    transfer (offline − production): {tr['offline_minus_production']*100:+.1f}pp")
    print(f"  calibration report : {json_path}")
    print(f"                      {json_path.replace('.json', '.html')}")
    return 0


# ---------------------------------------------------------------- connector


def cmd_connector(args) -> int:
    import json

    from . import connector

    if args.connector_cmd == "init":
        config = connector.default_config(args.experiment_id)
        connector.save_config(config, args.config)
        print(f"connector config: {args.config}")
        print(f"  experiment  : {args.experiment_id}")
        print(f"  tiers       : choice/execution/consumption default to 'local' (aggregated locally, never exported)")
        print(f"  tiers are   : off | local | export  — set per class: am connector set <class> <tier>")
        return 0

    if args.connector_cmd == "set":
        config = connector.load_config(args.config)
        connector.set_tier(config, args.data_class, args.tier)
        connector.save_config(config, args.config)
        print(f"authorization: {args.data_class}={args.tier} ({args.config})")
        return 0

    if args.connector_cmd == "export":
        try:
            payload = connector.export(args.config, args.events, args.out, args.key)
        except connector.ConnectorError as e:
            print(f"export refused: {e}", file=sys.stderr)
            return 1
        print(f"signed aggregate export: {args.out}")
        print(f"  key_id          : {payload['key_id']}")
        print(f"  excluded classes: {payload['excluded_classes'] or 'none'}")
        print(f"  content         : none (schema-level; counts only)")
        return 0

    if args.connector_cmd == "revoke":
        config = connector.revoke(args.config)
        print(f"connector REVOKED at {config['revoked_at']} — exports now refuse immediately")
        return 0

    if args.connector_cmd == "verify":
        result = connector.verify_export(args.export_file, args.key)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if (result["signature_valid"] and result["key_id_matches"]) else 1
    return 2


def cmd_mcp(args) -> int:
    from . import mcp_server

    tool_names = ", ".join(t["name"] for t in mcp_server._TOOLS)
    print(f"agentmeasure-lab MCP server (read-only) on stdio — tools: {tool_names}", file=sys.stderr)
    mcp_server.serve()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="am",
        description="AgentMeasure Lab — open experiment engine (offline, no registration)",
    )
    p.add_argument("--version", action="version", version=f"agentmeasure-lab {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    lab_p = sub.add_parser("lab", help="experiment engine: init / preregister / run / report / verify / selftest / calibrate")
    lsub = lab_p.add_subparsers(dest="lab_command", required=True)

    sp = lsub.add_parser("init", help="initialize a working directory with an example experiment")
    sp.add_argument("--dir", default="am-lab")
    sp.set_defaults(fn=cmd_init)

    sp = lsub.add_parser("preregister", help="lock an experiment manifest (hash-archived)")
    sp.add_argument("manifest")
    sp.add_argument("-o", "--out", default=None)
    sp.set_defaults(fn=cmd_preregister)

    sp = lsub.add_parser("run", help="run a preregistered experiment (local, offline)")
    sp.add_argument("prereg")
    sp.add_argument("--out", default=None, help="runs directory (default: <workspace>/runs)")
    sp.set_defaults(fn=cmd_run)

    sp = lsub.add_parser("report", help="regenerate report.json/html from a run's events")
    sp.add_argument("run_dir")
    sp.add_argument("prereg")
    sp.set_defaults(fn=cmd_report)

    sp = lsub.add_parser("verify", help="re-verify prereg hash, event schema and fingerprint")
    sp.add_argument("run_dir")
    sp.add_argument("prereg")
    sp.set_defaults(fn=cmd_verify)

    sp = lsub.add_parser("selftest", help="end-to-end sanity check (planted uplift + honest null)")
    sp.set_defaults(fn=cmd_selftest)

    sp = lsub.add_parser(
        "history",
        help="local experiment history / hypothesis library: every run, its verdicts and hashes",
    )
    sp.add_argument("--runs", default=None, help="runs directory (default: am-lab/runs or runs)")
    sp.set_defaults(fn=cmd_history)

    sp = lsub.add_parser(
        "calibrate",
        help="compare an offline run against production re-measurement events (CAL-002/003)",
    )
    sp.add_argument("run_dir")
    sp.add_argument("prereg")
    sp.add_argument("--production-events", required=True, help="FMT-002 JSONL from the rollout (treatment arms vs holdout)")
    sp.add_argument("--task-set", default=None, help="task set for strata join (default: from the preregistration)")
    sp.add_argument("--out", default=None, help="output directory (default: the run dir)")
    sp.set_defaults(fn=cmd_calibrate)

    connector_p = sub.add_parser("connector", help="local-first calibration connector data plane (CAL-001)")
    csub = connector_p.add_subparsers(dest="connector_cmd", required=True)

    sp = csub.add_parser("init", help="create a connector config (tiers default to 'local')")
    sp.add_argument("--config", default="connector.json")
    sp.add_argument("--experiment", dest="experiment_id", required=True)
    sp.set_defaults(fn=cmd_connector)

    sp = csub.add_parser("set", help="set one authorization tier: off | local | export")
    sp.add_argument("data_class", choices=["choice", "execution", "consumption"])
    sp.add_argument("tier", choices=["off", "local", "export"])
    sp.add_argument("--config", default="connector.json")
    sp.set_defaults(fn=cmd_connector)

    sp = csub.add_parser("export", help="produce a signed aggregate-only export (refuses if revoked)")
    sp.add_argument("events", help="production FMT-002 JSONL")
    sp.add_argument("--config", default="connector.json")
    sp.add_argument("--out", default="connector-export.json")
    sp.add_argument("--key", default=None, help="signing key file (default: connector.key next to the config)")
    sp.set_defaults(fn=cmd_connector)

    sp = csub.add_parser("revoke", help="revoke immediately — all exports refuse from now on")
    sp.add_argument("--config", default="connector.json")
    sp.set_defaults(fn=cmd_connector)

    sp = csub.add_parser("verify", help="verify an export's HMAC signature")
    sp.add_argument("export_file")
    sp.add_argument("--key", required=True)
    sp.set_defaults(fn=cmd_connector)

    mcp_p = sub.add_parser("mcp", help="MCP interface (read-only)")
    msub = mcp_p.add_subparsers(dest="mcp_cmd", required=True)
    sp = msub.add_parser("serve", help="serve read-only MCP tools over stdio")
    sp.set_defaults(fn=cmd_mcp)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — business users get one clean line, not a traceback
        if os.environ.get("AM_LAB_DEBUG"):
            raise
        print(f"error: {e}", file=sys.stderr)
        print("  (set AM_LAB_DEBUG=1 for the full traceback)", file=sys.stderr)
        return 1
