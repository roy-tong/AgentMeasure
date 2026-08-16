#!/usr/bin/env python3
"""AgentMeasure — Observer Capability Manifest（标准取代 observer 名称猜测）。

原则：系统不能靠 observer 名字（如 LIKE 'claude-otel%'）判断某信号是否可观察。
可观察性必须由 runtime 显式声明（AgentMeasure-QUALITY §3）。

Manifest 格式（YAML/JSON，随 runtime profile 发布）：
  runtime / runtime_version / collector_profile / valid_from /
  每信号: OBSERVABLE | PARTIAL | UNOBSERVABLE | UNKNOWN
"""
from __future__ import annotations

import json
from pathlib import Path

SIGNALS = ("presented", "selected", "invoked", "completed",
           "consumed", "task_outcome", "external_effect")

STATES = ("OBSERVABLE", "PARTIAL", "UNOBSERVABLE", "UNKNOWN")

# 默认 manifest：按 runtime profile 声明（reference/adapters/*/manifest.json）
MANIFESTS_DIR = Path(__file__).resolve().parents[1] / "adapters"


def load_manifest(runtime: str) -> dict:
    """按 runtime 名加载 manifest；未知 runtime → 全部 UNKNOWN（fail-closed）。"""
    path = MANIFESTS_DIR / runtime / "manifest.json"
    if not path.exists():
        return {"runtime": runtime, "signals": {s: "UNKNOWN" for s in SIGNALS}}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def is_observable(runtime: str, signal: str, required: str = "OBSERVABLE") -> bool:
    """信号在该 runtime 是否达到 required 可观察级别。"""
    manifest = load_manifest(runtime)
    level = manifest.get("signals", {}).get(signal, "UNKNOWN")
    order = {"OBSERVABLE": 3, "PARTIAL": 2, "UNKNOWN": 1, "UNOBSERVABLE": 0}
    return order.get(level, 0) >= order.get(required, 3)


def validate(manifest: dict) -> bool:
    """Manifest 结构校验。"""
    if not manifest.get("runtime") or not manifest.get("runtime_version"):
        return False
    if not manifest.get("collector_profile"):
        return False
    signals = manifest.get("signals", {})
    if not signals:
        return False
    for s, state in signals.items():
        if s not in SIGNALS or state not in STATES:
            return False
    return True
