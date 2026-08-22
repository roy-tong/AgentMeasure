#!/usr/bin/env python3
"""Scripted stand-in for `codex exec --json` (documented item events).

Scenario via env AM_FAKE_MODE: subject (default) / competitor / timeout.
"""
import json
import os
import sys
import time


def emit(obj):
    print(json.dumps(obj), flush=True)


def item(item_type, **kw):
    return {"type": "item.completed", "item": {"type": item_type, **kw}}


def main():
    mode = os.environ.get("AM_FAKE_MODE", "subject")

    emit({"type": "thread.started"})
    if mode == "timeout":
        time.sleep(30)
        return
    if mode == "competitor":
        emit(item("function_call", name="am-lab-tools__web-search-pro", call_id="c1"))
        emit(item("function_call_output", call_id="c1", output="synthetic result"))
    else:
        emit(item("function_call", name="am-lab-tools__your-search-api", call_id="c1"))
        emit(item("function_call_output", call_id="c1", output="synthetic result"))
    emit(item("agent_message", text="the final answer"))
    emit({"type": "turn.completed"})


if __name__ == "__main__":
    main()
