"""
Tests for Subprocess Mock Orchestrator (PRD-KIVA-005).

Validates:
- MockedCommand serialization/deserialization
- RECORD mode: executes and saves fixtures
- REPLAY mode: replays saved fixtures deterministically
- FAILURE mode: injects controlled failures
- PASSTHROUGH mode: real execution
- Fixture file I/O
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kiva_cli.core.subprocess_orchestrator import (
    MockedCommand,
    MockMode,
    MockResult,
    SubprocessMockOrchestrator,
)


class TestMockedCommand:
    """Tests for the MockedCommand dataclass."""

    def test_to_dict(self):
        cmd = MockedCommand(
            command=["docker", "build", "-t", "demo", "."],
            returncode=0,
            stdout="Successfully built",
            stderr="",
            duration_seconds=1.5,
        )
        d = cmd.to_dict()
        assert d["command"] == ["docker", "build", "-t", "demo", "."]
        assert d["returncode"] == 0
        assert d["stdout"] == "Successfully built"
        assert d["duration_seconds"] == 1.5

    def test_from_dict(self):
        data = {
            "command": ["git", "push"],
            "returncode": 0,
            "stdout": "Everything up-to-date",
            "stderr": "",
            "duration_seconds": 0.5,
        }
        cmd = MockedCommand.from_dict(data)
        assert cmd.command == ["git", "push"]
        assert cmd.returncode == 0
        assert cmd.stdout == "Everything up-to-date"

    def test_key_consistency(self):
        cmd1 = MockedCommand(command=["docker", "build", "."])
        cmd2 = MockedCommand(command=["docker", "build", "."])
        assert cmd1.key == cmd2.key

    def test_key_uniqueness(self):
        cmd1 = MockedCommand(command=["docker", "build", "."])
        cmd2 = MockedCommand(command=["docker", "run", "."])
        assert cmd1.key != cmd2.key


class TestMockResult:
    """Tests for the MockResult dataclass."""

    def test_ok_property(self):
        result = MockResult(args=["echo", "hello"], returncode=0)
        assert result.ok is True

        result_fail = MockResult(args=["false"], returncode=1)
        assert result_fail.ok is False

    def test_default_values(self):
        result = MockResult(args=["echo"], returncode=0)
        assert result.stdout == ""
        assert result.stderr == ""


class TestSubprocessMockOrchestratorRecord:
    """Tests for RECORD mode."""

    def test_record_saves_fixture(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        orch = SubprocessMockOrchestrator(
            mode=MockMode.RECORD,
            fixture_dir=fixture_dir,
        )
        result = orch.run(["python", "-c", "print('hello')"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "hello" in result.stdout

        # Check fixture was saved
        fixtures = list(fixture_dir.glob("*.json"))
        assert len(fixtures) == 1

        saved = json.loads(fixtures[0].read_text())
        assert saved["command"] == ["python", "-c", "print('hello')"]
        assert saved["returncode"] == 0

    def test_record_tracks_commands(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        orch = SubprocessMockOrchestrator(
            mode=MockMode.RECORD,
            fixture_dir=fixture_dir,
        )
        orch.run(["python", "-c", "print('first')"], capture_output=True, text=True)
        orch.run(["python", "-c", "print('second')"], capture_output=True, text=True)

        recorded = orch.get_recorded_commands()
        assert len(recorded) == 2
        assert recorded[0].command == ["python", "-c", "print('first')"]
        assert recorded[1].command == ["python", "-c", "print('second')"]


class TestSubprocessMockOrchestratorReplay:
    """Tests for REPLAY mode."""

    def test_replay_returns_recorded_result(self, tmp_path):
        # First, record
        fixture_dir = tmp_path / "fixtures"
        recorder = SubprocessMockOrchestrator(
            mode=MockMode.RECORD,
            fixture_dir=fixture_dir,
        )
        recorder.run(["python", "-c", "print('recorded')"], capture_output=True, text=True)

        # Then, replay
        player = SubprocessMockOrchestrator(
            mode=MockMode.REPLAY,
            fixture_dir=fixture_dir,
        )
        result = player.run(["python", "-c", "print('recorded')"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "recorded" in result.stdout

    def test_replay_missing_fixture(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        fixture_dir.mkdir(parents=True, exist_ok=True)

        orch = SubprocessMockOrchestrator(
            mode=MockMode.REPLAY,
            fixture_dir=fixture_dir,
        )
        result = orch.run(["nonexistent_binary_xyz"])
        assert result.returncode == 127
        assert "No fixture found" in result.stderr

    def test_replay_is_deterministic(self, tmp_path):
        # Record once
        fixture_dir = tmp_path / "fixtures"
        recorder = SubprocessMockOrchestrator(
            mode=MockMode.RECORD,
            fixture_dir=fixture_dir,
        )
        recorder.run(["python", "-c", "print('deterministic')"], capture_output=True, text=True)

        # Replay multiple times
        for _ in range(3):
            player = SubprocessMockOrchestrator(
                mode=MockMode.REPLAY,
                fixture_dir=fixture_dir,
            )
            result = player.run(["python", "-c", "print('deterministic')"], capture_output=True, text=True)
            assert result.returncode == 0
            assert "deterministic" in result.stdout


class TestSubprocessMockOrchestratorFailure:
    """Tests for FAILURE mode."""

    def test_failure_injects_error(self, tmp_path):
        orch = SubprocessMockOrchestrator(
            mode=MockMode.FAILURE,
            fixture_dir=tmp_path / "fixtures",
        )
        result = orch.run(["docker", "build", "."])
        assert result.returncode == 1
        assert "Mocked failure" in result.stderr

    def test_failure_custom_returncode(self, tmp_path):
        orch = SubprocessMockOrchestrator(
            mode=MockMode.FAILURE,
            fixture_dir=tmp_path / "fixtures",
            fail_returncode=42,
            fail_stderr="Custom error",
        )
        result = orch.run(["kubectl", "apply"])
        assert result.returncode == 42
        assert result.stderr == "Custom error"


class TestSubprocessMockOrchestratorPassthrough:
    """Tests for PASSTHROUGH mode."""

    def test_passthrough_executes_real(self, tmp_path):
        orch = SubprocessMockOrchestrator(
            mode=MockMode.PASSTHROUGH,
            fixture_dir=tmp_path / "fixtures",
        )
        result = orch.run(["python", "-c", "print('real')"], capture_output=True, text=True)
        assert result.returncode == 0
        assert "real" in result.stdout

    def test_passthrough_no_fixture_saved(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        orch = SubprocessMockOrchestrator(
            mode=MockMode.PASSTHROUGH,
            fixture_dir=fixture_dir,
        )
        orch.run(["echo", "no-save"], capture_output=True, text=True)
        assert not fixture_dir.exists() or len(list(fixture_dir.glob("*.json"))) == 0


class TestSubprocessMockOrchestratorSummary:
    """Tests for the summary method."""

    def test_summary_record(self, tmp_path):
        fixture_dir = tmp_path / "fixtures"
        orch = SubprocessMockOrchestrator(
            mode=MockMode.RECORD,
            fixture_dir=fixture_dir,
        )
        orch.run(["echo", "test"], capture_output=True, text=True)

        summary = orch.summary()
        assert summary["mode"] == "record"
        assert summary["recorded_count"] == 1
        assert "echo test" in summary["commands"]

    def test_summary_replay(self, tmp_path):
        # Record first
        fixture_dir = tmp_path / "fixtures"
        recorder = SubprocessMockOrchestrator(
            mode=MockMode.RECORD,
            fixture_dir=fixture_dir,
        )
        recorder.run(["echo", "test"], capture_output=True, text=True)

        # Replay and check summary
        player = SubprocessMockOrchestrator(
            mode=MockMode.REPLAY,
            fixture_dir=fixture_dir,
        )
        summary = player.summary()
        assert summary["mode"] == "replay"
        assert summary["recorded_count"] == 1


class TestSubprocessMockOrchestratorEdgeCases:
    """Edge case tests."""

    def test_timeout_handling(self, tmp_path):
        orch = SubprocessMockOrchestrator(
            mode=MockMode.PASSTHROUGH,
            fixture_dir=tmp_path / "fixtures",
        )
        result = orch.run(
            ["python", "-c", "import time; time.sleep(10)"],
            timeout=0.5,
        )
        assert result.returncode != 0  # Should fail (timeout or other error)
        assert "timed out" in result.stderr or result.returncode != 0

    def test_command_not_found(self, tmp_path):
        orch = SubprocessMockOrchestrator(
            mode=MockMode.PASSTHROUGH,
            fixture_dir=tmp_path / "fixtures",
        )
        result = orch.run(["nonexistent_binary_xyz"])
        assert result.returncode == 127
        assert "not found" in result.stderr.lower() or "not found" in result.stderr

    def test_mode_from_string(self, tmp_path):
        orch = SubprocessMockOrchestrator(
            mode="replay",
            fixture_dir=tmp_path / "fixtures",
        )
        assert orch.mode == MockMode.REPLAY
