"""Native-export preparation — a native vendor export becomes a canonical CSV.

The first step of a first-look engagement (BP r28 p10: 导入与归一). A buyer's
native Intercom/Zendesk export almost never carries the five judgement columns
the recount needs, and a wrong mapping read as a finding is the most expensive
mistake this tool can make. So `prepare` never judges:

- columns the export really carries are carried over verbatim, with a
  `prov_<column>` cell naming the original header;
- judgement columns that the export does not carry stay EMPTY — the concierge
  fills them by hand — and native signal columns travel alongside as
  `hint_<column>` cells, clearly labelled as leads, not verdicts;
- the alignment report prints before any file is written (`--inspect`), and
  the registry's per-vendor notes (F1.1 memo) print with it.

Nothing here reads message text, and no number is produced.
"""
from __future__ import annotations

import csv
import os
from typing import Any, Dict, List

from . import vendors as vendors_mod

# Columns a human must judge; they are never auto-filled from a hint.
JUDGEMENT_COLUMNS = ("human_agent_participated", "issue_addressed",
                     "customer_recontacted_within_window", "vendor_billed")


def _prepare_hints(vendor_id: str) -> Dict[str, Any]:
    return vendors_mod._RULES.get("prepare_hints", {}).get(vendor_id, {})


def prepare(export_path: str, vendor_id: str) -> Dict[str, Any]:
    """Map a native export onto the canonical columns. Produces no verdicts."""
    vendor = vendors_mod.get_vendor(vendor_id)
    hints = _prepare_hints(vendor_id)
    signal_columns: Dict[str, str] = {
        str(k).strip().lower(): v
        for k, v in hints.get("signal_columns", {}).items()
    }

    with open(export_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        mapping = vendors_mod._map_columns(fieldnames)
        lowered = {f.strip().lower(): f for f in fieldnames}
        rows = list(reader)

    # Only canonical and optional columns are mapped; hint sources are separate.
    mapped_targets = [c for c in vendors_mod.COLUMN_ALIASES if c in mapping]

    records: List[Dict[str, Any]] = []
    needs_fill: Dict[str, int] = {}
    used_hint_targets: set = set()
    for row in rows:
        rec: Dict[str, Any] = {}
        for col in vendors_mod.CANONICAL_COLUMNS + vendors_mod.OPTIONAL_COLUMNS:
            rec[col] = row.get(mapping[col]) if col in mapping else None
            if col in vendors_mod.REQUIRED_COLUMNS and not (rec[col] or "").strip():
                needs_fill[col] = needs_fill.get(col, 0) + 1
        for target in sorted(set(signal_columns.values())):
            if target in mapping:
                continue  # the export carries the real column; no hint needed
            parts = []
            for native, col_target in sorted(signal_columns.items()):
                if col_target != target or native not in lowered:
                    continue
                value = row.get(lowered[native])
                if value is not None and str(value).strip():
                    parts.append("%s=%s" % (native, value.strip()))
            if parts:
                # only carried when there is something to read; an absent hint
                # is not an empty verdict
                rec["hint_" + target] = "; ".join(parts)
                used_hint_targets.add(target)
        records.append(rec)

    provenance = {
        col: ("exported:" + mapping[col] if col in mapping else "needs_human")
        for col in vendors_mod.CANONICAL_COLUMNS + vendors_mod.OPTIONAL_COLUMNS
    }
    hint_targets = sorted(used_hint_targets)
    mapped_headers = set(mapping.values())
    unmapped = [f for f in fieldnames
                if f not in mapped_headers
                and f.strip().lower() not in signal_columns]

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor["name"],
        "rows": len(records),
        "records": records,
        "provenance": provenance,
        "hint_targets": hint_targets,
        "columns_missing": [c for c in vendors_mod.REQUIRED_COLUMNS
                            if c not in mapping],
        "needs_fill": needs_fill,
        "unmapped_native_columns": unmapped,
        "vendor_note": hints.get("note", ""),
    }


def prepared_header(prepared: Dict[str, Any]) -> List[str]:
    cols = list(vendors_mod.CANONICAL_COLUMNS + vendors_mod.OPTIONAL_COLUMNS)
    hint_cols = ["hint_" + t for t in prepared["hint_targets"]]
    prov_cols = ["prov_" + c for c in cols]
    return cols + hint_cols + prov_cols


def write_prepared(prepared: Dict[str, Any], out_path: str) -> str:
    """Write the canonical skeleton. Returns the path written."""
    cols = list(vendors_mod.CANONICAL_COLUMNS + vendors_mod.OPTIONAL_COLUMNS)
    directory = os.path.dirname(os.path.abspath(out_path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(prepared_header(prepared))
        for rec in prepared["records"]:
            row = [rec.get(c) for c in cols]
            row += [rec.get("hint_" + t, "") for t in prepared["hint_targets"]]
            row += [prepared["provenance"].get(c, "") for c in cols]
            writer.writerow(row)
    return out_path


def prepare_report(prepared: Dict[str, Any]) -> str:
    """Alignment report: what mapped, what needs a human, what happens next."""
    W = 58
    out = []
    out.append("Native export preparation — no verdicts produced")
    out.append("=" * W)
    out.append("Vendor: %s" % prepared["vendor_name"])
    out.append("Rows:   %d" % prepared["rows"])
    out.append("")
    out.append("Column mapping")
    out.append("-" * W)
    for col in vendors_mod.CANONICAL_COLUMNS + vendors_mod.OPTIONAL_COLUMNS:
        prov = prepared["provenance"][col]
        if prov.startswith("exported:"):
            out.append("  %-36s <- %s" % (col, prov[len("exported:"):]))
        else:
            mark = "NEEDS HUMAN" if col in vendors_mod.REQUIRED_COLUMNS \
                else "absent (optional)"
            out.append("  %-36s -- %s" % (col, mark))
    if prepared["columns_missing"]:
        out.append("")
        out.append("Required columns the export does not carry: %s"
                   % ", ".join(prepared["columns_missing"]))
        out.append("They stay empty. Fill them by hand before any recount;")
        out.append("a guessed value reads as a finding, and findings are money.")
    if prepared["needs_fill"]:
        out.append("")
        out.append("Rows needing a human judgement per column:")
        for col, n in sorted(prepared["needs_fill"].items()):
            out.append("  %-36s %d row(s)" % (col, n))
    if prepared["hint_targets"]:
        out.append("")
        out.append("Hint columns carried alongside (leads, never verdicts):")
        for t in prepared["hint_targets"]:
            out.append("  hint_%s" % t)
    if prepared["unmapped_native_columns"]:
        out.append("")
        out.append("Native columns not mapped anywhere (review once, then ignore):")
        out.append("  %s" % ", ".join(prepared["unmapped_native_columns"]))
    if prepared["vendor_note"]:
        out.append("")
        out.append("Vendor notes from the registry (F1.1):")
        out.append("  %s" % prepared["vendor_note"])
    out.append("")
    out.append("Next: fill the judgement columns, then run")
    out.append("  agentmeasure recount --export <prepared.csv> --vendor %s --inspect"
               % prepared["vendor_id"])
    out.append("and only when every required column matches, recount without --inspect.")
    return "\n".join(out)
