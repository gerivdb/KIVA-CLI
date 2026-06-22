"""Parallel pipeline step executor — KIVA-009 F2.

Provides:
- ParallelConflictError: intra-group dependency violation
- validate_parallel_groups(): pre-run safety check
- run_parallel_group(): concurrent step execution via ThreadPoolExecutor
- ParallelGroupExecutor: stateful executor tracking wall_clock + group count
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Any


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ParallelConflictError(Exception):
    """Raised when steps in the same parallel group have inter-dependencies."""


class UnknownStepInGroupError(Exception):
    """Raised when parallel_groups references a step not in steps list."""


# ---------------------------------------------------------------------------
# Types (minimal, avoids circular import with pipeline_types)
# ---------------------------------------------------------------------------

@dataclass
class ParallelGroupResult:
    """Aggregated result for one parallel group execution."""
    group_index: int
    step_results: dict[str, Any]     # {step_name: StepResult}
    wall_clock_seconds: float
    any_failed: bool
    skipped_count: int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_parallel_groups(
    steps: list[Any],                # list[PipelineStep] — typed loosely to avoid circular import
    parallel_groups: list[list[str]],
) -> None:
    """Validate parallel group definitions.

    Raises:
        UnknownStepInGroupError: if a group references a step name not in steps.
        ParallelConflictError: if steps in the same group have intra-group deps.
    """
    step_map = {s.name: s for s in steps}

    for group_idx, group in enumerate(parallel_groups):
        group_set = set(group)

        for name in group:
            if name not in step_map:
                raise UnknownStepInGroupError(
                    f"parallel_groups[{group_idx}] references unknown step: {name!r}"
                )
            step = step_map[name]
            deps = getattr(step, 'depends_on', None) or []
            for dep in deps:
                if dep in group_set:
                    raise ParallelConflictError(
                        f"Step {name!r} depends on {dep!r} — both in parallel group [{group_idx}]. "
                        f"Intra-group dependencies are not allowed."
                    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_parallel_group(
    steps: list[Any],
    run_step_fn: Callable[[Any], Any],
    max_workers: int = 4,
) -> dict[str, Any]:
    """Run a list of steps concurrently.

    Args:
        steps:        list of PipelineStep objects to run in parallel.
        run_step_fn:  callable(step) -> StepResult, same signature as runner._run_step.
        max_workers:  max thread pool size (capped at cpu_count).

    Returns:
        dict mapping step_name -> StepResult (insertion order = completion order).
    """
    cpu_cap = os.cpu_count() or 4
    effective_workers = min(max_workers, len(steps), cpu_cap)

    results: dict[str, Any] = {}
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=effective_workers) as pool:
        future_to_name = {
            pool.submit(run_step_fn, step): step.name
            for step in steps
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                # Wrap unexpected exceptions into a failed-like result
                # Caller must handle this by checking result type
                result = _make_error_result(name, exc)
            with lock:
                results[name] = result

    return results


def _make_error_result(step_name: str, exc: Exception) -> Any:
    """Create a minimal error result dict when step_fn raises unexpectedly."""
    return {
        "__error__": True,
        "step_name": step_name,
        "exception": str(exc),
        "exit_code": -1,
        "stdout": "",
        "stderr": str(exc),
        "duration": 0.0,
        "status": "failed",
    }


# ---------------------------------------------------------------------------
# Stateful executor (used by pipeline_runner)
# ---------------------------------------------------------------------------

@dataclass
class ParallelGroupExecutor:
    """Stateful wrapper that tracks wall_clock and group count across a pipeline run."""
    max_workers: int = 4
    _groups_executed: int = field(default=0, init=False, repr=False)
    _total_wall_clock: float = field(default=0.0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def groups_executed(self) -> int:
        return self._groups_executed

    @property
    def total_wall_clock(self) -> float:
        return self._total_wall_clock

    def run_group(
        self,
        group_index: int,
        steps: list[Any],
        run_step_fn: Callable[[Any], Any],
    ) -> ParallelGroupResult:
        """Execute one parallel group, update internal stats."""
        t_start = time.monotonic()
        step_results = run_parallel_group(steps, run_step_fn, self.max_workers)
        wall = time.monotonic() - t_start

        # Determine failure / skip counts
        any_failed = False
        skipped_count = 0
        for r in step_results.values():
            status = r.get("status", "") if isinstance(r, dict) else getattr(r, "status", "")
            if isinstance(status, str):
                if status == "failed":
                    any_failed = True
                elif status == "skipped":
                    skipped_count += 1
            else:
                # Assume it's a StepStatus enum
                status_val = status.value if hasattr(status, 'value') else str(status)
                if status_val == "failed":
                    any_failed = True
                elif status_val == "skipped":
                    skipped_count += 1

        with self._lock:
            self._groups_executed += 1
            self._total_wall_clock += wall

        return ParallelGroupResult(
            group_index=group_index,
            step_results=step_results,
            wall_clock_seconds=wall,
            any_failed=any_failed,
            skipped_count=skipped_count,
        )
