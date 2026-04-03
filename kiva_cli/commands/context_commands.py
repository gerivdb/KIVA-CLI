#!/usr/bin/env python3
"""
Context Commands - KIVA CLI

Provides context management commands for active repository selection.
"""

import click
from tools.core.context_manager import ContextManager
from tools.core.path_resolver import PathResolver


@click.group(name='context')
def context_cli():
    """
    Context management for active repository.

    Provides:
    - Set/get active repository context
    - Detect current repository
    - Context-aware path resolution
    """
    pass


@context_cli.command(name='set')
@click.argument('repo_name')
def set_context(repo_name: str):
    """
    Set the active repository context.

    REPO_NAME: Name of the repository (e.g., DevTools, KIVA-CLI)

    Example:
        kiva context set DevTools
    """
    manager = ContextManager()
    resolver = PathResolver()
    
    # Validate repo exists
    if repo_name not in resolver.repos:
        available = ", ".join(resolver.repos.keys())
        click.echo(click.style(f"Unknown repository: {repo_name}", fg="red"))
        click.echo(f"Available repositories: {available}")
        return
    
    manager.set_active_repo(repo_name)
    click.echo(click.style(f"Active repository set to: {repo_name}", fg="green"))


@context_cli.command(name='get')
def get_context():
    """
    Get the current context information.

    Example:
        kiva context get
    """
    manager = ContextManager()
    summary = manager.get_context_summary()
    
    click.echo("")
    click.echo(click.style("Current Context", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Active repo:    {summary['active_repo'] or 'Not set'}")
    click.echo(f"Last path:      {summary['last_path'] or 'None'}")
    click.echo(f"Last command:   {summary['last_command'] or 'None'}")
    click.echo(f"Detected repo:  {summary['detected_repo'] or 'None'}")
    click.echo("")


@context_cli.command(name='detect')
def detect_context():
    """
    Detect the current repository based on git.

    Example:
        kiva context detect
    """
    manager = ContextManager()
    detected = manager.detect_current_repo()
    
    if detected:
        click.echo(click.style(f"Detected repository: {detected}", fg="green"))
    else:
        click.echo(click.style("No repository detected.", fg="yellow"))


@context_cli.command(name='list')
def list_contexts():
    """
    List all available repositories for context selection.

    Example:
        kiva context list
    """
    resolver = PathResolver()
    manager = ContextManager()
    active = manager.get_active_repo()
    
    click.echo("")
    click.echo(click.style("Available Repositories", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for name, repo in resolver.repos.items():
        marker = " (active)" if name == active else ""
        click.echo(f"  {click.style(name, fg='green')}{marker}")
        click.echo(f"    Local:  {repo.local_path}")
        click.echo(f"    Remote: {repo.remote_url}")
    
    click.echo("")


@context_cli.command(name='clear')
def clear_context():
    """
    Clear the current context.

    Example:
        kiva context clear
    """
    manager = ContextManager()
    manager.clear_context()
    click.echo(click.style("Context cleared.", fg="green"))