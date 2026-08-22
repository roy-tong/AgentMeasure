"""Harness runner interface and registry (LAB-004).

A harness runner executes one assignment (task x variant) inside one agent
harness and returns observable funnel events. The engine ships with a
deterministic synthetic runner ("mock") so the full pipeline — prereg,
assignment, funnel capture, honest stats, report — runs offline with zero
external dependencies. Real harness adapters (claude-code, codex, dsh) are
third-party plugins implementing the same interface; see lab/README.md.

Plugin contract:
    class MyRunner(HarnessRunner):
        runner_id = "my-harness"
        def setup(self, config): ...
        def run_episode(self, task, variant_levels, assignment, rng) -> list[events]

Register via manifest: {"id": "...", "runner": "module.path:MyRunner"}.
"""

import abc
import importlib
from typing import Any, Dict, List


class HarnessRunner(abc.ABC):
    runner_id: str = "abstract"

    def setup(self, config: Dict[str, Any]) -> None:
        """Called once before the harness's first assignment."""

    @abc.abstractmethod
    def describe(self) -> Dict[str, Any]:
        """Public record of what this runner observes and how (goes into the report)."""

    @abc.abstractmethod
    def run_episode(
        self,
        task: Dict[str, Any],
        variant_levels: Dict[str, str],
        assignment: Dict[str, Any],
        rng,
    ) -> List[Dict[str, Any]]:
        """Execute one assignment; return funnel events in causal order."""

    def teardown(self) -> None:
        """Called once after the harness's last assignment."""


_REGISTRY: Dict[str, type] = {}


def register_runner(cls: type) -> type:
    if not issubclass(cls, HarnessRunner):
        raise TypeError("runner plugins must subclass HarnessRunner")
    _REGISTRY[cls.runner_id] = cls
    return cls


def get_runner(runner_spec: str):
    """Resolve a runner spec: builtin id ("mock") or "module.path:ClassName"."""
    if runner_spec in _REGISTRY:
        return _REGISTRY[runner_spec]()
    if ":" in runner_spec:
        module_name, class_name = runner_spec.split(":", 1)
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name)
        return register_runner(cls)() if cls.runner_id not in _REGISTRY else _REGISTRY[cls.runner_id]()
    raise ValueError(
        f"unknown harness runner {runner_spec!r}; builtins: {sorted(_REGISTRY)}; "
        "plugins use 'module.path:ClassName'"
    )


def _register_builtins() -> None:
    from . import harness_cli, mockharness

    register_runner(mockharness.MockHarnessRunner)
    register_runner(harness_cli.ClaudeCodeRunner)
    register_runner(harness_cli.CodexRunner)


_register_builtins()
