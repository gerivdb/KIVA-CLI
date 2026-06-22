"""Tests for KIVA-010 retry feature.

Tests that steps with retry=N are executed multiple times on failure,
and that total_retries_used is tracked correctly.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from kiva_cli.core.pipeline_types import Pipeline, Step, StepResult
from kiva_cli.core.pipeline_runner import run_pipeline


def _make_step(name: str, retry: int = 0, on_failure: str = "abort") -> Step:
    return Step(
        name=name,
        command=f"echo {name}",
        retry=retry,
        on_failure=on_failure,  # type: ignore[arg-type]
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


class TestRetryFeature:
    """KIVA-010 S1-S3: retry parameter parsing, execution, and tracking."""

    def test_retry_zero_is_single_attempt(self):
        """retry=0 (default) means exactly one attempt."""
        steps = [_make_step("step1", retry=0)]
        pipeline = Pipeline(name="retry-zero", steps=steps)

        side_effects = {"step1": _fail("step1")}

        def _mock_run_step(step, dry_run=False, verbose=False):
            return side_effects[step.name]

        with patch("kiva_cli.core.pipeline_runner._run_step_with_retry", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        # Should have 1 attempt (no retries)
        assert result.steps[0].attempts == 1
        assert result.total_retries_used == 0

    def test_retry_one_succeeds_on_second_attempt(self):
        """retry=1 means up to 2 attempts; success on 2nd should return SUCCESS."""
        steps = [_make_step("step1", retry=1)]
        pipeline = Pipeline(name="retry-one", steps=steps)

        call_count = {"count": 0}

        def _mock_run_step(step, dry_run=False, verbose=False):
            call_count["count"] += 1
            # Fail first, succeed second
            if call_count["count"] == 1:
                return _fail("step1")
            return _success("step1")

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.steps[0].status == "SUCCESS"
        assert result.steps[0].attempts == 2
        assert result.total_retries_used == 1

    def test_retry_exhausted_after_all_attempts(self):
        """retry=2 with 3 failures should return FAILED after 3 attempts."""
        steps = [_make_step("step1", retry=2)]
        pipeline = Pipeline(name="retry-exhausted", steps=steps)

        call_count = {"count": 0}

        def _mock_run_step(step, dry_run=False, verbose=False):
            call_count["count"] += 1
            return _fail("step1")

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.steps[0].status == "FAILED"
        assert result.steps[0].attempts == 3
        assert result.total_retries_used == 2

    def test_retry_with_abort_on_failure(self):
        """retry with on_failure=abort should still abort after final failure."""
        steps = [
            _make_step("pre"),
            _make_step("retry_step", retry=1, on_failure="abort"),
            _make_step("after"),
        ]
        pipeline = Pipeline(name="retry-abort", steps=steps)

        call_count = {"count": 0}

        def _mock_run_step(step, dry_run=False, verbose=False):
            call_count["count"] += 1
            if step.name == "retry_step":
                # Always fail
                return _fail("retry_step")
            return _success(step.name)

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.status == "ABORTED"
        assert result.steps[0].status == "SUCCESS"
        assert result.steps[1].status == "FAILED"
        assert result.steps[2].status == "SKIPPED"
        assert result.steps[1].attempts == 2
        assert result.total_retries_used == 1

    def test_retry_in_parallel_group(self):
        """retry should work correctly inside parallel groups."""
        steps = [
            _make_step("a", retry=1),
            _make_step("b", retry=0),
        ]
        pipeline = Pipeline(
            name="retry-parallel",
            steps=steps,
            parallel_groups=[["a", "b"]],
        )

        call_count = {"a": 0, "b": 0}

        def _mock_run_step(step, dry_run=False, verbose=False):
            call_count[step.name] += 1
            if step.name == "a":
                # Fail first, succeed second
                if call_count["a"] == 1:
                    return _fail("a")
                return _success("a")
            return _success("b")

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.steps[0].status == "SUCCESS"  # a succeeded on retry
        assert result.steps[0].attempts == 2
        assert result.steps[1].status == "SUCCESS"
        assert result.steps[1].attempts == 1
        assert result.total_retries_used == 1

    def test_total_retries_used_across_multiple_steps(self):
        """total_retries_used should sum retries from all steps."""
        steps = [
            _make_step("s1", retry=1),  # 1 retry if fails
            _make_step("s2", retry=2),  # 2 retries if fails
            _make_step("s3", retry=0),  # 0 retries
        ]
        pipeline = Pipeline(name="retry-total", steps=steps)

        call_counts = {"s1": 0, "s2": 0, "s3": 0}

        def _mock_run_step(step, dry_run=False, verbose=False):
            call_counts[step.name] += 1
            if step.name == "s1":
                return _success("s1") if call_counts["s1"] > 1 else _fail("s1")
            if step.name == "s2":
                return _success("s2") if call_counts["s2"] > 2 else _fail("s2")
            return _success("s3")

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        # s1: 1 retry, s2: 2 retries, s3: 0 retries
        assert result.total_retries_used == 3

    def test_retry_on_timeout_counts_as_attempt(self):
        """A timeout failure should be retried and count toward attempts + total_retries_used."""
        steps = [_make_step("timeout_step", retry=1)]
        pipeline = Pipeline(name="retry-timeout", steps=steps)

        call_count = {"count": 0}

        def _mock_run_step(step, dry_run=False, verbose=False):
            call_count["count"] += 1
            if call_count["count"] == 1:
                # Simulate timeout on first attempt
                return StepResult(
                    step_name=step.name,
                    status="FAILED",
                    returncode=-1,
                    error_message=f"Step '{step.name}' timed out after 5s",
                    duration_s=5.0,
                )
            return _success(step.name)

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            result = run_pipeline(pipeline, dry_run=False)

        assert result.steps[0].status == "SUCCESS"
        assert result.steps[0].attempts == 2
        assert result.total_retries_used == 1

    def test_on_failure_notify_emits_pipeline_alert_and_continues(self):
        """on_failure=notify must emit PIPELINE_ALERT with {step, error, retry_attempts} and continue (no abort)."""
        steps = [
            _make_step("pre"),
            _make_step("alert_step", retry=1, on_failure="notify"),
            _make_step("post"),
        ]
        pipeline = Pipeline(name="notify-alert", steps=steps)

        call_count = {"count": 0}

        def _mock_run_step(step, dry_run=False, verbose=False):
            call_count["count"] += 1
            if step.name == "alert_step":
                # Fail first, fail second (exhaust retries)
                return _fail("alert_step")
            return _success(step.name)

        with patch("kiva_cli.core.pipeline_runner._run_step", side_effect=_mock_run_step):
            with patch("kiva_cli.core.pipeline_runner._emit_wal_event") as mock_emit:
                result = run_pipeline(pipeline, dry_run=False)

        # Pipeline must continue (post step ran)
        assert result.status == "PARTIAL"  # because of the FAILED notify step
        assert result.steps[0].status == "SUCCESS"
        assert result.steps[1].status == "FAILED"
        assert result.steps[1].attempts == 2
        assert result.steps[2].status == "SUCCESS"
        assert result.total_retries_used == 1

        # Exactly one PIPELINE_ALERT must have been emitted
        # (robust to positional vs keyword calls: PIPELINE_RUN uses keywords)
        def _get_event_type(c):
            if getattr(c, "args", None):
                return c.args[0]
            return getattr(c, "kwargs", {}).get("event_type")

        def _get_payload(c):
            if getattr(c, "args", None) and len(c.args) > 1:
                return c.args[1]
            return getattr(c, "kwargs", {}).get("payload", {})

        alert_calls = [c for c in mock_emit.call_args_list if _get_event_type(c) == "PIPELINE_ALERT"]
        assert len(alert_calls) == 1
        payload = _get_payload(alert_calls[0])
        assert payload["step"] == "alert_step"
        assert "boom" in payload["error"]
        assert payload["retry_attempts"] == 2

        # Also the final PIPELINE_RUN was emitted (standard)
        assert any(_get_event_type(c) == "PIPELINE_RUN" for c in mock_emit.call_args_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
