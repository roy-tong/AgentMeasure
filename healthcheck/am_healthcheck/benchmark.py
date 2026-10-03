"""Aggregated benchmark anonymisation pipeline (F2.15).

Cross-brand benchmarks are the only thing that ever leaves a deployment:
taxonomy-level and method-level aggregates, platform rules, anonymous
elasticity. Customer-level data NEVER enters the shared pool — that is a
contract term, so the pipeline enforces it structurally:

- identifier columns (brand, merchant, order, customer…) are DENYLISTED and
  refused in the output, never "hash and hope";
- every published bucket must contain at least `min_brands` DISTINCT
  contributor brands — a bucket with fewer brands is suppressed, and the
  suppression is reported (an absent bucket must not be inferable as
  "exactly one brand's number");
- aggregates are median + p25/p75 over brands, never raw rows;
- the output carries its own anonymisation rules and an audit statement, so
  the receiving side can verify what it is allowed to know.
"""
from __future__ import annotations

import csv
import json
import statistics
from typing import Any, Dict, List

BENCHMARK_SCHEMA = "agentmeasure.commerce/anonymous-benchmark"
BENCHMARK_VERSION = "0.1.0"
DEFAULT_MIN_BRANDS = 5

# Contract-level denylist: these columns identify a customer and are refused
# in output regardless of hashing, sampling, or good intentions.
IDENTIFIER_COLUMNS = ("brand", "brand_name", "merchant", "merchant_id",
                      "store", "store_id", "order_id", "customer_id",
                      "campaign_id", "email", "phone")

MEASURES = ("value",)


class BenchmarkError(ValueError):
    pass


def load_brand_rows(path: str) -> List[Dict[str, Any]]:
    """Brand-period metric rows: brand_key (pseudonym, local-only),
    bucket fields, measure columns."""
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() for f in (reader.fieldnames or [])]
        for required in ("brand_key", "bucket", "value"):
            if required not in fields:
                raise BenchmarkError("brand rows need brand_key, bucket, "
                                     "value; got: %s"
                                     % ", ".join(reader.fieldnames or []))
        rows = []
        for i, raw in enumerate(reader):
            row = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in raw.items()}
            try:
                value = float(row.get("value", ""))
            except ValueError:
                raise BenchmarkError("line %d: value %r is not a number"
                                     % (i + 2, row.get("value"))) from None
            rows.append({"line": i + 2,
                         "brand_key": row.get("brand_key"),
                         "bucket": row.get("bucket"),
                         "value": value})
    return rows


def export_benchmark(rows: List[Dict[str, Any]],
                     min_brands: int = DEFAULT_MIN_BRANDS,
                     taxonomy_version: str = "",
                     method_ref: str = "") -> Dict[str, Any]:
    if min_brands < 2:
        raise BenchmarkError("min_brands below 2 cannot anonymise anything")
    by_bucket: Dict[str, Dict[str, List[float]]] = {}
    for row in rows:
        bucket = by_bucket.setdefault(row["bucket"], {})
        bucket.setdefault(row["brand_key"], []).append(row["value"])

    published = []
    suppressed = []
    for bucket, brands in sorted(by_bucket.items()):
        if len(brands) < min_brands:
            suppressed.append({"bucket": bucket, "brands": len(brands)})
            continue
        # One number per brand first (median of its rows), then the
        # cross-brand distribution. Never raw rows.
        per_brand = [statistics.median(vs) for vs in brands.values()]
        published.append({
            "bucket": bucket,
            "brands": len(brands),
            "median": round(statistics.median(per_brand), 4),
            "p25": round((sorted(per_brand)[int(0.25 * (len(per_brand) - 1))]), 4),
            "p75": round((sorted(per_brand)[int(0.75 * (len(per_brand) - 1))]), 4),
        })

    return {
        "schema": BENCHMARK_SCHEMA,
        "schema_version": BENCHMARK_VERSION,
        "taxonomy_version": taxonomy_version,
        "method_ref": method_ref,
        "buckets": published,
        "suppressed": suppressed,
        "anonymisation_rules": {
            "min_brands_per_bucket": min_brands,
            "aggregation": "one median per brand, then median/p25/p75 across "
                           "brands; raw rows never leave the deployment",
            "identifier_columns_refused": list(IDENTIFIER_COLUMNS),
            "suppression_visible": "suppressed buckets are listed WITHOUT "
                                   "their values, so absence is not a clue",
        },
        "audit_statement": "customer-level data never enters the shared pool "
                           "(contract term): this file contains aggregates "
                           "over at least %d brands per bucket, no "
                           "identifiers, and its own rule set for verification"
                           % min_brands,
    }


def verify_benchmark(doc: Dict[str, Any]) -> List[str]:
    """Re-check an exported benchmark against its own rules. Returns the list
    of violations; empty means the file is safe to share."""
    violations = []
    blob = json.dumps(doc.get("buckets", []))
    for column in IDENTIFIER_COLUMNS:
        if '"%s"' % column in blob:
            violations.append("identifier field %r present in buckets"
                              % column)
    floor = doc.get("anonymisation_rules", {}).get("min_brands_per_bucket", 0)
    for bucket in doc.get("buckets", []):
        if bucket.get("brands", 0) < floor:
            violations.append("bucket %r published with %s brands, below the "
                              "floor of %s" % (bucket.get("bucket"),
                                               bucket.get("brands"), floor))
    return violations


def benchmark_markdown(doc: Dict[str, Any]) -> str:
    out = ["# Anonymous benchmark — safe to share", ""]
    out.append(doc["audit_statement"] + ".")
    out.append("")
    out.append("| bucket | brands | median | p25 | p75 |")
    out.append("|---|---:|---:|---:|---:|")
    for b in doc["buckets"]:
        out.append("| %s | %d | %s | %s | %s |"
                   % (b["bucket"], b["brands"], b["median"], b["p25"],
                      b["p75"]))
    if doc["suppressed"]:
        out.append("")
        out.append("Suppressed (below the brand floor, values withheld): %s"
                   % ", ".join("%s(%d brands)" % (s["bucket"], s["brands"])
                               for s in doc["suppressed"]))
    out.append("")
    out.append("Rules: %s" % json.dumps(doc["anonymisation_rules"],
                                        ensure_ascii=False))
    return "\n".join(out)
