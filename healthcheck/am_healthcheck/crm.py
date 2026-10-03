"""Buyer business-system records — the third of the four inputs (BP r28 p5).

The export is the vendor-side view; the CRM/helpdesk records are the buyer's
own system of record. `crm-join` puts them together with one discipline:
a CRM record may FILL an empty judgement cell (provenance says so), may never
silently overwrite a value the export already carries, and a disagreement
between the two systems is named as a conflict row — a discrepancy between
witnesses, not a verdict.

CRM CSV columns: conversation_id (required), reopened_at / human_handover_at
(optional ISO timestamps), optional note. Nothing else is read; no message
text, no customer content.
"""
from __future__ import annotations

import csv
import os
from typing import Any, Dict, List, Tuple

from . import vendors as vendors_mod


class CrmError(ValueError):
    pass


def load_crm(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        if "conversation_id" not in fields:
            raise CrmError("CRM records need a conversation_id column; got: %s"
                           % ", ".join(reader.fieldnames or []))
        rows = []
        for i, row in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in row.items()}
            rows.append({
                "line": i + 2,
                "conversation_id": row.get("conversation_id"),
                "reopened_at": row.get("reopened_at", ""),
                "human_handover_at": row.get("human_handover_at", ""),
                "note": row.get("note", ""),
            })
    return rows


def crm_join(export_path: str, crm_rows: List[Dict[str, Any]],
             out_path: str) -> Dict[str, Any]:
    """Fill empty judgement cells from CRM; name conflicts. Returns a report."""
    export = vendors_mod.load_export(export_path)
    with open(export_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        raw_rows = list(reader)
    mapping = vendors_mod._map_columns(fieldnames)

    crm_by_id: Dict[str, List[Dict[str, Any]]] = {}
    for row in crm_rows:
        crm_by_id.setdefault(str(row["conversation_id"]), []).append(row)

    filled = 0
    conflicts: List[Dict[str, Any]] = []
    unmatched: List[str] = []
    out_columns = list(fieldnames)
    prov_col = "prov_customer_recontacted_at"
    if prov_col not in out_columns:
        out_columns.append(prov_col)

    writer_rows: List[Dict[str, Any]] = []
    for raw in raw_rows:
        row = dict(raw)
        cid = None
        if "conversation_id" in mapping:
            cid = (raw.get(mapping["conversation_id"]) or "").strip()
        recs = crm_by_id.get(cid, []) if cid else []
        if cid and cid not in crm_by_id:
            unmatched.append(cid)
        if recs:
            crm = recs[0]
            reopened = crm.get("reopened_at", "")
            handover = crm.get("human_handover_at", "")
            # FILL: only where the export has nothing.
            target = mapping.get("customer_recontacted_at")
            if reopened and (not target or not (raw.get(target) or "").strip()):
                row["customer_recontacted_at"] = reopened
                row[prov_col] = "crm:%s" % os.path.basename(str(reopened) and "record")
                row[prov_col] = "crm:reopened_at"
                filled += 1
            # CONFLICT: export says no human, CRM records a handover.
            h_target = mapping.get("human_agent_participated")
            if handover and h_target:
                current = vendors_mod._as_bool(raw.get(h_target))
                if current is False:
                    conflicts.append({
                        "conversation_id": cid,
                        "field": "human_agent_participated",
                        "export_says": "no",
                        "crm_says": "human_handover_at=%s" % handover,
                    })
        writer_rows.append(row)

    directory = os.path.dirname(os.path.abspath(out_path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=out_columns,
                                extrasaction="ignore")
        writer.writeheader()
        for row in writer_rows:
            writer.writerow({c: row.get(c, "") for c in out_columns})

    return {
        "crm_rows": len(crm_rows),
        "rows_filled": filled,
        "conflicts": conflicts,
        "export_ids_absent_from_crm": len(unmatched),
        "joined_file": os.path.basename(out_path),
        "reading": "CRM records filled empty cells only (provenance says so); "
                   "conflicts are named for a human, never resolved here",
    }


def crm_join_report(result: Dict[str, Any]) -> str:
    W = 58
    out = ["CRM join — buyer business records against the export",
           "=" * W]
    out.append("CRM rows: %d" % result["crm_rows"])
    out.append("empty cells filled from CRM: %d" % result["rows_filled"])
    out.append("conflicts (export vs CRM): %d" % len(result["conflicts"]))
    out.append("export ids absent from CRM: %d" % result["export_ids_absent_from_crm"])
    for c in result["conflicts"][:8]:
        out.append("  CONFLICT %s: export says %s, CRM says %s"
                   % (c["conversation_id"], c["export_says"], c["crm_says"]))
    out.append("")
    out.append(result["reading"])
    return "\n".join(out)
