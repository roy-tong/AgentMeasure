"""Period-over-period comparison — the subscription's monthly ritual (BP r28
appendix A: "每月核对新账单和规则变化").

Two verified ledgers (or dispute packs) in, one honest delta out: which
three-state counts moved, which disputed lines are new or cleared, whether
the vendor-rules version changed (a material event on its own), and what
happened to the recovery balance. The compare names changes; it never blends
two periods into one claim — rules version differs means the periods are
judged under different rules and must stay separate artifacts.
"""
from __future__ import annotations

from typing import Any, Dict, List

from . import dashboard as dash


def _tier1(doc: Dict[str, Any]) -> Dict[str, Any]:
    return doc.get("tier1") or {}


def _three_state(t1: Dict[str, Any]) -> Dict[str, int]:
    t = t1.get("three_state_counts")
    if t:
        return dict(t)
    c = t1.get("counts", {})
    return {"PASS": c.get("agrees", 0),
            "FAIL": (c.get("billed_but_not_billable", 0)
                     + c.get("billable_but_not_billed", 0)),
            "UNPROVABLE": c.get("cannot_settle", 0)}


def compare_periods(previous_path: str, current_path: str) -> Dict[str, Any]:
    prev = dash.load_document(previous_path)
    curr = dash.load_document(current_path)
    p1, c1 = _tier1(prev), _tier1(curr)

    def verdict_map(t1: Dict[str, Any]) -> Dict[str, str]:
        return {str(v.get("conversation_id")): v.get("verdict", "")
                for v in t1.get("verdicts", [])}

    pv, cv = verdict_map(p1), verdict_map(c1)
    new_fail = sorted(cid for cid in cv
                      if cv[cid] != "agrees" and cv[cid] != "cannot_settle"
                      and pv.get(cid) in ("agrees", None)
                      and pv.get(cid) != cv[cid])
    cleared = sorted(cid for cid in pv
                     if pv[cid] != "agrees" and pv[cid] != "cannot_settle"
                     and cv.get(cid) == "agrees")

    prev_rules = (prev.get("vendor") or {}).get("rules_version") \
        or prev.get("schema_version")
    curr_rules = (curr.get("vendor") or {}).get("rules_version") \
        or curr.get("schema_version")

    ps, cs = _three_state(p1), _three_state(c1)
    delta = {k: cs[k] - ps[k] for k in cs}

    rec_p = (prev.get("recovery") or {}).get("totals") if prev.get("recovery") else None
    rec_c = (curr.get("recovery") or {}).get("totals") if curr.get("recovery") else None

    return {
        "schema": "agentmeasure.commercial/period-compare",
        "schema_version": "0.1.0",
        "previous": {"file": previous_path, "generated_at": prev.get("generated_at"),
                     "rules_version": prev_rules},
        "current": {"file": current_path, "generated_at": curr.get("generated_at"),
                    "rules_version": curr_rules},
        "rules_version_changed": prev_rules != curr_rules,
        "three_state_delta": delta,
        "variance_delta": (round((c1.get("variance") or 0)
                                 - (p1.get("variance") or 0), 2)
                           if "variance" in c1 or "variance" in p1 else None),
        "new_fail_lines": new_fail,
        "cleared_lines": cleared,
        "recovery": ({"previous_realized": rec_p.get("realized"),
                      "current_realized": rec_c.get("realized"),
                      "delta": round((rec_c.get("realized") or 0)
                                     - (rec_p.get("realized") or 0), 2)}
                     if rec_p or rec_c else None),
        "reading": "a rules-version change means the two periods are judged "
                   "under different rules; the compare names it, the periods "
                   "stay separate artifacts",
    }


def compare_markdown(result: Dict[str, Any]) -> str:
    out = ["# Period compare — monthly reconciliation delta", ""]
    out.append("previous: %s (rules %s) → current: %s (rules %s)"
               % (result["previous"]["file"], result["previous"]["rules_version"],
                  result["current"]["file"], result["current"]["rules_version"]))
    out.append("")
    if result["rules_version_changed"]:
        out.append("**Vendor-rules version changed between the periods.** "
                   "Each period stands on its own rules; the delta below is "
                   "context, not a like-for-like trend.")
        out.append("")
    d = result["three_state_delta"]
    out.append("| PASS | FAIL | UNPROVABLE |")
    out.append("|---:|---:|---:|")
    out.append("| %+d | %+d | %+d |" % (d["PASS"], d["FAIL"], d["UNPROVABLE"]))
    if result["variance_delta"] is not None:
        out.append("")
        out.append("Net variance delta: %+0.2f" % result["variance_delta"])
    if result["new_fail_lines"]:
        out.append("")
        out.append("New disputed lines: %s" % ", ".join(result["new_fail_lines"][:15]))
    if result["cleared_lines"]:
        out.append("")
        out.append("Cleared since last period: %s" % ", ".join(result["cleared_lines"][:15]))
    if result["recovery"]:
        r = result["recovery"]
        out.append("")
        out.append("Realized recovery: %s → %s (Δ %+0.2f)"
                   % (r["previous_realized"], r["current_realized"], r["delta"]))
    out.append("")
    out.append(result["reading"] + ".")
    return "\n".join(out)
