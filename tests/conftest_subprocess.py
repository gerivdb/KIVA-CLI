"""
Pytest fixtures for Subprocess Mock Orchestrator (PRD-KIVA-005).

Usage in tests:

    def test_deploy(mock_subprocess):
        result = mock_subprocess.run(["docker", "build", "-t", "demo", "."])
        assert result.returncode == 0
"""

from __future__ import annotations

import pytest

from kiva_cli.core.subprocess_orchestrator import MockMode, SubprocessMockOrchestrator


@pytest.fixture
def mock_subprocess(tmp_path):
    """
    Provides a SubprocessMockOrchestrator in REPLAY mode with
    fixtures stored in a temporary directory.
    """
    fixture_dir = tmp_path / "subprocess_fixtures"
    orchestrator = SubprocessMockOrchestrator(
        mode=MockMode.REPLAY,
        fixture_dir=fixture_dir,
    )
    yield orchestrator


@pytest.fixture
def mock_subprocess_record(tmp_path):
    """
    Provides a SubprocessMockOrchestrator in RECORD mode.
    """
    fixture_dir = tmp_path / "subprocess_fixtures"
    orchestrator = SubprocessMockOrchestrator(
        mode=MockMode.RECORD,
        fixture_dir=fixture_dir,
    )
    yield orchestrator


@pytest.fixture
def mock_subprocess_failure(tmp_path):
    """
    Provides a SubprocessMockOrchestrator in FAILURE mode.
    """
    fixture_dir = tmp_path / "subprocess_fixtures"
    orchestrator = SubprocessMockOrchestrator(
        mode=MockMode.FAILURE,
        fixture_dir=fixture_dir,
    )
    yield orchestrator


@pytest.fixture
def mock_subprocess_passthrough(tmp_path):
    """
    Provides a SubprocessMockOrchestrator in PASSTHROUGH mode.
    """
    fixture_dir = tmp_path / "subprocess_fixtures"
    orchestrator = SubprocessMockOrchestrator(
        mode=MockMode.PASSTHROUGH,
        fixture_dir=fixture_dir,
    )
    yield orchestrator
