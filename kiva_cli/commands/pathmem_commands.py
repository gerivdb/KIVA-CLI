#!/usr/bin/env python3
"""
Path Memory Commands - KIVA CLI

Provides commands for path memory management and ultra-reliable path resolution.
"""

import click
from tools.core.path_memory_manager import UltraReliablePathResolver, PathErrorMemory


@click.group(name='pathmem')
def pathmem_cli():
    """Path memory and ultra-reliable path resolution."""
    pass


@pathmem_cli.command(name='resolve')
@click.argument('path')
def resolve_path(path: str):
    resolver = UltraReliablePathResolver()
    resolved = resolver.resolve(path)
    exists = __import__('os').path.exists(resolved)
    
    click.echo("")
    click.echo(click.style("Path Resolution", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Input:    {path}")
    click.echo(f"Resolved: {resolved}")
    click.echo(f"Exists:   {click.style('Yes', fg='green') if exists else click.style('No', fg='red')}")
    click.echo("")


@pathmem_cli.command(name='stats')
def path_stats():
    resolver = UltraReliablePathResolver()
    stats = resolver.get_error_stats()
    
    click.echo("")
    click.echo(click.style("Path Memory Statistics", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Total Errors: {stats['total_errors']}")
    click.echo(f"Unique Errors: {stats['unique_errors']}")
    click.echo(f"Known Roots: {stats['known_roots']}")
    click.echo("")


@pathmem_cli.command(name='roots')
def list_roots():
    resolver = UltraReliablePathResolver()
    roots = resolver.get_known_roots()
    
    click.echo("")
    click.echo(click.style("Known Root Paths", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    for keyword, path in sorted(roots.items()):
        click.echo(f"  {click.style(keyword, fg='green')}: {path}")
    click.echo("")


@pathmem_cli.command(name='clear')
def clear_memory():
    memory = PathErrorMemory()
    memory.clear()
    click.echo(click.style("Path memory cleared.", fg="green"))


@pathmem_cli.command(name='test')
def test_resolution():
    resolver = UltraReliablePathResolver()
    
    test_paths = [
        "devtools/bin/script.ps1",
        "kiva-cli/tools/core",
        "brain-docs/docs",
        "D:\\\\DO\\\\WEB\\\\TOOLS\\\\KIVA-CLI",
        "devtoosl/bin",
    ]
    
    click.echo("")
    click.echo(click.style("Path Resolution Tests", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    
    for path in test_paths:
        resolved = resolver.resolve(path)
        exists = __import__('os').path.exists(resolved)
        status = click.style('OK', fg='green') if exists else click.style('MISSING', fg='red')
        click.echo(f"  {path[:30]:<30} -> {resolved[:40]:<40} [{status}]")
    
    click.echo("")