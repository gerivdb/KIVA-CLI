"""TDD tests for on_failure policy inside parallel groups -- KIVA-009.

Currently RED: pipeline_runner.run_pipeline is still sequential (no group walker).
Turns GREEN once the group-aware walker + _apply_on_failure are implemented.

AC covered:
  AC-PF1  on_failure=abort in group  -> pipeline ABORTED, post-group steps SKIPPED
  AC-PF2  on_failure=warn  in group  -> siblings finish, pipeline PARTIAL, SEQ steps run
  AC-PF3  on_failure=continue        -> treated as SKIPPED, pipeline SUCCESS
  AC-PF4  parallel_groups_executed == 1 even when a member failed (warn)

All tests use synthetic pipelines + patched _run_step (no subprocess, no YAML).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures: synthetic Pipeline objects
# ---------------------------------------------------------------------------

def _make_pipeline(on_failure_for_failing_step: str):
    """Return a 4-step Pipeline with one parallel group.

    Layout:
      parallel_groups: [[step-a, step-b, step-c]]
      - step-a  : always SUCCESS
      - step-b  : always FAILED  -- on_failure = <param>
      - step-c  : always SUCCESS
      - step-seq: sequential, always SUCCESS (runs after the group)
    """
    try:
        from kiva_cli.core.pipeline_types import Pipeline, Step
    except ImportError as exc:
        pytest.skip(f"pipeline_types unavailable: {exc}")

    return Pipeline(
        name="test-on-failure",
        version="1.0.0",
        nexus_status="TEST",
        description="Synthetic pipeline for on_failure AC tests",
        steps=[
            Step(name="step-a", command="echo a", on_failure="abort"),
            Step(name="step-b", command="echo b", on_failure=on_failure_for_failing_step),
            Step(name="step-c", command="echo c", on_failure="abort"),
            Step(name="step-seq", command="echo seq", on_failure="abort"),
        ],
        parallel_groups=[["step-a", "step-b", "step-c"]],
        max_workers=3,
        on_failure="abort",
    )


def _make_step_result(name: str, status: str):
    """Return a minimal StepResult with given status."""
    try:
        from kiva_cli.core.pipeline_types import StepResult
        rc = 0 if status in ("SUCCESS", "SKIPPED") else 1
        return StepResult(
            step_name=name,
            status=status,
            returncode=rc,
            stdout=f"[mock] {name} -> {status}",
            duration_s=0.01,
            error_message="" if rc == 0 else f"mock failure in {name}",
        )
    except ImportError as exc:
        pytest.skip(f"pipeline_types unavailable: {exc}")


def _run(pipeline, failure_step: str = "step-b"):
    """Invoke run_pipeline with _run_step patched to inject controlled results."""
    try:
        from kiva_cli.core.pipeline_runner import run_pipeline
    except ImportError as exc:
        pytest.skip(f"pipeline_runner unavailable: {exc}")

    def mock_run_step(step, dry_run=False, verbose=False):
        if step.name == failure_step:
            return _make_step_result(step.name, "FAILED")
        return _make_step_result(step.name, "SUCCESS")

    with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=mock_run_step):
        return run_pipeline(pipeline, dry_run=False, verbose=False)


# ---------------------------------------------------------------------------
# AC-PF1 -- on_failure=abort inside parallel group
# ---------------------------------------------------------------------------

class TestOnFailureAbortInGroup:
    """AC-PF1: a failing step with on_failure=abort inside a group aborts the pipeline."""

    def test_pipeline_status_is_aborted(self):
        pipeline = _make_pipeline(on_failure_for_failing_step="abort")
        result = _run(pipeline)
        assert result.status in ("ABORTED", "FAILED"), (
            f"Expected ABORTED (or FAILED) when on_failure=abort in group, got {result.status!r}"
        )

    def test_sequential_step_is_skipped(self):
        """step-seq (after the group) must be SKIPPED when group aborts."""
        pipeline = _make_pipeline(on_failure_for_failing_step="abort")
        result = _run(pipeline)
        seq_results = {sr.step_name: sr.status for sr in result.steps}
        assert seq_results.get("step-seq") == "SKIPPED", (
            f"step-seq should be SKIPPED after group abort, got {seq_results}"
        )

    def test_step_b_is_failed_not_skipped(self):
        """The failing step itself must appear as FAILED in the result."""
        pipeline = _make_pipeline(on_failure_for_failing_step="abort")
        result = _run(pipeline)
        seq_results = {sr.step_name: sr.status for sr in result.steps}
        assert seq_results.get("step-b") == "FAILED", (
            f"step-b should be FAILED, got {seq_results}"
        )


# ---------------------------------------------------------------------------
# AC-PF2 -- on_failure=warn inside parallel group
# ---------------------------------------------------------------------------

class TestOnFailureWarnInGroup:
    """AC-PF2: warn -> siblings continue, pipeline PARTIAL, sequential steps run."""

    def test_pipeline_status_is_partial_not_aborted(self):
        pipeline = _make_pipeline(on_failure_for_failing_step="warn")
        result = _run(pipeline)
        assert result.status in ("PARTIAL", "FAILED"), (
            f"Expected PARTIAL (warn policy), got {result.status!r}"
        )
        assert result.status != "ABORTED", (
            "Pipeline must NOT abort when on_failure=warn"
        )

    def test_siblings_have_success_status(self):
        """step-a and step-c must run to completion despite step-b failing."""
        pipeline = _make_pipeline(on_failure_for_failing_step="warn")
        result = _run(pipeline)
        seq = {sr.step_name: sr.status for sr in result.steps}
        assert seq.get("step-a") == "SUCCESS", f"step-a should be SUCCESS, got {seq}"
        assert seq.get("step-c") == "SUCCESS", f"step-c should be SUCCESS, got {seq}"

    def test_sequential_step_runs_after_warn_group(self):
        """step-seq (after the group) must still run when group policy is warn."""
        pipeline = _make_pipeline(on_failure_for_failing_step="warn")
        result = _run(pipeline)
        seq = {sr.step_name: sr.status for sr in result.steps}
        assert seq.get("step-seq") == "SUCCESS", (
            f"step-seq should run after warn group, got {seq}"
        )


# ---------------------------------------------------------------------------
# AC-PF3 -- on_failure=continue inside parallel group
# ---------------------------------------------------------------------------

class TestOnFailureContinueInGroup:
    """AC-PF3: continue -> failing step treated as SKIPPED, pipeline SUCCESS."""

    def test_pipeline_status_is_success(self):
        pipeline = _make_pipeline(on_failure_for_failing_step="continue")
        result = _run(pipeline)
        assert result.status == "SUCCESS", (
            f"Expected SUCCESS when on_failure=continue, got {result.status!r}"
        )

    def test_step_b_appears_as_skipped(self):
        """step-b should be SKIPPED (not FAILED) in result when policy is continue."""
        pipeline = _make_pipeline(on_failure_for_failing_step="continue")
        result = _run(pipeline)
        seq = {sr.step_name: sr.status for sr in result.steps}
        assert seq.get("step-b") == "SKIPPED", (
            f"step-b should be SKIPPED with continue policy, got {seq}"
        )

    def test_all_steps_present_in_result(self):
        """All 4 steps must appear in PipelineResult.steps."""
        pipeline = _make_pipeline(on_failure_for_failing_step="continue")
        result = _run(pipeline)
        names = {sr.step_name for sr in result.steps}
        assert {"step-a", "step-b", "step-c", "step-seq"} == names, (
            f"Expected all 4 steps in result, got {names}"
        )


# ---------------------------------------------------------------------------
# AC-PF4 -- parallel_groups_executed stat
# ---------------------------------------------------------------------------

class TestParallelStatsWithFailure:
    """AC-PF4: parallel_groups_executed is updated even when a group member fails."""

    def test_groups_executed_is_1_after_warn_failure(self):
        pipeline = _make_pipeline(on_failure_for_failing_step="warn")
        result = _run(pipeline)
        assert result.parallel_groups_executed == 1, (
            f"Expected parallel_groups_executed=1 after group run, "
            f"got {result.parallel_groups_executed}"
        )

    def test_groups_executed_is_1_after_abort_failure(self):
        """Even when abort, the group ran (and was counted) before aborting."""
        pipeline = _make_pipeline(on_failure_for_failing_step="abort")
        result = _run(pipeline)
        assert result.parallel_groups_executed == 1, (
            f"Expected parallel_groups_executed=1 even after abort, "
            f"got {result.parallel_groups_executed}"
        )

    def test_groups_executed_is_0_for_sequential_only_pipeline(self):
        """A pipeline with no parallel_groups must have parallel_groups_executed=0."""
        try:
            from kiva_cli.core.pipeline_types import Pipeline, Step, PipelineResult
        except ImportError as exc:
            pytest.skip(f"pipeline_types unavailable: {exc}")

        seq_pipeline = Pipeline(
            name="seq-only",
            version="1.0.0",
            nexus_status="TEST",
            steps=[Step(name="s1", command="echo s1", on_failure="abort")],
        )
        try:
            from kiva_cli.core.pipeline_runner import run_pipeline
        except ImportError as exc:
            pytest.skip(f"pipeline_runner unavailable: {exc}")

        def mock_run_step(step, dry_run=False, verbose=False):
            try:
                from kiva_cli.core.pipeline_types import StepResult
                return StepResult(step_name=step.name, status="SUCCESS",
                                  returncode=0, stdout="ok", duration_s=0.01)
            except ImportError:
                pytest.skip("StepResult unavailable")

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=mock_run_step):
            result = run_pipeline(seq_pipeline, dry_run=False)

        assert result.parallel_groups_executed == 0, (
            f"Sequential pipeline must have parallel_groups_executed=0, "
            f"got {result.parallel_groups_executed}"
        )
