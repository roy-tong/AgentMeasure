#!/usr/bin/env python3
"""Scripted stand-in for `codex exec --json`.

Emits the LIVE-VALIDATED transcript shapes (codex-cli 0.149.0-alpha):
`mcp_tool_call` items with server/tool fields, `agent_message` final answer,
and `turn.completed` with token usage.

Scenario via env AM_FAKE_MODE: subject (default) / competitor / timeout / error.
"""
import json
import os
import sys
import time


def emit(obj):
    print(json.dumps(obj), flush=True)


def mcp(item_id, server, tool, status, error=None):
    return {"type": "item.completed",
            "item": {"id": f"item_{item_id}", "type": "mcp_tool_call",
                     "server": server, "tool": tool,
                     "arguments": {"query": "task"},
                     "status": status, "error": error}}


def main():
    mode = os.environ.get("AM_FAKE_MODE", "subject")
    server = "am-lab-tools"

    emit({"type": "thread.started"})
    if mode == "timeout":
        time.sleep(30)
        return

    if mode == "competitor":
        emit({"type": "item.completed", "item": {"id": "item_1", "type": "mcp_tool_call",
             "server": server, "tool": "web-search-pro", "status": "completed"}})
    elif mode == "error":
        emit(mcp(1, server, "your-search-api", "failed",
                 error={"message": "MCP tool call requires approval"}))
        emit(mcp(2, server, "your-search-api", "completed"))
    else:
        emit({"type": "item.started", "item": {"id": "item_1", "type": "mcp_tool_call",
             "server": server, "tool": "your-search-api", "status": "in_progress"}})
        emit(mcp(1, server, "your-search-api", "completed"))

    emit({"type": "item.completed", "item": {"id": "item_9", "type": "agent_message",
         "text": "the final answer"}})
    emit({"type": "turn.completed",
          "usage": {"input_tokens": 1000, "output_tokens": 200}})


if __name__ == "__main__":
    main()
