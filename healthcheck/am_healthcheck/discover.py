"""Runtime auto-discovery: find local agent logs without user configuration.

Supported runtimes:
- Codex (rollout JSONL): ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl  [supported]
- Claude Code: ~/.claude/projects/<munged-path>/*.jsonl                 [detected, not yet supported]

Discovery reports what it found even when the adapter is absent, so the user
always knows which of their runtimes the current release can read.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timedelta, timezone

ROLLOUT_NAME = re.compile(
    r"^rollout-(\d{4})-(\d{2})-(\d{2})T\d{2}-\d{2}-\d{2}-[0-9a-fA-F-]+(?:_[0-9a-fA-F-]+)?\.jsonl$"
)


@dataclass
class RuntimeFound:
    runtime: str                 # "codex" | "claude"
    supported: bool
    root: str
    files: List[str] = field(default_factory=list)
    note: str = ""


@dataclass
class DiscoveryResult:
    runtimes: List[RuntimeFound] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def selected_files(self) -> List[str]:
        for rt in self.runtimes:
            if rt.supported:
                return rt.files
        return []

    def primary(self) -> Optional[RuntimeFound]:
        for rt in self.runtimes:
            if rt.supported:
                return rt
        return None


def codex_root(home: Optional[str] = None) -> str:
    return os.path.join(home or os.path.expanduser("~"), ".codex", "sessions")


def claude_root(home: Optional[str] = None) -> str:
    return os.path.join(home or os.path.expanduser("~"), ".claude", "projects")


def _codex_date_of(path: str) -> Optional[datetime]:
    name = os.path.basename(path)
    match = ROLLOUT_NAME.match(name)
    if not match:
        return None
    try:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                        tzinfo=timezone.utc)
    except ValueError:
        return None


def collect_codex_files(root: str, since: Optional[datetime], until: Optional[datetime]) -> List[str]:
    out: List[str] = []
    for base, _dirs, names in os.walk(root):
        for name in sorted(names):
            if not name.endswith(".jsonl"):
                continue
            full = os.path.join(base, name)
            stamp = _codex_date_of(full)
            if stamp is None:
                continue                       # not a rollout file; skip silently
            if since and stamp < since:
                continue
            if until and stamp > until + timedelta(days=1):
                continue
            out.append(full)
    return sorted(out)


def collect_claude_files(root: str) -> List[str]:
    out: List[str] = []
    if not os.path.isdir(root):
        return out
    for base, _dirs, names in os.walk(root):
        for name in sorted(names):
            if name.endswith(".jsonl"):
                out.append(os.path.join(base, name))
    return out


def parse_date(text: str) -> datetime:
    """Parse a YYYY-MM-DD date; raises ValueError with a usable message."""
    if not isinstance(text, str):
        raise ValueError("dates must be YYYY-MM-DD strings")
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("invalid date %r — use YYYY-MM-DD, e.g. 2026-09-01" % text)


def filter_by_date(paths: List[str], since: Optional[datetime],
                   until: Optional[datetime]):
    """Filter explicitly-listed files by their rollout filename date.

    Files whose names carry no parseable rollout date are kept: their window
    cannot be decided, and dropping them silently would hide data. The caller
    discloses how many were kept undated.
    """
    kept: List[str] = []
    skipped = 0
    undated = 0
    for path in paths:
        stamp = _codex_date_of(path)
        if stamp is None:
            kept.append(path)
            undated += 1
            continue
        if since and stamp < since:
            skipped += 1
            continue
        if until and stamp > until + timedelta(days=1):
            skipped += 1
            continue
        kept.append(path)
    return kept, skipped, undated


def discover(since_days: Optional[int] = None, explicit_dir: Optional[str] = None,
             scan_all: bool = False, now: Optional[datetime] = None,
             since: Optional[datetime] = None, until: Optional[datetime] = None
             ) -> DiscoveryResult:
    result = DiscoveryResult()
    since_window = None
    if since_days is not None and not scan_all:
        since_window = (now or datetime.now(timezone.utc)) - timedelta(days=since_days)
    lower = since or since_window

    # --- Codex: supported runtime ---
    root = explicit_dir or codex_root()
    if not os.path.isdir(root):
        result.runtimes.append(RuntimeFound(
            runtime="codex", supported=True, root=root,
            note="Codex sessions directory not found. Pass --dir <path> to point at rollout-*.jsonl files."))
    else:
        files = collect_codex_files(root, lower, until)
        note = ""
        if not files and (lower is not None or until is not None):
            note = "No rollout files in the selected window; try --days N, --since/--until, or --all."
        result.runtimes.append(RuntimeFound(
            runtime="codex", supported=True, root=root, files=files, note=note))

    # --- Claude Code: detected, adapter pending real-sample validation ---
    if not explicit_dir:
        croot = claude_root()
        cfiles = collect_claude_files(croot)
        result.runtimes.append(RuntimeFound(
            runtime="claude", supported=False, root=croot, files=cfiles,
            note=("Detected %d Claude Code session file(s); the Claude adapter "
                  "ships after validation against real samples — this run only "
                  "reads Codex logs." % len(cfiles)) if cfiles else
                 "No Claude Code session files found."))
    return result
