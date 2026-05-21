#!/usr/bin/env python3
"""
Distributed WAL Commands - KIVA CLI

Provides commands for distributed WAL management.
"""

import click
from kiva_cli.core.distributed_wal_manager import DistributedWALManager


@click.group(name='wal-dist')
def wal_dist_cli():
    """
    Distributed WAL management.

    Provides:
    - Add WAL entries
    - Manage peer nodes
    - Check WAL status
    - Verify chain integrity
    """
    pass


@wal_dist_cli.command(name='add')
@click.argument('operation')
@click.option('--data', '-d', default='{}', help='Entry data as JSON')
@click.option('--node', '-n', default=None, help='Node ID')
def add_entry(operation: str, data: str, node: str):
    """
    Add a WAL entry.

    OPERATION: Operation type (e.g., CREATE, UPDATE, DELETE)

    Example:
        kiva wal-dist add CREATE --data '{"key": "value"}'
    """
    import json
    mgr = DistributedWALManager(node_id=node)
    try:
        data_dict = json.loads(data)
    except json.JSONDecodeError:
        data_dict = {"value": data}
    
    entry = mgr.add_entry(operation, data_dict)
    click.echo(click.style(f"Entry added: {entry.id}", fg="green"))


@wal_dist_cli.command(name='peers')
@click.option('--node', '-n', default=None, help='Node ID')
def list_peers(node: str):
    """
    List peer nodes.

    Example:
        kiva wal-dist peers
    """
    mgr = DistributedWALManager(node_id=node)
    peers = mgr.list_peers()
    
    click.echo("")
    click.echo(click.style(f"Peer Nodes ({len(peers)})", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    for peer in peers:
        click.echo(f"  - {peer}")
    click.echo("")


@wal_dist_cli.command(name='add-peer')
@click.argument('peer_id')
@click.option('--node', '-n', default=None, help='Node ID')
def add_peer(peer_id: str, node: str):
    """
    Add a peer node.

    PEER_ID: Peer node ID

    Example:
        kiva wal-dist add-peer node-2
    """
    mgr = DistributedWALManager(node_id=node)
    success = mgr.add_peer(peer_id)
    
    if success:
        click.echo(click.style(f"Peer '{peer_id}' added.", fg="green"))
    else:
        click.echo(click.style(f"Failed to add peer '{peer_id}'.", fg="yellow"))


@wal_dist_cli.command(name='status')
@click.option('--node', '-n', default=None, help='Node ID')
def status(node: str):
    """
    Check WAL status.

    Example:
        kiva wal-dist status
    """
    mgr = DistributedWALManager(node_id=node)
    s = mgr.get_status()
    
    click.echo("")
    click.echo(click.style("Distributed WAL Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Node ID: {s['node_id']}")
    click.echo(f"Total Entries: {s['total_entries']}")
    click.echo(f"Peers: {s['peers_count']}")
    click.echo("")