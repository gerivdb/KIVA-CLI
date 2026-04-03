#!/usr/bin/env python3
"""
LXC Orchestration Commands - KIVA CLI

Provides commands for LXC/LXD container management.
"""

import click
from tools.core.lxc_manager import LXCManager


@click.group(name='lxc')
def lxc_cli():
    """
    LXC/LXD container orchestration.

    Provides:
    - Create containers
    - Start/stop containers
    - Delete containers
    - List containers
    - Check container status
    """
    pass


@lxc_cli.command(name='create')
@click.argument('name')
@click.option('--image', '-i', default='ubuntu:22.04', help='Container image')
@click.option('--cpu', default=2, help='CPU cores')
@click.option('--memory', default='4GB', help='Memory allocation')
@click.option('--storage', default='20GB', help='Storage allocation')
def create_container(name: str, image: str, cpu: int, memory: str, storage: str):
    """
    Create a new LXC container.

    NAME: Container name

    Example:
        kiva lxc create my-container --image ubuntu:22.04
    """
    mgr = LXCManager()
    success = mgr.create_container(name, image, cpu, memory, storage)
    
    if success:
        click.echo(click.style(f"Container '{name}' created with image {image}", fg="green"))
    else:
        click.echo(click.style(f"Container '{name}' already exists.", fg="yellow"))


@lxc_cli.command(name='start')
@click.argument('name')
def start_container(name: str):
    """
    Start an LXC container.

    NAME: Container name

    Example:
        kiva lxc start my-container
    """
    mgr = LXCManager()
    success = mgr.start_container(name)
    
    if success:
        click.echo(click.style(f"Container '{name}' started.", fg="green"))
    else:
        click.echo(click.style(f"Container '{name}' not found.", fg="yellow"))


@lxc_cli.command(name='stop')
@click.argument('name')
def stop_container(name: str):
    """
    Stop an LXC container.

    NAME: Container name

    Example:
        kiva lxc stop my-container
    """
    mgr = LXCManager()
    success = mgr.stop_container(name)
    
    if success:
        click.echo(click.style(f"Container '{name}' stopped.", fg="green"))
    else:
        click.echo(click.style(f"Container '{name}' not found.", fg="yellow"))


@lxc_cli.command(name='delete')
@click.argument('name')
def delete_container(name: str):
    """
    Delete an LXC container.

    NAME: Container name

    Example:
        kiva lxc delete my-container
    """
    mgr = LXCManager()
    success = mgr.delete_container(name)
    
    if success:
        click.echo(click.style(f"Container '{name}' deleted.", fg="green"))
    else:
        click.echo(click.style(f"Container '{name}' not found.", fg="yellow"))


@lxc_cli.command(name='list')
def list_containers():
    """
    List all LXC containers.

    Example:
        kiva lxc list
    """
    mgr = LXCManager()
    containers = mgr.list_containers()
    
    click.echo("")
    click.echo(click.style(f"LXC Containers ({len(containers)})", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for c in containers:
        status_color = "green" if c.status == "running" else "white"
        click.echo(f"  {click.style(c.name, fg=status_color)} - {c.image} [{c.status}]")
        if c.status == "running":
            click.echo(f"    IP: {c.ip_address}")
        click.echo(f"    CPU: {c.cpu}, Memory: {c.memory}, Storage: {c.storage}")
    
    click.echo("")


@lxc_cli.command(name='status')
@click.argument('name', required=False)
def container_status(name: str):
    """
    Check container status.

    NAME: Container name (optional, shows all if not specified)

    Example:
        kiva lxc status
        kiva lxc status my-container
    """
    mgr = LXCManager()
    
    if name:
        c = mgr.get_container_status(name)
        if c:
            click.echo("")
            click.echo(click.style(f"Container: {name}", fg="cyan"))
            click.echo(click.style("=" * 40, fg="cyan"))
            click.echo(f"Image: {c.image}")
            click.echo(f"Status: {click.style(c.status, fg='green' if c.status == 'running' else 'white')}")
            click.echo(f"CPU: {c.cpu}")
            click.echo(f"Memory: {c.memory}")
            click.echo(f"Storage: {c.storage}")
            if c.ip_address:
                click.echo(f"IP: {c.ip_address}")
            click.echo("")
        else:
            click.echo(click.style(f"Container '{name}' not found.", fg="yellow"))
    else:
        s = mgr.get_all_status()
        click.echo("")
        click.echo(click.style("LXC Overview", fg="cyan"))
        click.echo(click.style("=" * 40, fg="cyan"))
        click.echo(f"Total: {s['total_containers']}")
        click.echo(f"Running: {s['running_containers']}")
        click.echo(f"Stopped: {s['stopped_containers']}")
        click.echo("")