"""AgentMeasure canonical JSON（AgentMeasure-DATA 规定的确定性序列化）。

目的：所有实现必须对同一 Receipt 产生完全相同的签名字节。
规则（对 signed 字段集）：
  1. 对象键按 UTF-8 字节序排序
  2. 无空白分隔
  3. 字符串：UTF-8、NFC 归一化、JSON 转义（ensure_ascii=False）
  4. 数字：整数原样；浮点按 repr（规范字段实际只允许整数/字符串/null）
  5. 递归处理嵌套对象/数组；null 原样
"""
from __future__ import annotations

import json
import unicodedata
from typing import Any


def _canonicalize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"non-finite number in canonical json: {value}")
        r = repr(value)
        return r if ("." in r or "e" in r or "E" in r) else r + ".0"
    if isinstance(value, str):
        return json.dumps(unicodedata.normalize("NFC", value), ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_canonicalize(v) for v in value) + "]"
    if isinstance(value, dict):
        items = sorted(
            ((unicodedata.normalize("NFC", str(k)), v) for k, v in value.items()),
            key=lambda kv: kv[0].encode("utf-8"),
        )
        return "{" + ",".join(
            json.dumps(k, ensure_ascii=False) + ":" + _canonicalize(v) for k, v in items
        ) + "}"
    raise TypeError(f"unsupported type in canonical json: {type(value)}")


def canonical_json(value: Any) -> str:
    return _canonicalize(value)
