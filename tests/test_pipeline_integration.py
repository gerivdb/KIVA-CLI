"""KIVA-008 Sprint 3 — CI-safe integration tests for pipeline_runner.

All tests use --dry-run or mock steps to avoid real subprocess execution.
Run with: pytest tests/test_pipeline_integration.py -v
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from kiva_cli.core.pipeline_types import Pipeline, PipelineResult, Step, StepResult
from kiva_cli.core.pipeline_runner import _run_step, run_pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pipeline(*steps: Step) -> Pipeline:
    return Pipeline(name="test-pipe", steps=list(steps))


# ---------------------------------------------------------------------------
# 1. DRY-RUN: all steps SUCCESS, no subprocess
# ---------------------------------------------------------------------------

def test_dry_run_all_success():
    p = _make_pipeline(
        Step(name="a", command="echo hello"),
        Step(name="b", command="echo world", depends_on=["a"]),
    )
    result = run_pipeline(p, dry_run=True)
    assert result.status == "SUCCESS"
    assert all(sr.status == "SUCCESS" for sr in result.steps)
    assert len(result.steps) == 2


def test_dry_run_intent_hash():
    p = _make_pipeline(Step(name="x", command="echo"))
    result = run_pipeline(p, dry_run=True)
    assert len(result.intent_hash) == 32
    assert result.intent_hash.isalnum()


# ---------------------------------------------------------------------------
# 2. on_failure matrix
# ---------------------------------------------------------------------------

def _failing_step(name: str, on_failure: str) -> Step:
    return Step(name=name, command="exit 1", on_failure=on_failure)


def test_on_failure_abort_stops_pipeline():
    """on_failure=abort: subsequent steps must be SKIPPED."""
    p = _make_pipeline(
        Step(name="ok",   command="echo ok"),
        Step(name="fail", command="exit 1", depends_on=["ok"], on_failure="abort"),
        Step(name="next", command="echo next", depends_on=["fail"]),
    )
    with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
        mock_run.side_effect = [
            StepResult(step_name="ok",   status="SUCCESS", duration_s=0.0),
            StepResult(step_name="fail", status="FAILED",  duration_s=0.0, returncode=1, error_message="exit 1"),
        ]
        result = run_pipeline(p)

    assert result.status == "ABORTED"
    names_skipped = [sr.step_name for sr in result.steps if sr.status == "SKIPPED"]
    assert "next" in names_skipped


def test_on_failure_warn_continues():
    """on_failure=warn: pipeline continues, final status PARTIAL."""
    p = _make_pipeline(
        Step(name="a", command="", on_failure="warn"),
        Step(name="b", command="", depends_on=["a"]),
    )
    with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
        mock_run.side_effect = [
            StepResult(step_name="a", status="FAILED",  duration_s=0.0, returncode=1),
            StepResult(step_name="b", status="SUCCESS", duration_s=0.0),
        ]
        result = run_pipeline(p)

    assert result.status == "PARTIAL"
    assert result.steps[0].status == "FAILED"
    assert result.steps[1].status == "SUCCESS"


def test_on_failure_continue_suppresses():
    """on_failure=continue: failed step becomes SKIPPED, pipeline SUCCESS."""
    p = _make_pipeline(
        Step(name="a", command="", on_failure="continue"),
        Step(name="b", command=""),
    )
    with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
        mock_run.side_effect = [
            StepResult(step_name="a", status="FAILED",  duration_s=0.0, returncode=1),
            StepResult(step_name="b", status="SUCCESS", duration_s=0.0),
        ]
        result = run_pipeline(p)

    assert result.status == "SUCCESS"
    assert result.steps[0].status == "SKIPPED"


# ---------------------------------------------------------------------------
# 3. phi_delta hook — called once per step
# ---------------------------------------------------------------------------

def test_phi_delta_called_per_step():
    p = _make_pipeline(
        Step(name="s1", command="echo"),
        Step(name="s2", command="echo"),
    )
    with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run, \
         patch("kiva_cli.core.pipeline_runner._phi_delta_record") as mock_phi:
        mock_run.side_effect = [
            StepResult(step_name="s1", status="SUCCESS", duration_s=0.1),
            StepResult(step_name="s2", status="SUCCESS", duration_s=0.2),
        ]
        run_pipeline(p)

    assert mock_phi.call_count == 2
    calls = [c.kwargs["label"] if c.kwargs else c.args[0] for c in mock_phi.call_args_list]
    assert any("s1" in str(c) for c in calls)
    assert any("s2" in str(c) for c in calls)


# ---------------------------------------------------------------------------
# 4. WAL event shape
# ---------------------------------------------------------------------------

def test_wal_event_emitted():
    p = _make_pipeline(Step(name="w", command="echo"))
    with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run, \
         patch("kiva_cli.core.pipeline_runner._emit_wal_event") as mock_wal:
        mock_run.return_value = StepResult(step_name="w", status="SUCCESS", duration_s=0.05)
        run_pipeline(p)

    mock_wal.assert_called_once()
    call_kwargs = mock_wal.call_args
    event_type = call_kwargs.args[0] if call_kwargs.args else call_kwargs.kwargs.get("event_type")
    payload    = call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs.get("payload")

    assert event_type == "PIPELINE_RUN"
    assert "intent_hash" in payload
    assert "pipeline_name" in payload
    assert "status" in payload
    assert isinstance(payload["steps"], list)
    assert payload["steps"][0]["name"] == "w"


# ---------------------------------------------------------------------------
# 5. duration tracked
# ---------------------------------------------------------------------------

def test_pipeline_result_duration():
    p = _make_pipeline(Step(name="d", command="echo"))
    with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
        mock_run.return_value = StepResult(step_name="d", status="SUCCESS", duration_s=0.01)
        result = run_pipeline(p)
    assert result.duration_s >= 0.0
    assert result.ended_at is not None
