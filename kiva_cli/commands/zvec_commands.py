#!/usr/bin/env python3
"""
zvec Commands - KIVA CLI

Provides commands for vector search and semantic operations.
"""

import click
from tools.core.zvec_manager import ZVecManager


@click.group(name='zvec')
def zvec_cli():
    """
    zvec vector database management.

    Provides:
    - Add vectors/text
    - Semantic search
    - Index statistics
    """
    pass


@zvec_cli.command(name='status')
def status():
    """Check zvec index status."""
    mgr = ZVecManager()
    stats = mgr.get_stats()
    
    click.echo("")
    click.echo(click.style("zvec Index Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Dimension: {stats['dimension']}")
    click.echo(f"Vectors: {stats['size']}")
    click.echo(f"Data Dir: {stats['data_dir']}")
    click.echo("")


@zvec_cli.command(name='add')
@click.argument('id')
@click.option('--text', '-t', required=True, help='Text content to embed')
def add_text(id: str, text: str):
    """
    Add text content to the vector index.

    ID: Unique identifier for the text

    Example:
        kiva zvec add my-doc --text "Hello world"
    """
    mgr = ZVecManager()
    success = mgr.add_text(id, text)
    
    if success:
        click.echo(click.style(f"Text added: {id}", fg="green"))
    else:
        click.echo(click.style(f"Failed to add text: {id}", fg="red"))


@zvec_cli.command(name='search')
@click.argument('query')
@click.option('--top-k', '-k', default=5, help='Number of results')
def search_text(query: str, top_k: int):
    """
    Search for similar text content.

    QUERY: Search query text

    Example:
        kiva zvec search "hello world"
    """
    mgr = ZVecManager()
    results = mgr.search_text(query, top_k)
    
    click.echo("")
    click.echo(click.style(f"Search Results: '{query}'", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    
    if not results:
        click.echo("No results found.")
    else:
        for i, r in enumerate(results, 1):
            click.echo(f"  {i}. {click.style(r['id'], fg='green')} (score: {r['score']:.4f})")
            if 'text' in r.get('metadata', {}):
                text = r['metadata']['text'][:100]
                click.echo(f"     {text}...")
    
    click.echo("")


@zvec_cli.command(name='clear')
def clear_index():
    """Clear the vector index."""
    mgr = ZVecManager()
    mgr.clear()
    click.echo(click.style("Index cleared.", fg="green"))