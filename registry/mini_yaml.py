#!/usr/bin/env python3
"""AgentMeasure registry mini-YAML parser（零依赖，registry 专用子集）。

只支持 registry/entities/*.yaml 用到的 YAML 子集：
  - 顶层 map（`key: value` / `key:` + 缩进子块）
  - 缩进 = 空格（任意一致缩进）
  - 列表项 `- key: value`（`- key:` 后缩进子块不支持；后续兄弟键比 "- " 深 2 格）
  - 标量：string / int / bool / null；支持单双引号
  - 注释：行首 `#` 或前导空格的 ` # ...`

不是通用 YAML 解析器；不支持的语法会抛 ValueError 而不是静默误读。
"""
from __future__ import annotations

import re

_SCALAR_INT = re.compile(r"-?\d+$")
_COMMENT = re.compile(r"(\s)#.*$")


def _scalar(s: str):
    s = s.strip()
    if s.startswith('"') and s.endswith('"') and len(s) >= 2:
        return s[1:-1]
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("null", "~", ""):
        return None
    if _SCALAR_INT.match(s):
        return int(s)
    return s


def _lines(text: str) -> list:
    out = []
    for raw in text.splitlines():
        s = _COMMENT.sub(r"\1", raw).rstrip()
        if not s.strip():
            continue
        if s.lstrip().startswith("#"):
            continue
        out.append((len(s) - len(s.lstrip(" ")), s.strip()))
    return out


def _parse(lines: list, i: int, indent: int):
    """Parse node starting at line i（该行缩进 == indent）。返回 (node, next_i)。"""
    content = lines[i][1]
    if content.startswith("- "):
        items = []
        while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
            rest = lines[i][1][2:].strip()
            if ":" not in rest:
                items.append(_scalar(rest))
                i += 1
                continue
            key, _, val = rest.partition(":")
            item = {key.strip(): _scalar(val.strip()) if val.strip() else None}
            i += 1
            # 列表 item 的后续兄弟键（比 "- " 深 2 格，YAML 惯例）
            item_indent = indent + 2
            while i < len(lines) and lines[i][0] == item_indent and not lines[i][1].startswith("- "):
                k2, _, v2 = lines[i][1].partition(":")
                k2, v2 = k2.strip(), v2.strip()
                if v2:
                    item[k2] = _scalar(v2)
                    i += 1
                else:
                    if i + 1 < len(lines) and lines[i + 1][0] > item_indent:
                        child, i2 = _parse(lines, i + 1, lines[i + 1][0])
                        item[k2] = child
                        i = i2
                    else:
                        item[k2] = None
                        i += 1
            items.append(item)
        return items, i

    # map
    obj = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        content = lines[i][1]
        key, _, val = content.partition(":")
        key, val = key.strip(), val.strip()
        if not key:
            raise ValueError(f"invalid map line: {content!r}")
        if val:
            obj[key] = _scalar(val)
            i += 1
        else:
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                child, i2 = _parse(lines, i + 1, lines[i + 1][0])
                obj[key] = child
                i = i2  # i2 已是下一条未解析行，不能再 +1
            else:
                obj[key] = None
                i += 1
    return obj, i


def parse(text: str):
    lines = _lines(text)
    if not lines:
        return {}
    node, end = _parse(lines, 0, lines[0][0])
    if end != len(lines):
        raise ValueError(f"unparsed trailing content at line {end + 1}: {lines[end][1]!r}")
    return node
