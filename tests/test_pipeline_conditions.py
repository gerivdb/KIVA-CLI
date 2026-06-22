"""KIVA-011 S6 — End-to-end integration tests for `when:` conditions.

Covers AC-K11-8:
- Pipeline YAML with when: expressions
- Loader parses when: as string
- Runner evaluates condition before execution
- Failing conditions produce SKIPPED + skip_reason
- No impact on on_failure logic
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from kiva_cli.core.pipeline_loader import load_pipeline
from kiva_cli.core.pipeline_runner import run_pipeline
from kiva_cli.core.pipeline_types import StepResult


def _write_temp_pipeline(name: str, steps: list[dict]) -> Path:
    """Write a temporary pipeline YAML and return its path.
    Caller is responsible for cleanup (use finally + shutil.rmtree).
    """
    tmpdir = Path(tempfile.mkdtemp())
    pipeline_path = tmpdir / f"{name}.yaml"
    data = {
        "name": name,
        "steps": steps,
    }
    pipeline_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return pipeline_path


def _success(name: str) -> StepResult:
    return StepResult(step_name=name, status="SUCCESS", returncode=0, duration_s=0.01)


def _fail(name: str) -> StepResult:
    return StepResult(
        step_name=name,
        status="FAILED",
        returncode=1,
        duration_s=0.01,
        error_message="boom",
    )


class TestWhenConditionIntegration:
    """Full path: YAML → load_pipeline → run_pipeline with when: evaluation."""

    def test_empty_when_always_runs(self):
        """when: absent or empty → step is executed."""
        path = _write_temp_pipeline(
            "empty-when",
            [
                {"name": "step1", "command": "echo 1"},
                {"name": "step2", "command": "echo 2", "when": ""},
            ],
        )
        try:
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
                mock_run.side_effect = [_success("step1"), _success("step2")]
                result = run_pipeline(load_pipeline(path))

            assert result.steps[0].status == "SUCCESS"
            assert result.steps[1].status == "SUCCESS"
            assert result.steps[1].skip_reason == ""
        finally:
            shutil.rmtree(str(path.parent), ignore_errors=True)

    def test_when_false_skips_step(self):
        """when: "False" → step is SKIPPED with correct skip_reason."""
        path = _write_temp_pipeline(
            "when-false",
            [
                {"name": "always", "command": "echo always"},
                {"name": "conditional", "command": "echo never", "when": "False"},
                {"name": "after", "command": "echo after"},
            ],
        )
        try:
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
                mock_run.side_effect = [_success("always"), _success("after")]
                result = run_pipeline(load_pipeline(path))

            assert result.steps[0].status == "SUCCESS"
            assert result.steps[1].status == "SKIPPED"
            assert "condition not met: False" in result.steps[1].skip_reason
            assert result.steps[2].status == "SUCCESS"
            # Conditional step was never executed
            assert mock_run.call_count == 2
        finally:
            shutil.rmtree(str(path.parent), ignore_errors=True)

    def test_when_dry_run_skips(self):
        """when: "dry_run" is False in normal run, True in --dry-run."""
        path = _write_temp_pipeline(
            "dry-run-when",
            [
                {"name": "only-in-dry-run", "command": "echo dry", "when": "dry_run"},
            ],
        )
        try:
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
                # In normal run, condition is false → skipped, no call to _run_step
                result = run_pipeline(load_pipeline(path), dry_run=False)

            assert result.steps[0].status == "SKIPPED"
            assert "condition not met: dry_run" in result.steps[0].skip_reason
            mock_run.assert_not_called()

            # In dry-run mode, condition should be true (but we still mock)
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run2:
                mock_run2.return_value = _success("only-in-dry-run")
                result_dry = run_pipeline(load_pipeline(path), dry_run=True)

            assert result_dry.steps[0].status == "SUCCESS"
        finally:
            shutil.rmtree(str(path.parent), ignore_errors=True)

    def test_when_last_status(self):
        """when: "last_status == 'SUCCESS'" works across steps."""
        path = _write_temp_pipeline(
            "last-status",
            [
                {"name": "first", "command": "echo first"},
                {"name": "second", "command": "echo second", "when": "last_status == 'SUCCESS'"},
            ],
        )
        try:
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
                mock_run.side_effect = [_success("first"), _success("second")]
                result = run_pipeline(load_pipeline(path))

            assert result.steps[1].status == "SUCCESS"
        finally:
            shutil.rmtree(str(path.parent), ignore_errors=True)

    def test_when_env_var(self):
        """when: using env.get(...) works."""
        path = _write_temp_pipeline(
            "env-when",
            [
                {"name": "prod-only", "command": "echo prod", "when": "env.get('KIVA_ENV') == 'production'"},
            ],
        )
        try:
            os.environ["KIVA_ENV"] = "production"
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
                mock_run.return_value = _success("prod-only")
                result = run_pipeline(load_pipeline(path))

            assert result.steps[0].status == "SUCCESS"

            # Now change env → should skip
            os.environ["KIVA_ENV"] = "staging"
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run2:
                result2 = run_pipeline(load_pipeline(path))

            assert result2.steps[0].status == "SKIPPED"
            assert "condition not met" in result2.steps[0].skip_reason
        finally:
            shutil.rmtree(str(path.parent), ignore_errors=True)
            os.environ.pop("KIVA_ENV", None)

    def test_when_skip_does_not_trigger_on_failure(self):
        """A when-skip must not be treated as a failure (no on_failure logic)."""
        path = _write_temp_pipeline(
            "when-skip-no-failure",
            [
                {"name": "a", "command": "echo a"},
                {"name": "b", "command": "echo b", "when": "False", "on_failure": "abort"},
                {"name": "c", "command": "echo c"},
            ],
        )
        try:
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
                mock_run.side_effect = [_success("a"), _success("c")]
                result = run_pipeline(load_pipeline(path))

            assert result.status == "SUCCESS"
            assert result.steps[1].status == "SKIPPED"
            assert result.steps[2].status == "SUCCESS"
            # Pipeline did not abort
        finally:
            shutil.rmtree(str(path.parent), ignore_errors=True)

    def test_invalid_when_expression_is_safe_skip(self):
        """Invalid expression → safely treated as False (no crash)."""
        path = _write_temp_pipeline(
            "invalid-when",
            [
                {"name": "bad", "command": "echo bad", "when": "this is not valid python syntax !!!"},
            ],
        )
        try:
            with patch("kiva_cli.core.pipeline_runner._run_step") as mock_run:
                result = run_pipeline(load_pipeline(path))

            assert result.steps[0].status == "SKIPPED"
            assert "condition not met" in result.steps[0].skip_reason
            mock_run.assert_not_called()
        finally:
            shutil.rmtree(str(path.parent), ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
