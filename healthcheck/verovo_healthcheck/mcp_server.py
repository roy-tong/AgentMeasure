"""verovo-mcp — minimal buyer-side MCP server (stdio JSON-RPC 2.0, zero deps).

Exposes the buyer review entry points as agent tools. Read/local-compute only:

  verovo_review          run a buyer review from a task file (or the synthetic
                         sample); returns lanes, per-criterion verdicts,
                         conclusion levels (rule consistency / evidence
                         credibility / buyer decision) and the boundary text
  verovo_review_template the deliberately incomplete task template (an agent
                         fills scope/criteria; it must not invent rules)
  verovo_recount         Tier 1 recount: apply a vendor's own published rules
                         to a counts-only export (or the bundled sample)

Deliberately NOT exposed: anything that writes, submits, disputes, or contacts
a network endpoint. The buyer decision (Level 3) stays with the human;
`dispute`/`recovery` remain CLI-only human-driven flows.

Run: `verovo-mcp` (console script) or `python3 -m verovo_healthcheck.mcp_server`.
"""
import json
import os
import sys

from . import review
from . import invoice_intake
from . import vendors as vendors_mod

PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "verovo_invoice_intake",
        "description": "Read a local supplier invoice through optional invoice2data. "
                       "Returns an unreviewed source-hashed draft, NEVER books a cost "
                       "or claims invoice authenticity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "local invoice path"},
            },
            "required": ["file"],
        },
    },
    {
        "name": "verovo_review",
        "description": "Run a scoped buyer review (charges / delivery as separate "
                       "conclusions) from a local task file, or the synthetic demo "
                       "sample. Read-only: local JSON in, verdicts out. Verdicts are "
                       "PASS/FAIL/UNPROVABLE per criterion; conclusion levels state "
                       "what the run establishes (rule consistency) and what it does "
                       "not (evidence credibility, buyer decision).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_path": {"type": "string",
                              "description": "path to a buyer-review task JSON "
                                             "(see verovo_review_template)"},
                "sample": {"type": "boolean", "default": False,
                           "description": "run the bundled synthetic demo task"},
            },
        },
    },
    {
        "name": "verovo_review_template",
        "description": "The deliberately incomplete buyer-review task template. "
                       "An agent fills scope and criteria from the buyer's contract "
                       "and authorized observations; it must not invent rules, "
                       "versions or missing facts.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "verovo_recount",
        "description": "Tier 1 recount: apply a vendor's own published billing "
                       "rules to a counts-only export CSV (local read + arithmetic). "
                       "Use --sample via sample=true for the bundled demo. Vendor ids "
                       "are listed by the CLI (`verovo recount --list-vendors`).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sample": {"type": "boolean", "default": False},
                "export_path": {"type": "string",
                                "description": "path to the counts-only export CSV"},
                "vendor": {"type": "string", "default": "zendesk"},
            },
        },
    },
]


def _text(payload):
    return {"content": [{"type": "text",
                         "text": json.dumps(payload, ensure_ascii=False, indent=1)}]}


def _err(message):
    return {"content": [{"type": "text", "text": str(message)}], "isError": True}


def _run_review(args):
    sample = bool(args.get("sample"))
    task_path = args.get("task_path")
    if sample and task_path:
        return _err("sample and task_path are mutually exclusive")
    if not sample and not task_path:
        return _err("provide task_path or sample=true")
    if sample:
        demo = os.path.join(os.path.dirname(os.path.abspath(review.__file__)),
                            "demo", "buyer-review.json")
        task_path = demo
    result = review.evaluate(task_path, synthetic=sample)
    return _text({
        "result": result,
        "report_text": review.report_text(result),
    })


def _run_recount(args):
    export_path = args.get("export_path")
    if args.get("sample"):
        if export_path:
            return _err("sample and export_path are mutually exclusive")
        export_path = os.path.join(
            os.path.dirname(os.path.abspath(vendors_mod.__file__)),
            "demo", "sample-recount-export.csv")
    if not export_path:
        return _err("provide export_path or sample=true")
    vendor = args.get("vendor") or "zendesk"
    export = vendors_mod.load_export(export_path)
    result = vendors_mod.recount(export, vendor)
    return _text({
        "vendor": vendor,
        "export": export_path,
        "result": result,
        "report_text": vendors_mod.recount_report(result),
    })


def call_tool(name, args):
    if name == "verovo_invoice_intake":
        if not args.get("file"):
            return _err("provide a local invoice file")
        return _text(invoice_intake.extract_invoice(args["file"]))
    if name == "verovo_review":
        return _run_review(args)
    if name == "verovo_review_template":
        return _text(review.template())
    if name == "verovo_recount":
        return _run_recount(args)
    return _err("unknown tool: %s" % name)


def handle(message):
    method = message.get("method", "")
    mid = message.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "verovo-mcp", "version": "0.1.0"},
        }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        try:
            result = call_tool(message["params"]["name"],
                               message["params"].get("arguments", {}))
        except Exception as exc:  # surface as tool error, not a crash
            result = _err("%s: %s" % (type(exc).__name__, exc))
        return {"jsonrpc": "2.0", "id": mid, "result": result}
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": "method not found: %s" % method}}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
