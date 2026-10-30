"""Agent 工具账单能力目录。

目录不是“已接通”清单：reader_status= cataloged 只表示账单/计费维度已建模，
recipe_status 与 live_bill_status 分别披露采集配方和真实账单验证状态。
"""

import json
import os
import re
from typing import Dict, Iterable, List

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "catalog", "tools.json")
VALID_REGIONS = {"cn", "global"}
VALID_ROLES = {"buyer", "seller"}
VALID_READER_STATUS = {"cataloged", "schema_ready", "synthetic_tested", "live_validated"}
VALID_RECIPE_STATUS = {"not_built", "recipe_ready", "synthetic_tested", "live_validated"}
VALID_LIVE_STATUS = {"not_validated", "synthetic_tested", "live_validated"}


def load_catalog(path=None) -> Dict:
    with open(path or CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    errors = validate_catalog(catalog)
    if errors:
        raise ValueError("invalid tool catalog: %s" % "; ".join(errors))
    return catalog


def validate_catalog(catalog: Dict) -> List[str]:
    errors = []
    if not catalog.get("catalog_version"):
        errors.append("catalog_version required")
    regions = set(catalog.get("regions", []))
    categories = set(catalog.get("categories", []))
    seen_ids, seen_aliases = set(), {}
    providers = catalog.get("providers")
    if not isinstance(providers, list) or not providers:
        return ["providers must be a non-empty list"]
    for index, provider in enumerate(providers):
        pid = provider.get("id")
        if not pid:
            errors.append("provider %d missing id" % index)
            continue
        if pid in seen_ids:
            errors.append("duplicate provider id: %s" % pid)
        seen_ids.add(pid)
        if provider.get("region") not in regions | VALID_REGIONS:
            errors.append("%s: invalid region" % pid)
        if provider.get("category") not in categories:
            errors.append("%s: invalid category" % pid)
        roles = set(provider.get("roles", []))
        if not roles or not roles <= VALID_ROLES:
            errors.append("%s: roles must be buyer/seller" % pid)
        if provider.get("reader_status") not in VALID_READER_STATUS:
            errors.append("%s: invalid reader_status" % pid)
        if provider.get("recipe_status") not in VALID_RECIPE_STATUS:
            errors.append("%s: invalid recipe_status" % pid)
        if provider.get("live_bill_status") not in VALID_LIVE_STATUS:
            errors.append("%s: invalid live_bill_status" % pid)
        for field in ("billing_models", "metering_units", "bill_sources",
                      "ledger_import_channels", "audit_capabilities"):
            if not isinstance(provider.get(field), list) or not provider[field]:
                errors.append("%s: %s must be a non-empty list" % (pid, field))
        if not str(provider.get("pricing_url", "")).startswith("https://"):
            errors.append("%s: pricing_url must be https" % pid)
        for alias in [pid, provider.get("name", "")] + list(provider.get("aliases", [])):
            key = normalize_provider(alias)
            if not key:
                continue
            if key in seen_aliases and seen_aliases[key] != pid:
                errors.append("alias %r maps to both %s and %s" %
                              (alias, seen_aliases[key], pid))
            seen_aliases[key] = pid
    return errors


def normalize_provider(value) -> str:
    text = str(value or "").strip().casefold()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)


def provider_index(catalog=None) -> Dict[str, Dict]:
    catalog = catalog or load_catalog()
    index = {}
    for provider in catalog["providers"]:
        for alias in [provider["id"], provider["name"]] + provider.get("aliases", []):
            index[normalize_provider(alias)] = provider
    return index


def list_providers(region=None, role=None, category=None, query="", catalog=None) -> List[Dict]:
    catalog = catalog or load_catalog()
    needle = str(query or "").casefold().strip()
    result = []
    for provider in catalog["providers"]:
        if region and provider["region"] != region:
            continue
        if role and role not in provider["roles"]:
            continue
        if category and provider["category"] != category:
            continue
        haystack = " ".join([
            provider["id"], provider["name"], provider.get("notes", ""),
            provider.get("buyer_use", ""), provider.get("seller_use", ""),
            " ".join(provider.get("aliases", [])),
        ]).casefold()
        if needle and needle not in haystack:
            continue
        result.append(provider)
    return sorted(result, key=lambda p: (p["region"], p["category"], p["name"]))


def get_provider(provider_id, catalog=None) -> Dict:
    catalog = catalog or load_catalog()
    match = provider_index(catalog).get(normalize_provider(provider_id))
    if not match:
        raise KeyError("unknown tool provider: %s" % provider_id)
    return match


def coverage(seen_providers: Iterable[str], catalog=None) -> Dict:
    """把账本中的 provider 名映射到支持目录，未知项显式保留。"""
    catalog = catalog or load_catalog()
    index = provider_index(catalog)
    known, unknown = [], []
    for name in sorted(set(seen_providers)):
        provider = index.get(normalize_provider(name))
        if provider:
            known.append({
                "input": name,
                "id": provider["id"],
                "name": provider["name"],
                "region": provider["region"],
                "category": provider["category"],
                "roles": provider["roles"],
                "reader_status": provider["reader_status"],
                "recipe_status": provider["recipe_status"],
                "live_bill_status": provider["live_bill_status"],
                "billing_models": provider["billing_models"],
                "metering_units": provider["metering_units"],
            })
        else:
            unknown.append(name)
    return {
        "catalog_version": catalog["catalog_version"],
        "known_count": len(known),
        "unknown_count": len(unknown),
        "known": known,
        "unknown": unknown,
    }


def support_summary(catalog=None) -> Dict:
    catalog = catalog or load_catalog()
    providers = catalog["providers"]
    by_region = {}
    by_role = {}
    by_status = {}
    for provider in providers:
        by_region[provider["region"]] = by_region.get(provider["region"], 0) + 1
        for role in provider["roles"]:
            by_role[role] = by_role.get(role, 0) + 1
        by_status[provider["reader_status"]] = by_status.get(provider["reader_status"], 0) + 1
    live = sum(1 for p in providers if p["live_bill_status"] == "live_validated")
    return {
        "catalog_version": catalog["catalog_version"],
        "total": len(providers),
        "by_region": by_region,
        "by_role": by_role,
        "by_reader_status": by_status,
        "live_bill_validated": live,
    }
