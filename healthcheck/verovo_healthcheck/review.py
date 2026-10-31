"""Scoped buyer review: independent charge and delivery checks on local JSON.

Criteria and rule references are supplied by the reviewer. This module compares
facts; it does not discover contractual obligations or certify source truth.

Conclusion levels (kept separate, never collapsed):
  Level 1 rule consistency — what this run establishes: PASS/FAIL/UNPROVABLE
      verdicts of supplied criteria against local observations.
  Level 2 evidence credibility — not established by this run: rule
      applicability is reviewer-supplied (basis.ref/version; an optional
      human confirmation confirmed_by/confirmed_at is echoed, never inferred),
      sources are local snapshots with SHA-256 (no third-party corroboration),
      coverage equals the stated scope.
  Level 3 buyer business decision — outside the tool: pay / accept / dispute /
      remediate is a human decision recorded separately (`verovo decisions`).
"""
import hashlib
import html
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

LANES = ("charges", "delivery")
OPERATORS = ("equals", "at_least", "at_most")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: %s" % key)
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("non-finite JSON number: %s" % value)


def _read(path):
    raw = Path(path).read_bytes()
    return (json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_object,
                       parse_constant=_invalid_constant),
            hashlib.sha256(raw).hexdigest())


def _text(obj, key):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % key)
    return value


def _number(value):
    return type(value) in (int, float) and (not isinstance(value, float)
                                           or math.isfinite(value))


def _scalar(value):
    return type(value) in (str, bool) or _number(value)


def _pointer(doc, pointer):
    if pointer == "":
        return doc
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("pointer must be an RFC 6901 JSON pointer")
    for part in pointer[1:].split("/"):
        # Validate escapes before unescaping: ~01 is a literal ~1 key.
        i = 0
        while i < len(part):
            if part[i] == "~":
                if i + 1 == len(part) or part[i + 1] not in "01":
                    raise ValueError("invalid JSON pointer escape")
                i += 1
            i += 1
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(doc, list):
            if not key.isascii() or not key.isdigit() or (len(key) > 1 and key[0] == "0"):
                raise ValueError("invalid array index")
            doc = doc[int(key)]
        elif isinstance(doc, dict):
            doc = doc[key]
        else:
            raise ValueError("pointer traverses a scalar")
    return doc


def template():
    """Deliberately incomplete: initialize a task without inventing facts."""
    return {"schema_version": "1.0", "workflow": "both",
            "scope": {"buyer": "", "service": "", "account_or_task": "",
                      "period_or_window": "", "decision": "", "owner": "",
                      "due_date": ""}, "criteria": []}


def evaluate(task_path, synthetic=False):
    path = Path(task_path).resolve()
    task, task_hash = _read(path)
    if not isinstance(task, dict) or task.get("schema_version") != "1.0":
        raise ValueError("expected buyer review schema_version 1.0")
    workflow = task.get("workflow")
    if workflow not in (*LANES, "both"):
        raise ValueError("workflow must be charges, delivery or both")
    scope = task.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("scope must be an object")
    for key in ("buyer", "service", "account_or_task", "period_or_window", "decision", "owner"):
        _text(scope, key)
    criteria = task.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("add at least one explicit criterion; an empty task is not a review")
    selected = LANES if workflow == "both" else (workflow,)
    rows, ids, input_paths = [], set(), [str(path)]
    # Read each evidence file once, so all checks refer to the same snapshot.
    cache = {}
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise ValueError("each criterion must be an object")
        cid = _text(criterion, "id")
        if cid in ids:
            raise ValueError("duplicate criterion id: %s" % cid)
        ids.add(cid)
        lane = criterion.get("lane")
        if lane not in selected:
            raise ValueError("criterion lane must belong to the selected workflow")
        _text(criterion, "statement")
        basis = criterion.get("basis")
        if not isinstance(basis, dict):
            raise ValueError("criterion requires a basis object")
        expected_kind = "billing_rule" if lane == "charges" else "buyer_requirement"
        if basis.get("kind") != expected_kind:
            raise ValueError("%s criteria require %s" % (lane, expected_kind))
        for key in ("ref", "version"):
            _text(basis, key)
        # Optional human confirmation that the cited rule/requirement actually
        # applies. Echoed, never inferred; absence is reported, not hidden.
        if ("confirmed_by" in basis) != ("confirmed_at" in basis):
            raise ValueError("basis confirmation requires confirmed_by and confirmed_at together")
        for key in ("confirmed_by", "confirmed_at"):
            if key in basis:
                _text(basis, key)
        op, expected = criterion.get("operator"), criterion.get("expected")
        if op not in OPERATORS or not _scalar(expected):
            raise ValueError("use a supported operator and finite scalar expected value")
        if op != "equals" and not _number(expected):
            raise ValueError("ordered comparisons require numeric values, not booleans")
        source = criterion.get("source")
        if not isinstance(source, dict):
            raise ValueError("source must name a local JSON path and pointer")
        relative = _text(source, "path")
        if Path(relative).is_absolute():
            raise ValueError("evidence path must be relative to the task directory")
        evidence_path = (path.parent / relative).resolve()
        try:
            evidence_path.relative_to(path.parent)
        except ValueError:
            raise ValueError("evidence path escapes the task directory")
        pointer = source.get("pointer")
        if not isinstance(pointer, str) or (pointer and not pointer.startswith("/")):
            raise ValueError("source.pointer must be a JSON pointer")
        input_paths.append(str(evidence_path))
        row = {"id": cid, "lane": lane, "statement": criterion["statement"],
               "basis": basis, "operator": op, "expected": expected,
               "source": source, "observed": None, "source_sha256": None,
               "verdict": "UNPROVABLE", "reason": ""}
        try:
            if evidence_path not in cache:
                try:
                    cache[evidence_path] = _read(evidence_path)
                except (OSError, ValueError) as exc:
                    cache[evidence_path] = exc
            cached = cache[evidence_path]
            if isinstance(cached, Exception):
                raise ValueError(str(cached))
            evidence, digest = cached
            row["source_sha256"] = digest
            actual = _pointer(evidence, pointer)
            if not _scalar(actual):
                raise ValueError("observation is missing, non-finite or not a scalar")
            if not ((_number(actual) and _number(expected)) or type(actual) is type(expected)):
                raise ValueError("observation and expected value have incompatible types")
            row["observed"] = actual
            left, right = ((Decimal(str(actual)), Decimal(str(expected)))
                           if _number(expected) else (actual, expected))
            passed = {"equals": lambda: left == right,
                      "at_least": lambda: left >= right,
                      "at_most": lambda: left <= right}[op]()
            row["verdict"] = "PASS" if passed else "FAIL"
            row["reason"] = "Local observation %s the supplied criterion." % (
                "meets" if passed else "does not meet")
        except (ValueError, KeyError, IndexError) as exc:
            row["reason"] = "Evidence gap: %s" % str(exc)
        rows.append(row)
    lanes = {}
    for lane in LANES:
        checks = [r for r in rows if r["lane"] == lane]
        counts = {v: sum(r["verdict"] == v for r in checks)
                  for v in ("PASS", "FAIL", "UNPROVABLE")}
        verdict = ("NOT_REVIEWED" if lane not in selected else
                   "FAIL" if counts["FAIL"] else
                   "UNPROVABLE" if not checks or counts["UNPROVABLE"] else "PASS")
        lanes[lane] = {"verdict": verdict, "checks": len(checks), "counts": counts}
    confirmed = sum(1 for r in rows if r["basis"].get("confirmed_by"))
    conclusion_levels = {
        "level_1_rule_consistency": (
            "Established by this run: per-criterion PASS/FAIL/UNPROVABLE verdicts "
            "comparing supplied criteria with local observations."),
        "level_2_evidence_credibility": (
            "Not established by this run: rule applicability is reviewer-supplied "
            "(%d of %d criteria carry an explicit human confirmation "
            "basis.confirmed_by/confirmed_at); sources are local snapshots with "
            "SHA-256 and no third-party corroboration; coverage equals the stated "
            "scope (%s / %s)." % (confirmed, len(rows),
                                  scope.get("service", ""), scope.get("period_or_window", ""))),
        "level_3_buyer_decision": (
            "Outside this tool: whether to pay, accept, dispute or require "
            "remediation is a buyer decision recorded separately "
            "(verovo decisions). A rule-consistent invoice is not delivery proof; "
            "a failed delivery check is not authorization to withhold payment."),
    }
    return {"schema_version": "1.0", "kind": "verovo.buyer-review",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "synthetic": synthetic, "scope": scope, "workflow": workflow,
            "task_sha256": task_hash, "input_paths": sorted(set(input_paths)),
            "lanes": lanes, "criteria": rows,
            "conclusion_levels": conclusion_levels,
            "boundary": "Verdicts apply only to supplied criteria and local observations. "
                        "Rule applicability and source truth need human review. "
                        "Delivery failure is not proof of incorrect billing or a refund. "
                        "No money is summed, recovered or approved by this report."}


def report_text(result):
    lines = ["Verovo buyer review" + (" — SYNTHETIC DEMO" if result["synthetic"] else ""), ""]
    lines.extend("%s: %s" % (k, v) for k, v in result["scope"].items())
    lines.append("")
    for lane, summary in result["lanes"].items():
        lines.append("%s: %s (%d checks; %d evidence gaps)" % (
            lane.upper(), summary["verdict"], summary["checks"], summary["counts"]["UNPROVABLE"]))
    levels = result.get("conclusion_levels") or {}
    lines.extend(["", "Conclusion levels (kept separate, never collapsed):"])
    for key, label in (("level_1_rule_consistency", "Level 1 rule consistency"),
                       ("level_2_evidence_credibility", "Level 2 evidence credibility"),
                       ("level_3_buyer_decision", "Level 3 buyer decision")):
        if levels.get(key):
            lines.append("  %s: %s" % (label, levels[key]))
    for row in result["criteria"]:
        confirmed = ""
        if row["basis"].get("confirmed_by"):
            confirmed = " [rule applicability confirmed by %s at %s]" % (
                row["basis"]["confirmed_by"], row["basis"]["confirmed_at"])
        lines.extend(["", "[%s] %s / %s: %s" % (row["verdict"], row["lane"], row["id"], row["statement"]),
                      "  Basis: %s (version %s)%s" % (row["basis"]["ref"], row["basis"]["version"], confirmed),
                      "  Expected: %s %s; observed: %s" % (row["operator"], row["expected"], row["observed"]),
                      "  Evidence: %s#%s" % (row["source"]["path"], row["source"]["pointer"]),
                      "  SHA-256: %s" % (row["source_sha256"] or "unavailable"), "  " + row["reason"]])
    lines.extend(["", "Next: review the rule references; obtain missing evidence; record the buyer's decision separately.", result["boundary"]])
    return "\n".join(lines)


def report_html(result):
    esc = html.escape
    cards = "".join('<section><h2>%s</h2><strong>%s</strong><p>%s checks · %s evidence gaps</p></section>' %
                    (esc(lane.title()), esc(v["verdict"]), v["checks"], v["counts"]["UNPROVABLE"])
                    for lane, v in result["lanes"].items())
    levels = result.get("conclusion_levels") or {}
    level_items = "".join("<li><strong>%s</strong> — %s</li>" % (esc(label), esc(levels[key]))
                          for key, label in (("level_1_rule_consistency", "Level 1 · rule consistency"),
                                             ("level_2_evidence_credibility", "Level 2 · evidence credibility"),
                                             ("level_3_buyer_decision", "Level 3 · buyer decision"))
                          if levels.get(key))
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verovo — buyer review</title><style>body{font:16px/1.6 system-ui,sans-serif;background:#f7f8f3;color:#17372c;margin:0;padding:28px}main{max-width:1000px;margin:auto}.lanes{display:flex;gap:20px;flex-wrap:wrap}section{background:#e8f0e9;padding:18px 24px;flex:1;min-width:200px;border:1px solid #b8cdbf}h2{margin:0 0 10px}.levels{background:#fff;border:1px solid #d5dfd7;padding:14px 24px;margin:20px 0}.levels ul{margin:8px 0 0;padding-left:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:24px;border:1px solid #d5dfd7;font:13px/1.8 ui-monospace,monospace}@media print{body{padding:0;background:white}pre{border:0}}</style><main><h1>Verovo buyer review</h1><p>Charges and delivery are separate conclusions. Local, scoped checks; human review required.</p>''' + (
        "<p><strong>SYNTHETIC DEMO — not a customer result.</strong></p>" if result["synthetic"] else "") + (
        '<div class="lanes">' + cards + '</div>'
        '<div class="levels"><strong>Conclusion levels</strong><ul>' + level_items + '</ul></div>'
        '<pre>' + esc(report_text(result)) + '</pre></main></html>')
