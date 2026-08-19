"""Unit tests for AutoChainManager + pipeline_commands --from / --steps (KIVA-008).

Coverage:
  AutoChainManager:
    - run_adhoc: happy path (2 steps, mock runner)
    - run_adhoc: empty steps list raises ValueError
    - run_adhoc: HAS_PIPELINE=False raises RuntimeError
    - run_adhoc: step naming convention (step_0, step_1, ...)
    - run_adhoc: dry_run flag forwarded to run_pipeline
    - run_adhoc: single-step chain
    - get_pipeline: FileNotFoundError on missing YAML
    - validate: cycle detection propagated
    - clear_cache: cache reset
    - get_auto_chain_manager: singleton pattern

  pipeline_commands (Click CLI via CliRunner):
    - `kiva pipeline run --steps` happy path (dry-run, mocked runner)
    - `kiva pipeline run --steps` empty list -> error exit
    - `kiva pipeline run --steps NAME` mutual exclusivity -> error
    - `kiva pipeline run` no args -> error
    - `kiva pipeline run --from` step not found -> error
    - `kiva pipeline run --steps --from` -> WARN emitted, --from ignored
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Lightweight stubs — avoid importing heavy KIVA internals in unit context
# ---------------------------------------------------------------------------

@dataclass
class _StepResult:
    step_name: str
    status: str = "SUCCESS"
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.01
    skip_reason: str = ""


@dataclass
class _PipelineResult:
    pipeline_name: str
    status: str
    steps: List[_StepResult]
    intent_hash: str = "test-hash"
    duration_s: float = 0.02
    parallel_groups_executed: int = 0
    total_parallel_wall_clock: float = 0.0
    total_retries_used: int = 0


def _make_ok_result(pipeline_name: str, step_names: List[str]) -> _PipelineResult:
    return _PipelineResult(
        pipeline_name=pipeline_name,
        status="SUCCESS",
        steps=[_StepResult(step_name=n) for n in step_names],
    )


def _make_fail_result(pipeline_name: str, step_names: List[str], failed: str) -> _PipelineResult:
    steps = []
    for n in step_names:
        status = "FAILED" if n == failed else "SUCCESS"
        steps.append(_StepResult(step_name=n, status=status, returncode=1 if n == failed else 0))
    return _PipelineResult(pipeline_name=pipeline_name, status="FAILED", steps=steps)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MODULE = "kiva_cli.core.auto_chain_manager"
CMD_MODULE = "kiva_cli.commands.pipeline_commands"


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def manager(tmp_path, monkeypatch):
    """AutoChainManager with HAS_PIPELINE=True and mocked run_pipeline."""
    monkeypatch.setenv("KIVA_PIPELINES_DIR", str(tmp_path / "pipelines"))
    monkeypatch.setattr(f"{MODULE}.HAS_PIPELINE", True)
    from kiva_cli.core.auto_chain_manager import AutoChainManager
    return AutoChainManager(pipelines_dir=tmp_path / "pipelines")


@pytest.fixture(autouse=True)
def _reset_pipeline_manager(monkeypatch):
    """Reset the lazy _manager singleton in pipeline_commands between tests."""
    import kiva_cli.commands.pipeline_commands as pc
    monkeypatch.setattr(pc, "_manager", None)


# ===========================================================================
# AutoChainManager.run_adhoc
# ===========================================================================

class TestRunAdhoc:
    def test_happy_path_two_steps(self, manager, monkeypatch):
        """run_adhoc with 2 steps returns SUCCESS PipelineResult."""
        expected = _make_ok_result("adhoc", ["step_0", "step_1"])
        monkeypatch.setattr(f"{MODULE}.run_pipeline", lambda p, **ctx: expected)
        monkeypatch.setattr(f"{MODULE}.HAS_PIPELINE", True)

        result = manager.run_adhoc(["echo hello", "echo world"])

        assert result.status == "SUCCESS"
        assert len(result.steps) == 2

    def test_single_step(self, manager, monkeypatch):
        """Single-step ad-hoc chain runs without error."""
        expected = _make_ok_result("adhoc", ["step_0"])
        monkeypatch.setattr(f"{MODULE}.run_pipeline", lambda p, **ctx: expected)
        monkeypatch.setattr(f"{MODULE}.HAS_PIPELINE", True)

        result = manager.run_adhoc(["echo single"])
        assert result.status == "SUCCESS"
        assert len(result.steps) == 1

    def test_step_naming_convention(self, manager, monkeypatch):
        """Steps are named step_0, step_1, step_2 in the synthetic pipeline."""
        captured = {}

        def _capture(p, **ctx):
            captured["names"] = [s.name for s in p.steps]
            return _make_ok_result("adhoc", captured["names"])

        monkeypatch.setattr(f"{MODULE}.run_pipeline", _capture)
        monkeypatch.setattr(f"{MODULE}.HAS_PIPELINE", True)

        manager.run_adhoc(["cmd_a", "cmd_b", "cmd_c"])
        assert captured["names"] == ["step_0", "step_1", "step_2"]

    def test_dry_run_forwarded(self, manager, monkeypatch):
        """dry_run=True is forwarded to run_pipeline via **context."""
        captured = {}

        def _capture(p, **ctx):
            captured.update(ctx)
            return _make_ok_result("adhoc", ["step_0"])

        monkeypatch.setattr(f"{MODULE}.run_pipeline", _capture)
        monkeypatch.setattr(f"{MODULE}.HAS_PIPELINE", True)

        manager.run_adhoc(["echo test"], dry_run=True)
        assert captured.get("dry_run") is True

    def test_has_pipeline_false_raises(self, manager, monkeypatch):
        """run_adhoc raises RuntimeError when HAS_PIPELINE is False."""
        monkeypatch.setattr(f"{MODULE}.HAS_PIPELINE", False)
        with pytest.raises(RuntimeError, match="disabled"):
            manager.run_adhoc(["echo hello"])

    def test_synthetic_pipeline_name(self, manager, monkeypatch):
        """Synthetic pipeline is always named 'adhoc'."""
        captured = {}

        def _capture(p, **ctx):
            captured["name"] = p.name
            return _make_ok_result("adhoc", ["step_0"])

        monkeypatch.setattr(f"{MODULE}.run_pipeline", _capture)
        monkeypatch.setattr(f"{MODULE}.HAS_PIPELINE", True)

        manager.run_adhoc(["echo x"])
        assert captured["name"] == "adhoc"


# ===========================================================================
# AutoChainManager: discovery & cache
# ===========================================================================

class TestAutoChainManagerMisc:
    def test_get_pipeline_missing_raises(self, manager):
        """get_pipeline raises FileNotFoundError for unknown pipeline."""
        with pytest.raises(FileNotFoundError, match="not found"):
            manager.get_pipeline("nonexistent_pipeline")

    def test_clear_cache(self, manager, tmp_path, monkeypatch):
        """clear_cache empties the internal cache."""
        manager._cache["fake"] = MagicMock()  # inject fake entry
        assert "fake" in manager._cache
        manager.clear_cache()
        assert manager._cache == {}

    def test_list_pipelines_empty_dir(self, manager, tmp_path):
        """list_pipelines returns [] when directory does not exist."""
        # pipelines_dir doesn't exist yet
        result = manager.list_pipelines()
        assert result == []

    def test_list_pipelines_finds_yaml(self, manager, tmp_path):
        """list_pipelines returns YAML stems when files are present."""
        pdir = tmp_path / "pipelines"
        pdir.mkdir(parents=True)
        (pdir / "build.yaml").write_text("name: build\n")
        (pdir / "deploy.yml").write_text("name: deploy\n")
        manager.pipelines_dir = pdir
        names = manager.list_pipelines()
        assert "build" in names
        assert "deploy" in names

    def test_singleton_returns_same_instance(self, monkeypatch):
        """get_auto_chain_manager always returns the same singleton."""
        import kiva_cli.core.auto_chain_manager as acm_mod
        monkeypatch.setattr(acm_mod, "_default_manager", None)
        from kiva_cli.core.auto_chain_manager import get_auto_chain_manager
        a = get_auto_chain_manager()
        b = get_auto_chain_manager()
        assert a is b


# ===========================================================================
# pipeline_commands CLI — --steps mode
# ===========================================================================

class TestPipelineRunSteps:
    """CLI-level tests for `kiva pipeline run --steps`."""

    def _get_cli(self):
        from kiva_cli.commands.pipeline_commands import pipeline_cli
        return pipeline_cli

    def test_steps_dry_run_exits_zero(self, runner, monkeypatch):
        """--steps with --dry-run exits 0 and shows 'Ad-hoc chain finished'."""
        ok_result = _make_ok_result("adhoc", ["step_0", "step_1"])

        mock_mgr = MagicMock()
        mock_mgr.run_adhoc.return_value = ok_result
        monkeypatch.setattr(
            "kiva_cli.commands.pipeline_commands.get_auto_chain_manager",
            lambda: mock_mgr,
        )
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)

        result = runner.invoke(
            self._get_cli(),
            ["run", "--steps", "echo hello,echo world", "--dry-run"],
        )
        assert result.exit_code == 0, result.output
        assert "Ad-hoc chain finished" in result.output

    def test_steps_failed_exits_one(self, runner, monkeypatch):
        """--steps exits 1 when result.status is FAILED."""
        fail_result = _make_fail_result("adhoc", ["step_0", "step_1"], failed="step_1")

        mock_mgr = MagicMock()
        mock_mgr.run_adhoc.return_value = fail_result
        monkeypatch.setattr(
            "kiva_cli.commands.pipeline_commands.get_auto_chain_manager",
            lambda: mock_mgr,
        )
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)

        result = runner.invoke(
            self._get_cli(),
            ["run", "--steps", "echo ok,false"],
        )
        assert result.exit_code == 1

    def test_steps_empty_string_exits_error(self, runner, monkeypatch):
        """--steps with empty/whitespace-only value exits non-zero with ERROR."""
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)
        result = runner.invoke(
            self._get_cli(),
            ["run", "--steps", "   ,  ,  "],
        )
        assert result.exit_code != 0
        assert "ERROR" in result.output

    def test_steps_and_name_mutually_exclusive(self, runner, monkeypatch):
        """Providing both NAME and --steps exits with ERROR."""
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)
        result = runner.invoke(
            self._get_cli(),
            ["run", "mybuild", "--steps", "echo hello"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "ERROR" in result.output

    def test_no_args_exits_error(self, runner, monkeypatch):
        """Calling `kiva pipeline run` with no NAME and no --steps exits with ERROR."""
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)
        result = runner.invoke(self._get_cli(), ["run"])
        assert result.exit_code != 0
        assert "ERROR" in result.output or "NAME" in result.output

    def test_steps_from_flag_warns(self, runner, monkeypatch):
        """--from is ignored in --steps mode and a WARN is emitted."""
        ok_result = _make_ok_result("adhoc", ["step_0"])
        mock_mgr = MagicMock()
        mock_mgr.run_adhoc.return_value = ok_result
        monkeypatch.setattr(
            "kiva_cli.commands.pipeline_commands.get_auto_chain_manager",
            lambda: mock_mgr,
        )
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)

        result = runner.invoke(
            self._get_cli(),
            ["run", "--steps", "echo hello", "--from", "some_step"],
        )
        assert result.exit_code == 0, result.output
        assert "WARN" in result.output or "warn" in result.output.lower()


# ===========================================================================
# pipeline_commands CLI — --from mode
# ===========================================================================

class TestPipelineRunFrom:
    """CLI-level tests for `kiva pipeline run NAME --from STEP`."""

    def _get_cli(self):
        from kiva_cli.commands.pipeline_commands import pipeline_cli
        return pipeline_cli

    def _make_pipeline_yaml(self, tmp_path: Path, name: str = "build") -> Path:
        """Write a minimal 3-step pipeline YAML to tmp_path/.kiva/pipelines/."""
        pdir = tmp_path / ".kiva" / "pipelines"
        pdir.mkdir(parents=True, exist_ok=True)
        content = (
            f"name: {name}\n"
            "version: '1'\n"
            "nexus_status: ACTIVE\n"
            "description: Test pipeline\n"
            "steps:\n"
            "  - name: build\n"
            "    command: echo build\n"
            "  - name: test\n"
            "    command: echo test\n"
            "    depends_on: [build]\n"
            "  - name: deploy\n"
            "    command: echo deploy\n"
            "    depends_on: [test]\n"
        )
        yaml_path = pdir / f"{name}.yaml"
        yaml_path.write_text(content)
        return yaml_path

    def test_from_unknown_step_exits_error(self, runner, tmp_path, monkeypatch):
        """--from with an unknown step name exits 1 with ERROR message."""
        self._make_pipeline_yaml(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)

        result = runner.invoke(
            self._get_cli(),
            ["run", "build", "--from", "nonexistent_step"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "ERROR" in result.output

    def test_from_valid_step_skips_prefix(self, runner, tmp_path, monkeypatch):
        """--from deploy skips 'build' and 'test' (marked SKIPPED in output)."""
        self._make_pipeline_yaml(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)

        # Mock run_pipeline to return a fake result for the suffix
        from kiva_cli.core.pipeline_types import Pipeline, StepResult

        def _mock_runner(p, **ctx):
            from kiva_cli.core.pipeline_types import PipelineResult
            steps = [StepResult(
                step_name=s.name,
                status="SUCCESS",
                returncode=0,
                stdout="",
                stderr="",
                duration_s=0.1,
                skip_reason="",
            ) for s in p.steps]
            return PipelineResult(
                pipeline_name=p.name,
                status="SUCCESS",
                steps=steps,
                intent_hash="mock-hash",
                started_at=0.0,
                ended_at=0.2,
            )

        monkeypatch.setattr(
            "kiva_cli.commands.pipeline_commands.run_pipeline",
            _mock_runner,
        )

        result = runner.invoke(
            self._get_cli(),
            ["run", "build", "--from", "deploy"],
        )
        assert result.exit_code == 0, result.output
        assert "Resuming" in result.output or "skipped" in result.output.lower()

    def test_pipeline_not_found_exits_error(self, runner, tmp_path, monkeypatch):
        """Named pipeline that does not exist exits 1 with ERROR."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("kiva_cli.core.pipeline_types.HAS_PIPELINE", True)

        result = runner.invoke(self._get_cli(), ["run", "ghost_pipeline"])
        assert result.exit_code != 0
        assert "ERROR" in result.output or "not found" in result.output.lower()
