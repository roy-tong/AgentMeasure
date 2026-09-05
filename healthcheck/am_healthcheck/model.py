"""Data model for the healthcheck pipeline.

Grain discipline (mirrors standard/CORE.md):
- an *execution* is one recorded command/tool execution (an Attempt in Core terms);
- a *logical operation* is a maximal retry chain of same-command executions;
- tokens are cumulative snapshots, not events to be summed.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LineStats:
    total: int = 0
    parsed: int = 0
    corrupt: int = 0
    blank: int = 0


@dataclass
class ExecRecord:
    """One command / tool execution with a decidable or unknown outcome.

    source: "exec" (CommandExecution) or "mcp" (McpToolCall).
    status: "ok" | "failed" | "unknown" — unknown is disclosed, never guessed.
    """
    session_id: str
    file: str
    line: int
    source: str
    kind: str            # exec: first token of the command; mcp: server/tool
    exec_id: str = ""
    status: str = "unknown"
    exit_code: Optional[int] = None
    duration: Optional[float] = None
    cmd_hash: str = ""   # sha256 of the normalized command — no raw content
    started_at: str = ""
    scope_hash: str = ""  # sha256 of cwd / MCP arguments — no raw content
    turn_index: int = 0


@dataclass
class CallRecord:
    """One response_item function/custom tool call (the model-side record)."""
    session_id: str
    file: str
    line: int
    call_id: str
    name: str
    kind: str            # "function" | "custom"
    has_output: bool = False
    output_line: Optional[int] = None


@dataclass
class TokenSnapshot:
    file: str
    line: int
    input_tokens: int = 0
    cached_input: int = 0
    cache_write_input: int = 0
    output_tokens: int = 0
    reasoning_output: int = 0
    total_tokens: int = 0
    timestamp: str = ""


@dataclass
class SessionRecord:
    path: str
    session_id: str = ""
    cli_version: str = ""
    originator: str = ""
    started_at: str = ""
    last_ts: str = ""
    models: List[str] = field(default_factory=list)
    line_stats: LineStats = field(default_factory=LineStats)
    execs: List[ExecRecord] = field(default_factory=list)
    calls: List[CallRecord] = field(default_factory=list)
    tokens: List[TokenSnapshot] = field(default_factory=list)
    thread_tokens: List[TokenSnapshot] = field(default_factory=list)
    turns: int = 0
    compactions: int = 0
    subagent_activity: int = 0
    file_changes: int = 0
    unknown_types: Dict[str, int] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)
    corrupt_lines: List[int] = field(default_factory=list)
    truncated: bool = False
    token_invalid: bool = False
    dup_lines: List[List[int]] = field(default_factory=list)      # [line, repeats]
    dup_call_ids: Dict[str, int] = field(default_factory=dict)    # call_id -> count
    dup_call_lines: Dict[str, List[int]] = field(default_factory=dict)

    def feature_flags(self) -> Dict[str, bool]:
        has_exec_events = any(e.source == "exec" for e in self.execs)
        return {
            "token_count_events": bool(self.tokens),
            "token_usage_records": bool(self.thread_tokens),
            "exec_item_events": has_exec_events,
            "compaction_events": self.compactions > 0,
            "multi_agent": self.subagent_activity > 0,
        }


@dataclass
class Evidence:
    session: str
    file: str
    line: int
    detail: Dict[str, object] = field(default_factory=dict)


@dataclass
class Finding:
    title: str
    severity: str = "finding"      # "finding" | "info"
    explanation: str = ""
    next_step: str = ""
    evidence: List[Evidence] = field(default_factory=list)

    def add(self, ev: Evidence) -> None:
        if len(self.evidence) < 50:  # keep reports bounded; count stays exact
            self.evidence.append(ev)


@dataclass
class CheckResult:
    check_id: str
    name: str
    status: str = "ok"              # ok | finding | unprovable | info
    summary: str = ""
    findings: List[Finding] = field(default_factory=list)
    evidence_count: int = 0
    unprovable_reason: str = ""


@dataclass
class RetryChain:
    session_id: str
    file: str
    cmd_hash: str
    kind: str
    attempts: int
    outcomes: List[str]
    first_line: int
    last_line: int
    resolved: bool


@dataclass
class Overview:
    window_label: str = ""
    files: int = 0
    sessions: int = 0
    lines: int = 0
    corrupt_lines: int = 0
    corrupt_ratio: float = 0.0
    truncated_files: int = 0
    unknown_type_lines: int = 0
    first_ts: str = ""
    last_ts: str = ""
    models: List[str] = field(default_factory=list)
    cli_versions: List[str] = field(default_factory=list)
    turns: int = 0
    exec_total: int = 0
    exec_ok: int = 0
    exec_failed: int = 0
    exec_unknown: int = 0
    call_total: int = 0
    retry_chains: int = 0
    retry_attempts_in_chains: int = 0
    unresolved_chains: int = 0
    compactions: int = 0
    subagent_activity: int = 0
    file_changes: int = 0
    token_total_input: int = 0
    token_cached_input: int = 0
    token_output: int = 0
    token_reasoning_output: int = 0
    token_total_reported: int = 0
    token_provable: bool = False
    token_missing_sessions: int = 0
    token_invalid_sessions: int = 0
    sessions_without_exec_events: int = 0
