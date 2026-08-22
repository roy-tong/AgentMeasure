"""Real harness runners for controlled experiments (LAB-004).

Architecture: the runner injects a CONTROLLED candidate set into a real
agent harness by exposing the subject capability plus competitors through a
local MCP tool server (``toolserver.py``), runs the harness headless on the
task, and parses the transcript into funnel events. What varies between
variants is the presentation surface (tool descriptions, output verbosity) —
exactly the provider-controllable factors the experiments measure.

Honest status (do not flatter, per project discipline):
- ``claude-code``: adapter implemented against the documented headless
  interface (``claude -p --output-format stream-json --mcp-config``) and
  integration-tested against scripted transcripts (tests/fake_claude.py);
  live-CLI validation is pending — treat the first live runs as validation.
- ``codex``: EXPERIMENTAL. Parsed from documented ``codex exec --json`` item
  events; the App Server surface is the better observation plane (see
  profiles/codex.md §4) and remains future work.

Observability limits disclosed per episode (also in every report):
- candidate set fully controlled; choice observed from the transcript;
- steps = position among candidate-tool calls (proxy);
- latency/cost are NOT observed headless → zeros are labeled placeholders;
- consumption = continuation proxy (non-empty final answer after a
  successful subject call), not the OTel-grade consumption chain.
"""

import json
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional

from . import funnel
from .harness import HarnessRunner

_TOOLSERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toolserver.py")

# Live-validated invocation notes (codex-cli 0.149.0-alpha, 2026-08-22):
# - MCP tool calls need `--approve-for-me` in exec mode, otherwise they fail
#   with "MCP tool call requires approval, but approval policy is never";
# - MCP servers appear as `mcp_tool_call` items with explicit server/tool
#   fields (not function_call);
# - stdin must be closed (DEVNULL) or codex waits on it as extra input;
# - turn.completed carries token usage -> cost_units (1 unit = 1 token).

DEFAULT_CANDIDATES = [
    {
        "id": "your-search-api",
        "role": "subject",
        "description": "Search the web for information.",
    },
    {"id": "web-search-pro", "description": "Web search with ranked results."},
    {"id": "docs-search", "description": "Search technical documentation."},
    {"id": "site-crawler", "description": "Fetch and extract a specific page."},
]

DEFAULT_LEVEL_OVERRIDES = {
    "description_clarity": {
        "clear": {
            "description": (
                "Search the web for information. Use for factual lookups, comparing "
                "sources, and finding current data. Returns 3 ranked results with "
                "titles, snippets and freshness. Prefer this over page crawlers when "
                "you need targeted answers rather than whole pages."
            )
        }
    },
    "output_verbosity": {
        "verbose": {"result_mode": "verbose"}
    },
}


class ParsedEpisode:
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []  # {"tool": str, "ok": bool|None}
        self.final_text: Optional[str] = None
        self.action_items = 0  # proxy for steps: all tool/search/command items
        self.total_tokens: Optional[int] = None


class HeadlessCliRunner(HarnessRunner):
    """Shared machinery: candidate injection, CLI execution, funnel derivation."""

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.candidates: List[Dict[str, Any]] = []
        self.level_overrides: Dict[str, Any] = {}
        self.subject_id: str = ""

    def setup(self, config: Dict[str, Any]) -> None:
        merged = {
            "cli_path": self.default_cli_path(),
            "model": None,
            "timeout_seconds": 120,
            "max_turns": 8,
            "server_name": "am-lab-tools",
            "candidate_tools": DEFAULT_CANDIDATES,
            "level_overrides": DEFAULT_LEVEL_OVERRIDES,
        }
        merged.update(config or {})
        self.config = merged
        self.candidates = [
            dict(t) if isinstance(t, dict) else {"id": str(t), "description": str(t)}
            for t in merged["candidate_tools"]
        ]
        self.level_overrides = merged["level_overrides"] or {}
        subjects = [c["id"] for c in self.candidates if c.get("role") == "subject"]
        if len(subjects) != 1:
            raise ValueError(
                f"{self.runner_id}: candidate_tools needs exactly one role=subject (got {subjects})"
            )
        self.subject_id = subjects[0]

    def default_cli_path(self) -> str:
        raise NotImplementedError

    # -- subclass hooks ------------------------------------------------------
    def build_command(self, prompt: str, spec_path: str, workdir: str) -> List[str]:
        raise NotImplementedError

    def parse_transcript(self, stdout: str) -> ParsedEpisode:
        raise NotImplementedError

    def observability_notes(self) -> List[str]:
        return []

    # -- shared episode machinery ---------------------------------------------
    def _toolset_for(self, variant_levels: Dict[str, str]) -> List[Dict[str, Any]]:
        """Normalized toolset in the toolserver's contract (keys: name/description/
        result_mode). Live-validation finding: the candidate dicts carry "id", but
        the MCP spec file must carry "name" — a mismatch crashed tools/list with
        KeyError('name') and the agent saw "server failed to start"."""
        tools: List[Dict[str, Any]] = []
        for c in self.candidates:
            t = {
                "name": c.get("name") or c["id"],
                "description": c.get("description", ""),
                "result_mode": c.get("result_mode", "baseline"),
            }
            if c.get("role") == "subject":
                for factor, level in (variant_levels or {}).items():
                    override = self.level_overrides.get(factor, {}).get(level)
                    if override:
                        t.update(override)
            tools.append(t)
        return tools

    def _prompt_for(self, task: Dict[str, Any]) -> str:
        return (
            f"{task.get('instruction', 'Complete the task.')}\n\n"
            "Complete this task using ONLY the tools provided by the "
            f"'{self.config['server_name']}' MCP server — they are synthetic and "
            "sufficient for this exercise. Do not use built-in web search or the "
            "shell. Then give your final answer."
        )

    def run_episode(self, task, variant_levels, assignment, rng) -> List[Dict[str, Any]]:
        assignment = dict(assignment, subject_id=self.subject_id)
        tools = self._toolset_for(variant_levels)
        candidate_ids = [t["name"] for t in tools]

        workdir = tempfile.mkdtemp(prefix=f"am-lab-{self.runner_id}-")
        timed_out = False
        stdout = ""
        try:
            spec = {"server_name": self.config["server_name"], "tools": tools}
            spec_path = os.path.join(workdir, "toolspec.json")
            with open(spec_path, "w", encoding="utf-8") as fh:
                json.dump(spec, fh, ensure_ascii=False)

            cmd = self.build_command(self._prompt_for(task), spec_path, workdir)
            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True,
                    stdin=subprocess.DEVNULL,
                    timeout=int(self.config["timeout_seconds"]),
                )
                stdout = proc.stdout or ""
                if proc.returncode != 0 and not stdout.strip():
                    raise ValueError(
                        f"{self.runner_id}: harness exited with code {proc.returncode}: "
                        f"{(proc.stderr or '')[:300]}"
                    )
            except subprocess.TimeoutExpired as e:
                timed_out = True
                raw = e.stdout
                stdout = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else (raw or "")
            except FileNotFoundError as e:
                raise ValueError(
                    f"{self.runner_id}: harness CLI not found ({e}). Install it or set "
                    f"'cli_path' in the harness config of your experiment manifest."
                ) from e

            parsed = self.parse_transcript(stdout)
            return self._derive_events(
                assignment, candidate_ids, parsed, timed_out
            )
        finally:
            import shutil

            shutil.rmtree(workdir, ignore_errors=True)

    def _candidate_tool_from_name(self, name: str, candidate_ids: List[str]) -> Optional[str]:
        for cid in candidate_ids:
            if name == cid or name.endswith(f"__{cid}"):
                return cid
        return None

    def _derive_events(
        self,
        assignment: Dict[str, Any],
        candidate_ids: List[str],
        parsed: ParsedEpisode,
        timed_out: bool,
    ) -> List[Dict[str, Any]]:
        events = [funnel.reach_event(assignment, candidate_ids)]

        calls: List[Dict[str, Any]] = []
        for call in parsed.calls:
            cid = self._candidate_tool_from_name(call.get("tool", ""), candidate_ids)
            if cid is not None:
                calls.append({"tool": cid, "ok": call.get("ok")})

        if calls:
            selected = calls[0]["tool"]
        else:
            selected = "none-of-the-candidates"
        events.append(funnel.choice_event(assignment, selected))

        subject_calls = [c for c in calls if c["tool"] == self.subject_id]
        if not subject_calls:
            return events

        steps_total = max(parsed.action_items, len(calls))
        any_ok = any(c["ok"] is True for c in subject_calls)
        all_unresolved = all(c["ok"] is None for c in subject_calls)
        # Token metering when the harness reports usage: 1 cost unit = 1 token,
        # amortized across the episode's subject attempts (disclosed in describe()).
        cost_per_attempt = (
            round(parsed.total_tokens / len(subject_calls), 2)
            if parsed.total_tokens else 0.0
        )
        for attempt_index, call in enumerate(subject_calls, start=1):
            outcome = "success" if call["ok"] is True else ("failure" if call["ok"] is False else "unresolved")
            events.append(
                funnel.attempt_event(
                    assignment, 1, attempt_index, outcome,
                    steps=steps_total, latency_ms=0, cost_units=cost_per_attempt,
                )
            )
        outcome = "unresolved" if all_unresolved else ("success" if any_ok else "failure")
        events.append(funnel.operation_result_event(assignment, 1, outcome, len(subject_calls)))

        if outcome == "failure":
            events.append(funnel.consumption_event(assignment, 1, False, "operation_failed"))
        elif outcome == "unresolved":
            events.append(funnel.consumption_event(assignment, 1, False, "unknown"))
        else:
            final = (parsed.final_text or "").strip()
            if timed_out and not final:
                events.append(funnel.consumption_event(assignment, 1, False, "unknown"))
            else:
                consumed = bool(final)
                events.append(
                    funnel.consumption_event(
                        assignment, 1, consumed,
                        "task_continuation" if consumed else "none",
                    )
                )
        return events


class ClaudeCodeRunner(HeadlessCliRunner):
    runner_id = "claude-code"

    def default_cli_path(self) -> str:
        return "claude"

    def build_command(self, prompt: str, spec_path: str, workdir: str) -> List[str]:
        server = self.config["server_name"]
        mcp_config = {
            "mcpServers": {
                server: {"command": sys.executable, "args": [_TOOLSERVER, "--spec", spec_path]}
            }
        }
        config_path = os.path.join(workdir, "mcp-config.json")
        with open(config_path, "w", encoding="utf-8") as fh:
            json.dump(mcp_config, fh)
        cmd = [
            self.config["cli_path"], "-p", prompt,
            "--output-format", "stream-json",
            "--mcp-config", config_path,
            "--allowedTools", f"mcp__{server}",
            "--max-turns", str(int(self.config["max_turns"])),
        ]
        model = self.config.get("model")
        if model:
            cmd += ["--model", model]
        return cmd

    def parse_transcript(self, stdout: str) -> ParsedEpisode:
        ep = ParsedEpisode()
        results_by_call: Dict[str, bool] = {}
        ordered: List[Dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = item.get("type")
            if kind == "assistant":
                for block in (item.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        ordered.append({"id": block.get("id"), "name": block.get("name", "")})
            elif kind == "user":
                for block in (item.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        results_by_call[block.get("tool_use_id")] = not block.get("is_error", False)
            elif kind == "result":
                ep.final_text = item.get("result")
        for call in ordered:
            ep.calls.append({"tool": call["name"], "ok": results_by_call.get(call["id"])})
        return ep

    def describe(self) -> Dict[str, Any]:
        return {
            "runner_id": self.runner_id,
            "kind": "real-harness-adapter (headless CLI)",
            "injection": (
                "controlled candidate set via a per-episode local MCP tool server; "
                "presentation (descriptions, output verbosity) varies per variant"
            ),
            "disclosure": (
                "Adapter integration-tested against scripted transcripts; live-CLI "
                "validation pending — treat first live runs as validation runs."
            ),
            "observability": {
                "reach": "full candidate set controlled (MCP tools exposed)",
                "choice": "first candidate-tool invocation in the transcript",
                "success": "per-call tool_result.is_error",
                "consumption": "continuation proxy: non-empty final answer after a successful subject call",
            },
            "proxies": [
                "steps = number of candidate-tool calls in the episode",
                "latency_ms and cost_units are NOT observed headless; zeros are labeled placeholders",
            ],
            "config": {k: self.config[k] for k in ("cli_path", "timeout_seconds", "max_turns", "model")},
        }


class CodexRunner(HeadlessCliRunner):
    runner_id = "codex"

    def default_cli_path(self) -> str:
        return "codex"

    def build_command(self, prompt: str, spec_path: str, workdir: str) -> List[str]:
        server = self.config["server_name"]
        # codex config overrides take scalar values; wrap args in a launcher script
        launcher = os.path.join(workdir, "launch-tools.sh")
        with open(launcher, "w", encoding="utf-8") as fh:
            fh.write(f'#!/bin/sh\nexec {sys.executable} "{_TOOLSERVER}" --spec {spec_path}\n')
        os.chmod(launcher, 0o755)
        cmd = [
            self.config["cli_path"], "exec", "--json", "--skip-git-repo-check",
            # live-validated: MCP calls need auto-approval in exec mode
            "--approve-for-me",
            # don't pollute the user's codex session history
            "--ephemeral",
            "-c", f'mcp_servers.{server}.command="{launcher}"',
        ]
        for key, value in (self.config.get("codex_config") or {}).items():
            cmd += ["-c", self._toml_override(key, value)]
        model = self.config.get("model")
        if model:
            cmd += ["-c", self._toml_override("model", model)]
        cmd += list(self.config.get("extra_args") or [])
        cmd.append(prompt)
        return cmd

    @staticmethod
    def _toml_override(key: str, value: Any) -> str:
        if isinstance(value, bool):
            return f"{key}={'true' if value else 'false'}"
        if isinstance(value, (int, float)):
            return f"{key}={value}"
        return f'{key}="{value}"'

    def parse_transcript(self, stdout: str) -> ParsedEpisode:
        """Live-validated shapes (codex-cli 0.149.0-alpha):

        - MCP tools appear as items of type ``mcp_tool_call`` with explicit
          ``server``/``tool`` fields, a ``status`` and an ``error`` object;
        - built-in actions appear as ``web_search`` / ``command_execution`` /
          ``local_shell_call`` / ``function_call`` items;
        - the final answer is an ``agent_message`` item; ``turn.completed``
          carries ``usage`` (tokens).
        """
        ep = ParsedEpisode()
        by_id: Dict[str, Dict[str, Any]] = {}
        server = self.config["server_name"]
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = item.get("type", "")
            payload = item.get("item") or {}
            item_type = payload.get("type", "")
            if item_type in ("agent_message", "error", "reasoning"):
                if item_type == "agent_message" and kind == "item.completed":
                    ep.final_text = payload.get("text")
                continue
            if item_type in ("web_search", "command_execution", "local_shell_call"):
                if kind == "item.completed":
                    ep.action_items += 1
                continue
            if item_type in ("mcp_tool_call", "function_call", "tool_call"):
                if kind == "item.started":
                    ep.action_items += 1
                if kind != "item.completed":
                    continue
                ep.action_items = max(ep.action_items, 1)
                if item_type == "mcp_tool_call":
                    name = f"{payload.get('server', '')}.{payload.get('tool', '')}"
                else:
                    name = payload.get("name", "")
                ok = None
                if payload.get("error"):
                    ok = False
                elif payload.get("status") == "completed":
                    ok = True
                elif payload.get("status") == "failed":
                    ok = False
                call_id = payload.get("call_id") or payload.get("id")
                by_id[call_id] = {"tool": name, "ok": ok, "mcp": item_type == "mcp_tool_call"}
            elif kind == "turn.completed":
                usage = item.get("usage") or {}
                ep.total_tokens = (
                    usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                ) or None
        for call in by_id.values():
            ep.calls.append({"tool": call["tool"], "ok": call["ok"]})
        return ep

    def _candidate_tool_from_name(self, name: str, candidate_ids: List[str]) -> Optional[str]:
        # mcp_tool_call names arrive as "<server>.<tool>"; match on the tool part
        tail = name.rsplit(".", 1)[-1]
        for cid in candidate_ids:
            if name == cid or tail == cid or name.endswith(f"__{cid}"):
                return cid
        return None

    def describe(self) -> Dict[str, Any]:
        d = ClaudeCodeRunner.describe(self)
        d.update(
            {
                "runner_id": self.runner_id,
                "kind": "real-harness-adapter (headless CLI)",
                "disclosure": (
                    "Live-validated against codex-cli 0.149.0-alpha (2026-08-22): "
                    "candidate injection via -c mcp_servers.*, MCP calls auto-approved "
                    "with --approve-for-me, ephemeral sessions. Transcript shapes are "
                    "from an alpha CLI and may change upstream; the App Server surface "
                    "remains the better observation plane (profiles/codex.md §4)."
                ),
                "proxies": [
                    "steps = count of action items (tool calls, searches, commands)",
                    "cost_units = episode tokens amortized across subject attempts (1 unit = 1 token)",
                    "latency_ms not observed headless; zero is a labeled placeholder",
                ],
            }
        )
        return d
