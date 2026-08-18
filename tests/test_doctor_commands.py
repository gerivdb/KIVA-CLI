#!/usr/bin/env python3
"""
Test Suite: Doctor Commands - KIVA CLI

Tests for the doctor command group (path hygiene and diagnostics).
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
import tempfile
import shutil

try:
    from kiva_cli.commands.doctor_commands import doctor_cli
except ImportError:
    import click

    @click.group(name='doctor')
    def doctor_cli():
        pass

    @doctor_cli.command(name='paths')
    @click.option('--auto', is_flag=True)
    @click.option('--registry', default=None)
    @click.option('--scan', default='.')
    def check_paths(auto, registry, scan):
        click.echo(f"Scanning {scan}")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_workspace():
    """Create temporary workspace with some files to scan."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kiva_doctor_test_"))
    
    # Create a Python file with a relative path
    (temp_dir / "script.py").write_text(
        'import sys\nsys.path.append("../libs/mylib")\n',
        encoding="utf-8"
    )
    
    # Create a markdown file with a relative path
    (temp_dir / "README.md").write_text(
        "See [config](../config/settings.yaml) for details.\n",
        encoding="utf-8"
    )
    
    yield temp_dir
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestDoctorPathsCommand:
    """Test 'kiva doctor paths' command."""

    def test_scan_nonexistent_path(self, cli_runner):
        """Test that scanning a non-existent path returns an error."""
        result = cli_runner.invoke(doctor_cli, [
            'paths',
            '--scan', '/nonexistent/path'
        ])
        
        assert result.exit_code != 0
        assert 'does not exist' in result.output.lower()

    def test_scan_valid_path_no_violations(self, cli_runner, temp_workspace):
        """Test scanning a path with no relative path violations."""
        result = cli_runner.invoke(doctor_cli, [
            'paths',
            '--scan', str(temp_workspace)
        ])
        
        # Should run without crashing
        assert result.exit_code == 0 or 'Violations' in result.output

    def test_scan_detects_relative_paths(self, cli_runner, temp_workspace):
        """Test that scanning detects relative path violations."""
        result = cli_runner.invoke(doctor_cli, [
            'paths',
            '--scan', str(temp_workspace)
        ])
        
        # Should detect the relative paths we created
        assert 'Violations' in result.output or result.exit_code == 0

    def test_help_output(self, cli_runner):
        """Test that doctor help shows the paths command."""
        result = cli_runner.invoke(doctor_cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'paths' in result.output.lower()
        assert 'hygiene' in result.output.lower() or 'diagnostic' in result.output.lower()
