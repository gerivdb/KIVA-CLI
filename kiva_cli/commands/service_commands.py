#!/usr/bin/env python3
"""
Service Discovery Commands - KIVA CLI

Provides commands for service registration, discovery, and management.
"""

import click
from tools.core.service_discovery import ServiceDiscovery


@click.group(name='service')
def service_cli():
    """
    Service discovery and management.

    Provides:
    - Register services
    - Discover services
    - List services
    - Health checks
    """
    pass


@service_cli.command(name='register')
@click.argument('name')
@click.option('--host', '-h', default='localhost', help='Service host')
@click.option('--port', '-p', required=True, type=int, help='Service port')
@click.option('--protocol', default='http', help='Service protocol')
def register(name: str, host: str, port: int, protocol: str):
    """
    Register a service.

    NAME: Service name

    Example:
        kiva service register my-api --port 8080
    """
    sd = ServiceDiscovery()
    success = sd.register_service(name, host, port, protocol)
    
    if success:
        click.echo(click.style(f"Service '{name}' registered at {host}:{port}", fg="green"))
    else:
        click.echo(click.style(f"Failed to register service '{name}'.", fg="red"))


@service_cli.command(name='discover')
@click.argument('name')
def discover(name: str):
    """
    Discover a service by name.

    NAME: Service name

    Example:
        kiva service discover my-api
    """
    sd = ServiceDiscovery()
    service = sd.discover_service(name)
    
    if service:
        click.echo("")
        click.echo(click.style(f"Service: {name}", fg="cyan"))
        click.echo(click.style("=" * 40, fg="cyan"))
        click.echo(f"URL: {service.get_url()}")
        click.echo(f"Status: {click.style(service.status, fg='green' if service.status == 'healthy' else 'red')}")
        click.echo(f"Last heartbeat: {service.last_heartbeat}")
        click.echo("")
    else:
        click.echo(click.style(f"Service '{name}' not found.", fg="yellow"))


@service_cli.command(name='list')
def list_services():
    """
    List all registered services.

    Example:
        kiva service list
    """
    sd = ServiceDiscovery()
    services = sd.list_services()
    
    click.echo("")
    click.echo(click.style(f"Registered Services ({len(services)})", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for service in services:
        status_color = "green" if service.status == "healthy" else "red"
        click.echo(f"  {click.style(service.name, fg='green')} - {service.get_url()} [{click.style(service.status, fg=status_color)}]")
    
    click.echo("")


@service_cli.command(name='deregister')
@click.argument('name')
def deregister(name: str):
    """
    Deregister a service.

    NAME: Service name

    Example:
        kiva service deregister my-api
    """
    sd = ServiceDiscovery()
    success = sd.deregister_service(name)
    
    if success:
        click.echo(click.style(f"Service '{name}' deregistered.", fg="green"))
    else:
        click.echo(click.style(f"Service '{name}' not found.", fg="yellow"))