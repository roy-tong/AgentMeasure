"""Production calibration connector — local-first data plane (CAL-001).

Boundary architecture (PRD NFR-ISO-001, BP §3):
- production Choice/Outcome events arrive here as FMT-002 funnel events
  from the party that holds the data rights (customer-owned agent app,
  buyer side, or runtime cooperation — never scraped from the provider
  side, which cannot see them);
- aggregation happens LOCALLY: per-arm counts and rates only, never
  per-assignment rows, never content (the funnel schema carries no content
  by design);
- export is opt-in per data class under a three-tier authorization:
    "off"     — not collected at all
    "local"   — aggregated locally, never exported
    "export"  — local + signed aggregate export
  tiers are independent for choice / execution / consumption;
- revocation is immediate: a revoked connector refuses every export;
- every export is HMAC-SHA256 signed so the receiving side can verify
  provenance and integrity.

What this module does NOT do: it does not transmit anything. Export writes
a local file; moving it to a counterparty is a data-rights decision made
outside this code (G0), under the contract the customer signed.
"""

import datetime
import hashlib
import hmac
import json
import os
from typing import Any, Dict, List, Optional

CONNECTOR_CONFIG_SCHEMA = "agentmeasure.lab/connector-config"
CONNECTOR_EXPORT_SCHEMA = "agentmeasure.lab/connector-export"
DATA_CLASSES = ("choice", "execution", "consumption")
TIERS = ("off", "local", "export")


class ConnectorError(ValueError):
    pass


# ---------------------------------------------------------------- config


def default_config(experiment_id: str) -> Dict[str, Any]:
    return {
        "schema": CONNECTOR_CONFIG_SCHEMA,
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "authorization": {c: "local" for c in DATA_CLASSES},
        "revoked": False,
        "created_at": _now(),
    }


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        config = json.load(fh)
    if config.get("schema") != CONNECTOR_CONFIG_SCHEMA:
        raise ConnectorError(f"{path} is not a connector config")
    for data_class, tier in config.get("authorization", {}).items():
        if data_class not in DATA_CLASSES or tier not in TIERS:
            raise ConnectorError(f"invalid authorization entry: {data_class}={tier}")
    return config


def save_config(config: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def set_tier(config: Dict[str, Any], data_class: str, tier: str) -> Dict[str, Any]:
    if data_class not in DATA_CLASSES:
        raise ConnectorError(f"unknown data class {data_class!r} (choose from {DATA_CLASSES})")
    if tier not in TIERS:
        raise ConnectorError(f"unknown tier {tier!r} (choose from {TIERS})")
    config["authorization"][data_class] = tier
    return config


def revoke(path: str) -> Dict[str, Any]:
    config = load_config(path)
    config["revoked"] = True
    config["revoked_at"] = _now()
    save_config(config, path)
    return config


# ---------------------------------------------------------------- key


def _load_key(key_path: str) -> bytes:
    if not os.path.exists(key_path):
        key = hashlib.sha256(os.urandom(32)).hexdigest().encode("utf-8")
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(key)
        return key
    with open(key_path, "rb") as fh:
        return fh.read().strip()


def _sign(payload: str, key: bytes) -> str:
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------- ingest & export


_EVENT_CLASS = {
    "reach": "choice",
    "choice": "choice",
    "attempt": "execution",
    "operation_result": "execution",
    "consumption": "consumption",
}


def aggregate_local(events: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregate FMT-002 events locally, honoring the "off" tier.

    Classes at "off" are dropped BEFORE aggregation — not collected means
    not collected. The result stays on disk only.
    """
    allowed = {c for c, tier in config["authorization"].items() if tier != "off"}
    counts: Dict[str, Dict[str, int]] = {}

    def bucket(variant: str) -> Dict[str, int]:
        return counts.setdefault(variant, {"reach": 0, "selected": 0, "operations": 0,
                                           "operations_succeeded": 0, "attempts": 0, "consumed": 0})

    for ev in events:
        data_class = _EVENT_CLASS.get(ev.get("event", ""))
        if data_class not in allowed:
            continue
        b = bucket(ev.get("variant_id", "unknown"))
        kind = ev["event"]
        if kind == "reach":
            b["reach"] += 1
        elif kind == "choice":
            if ev.get("selected_subject"):
                b["selected"] += 1
        elif kind == "operation_result":
            b["operations"] += 1
            b["attempts"] += ev.get("attempts", 0)
            if ev.get("outcome") == "success":
                b["operations_succeeded"] += 1
        elif kind == "consumption":
            if ev.get("consumed"):
                b["consumed"] += 1
    return {
        "schema": "agentmeasure.lab/connector-aggregate",
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "aggregate": "per-arm counts only; no per-assignment rows; no content (schema forbids it)",
        "counts": counts,
        "aggregated_at": _now(),
    }


def export(
    config_path: str,
    events_path: str,
    out_path: str,
    key_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Produce a signed, aggregate-only export — or refuse, loudly.

    Refusal conditions (all raise ConnectorError):
    - the connector has been revoked (revocation is immediate);
    - a data class is below "export" tier (its counts are excluded, and the
      export lists what is missing so the receiving side sees the gap);
    - events do not validate against FMT-002.
    """
    config = load_config(config_path)
    if config.get("revoked"):
        raise ConnectorError("connector is revoked — export refused (revocation is immediate)")

    from .prereg import load_schema
    from .schemas import validate as schema_validate

    events: List[Dict[str, Any]] = []
    with open(events_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    event_schema = load_schema("funnel-event.schema.json")
    for i, ev in enumerate(events):
        try:
            schema_validate(ev, event_schema)
        except Exception as e:  # noqa: BLE001
            raise ConnectorError(f"event[{i}] fails FMT-002: {e}") from e

    exportable = {c for c, tier in config["authorization"].items() if tier == "export"}
    if not exportable:
        raise ConnectorError(
            "no data class is authorized at 'export' tier — nothing may leave this machine"
        )

    # Export aggregates are computed from export-tier classes ONLY: classes at
    # 'local' stay on this machine, classes at 'off' were never collected.
    export_view = dict(config)
    export_view["authorization"] = {
        c: ("export" if c in exportable else "off") for c in DATA_CLASSES
    }
    local = aggregate_local(events, export_view)

    key_path = key_path or os.path.join(os.path.dirname(os.path.abspath(config_path)), "connector.key")
    key = _load_key(key_path)

    payload = {
        "schema": CONNECTOR_EXPORT_SCHEMA,
        "schema_version": "1.0.0",
        "experiment_id": config["experiment_id"],
        "exported_at": _now(),
        "authorization_used": {c: config["authorization"][c] for c in DATA_CLASSES},
        "excluded_classes": sorted(c for c in DATA_CLASSES if c not in exportable),
        "counts": local["counts"],
        "notes": (
            "aggregate counts only; per-assignment data and content are never exported. "
            "Verify signature with HMAC-SHA256 over the canonical JSON of everything "
            "except the 'signature' field."
        ),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    payload["key_id"] = hashlib.sha256(key).hexdigest()[:16]
    payload["signature"] = _sign(canonical, key)

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return payload


def verify_export(export_path: str, key_path: str) -> Dict[str, Any]:
    """Verify an export's signature and integrity."""
    with open(export_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    signature = payload.pop("signature", None)
    key_id = payload.pop("key_id", None)
    with open(key_path, "rb") as fh:
        key = fh.read().strip()
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    expected = _sign(canonical, key)
    return {
        "signature_valid": hmac.compare_digest(expected, signature or ""),
        "key_id_matches": key_id == hashlib.sha256(key).hexdigest()[:16],
        "experiment_id": payload.get("experiment_id"),
        "excluded_classes": payload.get("excluded_classes"),
    }
