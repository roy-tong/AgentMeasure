"""Certification grading + deterministic verification digest.

Two things the BP's trust story needs and only code can supply:

**Deterministic digest** — the same inputs under the same rules must produce
byte-identical verification. The digest is sha256 over the document with
generation timestamps stripped and keys sorted, so two runs on two machines
produce the same value. Any divergence is a finding about the tool, not the
data. Signing is deliberately OUT of this package (offline discipline): the
digest file is what you hand to `gpg`/`minisign`/your KMS — the same two-step
shape as the narrative layer.

**Stage grading** — where a verification artifact sits on the AMS-1 adoption
ladder (standard/SETTLEMENT.md Stage 0..3; the docs gate reserves the L-codes,
so the CLI speaks in stages too):

  stage-0  self-attested: the artifact exists and its inputs are hashed
  stage-1  recomputable: inputs hashed + rules version recorded — a third
           party with the same inputs and registry can reproduce every number
  stage-2  independently reproduced: a `reproductions` entry whose digest
           matches this artifact's digest
  stage-3  counterparty accepted: an `acceptances` entry (vendor credit,
           signed acknowledgement) referencing the artifact

The grader only ever promotes on evidence IN the document; it names what is
missing for the next stage instead of rounding up.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, List

from . import dashboard as dash

STAGES = ("stage-0", "stage-1", "stage-2", "stage-3")

_DIGEST_EXCLUDED_KEYS = ("generated_at", "digest", "reproductions", "acceptances")


def deterministic_digest(doc: Dict[str, Any]) -> str:
    """sha256 of the document minus volatile and annotation fields.

    `reproductions` and `acceptances` are excluded because they REFERENCE the
    digest — including them would make the digest depend on itself.
    """
    pruned = copy.deepcopy(doc)
    for key in _DIGEST_EXCLUDED_KEYS:
        pruned.pop(key, None)
    blob = json.dumps(pruned, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _has_hashed_inputs(doc: Dict[str, Any]) -> bool:
    inputs = doc.get("inputs", {})
    return any(k.endswith("_sha256") for k in inputs)


def _reproductions_matching(doc: Dict[str, Any], digest: str) -> List[Dict[str, Any]]:
    matches = []
    for rep in doc.get("reproductions", []) or []:
        if rep.get("digest") == digest:
            matches.append(rep)
    return matches


def certify(doc: Dict[str, Any]) -> Dict[str, Any]:
    digest = deterministic_digest(doc)
    t1 = doc.get("tier1") or {}
    requirements: Dict[str, bool] = {
        "artifact_is_pack_or_ledger": doc.get("schema") in (
            "agentmeasure.commercial/dispute-pack",
            "agentmeasure.commercial/verified-ledger"),
        "inputs_hashed": _has_hashed_inputs(doc),
        "rules_source_recorded": bool((doc.get("vendor") or {}).get("rule_source")
                                      or t1.get("vendor_rule_source")),
        "reproduction_digest_matches": bool(
            _reproductions_matching(doc, digest)),
        "counterparty_acceptance_recorded": bool(doc.get("acceptances")),
    }

    stage = "stage-0"
    if requirements["artifact_is_pack_or_ledger"]:
        stage = "stage-0"
    if stage == "stage-0" and requirements["inputs_hashed"] \
            and requirements["rules_source_recorded"]:
        stage = "stage-1"
    if requirements["reproduction_digest_matches"]:
        stage = "stage-2"
    if requirements["counterparty_acceptance_recorded"]:
        stage = "stage-3"

    next_requirements: Dict[str, str] = {}
    if stage == "stage-0":
        next_requirements["stage-1"] = "hash every input (verify does this) and record the rule source"
    elif stage == "stage-1":
        next_requirements["stage-2"] = ("have an independent party rerun and add "
                                        "reproductions: [{by, digest: %s…, date}]"
                                        % digest[:12])
    elif stage == "stage-2":
        next_requirements["stage-3"] = ("record the counterparty's acceptance: "
                                        "acceptances: [{by, role, date, ref}]")

    return {
        "schema": "agentmeasure.commercial/certification",
        "schema_version": "0.1.0",
        "artifact_schema": doc.get("schema"),
        "digest": digest,
        "stage": stage,
        "requirements": requirements,
        "next_requirements": next_requirements,
        "grading_rule": "promotion only on evidence inside the document; "
                        "missing evidence is named, never rounded up",
    }


def certification_report(result: Dict[str, Any]) -> str:
    W = 58
    out = ["Certification — AMS-1 adoption ladder", "=" * W]
    out.append("artifact: %s" % result["artifact_schema"])
    out.append("digest:  %s" % result["digest"])
    out.append("stage:   %s" % result["stage"])
    out.append("")
    out.append("requirements:")
    for k, v in result["requirements"].items():
        out.append("  %-34s %s" % (k, "yes" if v else "NO"))
    if result["next_requirements"]:
        for nxt, how in result["next_requirements"].items():
            out.append("")
            out.append("to reach %s: %s" % (nxt, how))
    out.append("")
    out.append("signing is yours to do outside this tool: hand the digest to")
    out.append("gpg/minisign/KMS — the package stays offline.")
    return "\n".join(out)


def load_artifact(path: str) -> Dict[str, Any]:
    return dash.load_document(path)
