"""Local run history — distinguishes demo runs, real runs, errors, repeats.

A tiny append-only file at ~/.agentmeasure/history.jsonl. It never leaves the
machine: this package contains no network code (asserted by tests). Delete the
file to reset first-run detection.
"""
import json
import os
from typing import Dict, List, Optional

HISTORY_DIRNAME = os.path.join(".agentmeasure")
HISTORY_FILENAME = "history.jsonl"


def history_path(home: Optional[str] = None) -> str:
    return os.path.join(home or os.path.expanduser("~"), HISTORY_DIRNAME, HISTORY_FILENAME)


def record_run(entry: Dict[str, object], home: Optional[str] = None) -> None:
    path = history_path(home)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n")
    except OSError:
        pass  # history is best-effort; never block the report


def load_history(home: Optional[str] = None) -> List[Dict[str, object]]:
    path = history_path(home)
    out: List[Dict[str, object]] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        out.append(value)
                except (ValueError, RecursionError):
                    continue
    except OSError:
        pass
    return out


def run_number(mode: str, home: Optional[str] = None) -> int:
    """1 for the first run of this mode, 2, 3, ... for repeats."""
    n = 0
    for entry in load_history(home):
        if entry.get("mode") == mode:
            n += 1
    return n + 1
