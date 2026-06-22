#!/usr/bin/env python3
"""
KVCache Commands - KIVA CLI

Provides commands for managing the KVCache system.
"""

import click
from kiva_cli.core.kvcache_manager import KVCacheManager


@click.group(name='kvcache')
def kvcache_cli():
    """
    KVCache management.

    Provides:
    - Check cache status
    - Clear cache
    - Get/set cache entries
    """
    pass


@kvcache_cli.command(name='status')
def status():
    """
    Check KVCache status.

    Example:
        kiva kvcache status
    """
    mgr = KVCacheManager()
    stats = mgr.get_stats()
    
    click.echo("")
    click.echo(click.style("KVCache Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"L1 Cache:")
    click.echo(f"  Size: {stats['l1']['size']}")
    click.echo(f"  Capacity: {stats['l1']['capacity']}")
    click.echo(f"  Hits: {stats['l1']['hits']}")
    click.echo(f"  Misses: {stats['l1']['misses']}")
    click.echo(f"  Hit Rate: {stats['l1']['hit_rate']}%")
    click.echo(f"L2 Cache:")
    click.echo(f"  Size: {stats['l2_size']}")
    click.echo(f"  Capacity: {stats['l2_capacity']}")
    click.echo("")


@kvcache_cli.command(name='clear')
def clear():
    """
    Clear all cache entries.

    Example:
        kiva kvcache clear
    """
    mgr = KVCacheManager()
    mgr.clear()
    click.echo(click.style("Cache cleared.", fg="green"))


@kvcache_cli.command(name='get')
@click.argument('key')
def get_entry(key: str):
    """
    Get a cache entry by key.

    KEY: Cache key

    Example:
        kiva kvcache get my-key
    """
    mgr = KVCacheManager()
    value = mgr.get(key)
    
    if value is not None:
        click.echo(f"Value: {value}")
    else:
        click.echo(click.style(f"Key '{key}' not found in cache.", fg="yellow"))


@kvcache_cli.command(name='set')
@click.argument('key')
@click.argument('value')
@click.option('--ttl', '-t', default=300, help='Time to live in seconds')
def set_entry(key: str, value: str, ttl: int):
    """
    Set a cache entry.

    KEY: Cache key
    VALUE: Cache value

    Example:
        kiva kvcache set my-key my-value --ttl 600
    """
    mgr = KVCacheManager()
    mgr.put(key, value, ttl)
    click.echo(click.style(f"Cache entry set: {key} = {value}", fg="green"))