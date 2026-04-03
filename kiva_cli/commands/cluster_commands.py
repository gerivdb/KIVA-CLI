#!/usr/bin/env python3
"""
Multi-Host Cluster Commands - KIVA CLI

Provides commands for cluster management.
"""

import click
from tools.core.cluster_manager import ClusterManager


@click.group(name='cluster')
def cluster_cli():
    """
    Multi-host cluster management.

    Provides:
    - Initialize cluster
    - Join/leave cluster
    - List nodes
    - Check cluster status
    """
    pass


@cluster_cli.command(name='init')
@click.argument('cluster_name')
@click.option('--master-host', '-h', required=True, help='Master node host')
@click.option('--master-port', '-p', default=8080, help='Master node port')
def init_cluster(cluster_name: str, master_host: str, master_port: int):
    """
    Initialize a new cluster.

    CLUSTER_NAME: Name of the cluster

    Example:
        kiva cluster init my-cluster --master-host 192.168.1.100
    """
    mgr = ClusterManager()
    mgr.init_cluster(cluster_name, master_host, master_port)
    click.echo(click.style(f"Cluster '{cluster_name}' initialized with master at {master_host}:{master_port}", fg="green"))


@cluster_cli.command(name='join')
@click.argument('node_id')
@click.option('--host', '-h', required=True, help='Node host')
@click.option('--port', '-p', default=8080, help='Node port')
@click.option('--role', default='worker', help='Node role (master/worker)')
def join_cluster(node_id: str, host: str, port: int, role: str):
    """
    Join a node to the cluster.

    NODE_ID: Unique node identifier

    Example:
        kiva cluster join node-2 --host 192.168.1.101
    """
    mgr = ClusterManager()
    success = mgr.join_cluster(node_id, host, port, role)
    
    if success:
        click.echo(click.style(f"Node '{node_id}' joined the cluster.", fg="green"))
    else:
        click.echo(click.style(f"Node '{node_id}' already exists.", fg="yellow"))


@cluster_cli.command(name='leave')
@click.argument('node_id')
def leave_cluster(node_id: str):
    """
    Remove a node from the cluster.

    NODE_ID: Node identifier to remove

    Example:
        kiva cluster leave node-2
    """
    mgr = ClusterManager()
    success = mgr.leave_cluster(node_id)
    
    if success:
        click.echo(click.style(f"Node '{node_id}' left the cluster.", fg="green"))
    else:
        click.echo(click.style(f"Node '{node_id}' not found or is master.", fg="yellow"))


@cluster_cli.command(name='list')
def list_nodes():
    """
    List all cluster nodes.

    Example:
        kiva cluster list
    """
    mgr = ClusterManager()
    nodes = mgr.list_nodes()
    
    click.echo("")
    click.echo(click.style(f"Cluster Nodes ({len(nodes)})", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for node in nodes:
        role_color = "green" if node.role == "master" else "white"
        click.echo(f"  {click.style(node.id, fg=role_color)} - {node.host}:{node.port} [{node.role}]")
    
    click.echo("")


@cluster_cli.command(name='status')
def cluster_status():
    """
    Check cluster status.

    Example:
        kiva cluster status
    """
    mgr = ClusterManager()
    s = mgr.get_cluster_status()
    
    click.echo("")
    click.echo(click.style("Cluster Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Cluster Name: {s['cluster_name']}")
    click.echo(f"Total Nodes: {s['total_nodes']}")
    click.echo(f"Active Nodes: {s['active_nodes']}")
    click.echo("")