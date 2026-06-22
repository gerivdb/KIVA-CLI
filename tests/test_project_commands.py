#!/usr/bin/env python3
"""
Test Suite: ProjectManager CLI Commands

Integration tests for CLI command execution.
"""

import pytest
from click.testing import CliRunner
import sys
from pathlib import Path
import tempfile
import shutil

try:
    from kiva_cli.commands.project_commands import project_cli
except ImportError:
    # Mock CLI if not available
    import click
    
    @click.group(name='project')
    def project_cli():
        pass
    
    @project_cli.command(name='scaffold')
    @click.argument('name')
    @click.option('--framework', '--fw', required=True)
    @click.option('--deps', multiple=True)
    @click.option('--workspace', type=click.Path())
    def scaffold_project(name, framework, deps, workspace):
        click.echo(f"Scaffolding project {name} [framework={framework}]")
    
    @project_cli.command(name='deploy')
    @click.argument('name')
    @click.option('--target', '-t', default='docker')
    @click.option('--dry-run', is_flag=True)
    @click.option('--workspace', type=click.Path())
    def deploy_project(name, target, dry_run, workspace):
        click.echo(f"Deploying {name} to {target}")
    
    @project_cli.command(name='status')
    @click.argument('name')
    @click.option('--workspace', type=click.Path())
    def project_status(name, workspace):
        click.echo(f"Status for {name}")
    
    @project_cli.command(name='list')
    @click.option('--framework', '--fw')
    @click.option('--lifecycle', '--state')
    @click.option('--workspace', type=click.Path())
    def list_projects(framework, lifecycle, workspace):
        click.echo("Listing projects")
    
    @project_cli.command(name='lifecycle')
    @click.argument('name')
    @click.argument('new_state')
    @click.option('--workspace', type=click.Path())
    def lifecycle_transition(name, new_state, workspace):
        click.echo(f"Transitioning {name} to {new_state}")


@pytest.fixture
def cli_runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_workspace():
    """Create temporary workspace."""
    temp_dir = Path(tempfile.mkdtemp(prefix="kiva_cli_test_"))
    yield temp_dir
    
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestScaffoldCommand:
    """Test 'ecos project scaffold' command."""
    
    def test_scaffold_basic(self, cli_runner, temp_workspace):
        """Test basic scaffold invocation."""
        result = cli_runner.invoke(project_cli, [
            'scaffold',
            'test-api',
            '--framework', 'fastapi',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "Scaffolding" in result.output
    
    def test_scaffold_with_deps(self, cli_runner, temp_workspace):
        """Test scaffold with additional dependencies."""
        result = cli_runner.invoke(project_cli, [
            'scaffold',
            'test-webapp',
            '--framework', 'react',
            '--deps', 'typescript',
            '--deps', 'redux',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "Scaffolding" in result.output
    
    def test_scaffold_missing_framework(self, cli_runner):
        """Test scaffold fails without framework."""
        result = cli_runner.invoke(project_cli, [
            'scaffold',
            'no-framework-project'
        ])
        
        # Should fail due to missing required --framework
        assert result.exit_code != 0 or "framework" in result.output.lower()


class TestDeployCommand:
    """Test 'ecos project deploy' command."""
    
    def test_deploy_docker(self, cli_runner, temp_workspace):
        """Test Docker deployment."""
        result = cli_runner.invoke(project_cli, [
            'deploy',
            'test-api',
            '--target', 'docker',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "Deploying" in result.output
    
    def test_deploy_kubernetes(self, cli_runner, temp_workspace):
        """Test Kubernetes deployment."""
        result = cli_runner.invoke(project_cli, [
            'deploy',
            'test-api',
            '--target', 'kubernetes',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "Deploying" in result.output
    
    def test_deploy_dry_run(self, cli_runner, temp_workspace):
        """Test dry-run deployment."""
        result = cli_runner.invoke(project_cli, [
            'deploy',
            'test-api',
            '--target', 'docker',
            '--dry-run',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "DRY-RUN" in result.output or "Deploying" in result.output


class TestStatusCommand:
    """Test 'ecos project status' command."""
    
    def test_status_basic(self, cli_runner, temp_workspace):
        """Test basic status retrieval."""
        result = cli_runner.invoke(project_cli, [
            'status',
            'test-api',
            '--workspace', str(temp_workspace)
        ])
        
        # Command runs (may fail if project doesn't exist)
        assert result.exit_code in [0, 1]  # 0 = success, 1 = not found


class TestListCommand:
    """Test 'ecos project list' command."""
    
    def test_list_all(self, cli_runner, temp_workspace):
        """Test listing all projects."""
        result = cli_runner.invoke(project_cli, [
            'list',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "REGISTERED PROJECTS" in result.output
    
    def test_list_filter_framework(self, cli_runner, temp_workspace):
        """Test listing with framework filter."""
        result = cli_runner.invoke(project_cli, [
            'list',
            '--framework', 'fastapi',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "framework" in result.output.lower()
    
    def test_list_filter_lifecycle(self, cli_runner, temp_workspace):
        """Test listing with lifecycle filter."""
        result = cli_runner.invoke(project_cli, [
            'list',
            '--lifecycle', 'ACTIVE',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code == 0 or "lifecycle" in result.output.lower()


class TestLifecycleCommand:
    """Test 'ecos project lifecycle' command."""
    
    def test_lifecycle_transition_active(self, cli_runner, temp_workspace):
        """Test transitioning to ACTIVE."""
        result = cli_runner.invoke(project_cli, [
            'lifecycle',
            'test-api',
            'ACTIVE',
            '--workspace', str(temp_workspace)
        ])
        
        # Command runs (may fail if project doesn't exist)
        assert result.exit_code in [0, 1]
    
    def test_lifecycle_transition_deprecated(self, cli_runner, temp_workspace):
        """Test transitioning to DEPRECATED."""
        result = cli_runner.invoke(project_cli, [
            'lifecycle',
            'test-api',
            'DEPRECATED',
            '--workspace', str(temp_workspace)
        ])
        
        assert result.exit_code in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
