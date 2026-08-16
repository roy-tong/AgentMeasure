#!/usr/bin/env python3
"""AgentMeasure canonical ingestion boundary（Draft 0.4.3）。

Adapter / Provider SDK / Runtime Adapter 只产出 Canonical Observation Envelope
（schemas/observation.schema.json）。本模块是 Collector 的**唯一** ingestion 输入：
  1. 校验 envelope（顶层 schema + per-type payload + timestamp + caller 自洽）
  2. flatten 为 internal observation dict（存储层保持 flattened 模型）

legacy flattened 行（旧 adapter 输出）仍可读取，但 MUST 视为 deprecated
（LEGACY-MIGRATION.md §2），spec-drift 之外的旧格式不再演进。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "registry"))
from validate_entities import validate as _schema_validate  # noqa: E402

sys.path.insert(0, str(ROOT / "reference"))
from collector.usage import empty_observation  # noqa: E402

_ENVELOPE_SCHEMA = json.loads(
    (ROOT / "schemas" / "observation.schema.json").read_text(encoding="utf-8"))
_PAYLOAD_SCHEMAS = {
    p.name.split(".")[0].replace("-", "_"): json.loads(p.read_text(encoding="utf-8"))
    for p in sorted((ROOT / "schemas" / "payloads").glob("*.json"))
}

_CALLER_COMPAT = {
    "unknown": {"unknown"},
    "claimed_agent": {"declared"},
    "correlated_agent": {"correlated"},
    "platform_attested": {"attested"},
}


def validate_canonical(envelope: dict) -> list:
    """返回错误列表；空 = 合法。"""
    errors = _schema_validate(envelope, _ENVELOPE_SCHEMA, "observation")
    otype = envelope.get("observation_type")
    key = otype.replace("-", "_") if otype else None
    payload = envelope.get("payload")
    if key in _PAYLOAD_SCHEMAS and payload is not None:
        errors += _schema_validate(payload, _PAYLOAD_SCHEMAS[key], "observation.payload")
    caller = envelope.get("caller") or {}
    ctype = caller.get("type", "unknown")
    strength = caller.get("identity_strength", "unknown")
    if strength not in _CALLER_COMPAT.get(ctype, set()):
        errors.append(f"observation: caller type={ctype!r} 与 strength={strength!r} 矛盾")
    return errors


def flatten_canonical(envelope: dict) -> dict:
    """Canonical Envelope → internal flattened observation（存储层模型）。"""
    obs = empty_observation()
    obs["observation_id"] = envelope.get("observation_id")
    obs["observed_at"] = envelope.get("observed_at")
    obs["observation_type"] = envelope.get("observation_type")
    observer = envelope.get("observer") or {}
    obs["observer_principal"] = observer.get("principal")
    obs["observer_side"] = observer.get("side")
    obs["trust_domain"] = observer.get("trust_domain")
    obs["provenance"] = envelope.get("provenance")
    dep = envelope.get("deployment_context") or {}
    obs["project_id"] = dep.get("project_id")
    surface = envelope.get("surface") or {}
    obs["surface_id"] = surface.get("surface_id")
    obs["surface_namespace"] = surface.get("surface_namespace")
    obs["provider_claim"] = surface.get("provider_claim")
    obs["capability_claim"] = surface.get("capability_claim")
    # internal `tool` = surface_id 的工具名部分（如 mcp_tool:bar.search → bar.search）
    sid = obs["surface_id"] or ""
    obs["tool"] = sid.split(":", 1)[-1] if ":" in sid else (sid or None)
    caller = envelope.get("caller") or {}
    obs["caller_type"] = caller.get("type")
    obs["caller_runtime"] = caller.get("runtime")
    obs["caller_identity_strength"] = caller.get("identity_strength")
    obs["client_key"] = envelope.get("client_key")
    obs["usage_context"] = envelope.get("usage_context", "unknown")
    obs["validity"] = envelope.get("validity", "unknown")
    obs["context_source"] = envelope.get("context_source", "none")
    obs["validity_source"] = envelope.get("validity_source", "none")
    health = envelope.get("collection_health") or {}
    obs["source_instance_id"] = health.get("source_instance_id")
    obs["source_sequence"] = health.get("source_sequence")
    obs["sequence_epoch"] = health.get("sequence_epoch")
    obs["dropped_since_last_report"] = health.get("dropped_since_last_report")
    obs["buffer_overflow"] = health.get("buffer_overflow")
    obs["sampling"] = envelope.get("sampling")
    obs["signature"] = envelope.get("signature")
    obs["key_id"] = envelope.get("key_id")
    # payload 平铺（internal flattened 模型）
    payload = envelope.get("payload") or {}
    obs.update({k: v for k, v in payload.items() if k in obs})
    return obs


def parse_canonical_line(line: str) -> dict:
    """单行 canonical envelope → internal observation；非法行抛 ValueError。"""
    try:
        envelope = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    errors = validate_canonical(envelope)
    if errors:
        raise ValueError("; ".join(errors))
    return flatten_canonical(envelope)


def ingest_canonical_jsonl(conn, path: Path, source: str, project_id: str,
                           principal: str) -> dict:
    """从 canonical JSONL 批量入库（Collector 唯一 canonical 输入）。"""
    from collector.correlator.correlator import store_observation

    accepted = rejected = 0
    reject_reasons: dict = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obs = parse_canonical_line(line)
        except ValueError as exc:
            rejected += 1
            reason = str(exc).split(":")[0][:40]
            reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
            continue
        # 部署上下文兜底（调用方提供）
        if not obs.get("project_id"):
            obs["project_id"] = project_id
        if store_observation(conn, obs):
            accepted += 1
        else:
            rejected += 1
    conn.commit()
    return {"accepted": accepted, "rejected": rejected, "reject_reasons": reject_reasons}
