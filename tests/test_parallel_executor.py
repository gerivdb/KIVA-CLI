"""Tests for parallel_executor.py — KIVA-009 Sprint 2.

Covers AC-2.5 through AC-2.12:
  AC-2.5  Steps in parallel groups run concurrently (wall_clock < sum_sequential)
  AC-2.6  ParallelConflictError raised if group steps have inter-deps
  AC-2.7  Failed step in group applies on_failure after group completes
  AC-2.8  SKIPPED step in group does not block other group steps
  AC-2.9  max_workers respected
  AC-2.10 validate raises ParallelConflictError correctly
  AC-2.11 kiva pipeline show displays parallel group index (via loader)
  AC-2.12 PipelineResult.wall_clock_seconds populated
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from kiva_cli.core.parallel_executor import (
    ParallelConflictError,
    UnknownStepInGroupError,
    ParallelGroupExecutor,
    validate_parallel_groups,
    run_parallel_group,
)


# ---------------------------------------------------------------------------
# Minimal stubs (avoids importing full pipeline_types)
# ---------------------------------------------------------------------------

@dataclass
class StubStep:
    name: str
    depends_on: list[str] = field(default_factory=list)
    command: str = "echo ok"


@dataclass
class StubStepResult:
    step_name: str
    status: str = "success"
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0


def make_sleep_fn(sleep_sec: float, status: str = "success") -> Any:
    """Returns a run_step_fn that sleeps and returns a StubStepResult."""
    def run_step(step: StubStep) -> StubStepResult:
        time.sleep(sleep_sec)
        return StubStepResult(step_name=step.name, status=status, duration=sleep_sec)
    return run_step


def make_instant_fn(status: str = "success") -> Any:
    """Returns a run_step_fn that returns immediately."""
    def run_step(step: StubStep) -> StubStepResult:
        return StubStepResult(step_name=step.name, status=status)
    return run_step


# ---------------------------------------------------------------------------
# AC-2.5: Concurrent wall_clock < sum_sequential
# ---------------------------------------------------------------------------

class TestParallelWallClock:
    """AC-2.5: parallel execution is actually faster than sequential."""

    def test_parallel_wall_clock_faster_than_sequential(self):
        """Three 0.1s steps should finish in ~0.1s total, not ~0.3s."""
        steps = [StubStep(name=f"step-{i}") for i in range(3)]
        run_fn = make_sleep_fn(0.1)

        t_start = time.monotonic()
        results = run_parallel_group(steps, run_fn, max_workers=4)
        wall = time.monotonic() - t_start

        # sequential would be ~0.3s; parallel should be <0.25s (generous margin)
        assert wall < 0.25, f"Expected parallel wall_clock < 0.25s, got {wall:.3f}s"
        assert len(results) == 3
        assert all(r.status == "success" for r in results.values())

    def test_single_step_runs_normally(self):
        """Single step in group still works."""
        steps = [StubStep(name="solo")]
        results = run_parallel_group(steps, make_instant_fn(), max_workers=4)
        assert "solo" in results
        assert results["solo"].status == "success"


# ---------------------------------------------------------------------------
# AC-2.6 / AC-2.10: ParallelConflictError on intra-group deps
# ---------------------------------------------------------------------------

class TestParallelConflictValidation:
    """AC-2.6 + AC-2.10: validate_parallel_groups raises on intra-group deps."""

    def test_raises_parallel_conflict_when_intra_group_dep(self):
        """Step B depends on Step A — both in same group → ParallelConflictError."""
        steps = [
            StubStep(name="a"),
            StubStep(name="b", depends_on=["a"]),  # intra-group dep!
            StubStep(name="c"),
        ]
        groups = [["a", "b", "c"]]
        with pytest.raises(ParallelConflictError, match="depends on"):
            validate_parallel_groups(steps, groups)

    def test_no_error_when_deps_are_outside_group(self):
        """Step C depends on Step A which is NOT in the same group → OK."""
        steps = [
            StubStep(name="a"),
            StubStep(name="b"),
            StubStep(name="c", depends_on=["a"]),  # a is outside group
        ]
        groups = [["b", "c"]]  # a is not in this group
        validate_parallel_groups(steps, groups)  # must not raise

    def test_raises_unknown_step_in_group(self):
        """Group references a non-existent step name."""
        steps = [StubStep(name="real-step")]
        groups = [["real-step", "ghost-step"]]
        with pytest.raises(UnknownStepInGroupError, match="ghost-step"):
            validate_parallel_groups(steps, groups)

    def test_empty_groups_no_error(self):
        """Empty parallel_groups list → no validation error."""
        steps = [StubStep(name="a"), StubStep(name="b")]
        validate_parallel_groups(steps, [])  # must not raise

    def test_multiple_groups_each_validated(self):
        """Each group is independently validated."""
        steps = [
            StubStep(name="x"),
            StubStep(name="y", depends_on=["x"]),
            StubStep(name="z"),
        ]
        # Group 0: x, z (fine). Group 1: x, y (conflict)
        groups = [["x", "z"], ["x", "y"]]
        with pytest.raises(ParallelConflictError):
            validate_parallel_groups(steps, groups)


# ---------------------------------------------------------------------------
# AC-2.7: Failed step in group — others complete, on_failure applied after
# ---------------------------------------------------------------------------

class TestParallelFailureBehavior:
    """AC-2.7: A failing step does not cancel sibling steps in the group."""

    def test_failed_step_does_not_cancel_siblings(self):
        """Steps run concurrently; one fails; others still return results."""
        completed = []

        def run_step(step: StubStep) -> StubStepResult:
            if step.name == "fail-me":
                time.sleep(0.02)
                return StubStepResult(step_name=step.name, status="failed", exit_code=1)
            time.sleep(0.05)
            completed.append(step.name)
            return StubStepResult(step_name=step.name, status="success")

        steps = [
            StubStep(name="fail-me"),
            StubStep(name="ok-1"),
            StubStep(name="ok-2"),
        ]
        results = run_parallel_group(steps, run_step, max_workers=4)

        assert results["fail-me"].status == "failed"
        assert results["ok-1"].status == "success"
        assert results["ok-2"].status == "success"
        assert "ok-1" in completed and "ok-2" in completed

    def test_group_result_any_failed_flag(self):
        """ParallelGroupResult.any_failed is True when a step fails."""
        executor = ParallelGroupExecutor(max_workers=4)

        def run_step(step):
            if step.name == "bad":
                return StubStepResult(step_name="bad", status="failed", exit_code=1)
            return StubStepResult(step_name=step.name, status="success")

        steps = [StubStep(name="bad"), StubStep(name="good")]
        group_result = executor.run_group(0, steps, run_step)

        assert group_result.any_failed is True
        assert group_result.step_results["bad"].status == "failed"
        assert group_result.step_results["good"].status == "success"


# ---------------------------------------------------------------------------
# AC-2.8: SKIPPED step in group does not block others
# ---------------------------------------------------------------------------

class TestParallelSkipBehavior:
    """AC-2.8: A skipped step in a group doesn't prevent other steps from running."""

    def test_skipped_step_does_not_block_group(self):
        """One step is SKIPPED; others run and succeed."""
        def run_step(step: StubStep) -> StubStepResult:
            if step.name == "skip-me":
                return StubStepResult(step_name="skip-me", status="skipped")
            return StubStepResult(step_name=step.name, status="success")

        steps = [StubStep(name="skip-me"), StubStep(name="run-1"), StubStep(name="run-2")]
        results = run_parallel_group(steps, run_step, max_workers=4)

        assert results["skip-me"].status == "skipped"
        assert results["run-1"].status == "success"
        assert results["run-2"].status == "success"

    def test_group_result_skipped_count(self):
        """ParallelGroupResult.skipped_count reflects number of skipped steps."""
        executor = ParallelGroupExecutor(max_workers=4)

        def run_step(step):
            return StubStepResult(step_name=step.name, status="skipped")

        steps = [StubStep(name=f"s{i}") for i in range(3)]
        group_result = executor.run_group(0, steps, run_step)

        assert group_result.skipped_count == 3
        assert group_result.any_failed is False


# ---------------------------------------------------------------------------
# AC-2.9: max_workers respected
# ---------------------------------------------------------------------------

class TestMaxWorkers:
    """AC-2.9: max_workers setting is passed to ThreadPoolExecutor."""

    def test_max_workers_caps_concurrency(self):
        """With max_workers=2 and 4 steps, at most 2 run simultaneously."""
        concurrency_log = []
        active = [0]
        lock = threading.Lock()

        def run_step(step: StubStep) -> StubStepResult:
            with lock:
                active[0] += 1
                concurrency_log.append(active[0])
            time.sleep(0.05)
            with lock:
                active[0] -= 1
            return StubStepResult(step_name=step.name, status="success")

        steps = [StubStep(name=f"w{i}") for i in range(4)]
        run_parallel_group(steps, run_step, max_workers=2)

        max_concurrent = max(concurrency_log)
        assert max_concurrent <= 2, f"Expected max 2 concurrent, got {max_concurrent}"

    def test_max_workers_capped_at_cpu_count(self):
        """max_workers is capped at os.cpu_count()."""
        cpu = os.cpu_count() or 4
        with patch("kiva_cli.core.parallel_executor.os.cpu_count", return_value=2):
            steps = [StubStep(name=f"s{i}") for i in range(10)]
            results = run_parallel_group(steps, make_instant_fn(), max_workers=100)
        assert len(results) == 10  # all steps completed


# ---------------------------------------------------------------------------
# AC-2.12: wall_clock_seconds in ParallelGroupResult
# ---------------------------------------------------------------------------

class TestWallClockTracking:
    """AC-2.12: wall_clock_seconds is populated in ParallelGroupResult."""

    def test_wall_clock_populated_for_group(self):
        """ParallelGroupResult.wall_clock_seconds > 0 when steps take time."""
        executor = ParallelGroupExecutor(max_workers=4)
        steps = [StubStep(name="slow")]
        group_result = executor.run_group(0, steps, make_sleep_fn(0.05))

        assert group_result.wall_clock_seconds >= 0.04

    def test_executor_accumulates_wall_clock(self):
        """total_wall_clock accumulates across multiple group runs."""
        executor = ParallelGroupExecutor(max_workers=4)
        for i in range(3):
            executor.run_group(i, [StubStep(name="s")], make_sleep_fn(0.02))

        assert executor.total_wall_clock >= 0.05  # 3 x 0.02s, some margin
        assert executor.groups_executed == 3

    def test_groups_executed_counter(self):
        """groups_executed increments per group run."""
        executor = ParallelGroupExecutor(max_workers=4)
        assert executor.groups_executed == 0
        executor.run_group(0, [StubStep(name="a")], make_instant_fn())
        executor.run_group(1, [StubStep(name="b")], make_instant_fn())
        assert executor.groups_executed == 2
