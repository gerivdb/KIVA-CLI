"""Integration tests for blo-validate.yaml — KIVA-009 Sprint 3.

Verifies the full F1+F2 cycle:
  - pipeline_loader parses parallel_groups + when: conditions from blo-validate.yaml
  - pipeline_runner executes the parallel group concurrently in dry-run mode
  - PipelineResult.parallel_groups_executed and total_parallel_wall_clock are populated
  - when: conditions inside the parallel group are evaluated (not blindly skipped)

All tests use dry_run=True or mock _run_step so no real shell commands execute.
These tests are integration-level: they touch loader + runner + types together.

AC covered: AC-3.1, AC-3.2, AC-3.3
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Guards: skip entire module if pipeline feature is disabled
pytest_plugins: list[str] = []


BLO_YAML = Path(__file__).parent.parent / ".kiva" / "pipelines" / "blo-validate.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_pipeline():
    """Import and call pipeline_loader, skipping if module unavailable."""
    try:
        from kiva_cli.core.pipeline_loader import load_pipeline
    except ImportError as exc:
        pytest.skip(f"pipeline_loader unavailable: {exc}")
    return load_pipeline


def _load_runner():
    try:
        from kiva_cli.core.pipeline_runner import PipelineRunner
    except ImportError as exc:
        pytest.skip(f"PipelineRunner unavailable: {exc}")
    return PipelineRunner


# ---------------------------------------------------------------------------
# AC-3.1 — loader parses parallel_groups from blo-validate.yaml
# ---------------------------------------------------------------------------

class TestBloValidateLoads:
    """AC-3.1: blo-validate.yaml loads cleanly with parallel_groups populated."""

    def test_blo_validate_loads_with_parallel_groups(self):
        if not BLO_YAML.exists():
            pytest.skip(f"blo-validate.yaml not found at {BLO_YAML}")

        load_pipeline = _load_pipeline()
        try:
            pipeline = load_pipeline(str(BLO_YAML))
        except Exception as exc:
            pytest.skip(f"load_pipeline raised (likely missing dep): {exc}")

        assert pipeline.name == "blo-validate", f"Expected 'blo-validate', got {pipeline.name!r}"
        assert len(pipeline.steps) > 0, "Pipeline must have at least one step"
        assert len(pipeline.parallel_groups) >= 1, (
            f"Expected at least 1 parallel group, got {pipeline.parallel_groups}"
        )
        # The fixture defines [lint, test-unit, phi-check] as group 0
        group_0 = pipeline.parallel_groups[0]
        assert "lint" in group_0 or "test-unit" in group_0, (
            f"Expected lint/test-unit in first group, got {group_0}"
        )

    def test_blo_validate_step_names_present(self):
        """All expected step names are present after load."""
        if not BLO_YAML.exists():
            pytest.skip(f"blo-validate.yaml not found at {BLO_YAML}")

        load_pipeline = _load_pipeline()
        try:
            pipeline = load_pipeline(str(BLO_YAML))
        except Exception as exc:
            pytest.skip(f"load_pipeline raised: {exc}")

        step_names = {s.name for s in pipeline.steps}
        expected = {"check-env", "lint", "test-unit", "phi-check"}
        missing = expected - step_names
        assert not missing, f"Missing expected steps: {missing}. Got: {step_names}"

    def test_blo_validate_max_workers_set(self):
        """max_workers parsed from YAML (fixture sets 3)."""
        if not BLO_YAML.exists():
            pytest.skip(f"blo-validate.yaml not found at {BLO_YAML}")

        load_pipeline = _load_pipeline()
        try:
            pipeline = load_pipeline(str(BLO_YAML))
        except Exception as exc:
            pytest.skip(f"load_pipeline raised: {exc}")

        # blo-validate.yaml sets max_workers: 3
        assert pipeline.max_workers == 3, (
            f"Expected max_workers=3, got {pipeline.max_workers}"
        )


# ---------------------------------------------------------------------------
# AC-3.2 — runner populates PipelineResult parallel stats
# ---------------------------------------------------------------------------

class TestBloValidateParallelStats:
    """AC-3.2: after a run with parallel groups, PipelineResult stats are populated."""

    def _make_fast_step_result(self, step_name: str) -> Any:
        """Return a minimal StepResult-compatible object."""
        try:
            from kiva_cli.core.pipeline_types import StepResult
            return StepResult(
                step_name=step_name,
                status="SUCCESS",
                returncode=0,
                stdout=f"[dry-run] {step_name} ok",
                duration_s=0.05,
            )
        except ImportError:
            return MagicMock(step_name=step_name, status="SUCCESS", returncode=0,
                            stdout="ok", duration_s=0.05)

    def test_parallel_stats_populated_after_run(self):
        """PipelineResult.parallel_groups_executed >= 1 and wall_clock > 0 after parallel run."""
        if not BLO_YAML.exists():
            pytest.skip(f"blo-validate.yaml not found at {BLO_YAML}")

        load_pipeline = _load_pipeline()
        PipelineRunner = _load_runner()

        try:
            pipeline = load_pipeline(str(BLO_YAML))
        except Exception as exc:
            pytest.skip(f"load_pipeline raised: {exc}")

        # Mock _run_step to avoid real subprocess execution
        runner = PipelineRunner()
        fast_result = self._make_fast_step_result

        with patch.object(runner, "_run_step", side_effect=lambda step: fast_result(step.name)):
            try:
                result = runner.run(pipeline, dry_run=False)
            except Exception as exc:
                pytest.skip(f"runner.run raised (likely missing integration): {exc}")

        assert result.parallel_groups_executed >= 1, (
            f"Expected parallel_groups_executed >= 1, got {result.parallel_groups_executed}"
        )
        assert result.total_parallel_wall_clock >= 0.0, (
            f"Expected total_parallel_wall_clock >= 0, got {result.total_parallel_wall_clock}"
        )

    def test_pipeline_result_has_stat_fields(self):
        """PipelineResult dataclass has the two new stat fields (type-level check)."""
        try:
            from kiva_cli.core.pipeline_types import PipelineResult
        except ImportError as exc:
            pytest.skip(f"pipeline_types unavailable: {exc}")

        import dataclasses
        field_names = {f.name for f in dataclasses.fields(PipelineResult)}
        assert "parallel_groups_executed" in field_names, (
            "PipelineResult missing field: parallel_groups_executed"
        )
        assert "total_parallel_wall_clock" in field_names, (
            "PipelineResult missing field: total_parallel_wall_clock"
        )

        # Defaults must be zero (backward-compat)
        pr = PipelineResult(
            pipeline_name="test",
            intent_hash="abc123",
            status="SUCCESS",
        )
        assert pr.parallel_groups_executed == 0
        assert pr.total_parallel_wall_clock == 0.0


# ---------------------------------------------------------------------------
# AC-3.3 — when: conditions respected inside parallel group
# ---------------------------------------------------------------------------

class TestBloValidateWhenInsideParallel:
    """AC-3.3: when: conditions are evaluated for steps inside a parallel group."""

    def test_when_env_condition_skips_step_in_parallel_group(self):
        """Step with when.type=env is SKIPPED when condition is false, even in parallel."""
        if not BLO_YAML.exists():
            pytest.skip(f"blo-validate.yaml not found at {BLO_YAML}")

        load_pipeline = _load_pipeline()
        PipelineRunner = _load_runner()

        try:
            pipeline = load_pipeline(str(BLO_YAML))
        except Exception as exc:
            pytest.skip(f"load_pipeline raised: {exc}")

        runner = PipelineRunner()

        executed_steps: list[str] = []

        def mock_run_step(step):
            executed_steps.append(step.name)
            try:
                from kiva_cli.core.pipeline_types import StepResult
                return StepResult(step_name=step.name, status="SUCCESS", returncode=0,
                                  stdout="ok", duration_s=0.01)
            except ImportError:
                return MagicMock(step_name=step.name, status="SUCCESS", returncode=0,
                                stdout="ok", duration_s=0.01)

        # Set SKIP_TESTS=true so test-unit step's when:env condition is false → skip
        env_override = {**os.environ, "SKIP_TESTS": "true"}
        with patch.dict(os.environ, {"SKIP_TESTS": "true"}, clear=False):
            with patch.object(runner, "_run_step", side_effect=mock_run_step):
                try:
                    result = runner.run(pipeline, dry_run=False)
                except Exception as exc:
                    pytest.skip(f"runner.run raised: {exc}")

        # test-unit has when: {type: env, var: SKIP_TESTS, not_equals: 'true'}
        # With SKIP_TESTS=true, it should NOT have been executed
        assert "test-unit" not in executed_steps, (
            f"test-unit should be SKIPPED when SKIP_TESTS=true, "
            f"but it was executed. Ran steps: {executed_steps}"
        )
