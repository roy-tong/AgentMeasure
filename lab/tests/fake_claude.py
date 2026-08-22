#!/usr/bin/env python3
"""Scripted stand-in for `claude -p --output-format stream-json`.

Emits exactly the documented headless transcript shapes so the
ClaudeCodeRunner adapter can be integration-tested without the real CLI.
Scenario selected via env AM_FAKE_MODE:
  subject    — agent picks the subject tool, succeeds, answers (default)
  competitor — agent picks a competitor tool only
  timeout    — hangs (runner's timeout path)
  error      — subject tool errors on first call, succeeds on retry
"""
import json
import os
import sys
import time


def emit(obj):
    print(json.dumps(obj), flush=True)


def tool_use(uid, server, tool):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": uid, "name": f"mcp__{server}__{tool}", "input": {"query": "task"}}
    ]}}


def tool_result(uid, is_error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": uid, "is_error": is_error,
         "content": "synthetic result"}
    ]}}


def main():
    mode = os.environ.get("AM_FAKE_MODE", "subject")
    server = "am-lab-tools"
    # discover the server name from --allowedTools if present
    args = sys.argv[1:]
    if "--allowedTools" in args:
        server = args[args.index("--allowedTools") + 1].replace("mcp__", "")

    emit({"type": "system", "subtype": "init", "tools": ["mcp__" + server]})

    if mode == "timeout":
        time.sleep(30)
        return

    if mode == "competitor":
        emit(tool_use("u1", server, "web-search-pro"))
        emit(tool_result("u1"))
        emit({"type": "result", "subtype": "success", "result": "done with the pro tool"})
        return

    if mode == "error":
        emit(tool_use("u1", server, "your-search-api"))
        emit(tool_result("u1", is_error=True))
        emit(tool_use("u2", server, "your-search-api"))
        emit(tool_result("u2"))
        emit({"type": "result", "subtype": "success", "result": "recovered and answered"})
        return

    # default: subject
    emit(tool_use("u1", server, "your-search-api"))
    emit(tool_result("u1"))
    emit({"type": "result", "subtype": "success", "result": "the final answer"})


if __name__ == "__main__":
    main()
