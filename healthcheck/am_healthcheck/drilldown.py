"""Single-line drill-down — the "re-check one judgement" view (BP r32 p09).

The competitor page promises: "ask the customer to re-check one finding."
This module is that promise as an artifact: given the export and the vendor,
pick one conversation and get the full replay on screen — the row's inputs,
each rule step that fired (in order, in plain language), the verdict, and
the exact command to reproduce it. What the customer sees is what the
engine saw; nothing is summarised away.

Tier 1 only, by design: the buyer's own service standard (the contract
overlay) is leverage about quality, not part of the billing replay.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import vendors as vendors_mod
from .vendors import (AGREES, BILLABLE_BUT_NOT_BILLED, BILLED_BUT_NOT_BILLABLE,
                      CANNOT_SETTLE)


def _fmt(value: Any) -> str:
    if value is None or str(value).strip() == "":
        return "(absent)"
    return str(value)


def explain_one(rec: Dict[str, Any], vendor: Dict[str, Any]) -> Dict[str, Any]:
    """Walk one row through the vendor's rules, narrating every step.

    Same branches as vendors._judge_one, in the same order — the recount and
    this explanation are one logic, not two. Returns verdict + three-state +
    steps + the rules cited.
    """
    billed = vendors_mod._as_bool(rec.get("vendor_billed"))
    human = vendors_mod._as_bool(rec.get("human_agent_participated"))
    addressed = vendors_mod._as_bool(rec.get("issue_addressed"))
    recontacted = vendors_mod._as_bool(rec.get("customer_recontacted_within_window"))
    steps: List[str] = []
    rules: List[str] = []

    steps.append("Row as exported: billed=%s · human participated=%s · "
                 "issue addressed=%s · recontacted within window=%s"
                 % (_fmt(billed), _fmt(human), _fmt(addressed),
                    _fmt(recontacted)))

    if None in (billed, human, addressed, recontacted):
        steps.append("Evidence is incomplete — the verdict lowers to "
                     "cannot-settle rather than guessing the missing field.")
        return {"verdict": CANNOT_SETTLE, "verdict_3state": "UNPROVABLE",
                "steps": steps, "rules": rules, "should_bill": None}

    should_bill: Optional[bool]
    if human:
        steps.append("A human finished the conversation. Under every vendor "
                     "rule we have read, a human-handled finish is not an AI "
                     "resolution — the vendor's own rule does not bill it.")
        rules.append("human-handled finish ≠ AI resolution (all read rules)")
        should_bill = False
    elif not addressed:
        steps.append("The issue was not addressed. An unresolved "
                     "conversation is not a billable resolution.")
        rules.append("unaddressed conversation is not a resolution")
        should_bill = False
    elif recontacted:
        if str(vendor["reopen_deduction"]).startswith("documented"):
            steps.append("The customer came back inside the window, and %s "
                         "documents a reopen deduction — including across "
                         "billing periods. Their own rule un-bills it."
                         % vendor["name"])
            rules.append("documented reopen deduction (%s)"
                         % vendor["reopen_deduction"])
            should_bill = False
        else:
            steps.append("The customer came back inside the window, but %s "
                         "documents no reopen deduction. We do not invent a "
                         "rule in either direction — cannot-settle."
                         % vendor["name"])
            rules.append("reopen deduction not documented by the vendor")
            return {"verdict": CANNOT_SETTLE, "verdict_3state": "UNPROVABLE",
                    "steps": steps, "rules": rules, "should_bill": None}
    else:
        trigger = vendor["billing_trigger"]
        if trigger in ("confirmed_or_assumed", "assumed_with_lock",
                       "algorithmic_classification"):
            steps.append("No human, issue addressed, no recontact — under "
                         "%s's trigger (%s) this resolves and bills."
                         % (vendor["name"], trigger))
            rules.append("billing trigger: %s" % trigger)
            should_bill = True
        elif trigger == "llm_verified_only":
            steps.append("%s bills only on an affirmative model adjudication, "
                         "and a counts-only export does not carry that "
                         "verdict. Reading silence as a pass would be a "
                         "guess — cannot-settle." % vendor["name"])
            rules.append("billing trigger: llm_verified_only")
            return {"verdict": CANNOT_SETTLE, "verdict_3state": "UNPROVABLE",
                    "steps": steps, "rules": rules, "should_bill": None}
        else:
            steps.append("%s publishes no billing trigger we could read. "
                         "No rule to apply — cannot-settle." % vendor["name"])
            return {"verdict": CANNOT_SETTLE, "verdict_3state": "UNPROVABLE",
                    "steps": steps, "rules": rules, "should_bill": None}

    if billed and not should_bill:
        verdict = BILLED_BUT_NOT_BILLABLE
        steps.append("It was billed, but the vendor's own rules say it "
                     "should not be → billed but not billable.")
    elif should_bill and not billed:
        verdict = BILLABLE_BUT_NOT_BILLED
        steps.append("Their rules would bill it, but it was not billed → "
                     "billable but not billed (reported in their favour).")
    else:
        verdict = AGREES
        steps.append("The bill and the vendor's own rule agree → agrees.")
    return {"verdict": verdict,
            "verdict_3state": "FAIL" if verdict in
            (BILLED_BUT_NOT_BILLABLE, BILLABLE_BUT_NOT_BILLED) else "PASS",
            "steps": steps, "rules": rules, "should_bill": should_bill}


def drilldown(export: Dict[str, Any], vendor_id: str,
              conversation: Optional[str] = None,
              line: Optional[int] = None) -> Dict[str, Any]:
    """Explain one conversation of the export, by id or by export line."""
    vendor = vendors_mod.get_vendor(vendor_id)
    records = export["records"]
    match = None
    index = -1
    for i, rec in enumerate(records):
        if conversation is not None and str(rec.get("conversation_id")) == str(conversation):
            match, index = rec, i
            break
        if line is not None and (i + 2) == line:
            match, index = rec, i
            break
    if match is None:
        raise ValueError("conversation %r / line %r not found in the export"
                         % (conversation, line))
    result = explain_one(match, vendor)
    result.update({
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "conversation_id": match.get("conversation_id"),
        "export_line": index + 2,
        "row": {k: _fmt(match.get(k)) for k in vendors_mod.CANONICAL_COLUMNS},
        "rule_source": vendor["source"],
    })
    price = vendor.get("unit_price")
    if price and result["verdict"] in (BILLED_BUT_NOT_BILLABLE,
                                       BILLABLE_BUT_NOT_BILLED):
        result["amount_at_issue"] = round(price, 2)
        result["currency"] = vendor.get("currency")
    return result


def drilldown_text(result: Dict[str, Any], export_path: str) -> str:
    W = 64
    out = ["One finding, fully replayed — %s" % result["vendor_name"],
           "=" * W,
           "conversation %s (export line %d)"
           % (result["conversation_id"], result["export_line"]),
           "rule source: %s" % result["rule_source"], ""]
    out.append("The row as the buyer exported it:")
    for k, v in result["row"].items():
        out.append("  %-34s %s" % (k, v))
    out.append("")
    out.append("The rules, step by step:")
    for i, step in enumerate(result["steps"], 1):
        out.append("  %d. %s" % (i, step))
    out.append("")
    out.append("verdict: %s (%s)" % (result["verdict"],
                                     result["verdict_3state"]))
    if "amount_at_issue" in result:
        out.append("amount at issue: %s %s" % (result.get("currency"),
                                               result["amount_at_issue"]))
    out.append("")
    out.append("Re-check it yourself — same input, same rules, same answer:")
    out.append("  agentmeasure recount --export %s --vendor %s"
               % (export_path, result["vendor_id"]))
    out.append("  agentmeasure drilldown --export %s --vendor %s "
               "--conversation %s"
               % (export_path, result["vendor_id"], result["conversation_id"]))
    return "\n".join(out)


def drilldown_markdown(result: Dict[str, Any], export_path: str) -> str:
    out = ["# One finding, fully replayed — %s" % result["vendor_name"], ""]
    out.append("Conversation `%s` (export line %d). Rule source: %s"
               % (result["conversation_id"], result["export_line"],
                  result["rule_source"]))
    out.append("")
    out.append("| field | value |")
    out.append("|---|---|")
    for k, v in result["row"].items():
        out.append("| %s | `%s` |" % (k, v))
    out.append("")
    out.append("## The rules, step by step")
    out.append("")
    for i, step in enumerate(result["steps"], 1):
        out.append("%d. %s" % (i, step))
    out.append("")
    out.append("**Verdict: %s (%s)**" % (result["verdict"],
                                          result["verdict_3state"]))
    if "amount_at_issue" in result:
        out.append("")
        out.append("Amount at issue: **%s %s**"
                   % (result.get("currency"), result["amount_at_issue"]))
    out.append("")
    out.append("Re-check it yourself — same input, same rules, same answer:")
    out.append("")
    out.append("```bash")
    out.append("agentmeasure recount --export %s --vendor %s"
               % (export_path, result["vendor_id"]))
    out.append("```")
    return "\n".join(out)
