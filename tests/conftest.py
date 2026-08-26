import sys
import tempfile
import shutil
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_workspace():
    """Create temporary workspace."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kiva_cli_test_"))
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_deployments_dir():
    """Create temporary deployments directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kiva_deployments_"))
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_ecos_cli():
    """Mock ECOS-CLI for tests that don't need real subprocess."""
    class MockEcosCli:
        def status(self):
            return {"status": "ok", "repos": []}
        def health(self):
            return {"healthy": True}
    return MockEcosCli()
