"""Intent Cluster taxonomy (F2.13) — infinite intents, finite consumption tasks.

An agent user never says "query family #47291"; they say "下午提神" or
"gift for a new dad". The taxonomy clusters intents by CONSUMPTION TASK and
derives the Operating Cell:

    Operating Cell = Intent Cluster × Surface × Proposition

A cell is where operating actually happens: the same cluster on a different
surface, or with a different proposition, is a different business. The
registry is a plain, diff-able JSON file so the "100 high-value clusters"
checklist stays reviewable in a pull request and maintainable by a human:

- ids are stable (IC-NNN); retiring a cluster sets status, never deletes it
  (history is evidence);
- every cluster names an owner and a review date; a review overdue by more
  than the cadence flags in validation;
- merging two clusters keeps one id alive and one retired with a successor
  pointer — counts never silently shrink.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

TAXONOMY_SCHEMA = "agentmeasure.commerce/intent-taxonomy"
TAXONOMY_VERSION = "0.1.0"
DEFAULT_CADENCE_DAYS = 90
STATUSES = ("active", "watch", "retired")


class TaxonomyError(ValueError):
    pass


def validate_taxonomy(doc: Dict[str, Any],
                      today: Optional[date] = None) -> Dict[str, Any]:
    """Validate and report. Returns stats + findings; raises on structural
    breakage (duplicate ids, missing required fields)."""
    today = today or date.today()
    if doc.get("schema") != TAXONOMY_SCHEMA:
        raise TaxonomyError("not an intent taxonomy (schema %r)"
                            % doc.get("schema"))
    clusters = doc.get("clusters", [])
    seen: Dict[str, int] = {}
    findings: List[Dict[str, Any]] = []
    active = watch = retired = 0
    cells = set()
    overdue: List[str] = []

    for c in clusters:
        cid = c.get("id") or ""
        if not cid:
            raise TaxonomyError("a cluster without id")
        if cid in seen:
            raise TaxonomyError("duplicate cluster id %s" % cid)
        seen[cid] = 1
        if not (c.get("task") or "").strip():
            raise TaxonomyError("cluster %s has no consumption task" % cid)
        status = c.get("status", "active")
        if status not in STATUSES:
            raise TaxonomyError("cluster %s: status %r invalid" % (cid, status))
        if status == "active":
            active += 1
        elif status == "watch":
            watch += 1
        else:
            retired += 1
            if not c.get("successor_id"):
                findings.append({"cluster": cid,
                                 "finding": "retired without a successor id"})
        if status != "retired":
            if not (c.get("proposition") or "").strip():
                findings.append({"cluster": cid,
                                 "finding": "no proposition — the Operating "
                                            "Cell is incomplete"})
            owner = c.get("owner") or ""
            if not owner:
                findings.append({"cluster": cid,
                                 "finding": "no owner — unowned clusters rot"})
            next_review = c.get("next_review")
            if next_review:
                try:
                    due = date.fromisoformat(str(next_review)[:10])
                except ValueError:
                    due = None
                if due and (today - due).days > DEFAULT_CADENCE_DAYS:
                    overdue.append(cid)
        for surface in (c.get("surfaces") or []):
            cells.add((cid, surface, c.get("proposition") or ""))

    return {
        "schema_version": doc.get("schema_version"),
        "clusters_total": len(clusters),
        "active": active,
        "watch": watch,
        "retired": retired,
        "operating_cells": len(cells),
        "overdue_reviews": overdue,
        "findings": findings,
        "cadence_days": DEFAULT_CADENCE_DAYS,
        "maintenance_rules": [
            "ids are stable; retire with a successor_id, never delete",
            "every live cluster names an owner and a review date",
            "a cluster is task-phrased ('下午提神'), never intent-phrased "
            "('long-tail query #47291')",
        ],
    }


def load_taxonomy(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def taxonomy_markdown(stats: Dict[str, Any]) -> str:
    out = ["# Intent Cluster taxonomy — health", ""]
    out.append("clusters: %d (active %d · watch %d · retired %d)"
               % (stats["clusters_total"], stats["active"], stats["watch"],
                  stats["retired"]))
    out.append("Operating Cells (cluster × surface × proposition): %d"
               % stats["operating_cells"])
    if stats["overdue_reviews"]:
        out.append("")
        out.append("Review overdue (>%dd): %s"
                   % (stats["cadence_days"], ", ".join(stats["overdue_reviews"][:10])))
    for f in stats["findings"][:10]:
        out.append("- %s: %s" % (f["cluster"], f["finding"]))
    out.append("")
    out.append("Maintenance rules:")
    for rule in stats["maintenance_rules"]:
        out.append("- %s" % rule)
    return "\n".join(out)


def write_seed_template(path: str) -> str:
    """A starter registry with worked examples — fill to 100 by copy-editing
    real consumption tasks, never by generating filler."""
    doc = {
        "schema": TAXONOMY_SCHEMA,
        "schema_version": TAXONOMY_VERSION,
        "clusters": [
            {"id": "IC-001", "task": "下午提神（饮品）",
             "aliases": ["afternoon caffeine", "办公室咖啡"],
             "surfaces": ["chat", "agent-browser"],
             "proposition": "30 分钟送达",
             "status": "active", "owner": "growth",
             "next_review": "2026-12-01"},
            {"id": "IC-002", "task": "给新生儿父母的礼物",
             "aliases": ["new dad gift", "新生儿礼物"],
             "surfaces": ["chat"],
             "proposition": "礼品套装 + 贺卡代写",
             "status": "active", "owner": "growth",
             "next_review": "2026-12-15"},
            {"id": "IC-003", "task": "周末露营装备补齐",
             "aliases": ["camping restock"],
             "surfaces": ["agent-browser"],
             "proposition": "清单式一键补齐",
             "status": "watch", "owner": "ops",
             "next_review": "2026-11-20"},
        ],
    }
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
    return path
