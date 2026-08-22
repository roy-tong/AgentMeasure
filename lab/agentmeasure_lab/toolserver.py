#!/usr/bin/env python3
"""Minimal MCP tool server for candidate-set injection (LAB-004).

Real harness experiments need the candidate set to be *controlled*: the
runner exposes the subject capability plus competitors as MCP tools and
lets the real agent choose. This server speaks just enough MCP (stdio,
JSON-RPC 2.0, one message per line) to do that — pure standard library,
launched per-episode by the harness runners, never installed anywhere.

The tools are synthetic: a tools/call returns a deterministic canned result
derived from the tool name and the arguments. What varies between variants
is the PRESENTATION (description text, output verbosity) — exactly the
provider-controllable surface the experiments measure.

Spec file format:
    {
      "tools": [{"name": "...", "description": "...", "result_mode": "baseline"}],
      "server_name": "am-lab-tools"
    }
"""

import argparse
import hashlib
import json
import sys
from typing import Any, Dict, List, Optional

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED = {"2024-11-05", "2025-03-26", "2025-06-18"}


def _result_for(name: str, args: Dict[str, Any], mode: str) -> str:
    seed = hashlib.sha256(f"{name}|{json.dumps(args, sort_keys=True)}".encode()).hexdigest()[:8]
    base = {
        "tool": name,
        "status": "ok",
        "retrieved": 5,
        "query_ref": seed,
        "items": [
            {"title": f"result-{seed}-{i}", "snippet": f"synthetic result {i} for this query", "score": round(0.9 - i * 0.15, 2)}
            for i in range(3)
        ],
    }
    if mode == "verbose":
        base["explanation"] = (
            "This result set was assembled by evaluating your query against the full index. "
            "We considered several interpretation branches, re-ranked candidates by semantic "
            "and lexical signals, and include this paragraph so the payload is noticeably "
            "longer than the baseline format."
        )
        base["notes"] = ["ranking heuristic v2 applied", "index freshness window 24h", "dedup pass enabled"]
    return json.dumps(base, ensure_ascii=False)


class ToolServer:
    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.tools: List[Dict[str, Any]] = spec.get("tools", [])
        self.server_name = spec.get("server_name", "am-lab-tools")

    def dispatch(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = message.get("method", "")
        req_id = message.get("id")
        if method.startswith("notifications/"):
            return None
        try:
            result = self._handle(method, message.get("params") or {})
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:  # noqa: BLE001
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": -32000, "message": f"{type(e).__name__}: {e}"}}

    def _handle(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "initialize":
            version = params.get("protocolVersion")
            return {
                "protocolVersion": version if version in SUPPORTED else PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": self.server_name, "version": "1.0.0"},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [self._tool_schema(t) for t in self.tools]}
        if method == "tools/call":
            name = params.get("name", "")
            tool = next((t for t in self.tools if t["name"] == name), None)
            if tool is None:
                raise ValueError(f"unknown tool: {name}")
            args = params.get("arguments") or {}
            return {"content": [{"type": "text", "text": _result_for(name, args, tool.get("result_mode", "baseline"))}]}
        raise ValueError(f"method not found: {method}")

    @staticmethod
    def _tool_schema(tool: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "the task query"}},
                "required": ["query"],
            },
        }


def serve(stdin=sys.stdin, stdout=sys.stdout) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="path to the tool spec JSON")
    args = parser.parse_args()
    with open(args.spec, "r", encoding="utf-8") as fh:
        server = ToolServer(json.load(fh))
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            response = server.dispatch(message)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve()
