"""Tests for epic_commands.py — EPIC-centric CLI coverage.

Covers helper classes and Click commands:
- OntologyClient, Sco7Client, ContextManager, ResourceDiscovery, KivaEpicMode
- setup_epic, epic_status, clear_epic, list_epics
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from kiva_cli.commands.epic_commands import (
    epic_cli,
    setup_epic,
    epic_status,
    clear_epic,
    list_epics,
    OntologyClient,
    Sco7Client,
    ContextManager,
    ResourceDiscovery,
    KivaEpicMode,
    EpicMetadata,
    GovernanceStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_ontology():
    client = MagicMock(spec=OntologyClient)
    client.get_epic_metadata.return_value = EpicMetadata(
        epic_id="EPIC_TEST",
        title="Test Epic",
        intent="test intent",
        status="ACTIVE",
        category="test",
        verses=["v1", "v2"],
        modules=["mod1", "mod2"],
        intent_hash="0xTEST",
    )
    client.get_categories.return_value = {
        "test": {"epics": ["EPIC_TEST"]}
    }
    return client


@pytest.fixture
def mock_sco7():
    client = MagicMock(spec=Sco7Client)
    client.check_governance.return_value = GovernanceStatus(
        compliant=True,
        warnings=[],
        recommendations=[],
    )
    return client


# ---------------------------------------------------------------------------
# Dataclass helpers
# ---------------------------------------------------------------------------

class TestDataclasses:
    def test_epic_metadata_defaults(self):
        m = EpicMetadata(
            epic_id="E1", title="T", intent="I", status="S",
            category="C", verses=[], modules=[], intent_hash="0x",
        )
        assert m.epic_id == "E1"
        assert m.verses == []
        assert m.modules == []

    def test_governance_status_defaults(self):
        g = GovernanceStatus(compliant=False, warnings=[], recommendations=[])
        assert g.compliant is False
        assert g.warnings == []


# ---------------------------------------------------------------------------
# OntologyClient
# ---------------------------------------------------------------------------

class TestOntologyClient:
    def test_get_epic_metadata_success(self, mock_ontology):
        meta = mock_ontology.get_epic_metadata("EPIC_TEST")
        assert meta.epic_id == "EPIC_TEST"
        assert meta.title == "Test Epic"

    def test_get_epic_metadata_request_exception(self):
        import requests
        client = OntologyClient.__new__(OntologyClient)
        client.base_url = "http://localhost:8080"
        client.session = MagicMock()
        client.session.get.side_effect = requests.RequestException("boom")
        assert client.get_epic_metadata("E1") is None

    def test_get_categories_request_exception(self):
        import requests
        client = OntologyClient.__new__(OntologyClient)
        client.base_url = "http://localhost:8080"
        client.session = MagicMock()
        client.session.get.side_effect = requests.RequestException("boom")
        assert client.get_categories() == {}


# ---------------------------------------------------------------------------
# Sco7Client
# ---------------------------------------------------------------------------

class TestSco7Client:
    def test_check_governance_success(self, mock_sco7):
        g = mock_sco7.check_governance("EPIC_TEST")
        assert g.compliant is True

    def test_check_governance_unavailable(self):
        import requests
        client = Sco7Client.__new__(Sco7Client)
        client.base_url = "http://localhost:8081"
        client.session = MagicMock()
        client.session.get.side_effect = requests.RequestException("boom")
        g = client.check_governance("E1")
        assert g.compliant is False
        assert "unavailable" in g.warnings[0]


# ---------------------------------------------------------------------------
# ContextManager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_set_and_get_epic_context(self, monkeypatch):
        cm = ContextManager.__new__(ContextManager)
        cm.context_file = Path("/tmp/test_kiva_epic_context")
        cm.env_var = "TEST_KIVA_EPIC_CONTEXT"
        cm.set_epic_context("EPIC_TEST")
        assert cm.get_epic_context() == "EPIC_TEST"
        cm.clear_epic_context()

    def test_clear_epic_context(self, monkeypatch):
        cm = ContextManager.__new__(ContextManager)
        cm.context_file = Path("/tmp/test_kiva_epic_context_clear")
        cm.env_var = "TEST_KIVA_EPIC_CONTEXT_CLEAR"
        cm.set_epic_context("EPIC_TEST")
        cm.clear_epic_context()
        assert cm.get_epic_context() is None


# ---------------------------------------------------------------------------
# ResourceDiscovery (unit, no filesystem needed for _find_module_files)
# ---------------------------------------------------------------------------

class TestResourceDiscovery:
    def test_find_module_files(self, tmp_path):
        rd = ResourceDiscovery.__new__(ResourceDiscovery)
        rd.ontology = MagicMock()
        discovered = {"epic_files": [], "prds": [], "tests": [], "modules": [], "docs": []}
        (tmp_path / "mod1.py").write_text("")
        rd._find_module_files(tmp_path, "mod1", discovered)
        assert "mod1.py" in discovered["modules"]


# ---------------------------------------------------------------------------
# KivaEpicMode
# ---------------------------------------------------------------------------

class TestKivaEpicMode:
    def test_setup_workspace_success(self, mock_ontology, mock_sco7):
        mode = KivaEpicMode.__new__(KivaEpicMode)
        mode.ontology = mock_ontology
        mode.sco7 = mock_sco7
        mode.context = MagicMock()
        mode.discovery = MagicMock()
        mode.discovery.discover_files.return_value = {
            "epic_files": [], "prds": [], "tests": [], "modules": [], "docs": []
        }

        result = mode.setup_workspace("EPIC_TEST", interactive=False)
        assert result["metadata"] is not None
        assert result["governance"] is not None
        assert result["errors"] == []


# ---------------------------------------------------------------------------
# Click commands
# ---------------------------------------------------------------------------

class TestEpicCommands:
    def test_setup_epic_success(self, runner, mock_ontology, mock_sco7):
        with patch("kiva_cli.commands.epic_commands.OntologyClient", return_value=mock_ontology):
            with patch("kiva_cli.commands.epic_commands.Sco7Client", return_value=mock_sco7):
                with patch("kiva_cli.commands.epic_commands.ContextManager") as MockCtx:
                    mock_ctx = MagicMock()
                    mock_ctx.get_epic_context.return_value = None
                    MockCtx.return_value = mock_ctx
                    result = runner.invoke(setup_epic, ["EPIC_TEST", "--no-interactive"])
        assert result.exit_code == 0
        assert "EPIC_TEST" in result.output or "Test Epic" in result.output

    def test_epic_status_no_context(self, runner, monkeypatch):
        cm = ContextManager.__new__(ContextManager)
        cm.context_file = Path("/tmp/test_kiva_epic_status_none")
        cm.env_var = "TEST_KIVA_EPIC_STATUS_NONE"
        monkeypatch.setenv(cm.env_var, "")
        monkeypatch.setattr(Path, "exists", lambda self: False)

        with patch("kiva_cli.commands.epic_commands.ContextManager") as MockCtx:
            mock_ctx = MagicMock()
            mock_ctx.get_epic_context.return_value = None
            MockCtx.return_value = mock_ctx
            result = runner.invoke(epic_status, ["--brief"])
        assert result.exit_code == 0

    def test_clear_epic_no_context(self, runner):
        with patch("kiva_cli.commands.epic_commands.ContextManager") as MockCtx:
            mock_ctx = MagicMock()
            mock_ctx.get_epic_context.return_value = None
            MockCtx.return_value = mock_ctx
            result = runner.invoke(clear_epic)
        assert result.exit_code == 0
        assert "No active" in result.output or "cleared" in result.output

    def test_list_epics_success(self, runner, mock_ontology):
        with patch("kiva_cli.commands.epic_commands.OntologyClient", return_value=mock_ontology):
            result = runner.invoke(list_epics)
        assert result.exit_code == 0

    def test_list_epics_unavailable(self, runner):
        client = MagicMock()
        client.get_categories.return_value = {}
        with patch("kiva_cli.commands.epic_commands.OntologyClient", return_value=client):
            result = runner.invoke(list_epics)
        assert result.exit_code == 0
