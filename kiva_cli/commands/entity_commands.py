#!/usr/bin/env python3
"""
Entity Commands - KIVA CLI

Provides entity path mapping commands.
"""

import click
from kiva_cli.core.entity_path_mapper import EntityPathMapper


@click.group(name='entity')
def entity_cli():
    """
    Entity path mapping utilities.

    Provides:
    - Locate citizen local paths
    - List citizens by repository
    - Sync citizen registry
    """
    pass


@entity_cli.command(name='locate')
@click.argument('citizen_id')
@click.option('--repo', '-r', default=None, help='Repository name')
def locate_citizen(citizen_id: str, repo: str):
    """
    Get the local path for a citizen.

    CITIZEN_ID: Citizen ID (e.g., kiva-cli)

    Example:
        kiva entity locate kiva-cli
        kiva entity locate kiva-cli --repo KIVA
    """
    mapper = EntityPathMapper()
    path = mapper.locate_citizen(citizen_id, repo)
    
    if path:
        click.echo(click.style(f"Local path: {path}", fg="green"))
    else:
        click.echo(click.style(f"No local path found for: {citizen_id}", fg="yellow"))


@entity_cli.command(name='list')
@click.option('--repo', '-r', default=None, help='Filter by repository')
def list_citizens(repo: str):
    """
    List all citizens.

    Example:
        kiva entity list
        kiva entity list --repo KIVA-CLI
    """
    mapper = EntityPathMapper()
    citizens = mapper.list_citizens(repo)
    
    click.echo("")
    click.echo(click.style(f"Citizens ({len(citizens)})", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for citizen in citizens:
        click.echo(click.style(f"\n{citizen.id}", fg="green"))
        click.echo(f"  Slug: {citizen.slug}")
        click.echo(f"  Role: {citizen.role_type}")
        click.echo(f"  Tier: {citizen.tier}")
        click.echo(f"  Status: {citizen.status}")
        click.echo(f"  Repos: {', '.join(citizen.repos_served)}")
        if citizen.local_paths:
            click.echo(f"  Paths:")
            for repo_name, path in citizen.local_paths.items():
                click.echo(f"    {repo_name}: {path}")
    
    click.echo("")


@entity_cli.command(name='sync')
def sync_citizens():
    """
    Re-sync citizen registry from YAML files.

    Example:
        kiva entity sync
    """
    mapper = EntityPathMapper()
    count = mapper.sync_citizens()
    click.echo(click.style(f"Synced {count} citizens", fg="green"))


@entity_cli.command(name='export')
@click.option('--output', '-o', default=None, help='Output file path')
def export_registry(output: str):
    """
    Export citizen registry as JSON.

    Example:
        kiva entity export
        kiva entity export -o citizens.json
    """
    mapper = EntityPathMapper()
    registry = mapper.export_registry()
    
    import json
    json_output = json.dumps(registry, indent=2, ensure_ascii=False)
    
    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(json_output)
        click.echo(click.style(f"Exported to: {output}", fg="green"))
    else:
        click.echo(json_output)