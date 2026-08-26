#!/usr/bin/env python3
"""
Test Suite: Security Commands - KIVA CLI

Tests for the security command group (security hardening and audit).
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

try:
    from kiva_cli.commands.security_commands import security_cli
except ImportError:
    import click

    @click.group(name='security')
    def security_cli():
        pass

    @security_cli.command(name='audit')
    @click.argument('repo_path')
    def audit(repo_path: str):
        click.echo("Security Audit Results")

    @security_cli.command(name='status')
    @click.argument('repo_path')
    def status(repo_path: str):
        click.echo("Security Status")

    @security_cli.command(name='rotate')
    @click.argument('secret_name')
    @click.option('--repo', '-r', required=True)
    def rotate_secret(secret_name: str, repo: str):
        click.echo("Secret rotated")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


class TestSecurityAuditCommand:
    """Test 'kiva security audit' command."""

    @patch('kiva_cli.commands.security_commands.SecurityManager')
    def test_audit_pass(self, mock_manager_class, cli_runner):
        """Test security audit passes."""
        mock_manager = MagicMock()
        mock_manager.run_security_audit.return_value = {
            'repo_path': 'D:\\Repos\\test',
            'status': 'PASS',
            'issues_count': 0,
            'issues': []
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(security_cli, ['audit', 'D:\\Repos\\test'])

        assert result.exit_code == 0
        assert "Security Audit Results" in result.output
        assert "PASS" in result.output
        assert "Issues found: 0" in result.output
        mock_manager.run_security_audit.assert_called_once_with('D:\\Repos\\test')

    @patch('kiva_cli.commands.security_commands.SecurityManager')
    def test_audit_with_issues(self, mock_manager_class, cli_runner):
        """Test security audit with issues."""
        mock_manager = MagicMock()
        mock_manager.run_security_audit.return_value = {
            'repo_path': 'D:\\Repos\\test',
            'status': 'FAIL',
            'issues_count': 2,
            'issues': [
                {'severity': 'HIGH', 'message': 'Hardcoded secret', 'file': 'config.py'},
                {'severity': 'MEDIUM', 'message': 'Weak encryption', 'file': 'crypto.py'}
            ]
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(security_cli, ['audit', 'D:\\Repos\\test'])

        assert result.exit_code == 0
        assert "FAIL" in result.output
        assert "Issues found: 2" in result.output
        assert "Hardcoded secret" in result.output
        assert "Weak encryption" in result.output


class TestSecurityStatusCommand:
    """Test 'kiva security status' command."""

    @patch('kiva_cli.commands.security_commands.SecurityManager')
    def test_status(self, mock_manager_class, cli_runner):
        """Test security status."""
        mock_manager = MagicMock()
        mock_manager.get_security_status.return_value = {
            'repo_path': 'D:\\Repos\\test',
            'status': 'PASS',
            'issues_count': 0
        }
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(security_cli, ['status', 'D:\\Repos\\test'])

        assert result.exit_code == 0
        assert "Security Status" in result.output
        assert "PASS" in result.output
        assert "Issues: 0" in result.output


class TestSecurityRotateCommand:
    """Test 'kiva security rotate' command."""

    @patch('kiva_cli.commands.security_commands.SecurityManager')
    def test_rotate_success(self, mock_manager_class, cli_runner):
        """Test rotating secret successfully."""
        mock_manager = MagicMock()
        mock_manager.rotate_secrets.return_value = True
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(security_cli, ['rotate', 'API_KEY', '--repo', 'D:\\Repos\\test'])

        assert result.exit_code == 0
        assert "rotated successfully" in result.output
        mock_manager.rotate_secrets.assert_called_once_with('D:\\Repos\\test', 'API_KEY')

    @patch('kiva_cli.commands.security_commands.SecurityManager')
    def test_rotate_failure(self, mock_manager_class, cli_runner):
        """Test rotating secret failure."""
        mock_manager = MagicMock()
        mock_manager.rotate_secrets.return_value = False
        mock_manager_class.return_value = mock_manager

        result = cli_runner.invoke(security_cli, ['rotate', 'API_KEY', '--repo', 'D:\\Repos\\test'])

        assert result.exit_code == 0
        assert "Failed to rotate" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])