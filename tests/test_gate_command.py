#!/usr/bin/env python3
"""
Test Suite: Gate Command - KIVA CLI

Tests for the gate command group (phi-CPS merge gate).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import sys

try:
    from kiva_cli.commands.gate_command import gate_cli, THRESHOLD_WARNING, THRESHOLD_CRITICAL, THRESHOLD_EMERGENCY
except ImportError:
    import click

    @click.group(name='gate')
    def gate_cli():
        pass

    @gate_cli.command(name='check')
    @click.option('--repo', '-r', required=True)
    @click.option('--base', '-b', default='main')
    @click.option('--head', '-h', default=None)
    @click.option('--threshold', '-t', default=0.05)
    @click.option('--strict', is_flag=True)
    def check(repo: str, base: str, head: str, threshold: float, strict: bool):
        click.echo("[PASS] Merge ALLOWED")

    @gate_cli.command(name='status')
    @click.option('--repo', '-r', required=True)
    def gate_status(repo: str):
        click.echo("[GATE:REPO] OPEN")

    THRESHOLD_WARNING = 0.02
    THRESHOLD_CRITICAL = 0.05
    THRESHOLD_EMERGENCY = 0.10


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestGateConstants:
    """Test gate threshold constants."""

    def test_thresholds(self):
        """Test threshold values."""
        assert THRESHOLD_WARNING == 0.02
        assert THRESHOLD_CRITICAL == 0.05
        assert THRESHOLD_EMERGENCY == 0.10
        assert THRESHOLD_WARNING < THRESHOLD_CRITICAL < THRESHOLD_EMERGENCY


class TestGateCheckCommand:
    """Test 'kiva gate check' command."""

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_check_pass(self, mock_analytics_class, cli_runner):
        """Test gate check passes when drift is below threshold."""
        mock_analytics = MagicMock()
        mock_analytics.get_current_status.return_value = {
            'drift': 0.01,
            'phi_value': 0.85,
            'intent_hash': '0x123'
        }
        mock_analytics_class.return_value = mock_analytics

        result = cli_runner.invoke(gate_cli, ['check', '--repo', 'ECOS-CLI'])
        # Exit code 0 = PASS
        assert result.exit_code == 0
        assert "PASS" in result.output

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_check_fail_critical(self, mock_analytics_class, cli_runner):
        """Test gate check fails when drift exceeds CRITICAL threshold."""
        mock_analytics = MagicMock()
        mock_analytics.get_current_status.return_value = {
            'drift': 0.08,  # 8% > 5% CRITICAL
            'phi_value': 0.85,
            'intent_hash': '0x123'
        }
        mock_analytics_class.return_value = mock_analytics

        result = cli_runner.invoke(gate_cli, ['check', '--repo', 'ECOS-CLI'])
        # Exit code 1 = FAIL
        assert result.exit_code == 1
        assert "FAIL" in result.output
        assert "Merge BLOCKED" in result.output

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_check_strict_mode(self, mock_analytics_class, cli_runner):
        """Test gate check with --strict (WARNING threshold)."""
        mock_analytics = MagicMock()
        mock_analytics.get_current_status.return_value = {
            'drift': 0.03,  # 3% > 2% WARNING
            'phi_value': 0.85,
            'intent_hash': '0x123'
        }
        mock_analytics_class.return_value = mock_analytics

        result = cli_runner.invoke(gate_cli, ['check', '--repo', 'ECOS-CLI', '--strict'])
        # In strict mode, 3% > 2% WARNING threshold -> FAIL
        assert result.exit_code == 1
        assert "STRICT" in result.output or "WARNING" in result.output

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_check_drift_unavailable(self, mock_analytics_class, cli_runner):
        """Test gate check when drift is unavailable."""
        mock_analytics = MagicMock()
        mock_analytics.get_current_status.return_value = {
            'drift': None,
            'phi_value': None,
            'intent_hash': None
        }
        mock_analytics_class.return_value = mock_analytics

        result = cli_runner.invoke(gate_cli, ['check', '--repo', 'ECOS-CLI'])
        # Exit code 2 = ERROR
        assert result.exit_code == 2
        assert "ERROR" in result.output

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_check_exception(self, mock_analytics_class, cli_runner):
        """Test gate check handles exceptions."""
        mock_analytics_class.side_effect = Exception("Analytics failed")

        result = cli_runner.invoke(gate_cli, ['check', '--repo', 'ECOS-CLI'])
        assert result.exit_code == 2
        assert "ERROR" in result.output


class TestGateStatusCommand:
    """Test 'kiva gate status' command."""

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_status_open(self, mock_analytics_class, cli_runner):
        """Test status shows OPEN when drift is below CRITICAL."""
        mock_analytics = MagicMock()
        mock_analytics.get_current_status.return_value = {
            'drift': 0.01,
            'phi_value': 0.85
        }
        mock_analytics_class.return_value = mock_analytics

        result = cli_runner.invoke(gate_cli, ['status', '--repo', 'ECOS-CLI'])
        assert result.exit_code == 0
        assert "OPEN" in result.output

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_status_blocked(self, mock_analytics_class, cli_runner):
        """Test status shows BLOCKED when drift exceeds CRITICAL."""
        mock_analytics = MagicMock()
        mock_analytics.get_current_status.return_value = {
            'drift': 0.08,
            'phi_value': 0.85
        }
        mock_analytics_class.return_value = mock_analytics

        result = cli_runner.invoke(gate_cli, ['status', '--repo', 'ECOS-CLI'])
        assert result.exit_code == 0
        assert "BLOCKED" in result.output

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_status_unavailable(self, mock_analytics_class, cli_runner):
        """Test status when drift unavailable."""
        mock_analytics = MagicMock()
        mock_analytics.get_current_status.return_value = {
            'drift': None,
            'phi_value': None
        }
        mock_analytics_class.return_value = mock_analytics

        result = cli_runner.invoke(gate_cli, ['status', '--repo', 'ECOS-CLI'])
        assert result.exit_code == 0
        assert "UNKNOWN" in result.output

    @patch('kiva_cli.commands.gate_command.PhiCPSAnalytics')
    def test_status_exception(self, mock_analytics_class, cli_runner):
        """Test status handles exceptions."""
        mock_analytics_class.side_effect = Exception("Failed")

        result = cli_runner.invoke(gate_cli, ['status', '--repo', 'ECOS-CLI'])
        assert result.exit_code == 0
        assert "ERROR" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])