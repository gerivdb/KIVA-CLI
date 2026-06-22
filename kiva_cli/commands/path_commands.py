#!/usr/bin/env python3
"""
Path Commands - KIVA CLI

Provides path resolution and conversion commands.
"""

import click
from pathlib import Path
from typing import Optional

from kiva_cli.core.path_resolver import PathResolver


@click.group(name='path')
def path_cli():
    """
    Path resolution and conversion utilities.

    Provides:
    - Local <-> Remote path conversion
    - Repository detection
    - Path resolution across multi-repo ecosystem
    """
    pass


@path_cli.command(name='convert')
@click.argument('path')
@click.option('--to', '-t', 'target_format', default='auto', type=click.Choice(['local', 'remote', 'auto']), help='Target format')
def convert_path(path: str, target_format: str):
    """
    Convert path between local and remote formats.

    PATH: Path to convert (local or remote)

    Examples:
        kiva path convert C:\\DevTools\\bin\\script.ps1
        kiva path convert gerivdb/DevTools/bin/script.ps1 --to local
    """
    resolver = PathResolver()
    result = resolver.convert_path(path, target_format)
    
    if result == path:
        click.echo(click.style(f"Could not convert: {path}", fg="yellow"))
    else:
        click.echo(result)


@path_cli.command(name='resolve')
@click.argument('path')
def resolve_path(path: str):
    """
    Resolve a path and show both local and remote versions.

    PATH: Path to resolve

    Example:
        kiva path resolve C:\\DevTools\\bin\\script.ps1
    """
    resolver = PathResolver()
    result = resolver.resolve(path)
    
    click.echo("")
    click.echo(click.style("Path Resolution", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Input:    {result['input']}")
    click.echo(f"Local:    {result['local'] or 'N/A'}")
    click.echo(f"Remote:   {result['remote'] or 'N/A'}")
    click.echo(f"Repo:     {result['repo'] or 'N/A'}")
    click.echo(f"Exists:   {click.style('Yes', fg='green') if result['exists'] else click.style('No', fg='red')}")
    click.echo("")


@path_cli.command(name='detect')
@click.argument('path', default='.')
def detect_repo(path: str):
    """
    Detect which repository contains the given path.

    PATH: Path to check (default: current directory)

    Example:
        kiva path detect C:\\DevTools\\bin
    """
    resolver = PathResolver()
    repo_name = resolver.detect_repo(path)
    
    if repo_name:
        repo_info = resolver.repos.get(repo_name)
        click.echo(f"Repository: {click.style(repo_name, fg='green')}")
        if repo_info:
            click.echo(f"Local path: {repo_info.local_path}")
            click.echo(f"Remote URL: {repo_info.remote_url}")
    else:
        click.echo(click.style("No repository detected for this path.", fg="yellow"))


@path_cli.command(name='list')
def list_repos():
    """
    List all registered repositories.
    """
    resolver = PathResolver()
    repos = resolver.list_repos()
    
    click.echo("")
    click.echo(click.style("Registered Repositories", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for name, info in repos.items():
        click.echo(click.style(f"\n{name}", fg="green"))
        click.echo(f"  Local:  {info['local_path']}")
        click.echo(f"  Remote: {info['remote_url']}")
    
    click.echo("")


@path_cli.command(name='add')
@click.argument('name')
@click.argument('local_path')
@click.argument('remote_url')
def add_repo(name: str, local_path: str, remote_url: str):
    """
    Add a new repository to the registry.

    NAME: Repository name
    LOCAL_PATH: Local filesystem path
    REMOTE_URL: Remote repository URL (e.g., gerivdb/repo-name)

    Example:
        kiva path add MyRepo D:\\MyRepos\\MyRepo gerivdb/MyRepo
    """
    resolver = PathResolver()
    resolver.add_repo(name, local_path, remote_url)
    click.echo(click.style(f"Added repository: {name}", fg="green"))


@path_cli.command(name='remove')
@click.argument('name')
def remove_repo(name: str):
    """
    Remove a repository from the registry.

    NAME: Repository name to remove
    """
    resolver = PathResolver()
    if name in resolver.repos:
        resolver.remove_repo(name)
        click.echo(click.style(f"Removed repository: {name}", fg="green"))
    else:
        click.echo(click.style(f"Repository not found: {name}", fg="yellow"))


@path_cli.command(name='current')
def current_repo():
    """
    Detect the repository of the current working directory.
    """
    resolver = PathResolver()
    repo_name = resolver.detect_current_repo()
    
    if repo_name:
        repo_info = resolver.repos.get(repo_name)
        click.echo(f"Current repository: {click.style(repo_name, fg='green')}")
        if repo_info:
            click.echo(f"Local path: {repo_info.local_path}")
            click.echo(f"Remote URL: {repo_info.remote_url}")
    else:
        click.echo(click.style("Not in a registered repository.", fg="yellow"))