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
        tools = [dict(c) for c in self.candidates]
        subject = next(t for t in tools if t["id"] == self.subject_id)
        for factor, level in (variant_levels or {}).items():
            override = self.level_overrides.get(factor, {}).get(level)
            if override:
                subject.update(override)
        for t in tools:
            t.setdefault("description", "")
            t.setdefault("result_mode", "baseline")
        return tools

    def _prompt_for(self, task: Dict[str, Any]) -> str:
        return (
            f"{task.get('instruction', 'Complete the task.')}\n\n"
            "Use the available tools to complete this task, then give your final answer."
        )

    def run_episode(self, task, variant_levels, assignment, rng) -> List[Dict[str, Any]]:
        assignment = dict(assignment, subject_id=self.subject_id)
        tools = self._toolset_for(variant_levels)
        candidate_ids = [t["id"] for t in tools]

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
                    timeout=int(self.config["timeout_seconds"]),
                )
                stdout = proc.stdout or ""
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

        steps_total = len(calls)
        any_ok = any(c["ok"] is True for c in subject_calls)
        all_unresolved = all(c["ok"] is None for c in subject_calls)
        for attempt_index, call in enumerate(subject_calls, start=1):
            outcome = "success" if call["ok"] is True else ("failure" if call["ok"] is False else "unresolved")
            events.append(
                funnel.attempt_event(
                    assignment, 1, attempt_index, outcome,
                    steps=steps_total, latency_ms=0, cost_units=0.0,
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
    experimental = True

    def default_cli_path(self) -> str:
        return "codex"

    def build_command(self, prompt: str, spec_path: str, workdir: str) -> List[str]:
        server = self.config["server_name"]
        # codex config overrides take scalar values; wrap args in a launcher script
        launcher = os.path.join(workdir, "launch-tools.sh")
        with open(launcher, "w", encoding="utf-8") as fh:
            fh.write(f"#!/bin/sh\nexec {sys.executable} {_TOOLSERVER} --spec {spec_path}\n")
        os.chmod(launcher, 0o755)
        return [
            self.config["cli_path"], "exec", "--json", "--skip-git-repo-check",
            "-c", f"mcp_servers.{server}.command={launcher}",
            prompt,
        ]

    def parse_transcript(self, stdout: str) -> ParsedEpisode:
        ep = ParsedEpisode()
        outputs_by_call: Dict[str, bool] = {}
        ordered: List[Dict[str, Any]] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = item.get("type", "")
            payload = item.get("item") or item
            item_type = payload.get("type", "")
            if kind == "item.started" or kind == "item.updated":
                continue
            if item_type in ("function_call", "tool_call", "local_shell_call"):
                call_id = payload.get("call_id") or payload.get("id")
                ordered.append({"id": call_id, "name": payload.get("name", "")})
            elif item_type in ("function_call_output", "tool_call_output"):
                call_id = payload.get("call_id") or payload.get("id")
                out = str(payload.get("output", ""))
                outputs_by_call[call_id] = "error" not in out[:200].lower()
            elif item_type == "agent_message":
                ep.final_text = payload.get("text")
            elif kind == "turn.completed":
                if ep.final_text is None:
                    ep.final_text = item.get("last_agent_message") or ep.final_text
        for call in ordered:
            ep.calls.append({"tool": call["name"], "ok": outputs_by_call.get(call["id"])})
        return ep

    def describe(self) -> Dict[str, Any]:
        d = ClaudeCodeRunner.describe(self)
        d.update(
            {
                "runner_id": self.runner_id,
                "kind": "real-harness-adapter (headless CLI) — EXPERIMENTAL",
                "disclosure": (
                    "EXPERIMENTAL: parsed from documented `codex exec --json` item events; "
                    "shapes may change upstream. The App Server surface is the better "
                    "observation plane (profiles/codex.md §4) and remains future work. "
                    "Integration-tested against scripted transcripts only."
                ),
            }
        )
        return d
