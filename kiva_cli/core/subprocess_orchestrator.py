"""
Subprocess Mock Orchestrator (PRD-KIVA-005)

Centralized subprocess mocking for KIVA-CLI. Supports:
- RECORD: Execute real subprocess calls and save fixtures
- REPLAY: Replay saved fixtures deterministically
- FAILURE: Inject controlled failures
- PASSTHROUGH: Real execution (debug mode)

Usage:
    orchestrator = SubprocessMockOrchestrator(mode="replay")
    result = orchestrator.run(["docker", "build", "-t", "demo", "."])
    assert result.returncode == 0

Pytest fixture:
    @pytest.fixture
    def mock_subprocess(tmp_path):
        yield SubprocessMockOrchestrator(mode="replay", fixture_dir=tmp_path / "fixtures")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from kiva_cli.core.types import ValidationState

logger = logging.getLogger(__name__)


class MockMode(str, Enum):
    """Orchestrator operating modes."""
    RECORD = "record"
    REPLAY = "replay"
    FAILURE = "failure"
    PASSTHROUGH = "passthrough"


@dataclass
class MockedCommand:
    """Represents a recorded or expected subprocess command."""
    command: List[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "env": self.env,
            "cwd": self.cwd,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MockedCommand":
        return cls(
            command=data["command"],
            returncode=data.get("returncode", 0),
            stdout=data.get("stdout", ""),
            stderr=data.get("stderr", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
            env=data.get("env"),
            cwd=data.get("cwd"),
        )

    @property
    def key(self) -> str:
        """Generate a unique key for this command (for fixture lookup)."""
        cmd_str = " ".join(self.command)
        return hashlib.sha256(cmd_str.encode()).hexdigest()[:16]


@dataclass
class MockResult:
    """Result returned by the orchestrator (mimics subprocess.CompletedProcess)."""
    args: List[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class SubprocessMockOrchestrator:
    """
    Centralized subprocess mock orchestrator for KIVA-CLI.

    Modes:
        RECORD:    Execute real subprocess, save fixture, return result
        REPLAY:    Load fixture, return recorded result (deterministic)
        FAILURE:   Return a controlled failure (for testing error paths)
        PASSTHROUGH: Execute real subprocess, don't save
    """

    def __init__(
        self,
        mode: Union[str, MockMode] = MockMode.REPLAY,
        fixture_dir: Union[str, Path] = "tests/fixtures/subprocess",
        fail_returncode: int = 1,
        fail_stderr: str = "Mocked failure injected by SubprocessMockOrchestrator",
    ):
        self.mode = MockMode(mode) if isinstance(mode, str) else mode
        self.fixture_dir = Path(fixture_dir)
        self.fail_returncode = fail_returncode
        self.fail_stderr = fail_stderr
        self._recorded: List[MockedCommand] = []
        self._replay_index: int = 0

        if self.mode == MockMode.REPLAY:
            self._load_fixtures()

    def _load_fixtures(self) -> None:
        """Load all fixture files from the fixture directory."""
        if not self.fixture_dir.exists():
            logger.warning(f"Fixture directory not found: {self.fixture_dir}")
            return
        for fixture_file in sorted(self.fixture_dir.glob("*.json")):
            try:
                data = json.loads(fixture_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._recorded.extend(MockedCommand.from_dict(d) for d in data)
                elif isinstance(data, dict):
                    self._recorded.append(MockedCommand.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load fixture {fixture_file}: {e}")

    def _save_fixture(self, cmd: MockedCommand) -> None:
        """Save a recorded command to the fixture directory."""
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        fixture_file = self.fixture_dir / f"{cmd.key}.json"
        fixture_file.write_text(
            json.dumps(cmd.to_dict(), indent=2),
            encoding="utf-8",
        )
        logger.debug(f"Saved fixture: {fixture_file}")

    def _find_replay(self, command: List[str]) -> Optional[MockedCommand]:
        """Find a matching recorded command for replay."""
        cmd_key = hashlib.sha256(" ".join(command).encode()).hexdigest()[:16]
        for recorded in self._recorded:
            if recorded.key == cmd_key:
                return recorded
        return None

    def run(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        capture_output: bool = True,
        text: bool = True,
        shell: bool = False,
        **kwargs: Any,
    ) -> MockResult:
        """
        Execute or mock a subprocess command based on the current mode.

        Args:
            command: Command and arguments as a list
            cwd: Working directory
            env: Environment variables
            timeout: Timeout in seconds
            capture_output: Capture stdout/stderr
            text: Return text instead of bytes
            shell: Use shell execution
            **kwargs: Additional arguments passed to subprocess.run

        Returns:
            MockResult with returncode, stdout, stderr
        """
        if self.mode == MockMode.PASSTHROUGH:
            return self._real_run(command, cwd=cwd, env=env, timeout=timeout,
                                  capture_output=capture_output, text=text,
                                  shell=shell, **kwargs)

        if self.mode == MockMode.RECORD:
            return self._record(command, cwd=cwd, env=env, timeout=timeout,
                                capture_output=capture_output, text=text,
                                shell=shell, **kwargs)

        if self.mode == MockMode.REPLAY:
            return self._replay(command)

        if self.mode == MockMode.FAILURE:
            return self._inject_failure(command)

        # Fallback to passthrough
        return self._real_run(command, cwd=cwd, env=env, timeout=timeout,
                              capture_output=capture_output, text=text,
                              shell=shell, **kwargs)

    def _real_run(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        capture_output: bool = True,
        text: bool = True,
        shell: bool = False,
        **kwargs: Any,
    ) -> MockResult:
        """Execute a real subprocess call."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                timeout=timeout,
                capture_output=capture_output,
                text=text,
                shell=shell,
                **kwargs,
            )
            return MockResult(
                args=command,
                returncode=result.returncode,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
            )
        except subprocess.TimeoutExpired:
            return MockResult(
                args=command,
                returncode=124,
                stdout="",
                stderr=f"Command timed out after {timeout}s",
            )
        except FileNotFoundError:
            return MockResult(
                args=command,
                returncode=127,
                stdout="",
                stderr=f"Command not found: {command[0]}",
            )
        except Exception as e:
            return MockResult(
                args=command,
                returncode=1,
                stdout="",
                stderr=str(e),
            )

    def _record(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        capture_output: bool = True,
        text: bool = True,
        shell: bool = False,
        **kwargs: Any,
    ) -> MockResult:
        """Execute real call and save the result as a fixture."""
        start = time.time()
        result = self._real_run(command, cwd=cwd, env=env, timeout=timeout,
                                capture_output=capture_output, text=text,
                                shell=shell, **kwargs)
        duration = time.time() - start

        recorded = MockedCommand(
            command=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_seconds=round(duration, 3),
            env=env,
            cwd=cwd,
        )
        self._save_fixture(recorded)
        self._recorded.append(recorded)
        return result

    def _replay(self, command: List[str]) -> MockResult:
        """Replay a previously recorded command."""
        recorded = self._find_replay(command)
        if recorded is not None:
            logger.debug(f"Replaying: {' '.join(command)}")
            return MockResult(
                args=command,
                returncode=recorded.returncode,
                stdout=recorded.stdout,
                stderr=recorded.stderr,
            )

        # No fixture found — return a helpful error
        logger.warning(f"No fixture found for: {' '.join(command)}")
        return MockResult(
            args=command,
            returncode=127,
            stdout="",
            stderr=f"No fixture found for: {' '.join(command)}",
        )

    def _inject_failure(self, command: List[str]) -> MockResult:
        """Inject a controlled failure."""
        logger.debug(f"Injecting failure for: {' '.join(command)}")
        return MockResult(
            args=command,
            returncode=self.fail_returncode,
            stdout="",
            stderr=self.fail_stderr,
        )

    def get_recorded_commands(self) -> List[MockedCommand]:
        """Return all recorded/replayed commands."""
        return list(self._recorded)

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the orchestrator state."""
        return {
            "mode": self.mode.value,
            "fixture_dir": str(self.fixture_dir),
            "recorded_count": len(self._recorded),
            "commands": [" ".join(c.command) for c in self._recorded],
        }
