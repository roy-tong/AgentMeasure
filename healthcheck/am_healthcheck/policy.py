"""Commercial Decision Policy execution log (F2.14) — every commercial action
an agent takes carries its policy basis, and the log is auditable.

Three authorization tiers, versioned as a policy document:

    auto       within the stated bound (coupon <= X), the agent acts alone
    approval   acts only with a named approver on the record
    forbidden  the action is out of bounds, full stop

The policy document links to the Agentic Ops Action Risk Policy by reference
(`risk_policy_ref`) — one risk language, two consumption surfaces. The audit
engine reads a policy + an execution log and grades each execution:

- complies            the tier matches the policy and the bound holds
- violates            outside the bound, or approval required but nobody
                      approved, or a forbidden action taken at all
- outside_policy      no rule matches — default-forbidden, and the finding
                      names it (a gap in the policy is a finding about the
                      policy, never a silent pass)

Grading is per execution, each with its policy citation: "every Offer/price
change carries a policy basis" is enforced line by line.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

POLICY_SCHEMA = "agentmeasure.commerce/decision-policy"
POLICY_VERSION_MARK = "0.1.0"
ACTION_TYPES = ("coupon", "price_change", "bundle", "offer", "refund",
                "inventory_change")
TIERS = ("auto", "approval", "forbidden")


class PolicyError(ValueError):
    pass


def load_policy(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("schema") != POLICY_SCHEMA:
        raise PolicyError("not a decision policy (schema %r)" % doc.get("schema"))
    if not (doc.get("risk_policy_ref") or "").strip():
        raise PolicyError("policy carries no risk_policy_ref — the link to "
                          "the Agentic Ops Action Risk Policy is required, "
                          "not decorative")
    seen = set()
    for rule in doc.get("rules", []):
        if rule.get("action_type") not in ACTION_TYPES:
            raise PolicyError("rule %r: unknown action_type"
                              % rule.get("rule_id"))
        if rule.get("tier") not in TIERS:
            raise PolicyError("rule %r: tier must be auto/approval/forbidden"
                              % rule.get("rule_id"))
        if rule["rule_id"] in seen:
            raise PolicyError("duplicate rule_id %s" % rule["rule_id"])
        seen.add(rule["rule_id"])
    return doc


def load_executions(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        rows = []
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                raise PolicyError("line %d is not valid JSONL" % (i + 1)) from None
            if not (rows[-1].get("execution_id") and
                    rows[-1].get("action_type") in ACTION_TYPES):
                raise PolicyError("line %d: execution needs execution_id and a "
                                  "known action_type" % (i + 1))
    return rows


def _match_rule(policy: Dict[str, Any],
                execution: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = [r for r in policy.get("rules", [])
                  if r["action_type"] == execution["action_type"]]
    value = execution.get("value")
    # The tightest bound that covers the value wins.
    covering = [r for r in candidates
                if r.get("max_value") is None
                or (value is not None and value <= r["max_value"])]
    if not covering:
        return None
    return min(covering, key=lambda r: r.get("max_value")
               if r.get("max_value") is not None else float("inf"))


def audit_executions(policy: Dict[str, Any],
                     executions: List[Dict[str, Any]]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    counts = {"complies": 0, "violates": 0, "outside_policy": 0}
    for ex in executions:
        rule = _match_rule(policy, ex)
        entry: Dict[str, Any] = {
            "execution_id": ex["execution_id"],
            "action_type": ex["action_type"],
            "value": ex.get("value"),
        }
        if rule is None:
            counts["outside_policy"] += 1
            entry.update({
                "grade": "outside_policy",
                "basis": "no policy rule covers this %s at this value — "
                         "policies default to forbidden, and the gap is a "
                         "finding about the policy" % ex["action_type"]})
            findings.append(entry)
            continue
        entry["policy_version"] = policy["policy_version"]
        entry["rule_id"] = rule["rule_id"]
        tier = rule["tier"]
        approver = (ex.get("approver") or "").strip()
        if tier == "forbidden":
            counts["violates"] += 1
            entry.update({"grade": "violates",
                          "basis": "%s is forbidden by rule %s"
                                   % (ex["action_type"], rule["rule_id"])})
        elif tier == "approval" and not approver:
            counts["violates"] += 1
            entry.update({"grade": "violates",
                          "basis": "rule %s requires approval; executed with "
                                   "no approver on the record"
                                   % rule["rule_id"]})
        elif tier == "approval" and approver:
            counts["complies"] += 1
            entry.update({"grade": "complies",
                          "basis": "rule %s (approval) — approved by %s"
                                   % (rule["rule_id"], approver)})
        else:  # auto
            if approver:
                counts["complies"] += 1
                entry.update({"grade": "complies",
                              "basis": "rule %s (auto) — approval recorded "
                                       "unnecessarily but not harmful"
                                       % rule["rule_id"]})
            else:
                counts["complies"] += 1
                entry.update({"grade": "complies",
                              "basis": "rule %s (auto, bound %s)"
                                       % (rule["rule_id"],
                                          rule.get("max_value"))})
        findings.append(entry)

    return {
        "schema": "agentmeasure.commerce/decision-audit",
        "schema_version": POLICY_VERSION_MARK,
        "policy_version": policy.get("policy_version"),
        "risk_policy_ref": policy.get("risk_policy_ref"),
        "executions_total": len(executions),
        "counts": counts,
        "lines": findings,
        "rule": "every commercial decision carries its policy basis; a gap "
                "in coverage is a finding about the policy, never a pass",
    }


def audit_markdown(result: Dict[str, Any]) -> str:
    out = ["# Commercial decision audit — policy v%s"
           % result["policy_version"], ""]
    out.append("risk policy link: `%s`" % result["risk_policy_ref"])
    out.append("")
    out.append("executions: %d — complies %d · violates %d · outside_policy %d"
               % (result["executions_total"], result["counts"]["complies"],
                  result["counts"]["violates"],
                  result["counts"]["outside_policy"]))
    problems = [l for l in result["lines"] if l["grade"] != "complies"]
    if problems:
        out.append("")
        out.append("| execution | action | grade | basis |")
        out.append("|---|---|---|---|")
        for l in problems:
            out.append("| %s | %s | %s | %s |"
                       % (l["execution_id"], l["action_type"], l["grade"],
                          l["basis"]))
    out.append("")
    out.append(result["rule"] + ".")
    return "\n".join(out)
