#!/usr/bin/env python3
"""
CI/CD Commands - KIVA CLI

Provides commands for CI/CD integration and pipeline management.
"""

import click
from tools.core.cicd_manager import CICDManager


@click.group(name='cicd')
def cicd_cli():
    """
    CI/CD integration and pipeline management.

    Provides:
    - Setup GitHub Actions workflows
    - Configure self-hosted runners
    - Run CI pipelines locally
    - Check pipeline status
    """
    pass


@cicd_cli.command(name='setup')
@click.argument('repo_path')
@click.option('--pipeline', '-p', default='ecos-ci', help='Pipeline name')
def setup(repo_path: str, pipeline: str):
    """
    Setup GitHub Actions workflow for a repository.

    REPO_PATH: Path to the repository

    Example:
        kiva cicd setup D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = CICDManager()
    success = manager.setup_github_actions(repo_path, pipeline)
    
    if success:
        click.echo(click.style(f"GitHub Actions workflow setup successfully.", fg="green"))
    else:
        click.echo(click.style(f"Failed to setup workflow.", fg="red"))


@cicd_cli.command(name='run')
@click.argument('repo_path')
def run_pipeline(repo_path: str):
    """
    Run CI pipeline locally for testing.

    REPO_PATH: Path to the repository

    Example:
        kiva cicd run D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = CICDManager()
    success = manager.run_ci_pipeline(repo_path)
    
    if success:
        click.echo(click.style("CI pipeline passed!", fg="green"))
    else:
        click.echo(click.style("CI pipeline failed!", fg="red"))


@cicd_cli.command(name='status')
@click.argument('repo_path')
def status(repo_path: str):
    """
    Check CI pipeline status for a repository.

    REPO_PATH: Path to the repository

    Example:
        kiva cicd status D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = CICDManager()
    info = manager.get_pipeline_status(repo_path)
    
    click.echo("")
    click.echo(click.style("CI/CD Pipeline Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Repository: {info['repo_path']}")
    click.echo(f"Workflows: {info['workflows_count']}")
    for wf in info['workflows']:
        click.echo(f"  - {wf}")
    click.echo("")