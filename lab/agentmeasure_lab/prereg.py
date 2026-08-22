"""Preregistration contract (LAB-003) and manifest handling.

Discipline (PRD G2 / §4.4): the hypothesis, primary metric, guardrails,
sample size and analysis plan are hashed and locked *before* the run; the
run refuses a modified manifest; the report only draws primary conclusions
from the preregistered plan; changing the plan means starting a new
experiment, never editing this one.
"""

import copy
import datetime
import hashlib
import json
import os
from typing import Any, Dict

from . import __version__
from .schemas import SchemaError, validate

MANIFEST_SCHEMA_ID = "agentmeasure.lab/experiment-manifest"
MANIFEST_SCHEMA_VERSION = "1.0.0"

_SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schemas")

_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


def load_schema(name: str) -> Dict[str, Any]:
    if name not in _SCHEMA_CACHE:
        path = os.path.join(_SCHEMA_DIR, name)
        with open(path, "r", encoding="utf-8") as fh:
            _SCHEMA_CACHE[name] = json.load(fh)
    return _SCHEMA_CACHE[name]


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def manifest_hash(manifest: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


def load_manifest(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Dict[str, Any]) -> None:
    schema = load_schema("experiment-manifest.schema.json")
    try:
        validate(manifest, schema)
    except SchemaError as e:
        raise ValueError(f"manifest failed schema validation: {e}") from e
    # Cross-field semantic checks beyond the schema's reach.
    factor_levels = {f["name"]: set(f["levels"]) for f in manifest["factors"]}
    if not factor_levels:
        raise ValueError("manifest must declare at least one factor")
    variant_ids = [v["id"] for v in manifest["variants"]]
    if len(set(variant_ids)) != len(variant_ids):
        raise ValueError("variant ids must be unique")
    controls = [v for v in manifest["variants"] if v.get("baseline")]
    if len(controls) != 1:
        raise ValueError("exactly one variant must be marked baseline: true")
    for v in manifest["variants"]:
        for fname, level in v["levels"].items():
            if fname not in factor_levels:
                raise ValueError(f"variant {v['id']}: unknown factor {fname!r}")
            if level not in factor_levels[fname]:
                raise ValueError(
                    f"variant {v['id']}: level {level!r} not declared for factor {fname!r}"
                )
    guardrail_metrics = {g["metric"] for g in manifest.get("guardrails", [])}
    allowed = set(guardrail_metric_names())
    unknown = guardrail_metrics - allowed
    if unknown:
        raise ValueError(f"unknown guardrail metrics: {sorted(unknown)}")
    if manifest["primary_metric"] not in ("selection_rate", "operation_success_rate", "consumption_rate"):
        raise ValueError("primary_metric must be one of selection_rate / operation_success_rate / consumption_rate")


def guardrail_metric_names():
    return [
        "attempts_per_operation",
        "consumption_rate",
        "median_steps_per_operation",
        "cost_units_per_operation",
    ]


def create_preregistration(manifest: Dict[str, Any]) -> Dict[str, Any]:
    record = {
        "schema": "agentmeasure.lab/preregistration",
        "schema_version": "1.0.0",
        "experiment_id": manifest["experiment_id"],
        "manifest_hash": manifest_hash(manifest),
        "lab_version": __version__,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "manifest": copy.deepcopy(manifest),
    }
    return record


def save_preregistration(record: Dict[str, Any], path: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def load_preregistration(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        record = json.load(fh)
    for key in ("schema", "experiment_id", "manifest_hash", "manifest"):
        if key not in record:
            raise ValueError(f"preregistration file missing {key!r}")
    if record.get("schema") != "agentmeasure.lab/preregistration":
        raise ValueError("not an AgentMeasure Lab preregistration file")
    actual = manifest_hash(record["manifest"])
    if actual != record["manifest_hash"]:
        raise ValueError(
            "preregistration integrity failure: manifest no longer matches its locked hash "
            f"({actual} != {record['manifest_hash']}); start a new experiment instead of editing this one"
        )
    validate_manifest(record["manifest"])
    return record
