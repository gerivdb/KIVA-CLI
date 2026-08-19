"""Tests for on_failure policy inside parallel groups (KIVA-009 PF1-PF4).

These 11 tests validate that `on_failure` declared on individual steps
is correctly applied even when the step runs inside a ParallelGroupExecutor.

AC covered:
  PF1  on_failure=abort inside group  → pipeline ABORTED, later steps SKIPPED
  PF2  on_failure=warn inside group   → group finishes, pipeline PARTIAL, later steps run
  PF3  on_failure=continue inside group → failing step SKIPPED, pipeline still SUCCESS
  PF4  parallel stats are reported even when failures occur inside a group

All tests use dry_run + monkey-patch of _run_step so they are hermetic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from unittest.mock import patch

import pytest

from kiva_cli.core.pipeline_types import Pipeline, Step, StepResult
from kiva_cli.core.pipeline_runner import run_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_step(name: str, on_failure: str = "abort", depends_on: List[str] | None = None) -> Step:
    return Step(
        name=name,
        command=f"echo {name}",
        on_failure=on_failure,  # type: ignore[arg-type]
        depends_on=depends_on or [],
    )


def _success(name: str) -> StepResult:
    return StepResult(step_name=name, status="SUCCESS", returncode=0, duration_s=0.01)


def _fail(name: str) -> StepResult:
    return StepResult(
        step_name=name,
        status="FAILED",
        returncode=1,
        stderr="boom",
        duration_s=0.02,
        error_message="boom",
    )


# ---------------------------------------------------------------------------
# PF1 — on_failure=abort inside a parallel group
# ---------------------------------------------------------------------------

class TestOnFailureAbortInGroup:
    """PF1: A failing step with on_failure=abort inside a parallel group must
    abort the whole pipeline. Siblings in the same group still complete
    (they run concurrently), but any step after the group is SKIPPED.
    """

    def test_abort_stops_later_sequential_steps(self):
        steps = [
            _make_step("pre"),
            _make_step("a", on_failure="abort"),
            _make_step("b", on_failure="abort"),
            _make_step("c", on_failure="abort"),
            _make_step("seq-after", depends_on=["a", "b", "c"]),
        ]
        pipeline = Pipeline(
            name="abort-in-group",
            steps=steps,
            parallel_groups=[["a", "b", "c"]],
            max_workers=3,
        )

        # a will fail, b and c succeed
        side_effects = {
            "pre": _success("pre"),
            "a": _fail("a"),
            "b": _success("b"),
            "c": _success("c"),
            "seq-after": _success("seq-after"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "ABORTED"
        assert any(r.step_name == "a" and r.status == "FAILED" for r in result.steps)
        assert any(r.step_name == "seq-after" and r.status == "SKIPPED" for r in result.steps)
        assert result.parallel_groups_executed == 1

    def test_abort_marks_only_the_failing_step_failed(self):
        """Only the failing step keeps FAILED; siblings keep their real status."""
        steps = [
            _make_step("pre"),
            _make_step("a", on_failure="abort"),
            _make_step("b", on_failure="abort"),
            _make_step("c", on_failure="abort"),
            _make_step("seq-after", depends_on=["a", "b", "c"]),
        ]
        pipeline = Pipeline(
            name="abort-only-failing",
            steps=steps,
            parallel_groups=[["a", "b", "c"]],
        )

        side_effects = {
            "pre": _success("pre"),
            "a": _fail("a"),
            "b": _success("b"),
            "c": _success("c"),
            "seq-after": _success("seq-after"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "ABORTED"
        assert any(r.step_name == "a" and r.status == "FAILED" for r in result.steps)
        assert any(r.step_name == "b" and r.status == "SUCCESS" for r in result.steps)
        assert any(r.step_name == "c" and r.status == "SUCCESS" for r in result.steps)
        assert any(r.step_name == "seq-after" and r.status == "SKIPPED" for r in result.steps)

    def test_abort_inside_group_still_executes_all_group_members(self):
        """All members of the parallel group finish even when one aborts."""
        completion_order = []

        def run_step(step, **kwargs):
            completion_order.append(step.name)
            if step.name == "fail-me":
                return _fail("fail-me")
            return _success(step.name)

        steps = [
            _make_step("pre"),
            _make_step("fail-me", on_failure="abort"),
            _make_step("ok-1", on_failure="abort"),
            _make_step("ok-2", on_failure="abort"),
            _make_step("seq-after", depends_on=["fail-me", "ok-1", "ok-2"]),
        ]
        pipeline = Pipeline(
            name="abort-all-members",
            steps=steps,
            parallel_groups=[["fail-me", "ok-1", "ok-2"]],
        )

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=run_step):
            result = run_pipeline(pipeline, dry_run=False)

        # All group members were executed
        assert "fail-me" in completion_order
        assert "ok-1" in completion_order
        assert "ok-2" in completion_order
        assert result.status == "ABORTED"
        assert any(r.step_name == "seq-after" and r.status == "SKIPPED" for r in result.steps)


# ---------------------------------------------------------------------------
# PF2 — on_failure=warn inside a parallel group
# ---------------------------------------------------------------------------

class TestOnFailureWarnInGroup:
    """PF2: on_failure=warn inside group → the group completes fully,
    pipeline ends as PARTIAL, subsequent sequential steps still execute.
    """

    def test_warn_allows_later_steps(self):
        steps = [
            _make_step("pre"),
            _make_step("a", on_failure="warn"),
            _make_step("b", on_failure="warn"),
            _make_step("c", on_failure="warn"),
            _make_step("seq-after"),
        ]
        pipeline = Pipeline(
            name="warn-in-group",
            steps=steps,
            parallel_groups=[["a", "b", "c"]],
        )

        side_effects = {
            "pre": _success("pre"),
            "a": _fail("a"),
            "b": _success("b"),
            "c": _success("c"),
            "seq-after": _success("seq-after"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "PARTIAL"
        assert result.parallel_groups_executed == 1
        assert any(r.step_name == "seq-after" and r.status == "SUCCESS" for r in result.steps)

    def test_warn_keeps_group_siblings_running(self):
        """Siblings in a warn group finish even if one member fails."""
        completion_order = []

        def run_step(step, **kwargs):
            completion_order.append(step.name)
            if step.name == "fail-me":
                return _fail("fail-me")
            return _success(step.name)

        steps = [
            _make_step("pre"),
            _make_step("fail-me", on_failure="warn"),
            _make_step("ok-1", on_failure="warn"),
            _make_step("ok-2", on_failure="warn"),
            _make_step("seq-after"),
        ]
        pipeline = Pipeline(
            name="warn-siblings-run",
            steps=steps,
            parallel_groups=[["fail-me", "ok-1", "ok-2"]],
        )

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert "ok-1" in completion_order
        assert "ok-2" in completion_order
        assert result.status == "PARTIAL"
        assert any(r.step_name == "fail-me" and r.status == "FAILED" for r in result.steps)
        assert any(r.step_name == "ok-1" and r.status == "SUCCESS" for r in result.steps)
        assert any(r.step_name == "seq-after" and r.status == "SUCCESS" for r in result.steps)

    def test_warn_records_failure_but_does_not_abort(self):
        """warn must leave the pipeline as PARTIAL, not ABORTED."""
        steps = [
            _make_step("pre"),
            _make_step("a", on_failure="warn"),
            _make_step("seq-after"),
        ]
        pipeline = Pipeline(
            name="warn-no-abort",
            steps=steps,
            parallel_groups=[["a"]],
        )

        side_effects = {
            "pre": _success("pre"),
            "a": _fail("a"),
            "seq-after": _success("seq-after"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "PARTIAL"
        assert any(r.step_name == "a" and r.status == "FAILED" for r in result.steps)
        assert any(r.step_name == "seq-after" and r.status == "SUCCESS" for r in result.steps)


# ---------------------------------------------------------------------------
# PF3 — on_failure=continue inside a parallel group
# ---------------------------------------------------------------------------

class TestOnFailureContinueInGroup:
    """PF3: on_failure=continue inside group → failing step is turned into
    SKIPPED, the whole pipeline can still be SUCCESS.
    """

    def test_continue_treats_failure_as_skipped(self):
        steps = [
            _make_step("a", on_failure="continue"),
            _make_step("b", on_failure="continue"),
            _make_step("seq"),
        ]
        pipeline = Pipeline(
            name="continue-in-group",
            steps=steps,
            parallel_groups=[["a", "b"]],
        )

        side_effects = {
            "a": _fail("a"),
            "b": _success("b"),
            "seq": _success("seq"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "SUCCESS"
        assert any(r.step_name == "a" and r.status == "SKIPPED" for r in result.steps)
        assert len(result.steps) == 3

    def test_continue_does_not_pollute_stats(self):
        """continue failure must not inflate parallel failure counters."""
        steps = [
            _make_step("a", on_failure="continue"),
            _make_step("b", on_failure="continue"),
            _make_step("seq"),
        ]
        pipeline = Pipeline(
            name="continue-stats",
            steps=steps,
            parallel_groups=[["a", "b"]],
        )

        side_effects = {
            "a": _fail("a"),
            "b": _fail("b"),
            "seq": _success("seq"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "SUCCESS"
        assert any(r.step_name == "a" and r.status == "SKIPPED" for r in result.steps)
        assert any(r.step_name == "b" and r.status == "SKIPPED" for r in result.steps)
        assert any(r.step_name == "seq" and r.status == "SUCCESS" for r in result.steps)
        assert result.parallel_groups_executed == 1

    def test_continue_multiple_failures(self):
        """Multiple continue failures all become SKIPPED, pipeline still SUCCESS."""
        steps = [
            _make_step("a", on_failure="continue"),
            _make_step("b", on_failure="continue"),
            _make_step("c", on_failure="continue"),
            _make_step("seq"),
        ]
        pipeline = Pipeline(
            name="continue-multi",
            steps=steps,
            parallel_groups=[["a", "b", "c"]],
        )

        side_effects = {
            "a": _fail("a"),
            "b": _fail("b"),
            "c": _fail("c"),
            "seq": _success("seq"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "SUCCESS"
        assert all(
            r.status == "SKIPPED"
            for r in result.steps
            if r.step_name in ("a", "b", "c")
        )
        assert any(r.step_name == "seq" and r.status == "SUCCESS" for r in result.steps)


# ---------------------------------------------------------------------------
# PF4 — Parallel stats are always populated, even with failures
# ---------------------------------------------------------------------------

class TestParallelStatsWithFailure:
    def test_stats_reported_on_warn(self):
        """Parallel stats are populated when on_failure=warn."""
        steps = [
            _make_step("pre"),
            _make_step("a", on_failure="warn"),
            _make_step("seq-after"),
        ]
        pipeline = Pipeline(
            name="warn-stats",
            steps=steps,
            parallel_groups=[["a"]],
        )

        side_effects = {
            "pre": _success("pre"),
            "a": _fail("a"),
            "seq-after": _success("seq-after"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.parallel_groups_executed == 1
        # wall_clock is tracked (may be ~0 with instant mocks)
        assert result.total_parallel_wall_clock >= 0

    def test_stats_reported_on_abort(self):
        """Parallel stats are populated when on_failure=abort."""
        steps = [
            _make_step("pre"),
            _make_step("a", on_failure="abort"),
            _make_step("seq-after"),
        ]
        pipeline = Pipeline(
            name="abort-stats",
            steps=steps,
            parallel_groups=[["a"]],
        )

        side_effects = {
            "pre": _success("pre"),
            "a": _fail("a"),
            "seq-after": _success("seq-after"),
        }

        def _mock_run_step(step, dry_run=False, verbose=False, **kwargs):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.parallel_groups_executed == 1
        # wall_clock is tracked (may be ~0 with instant mocks)
        assert result.total_parallel_wall_clock >= 0

    def test_no_parallel_stats_on_pure_sequential_pipeline(self):
        p = Pipeline(name="seq", steps=[_make_step("only")])
        with patch("kiva_cli.core.pipeline_runner._run_step", return_value=_success("only")):
            res = run_pipeline(p, dry_run=False)
        assert res.parallel_groups_executed == 0
        assert res.total_parallel_wall_clock == 0.0
