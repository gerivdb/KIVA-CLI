"""Pytest fixtures and configuration."""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_workspace() -> Generator[Path, None, None]:
    """Create temporary workspace directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kiva_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_deployments_dir(tmp_path) -> Path:
    """Create temporary deployments directory."""
    d = tmp_path / "deployments"
    d.mkdir()
    return d


@pytest.fixture
def mock_ecos_cli(monkeypatch):
    """Mock ECOS CLI subprocess calls."""
    import subprocess
    import json
    
    def mock_run(*args, **kwargs):
        """Mock subprocess.run for ECOS CLI."""
        cmd = args[0] if args else kwargs.get("args", [])
        
        if "--version" in cmd:
            # ECOS CLI version check
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="ecos-cli 1.0.0",
                stderr="",
            )
        elif "gateway" in cmd and "delegate" in cmd:
            # Gateway delegation
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=json.dumps({"intent_hash": "0xMOCK_INTENT_HASH"}),
                stderr="",
            )
        else:
            # Unknown command
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr="Unknown command",
            )
    
    monkeypatch.setattr(subprocess, "run", mock_run)
