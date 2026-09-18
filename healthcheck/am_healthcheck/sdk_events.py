"""Cross-side SDK event pairing (--sdk-events).

Reads AgentMeasure MCP SDK observations (JSONL from @agentmeasure/mcp),
pairs them with client-side sessions for the billable_audit use profile
(QUALITY §4).  Draft 0.4.4 / v0.4.0.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def load_sdk_events(path: str) -> List[Dict[str, Any]]:
    """Load SDK observation JSONL.

    Each line is a canonical observation (attempt_started / attempt_completed)
    emitted by @agentmeasure/mcp middleware.
    """
    events = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError("SDK events: line %d: invalid JSON: %s" % (i, e))
            if not isinstance(ev, dict):
                continue
            events.append(ev)
    return events


def build_cross_side_report(
    client_sessions: List,
    sdk_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Pair client-side sessions with server-side SDK observations.

    Returns a dict with:
      - total_client_operations
      - total_sdk_attempts
      - paired: list of matched operation↔attempt pairs
      - sdk_only: SDK observations without a matching client session
      - client_only: client sessions without SDK observations
    """
    # Build lookup: call/exec id → client-side record.
    # ExecRecord carries exec_id; CallRecord carries call_id. Neither is
    # guaranteed present, so read both defensively.
    client_by_call = {}
    for session in client_sessions:
        for e in getattr(session, "execs", []):
            cid = getattr(e, "call_id", "") or getattr(e, "exec_id", "")
            if cid:
                client_by_call[cid] = e
        for c in getattr(session, "calls", []):
            cid = getattr(c, "call_id", "")
            if cid:
                client_by_call[cid] = c

    paired = []
    sdk_only = []
    for ev in sdk_events:
        call_id = ev.get("tool_call_id") or ev.get("call_id") or ""
        matched = client_by_call.get(call_id)
        if matched:
            paired.append({"sdk_event": ev, "client_exec": matched._asdict() if hasattr(matched, '_asdict') else str(matched)})
        else:
            sdk_only.append(ev)

    client_operations = sum(
        1 for s in client_sessions
        for e in getattr(s, "execs", [])
    )

    return {
        "total_client_operations": client_operations,
        "total_sdk_attempts": len(sdk_events),
        "paired_count": len(paired),
        "sdk_only_count": len(sdk_only),
        "client_only_count": client_operations - len(paired),
        "paired": paired[:20],   # sample
        "sdk_only_sample": sdk_only[:10],
        "note": "Pairing is by tool_call_id; NULL or mismatched IDs prevent matching. "
                "This is the cross-side_attribution use profile, not billable_audit — "
                "billable_audit additionally requires provenance and replay_protection "
                "(COMMERCIAL §6).",
    }