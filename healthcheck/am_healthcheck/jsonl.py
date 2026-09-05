"""Streaming JSONL reader with per-file corrupt-line accounting."""
import json
from typing import Iterator, Optional, Tuple


def iter_lines(path: str, limit_bytes: Optional[int] = None) -> Iterator[Tuple[int, Optional[dict], str]]:
    """Yield (line_number, parsed_object_or_None, raw_line).

    Never raises on malformed lines — the caller accounts them as corrupt.
    `limit_bytes` guards against pathological inputs; when hit, iteration stops.
    """
    read = 0
    try:
        # Read bytes first so the safety cap is measured in file bytes rather
        # than decoded Python characters. Decode each line independently so a
        # single malformed UTF-8 line is disclosed as corrupt while the rest
        # of the session remains usable.
        handle = open(path, "rb")
    except OSError:
        return
    with handle:
        for lineno, raw_bytes in enumerate(handle, start=1):
            read += len(raw_bytes)
            if limit_bytes and read > limit_bytes:
                return
            try:
                raw = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                yield lineno, None, raw_bytes.decode("utf-8", "replace")
                continue
            stripped = raw.strip()
            if not stripped:
                yield lineno, None, raw
                continue
            try:
                obj = json.loads(stripped)
            except (json.JSONDecodeError, ValueError, RecursionError):
                yield lineno, None, raw
                continue
            if not isinstance(obj, dict):
                yield lineno, None, raw
                continue
            yield lineno, obj, raw


def parse_ts(value) -> str:
    """Normalize an ISO timestamp defensively; returns '' when unusable."""
    if not isinstance(value, str) or not value:
        return ""
    text = value.strip().encode("utf-8", "replace").decode("utf-8")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return text
