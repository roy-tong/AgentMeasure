"""Narrative layer — LLM writes the words, rules keep the numbers (BP r28 p13).

The settlement letter and the finance explanation are prose. Prose is the one
thing a language model may draft — but a single invented number in a dispute
letter destroys the credibility the whole product rests on. So this layer has
a hard guard, and it never executes a model itself (the package stays offline;
you choose the model, you see the exact prompt):

  agentmeasure narrative --pack pack/dispute-pack.json --audience vendor \\
      --emit-prompt prompt.txt
  <your own model command> < prompt.txt > draft.txt
  agentmeasure narrative --pack pack/dispute-pack.json \\
      --check-draft draft.txt --out letter.md

1. the prompt is built **from the pack** — every fact the letter may state is
   already in it;
2. `--check-draft` verifies every number in the draft appears in the pack's
   own numbers; anything else — rounded, reformatted, hallucinated — fails;
3. on failure the draft is refused and the rule-based template ships instead,
   with the violating numbers printed. The judgement, the claim, the totals:
   never touched by the model.

Without any model at all, the pure-rule template is the output — the BP's
degradation promise: "客户机器上没模型？退回纯规则照样跑，只是叙述平一些".
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


def fact_numbers(pack: Dict[str, Any]) -> set:
    """Every number the pack itself contains, as plain strings."""
    blob = json.dumps(pack, ensure_ascii=True, default=str)
    found = set()
    for token in NUMBER_RE.findall(blob):
        found.add(token)
        found.add(token.replace(",", ""))
    return found


def build_prompt(pack: Dict[str, Any], audience: str) -> str:
    """The model sees the pack's facts and one instruction: prose, not numbers."""
    if audience == "finance":
        ask = ("Write a short internal explanation for the buyer's finance "
               "team: what was reviewed, what the two kinds of findings are, "
               "what is claimed, what is only renewal leverage, what is still "
               "unproven.")
    else:
        ask = ("Write a firm, courteous settlement enquiry letter to the "
               "vendor's account team, first person, signed by the buyer "
               "label. State findings and amounts exactly as given.")
    return (
        "You are drafting prose from a verified evidence pack. You may "
        "reorganise and soften the wording, but you MUST NOT introduce, "
        "round, or alter any number, and you must not add claims that are "
        "not in the pack. Amounts and counts appear exactly as in the pack.\n\n"
        "%s\n\nEVIDENCE PACK (JSON):\n%s" % (ask, json.dumps(pack, indent=1))
    )


def check_draft(pack: Dict[str, Any], draft: str) -> List[str]:
    """Numbers not present in the pack — empty list means the draft may ship."""
    allowed = fact_numbers(pack)
    violations = []
    for token in NUMBER_RE.findall(draft):
        if token not in allowed and token.replace(",", "") not in allowed:
            violations.append(token)
    return violations


def render_finance_note(pack: Dict[str, Any]) -> str:
    """Pure-rule finance explanation — the fallback, and the no-model default."""
    t1 = pack["tier1"]
    c = t1["counts"]
    claim = pack.get("claim", {})
    dollars = claim.get("dollars", {})
    lines = []
    lines.append("# Finance note — what was reviewed and what it means")
    lines.append("")
    lines.append("Vendor: %s. We re-counted the period's conversations "
                 "against the vendor's own published billing rule, line by "
                 "line, on our own export." % pack["vendor"]["name"])
    lines.append("")
    lines.append("- Billed but not billable under their own rule: %d"
                 % c["billed_but_not_billable"])
    lines.append("- Billable under their own rule but not billed: %d"
                 % c["billable_but_not_billed"])
    lines.append("- Cannot settle from this export (removed, not zeroed): %d"
                 % c["cannot_settle"])
    if dollars:
        lines.append("- Net variance claimed: %s %s"
                     % (pack.get("currency"), dollars["net_variance"]))
    lane = pack.get("outcome_lane")
    if lane:
        lc = lane["counts"]
        lines.append("")
        lines.append("Separately from the claim (renewal leverage only): %d "
                     "billed conversations fail our own outcome standard; %d "
                     "could not be judged from the export."
                     % (lc["fails_buyer_standard"], lc["unprovable"]))
    lines.append("")
    lines.append("Nothing here is a credit until the vendor confirms it. "
                 "Every figure above recomputes from the attached pack.")
    return "\n".join(lines)


def render_template(pack: Dict[str, Any], audience: str) -> str:
    if audience == "finance":
        return render_finance_note(pack)
    from .dispute import render_cover_letter
    return render_cover_letter(pack)


def render_or_draft(pack: Dict[str, Any], draft: Optional[str],
                    audience: str) -> Tuple[str, str, Optional[List[str]]]:
    """Returns (text, source, violations); source is 'llm' or 'template'.

    A draft with any number the pack does not contain is refused: the
    template ships and the violations come back for printing.
    """
    if draft is None or not draft.strip():
        return render_template(pack, audience), "template", None
    violations = check_draft(pack, draft)
    if violations:
        return render_template(pack, audience), "template", violations
    return draft.strip(), "llm", None
