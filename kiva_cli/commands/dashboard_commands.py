#!/usr/bin/env python3
"""
Dashboard Commands - KIVA CLI

Provides commands for starting and managing the web UI dashboard.
"""

import click
import time
from kiva_cli.core.dashboard_server import DashboardServer


@click.group(name='dashboard')
def dashboard_cli():
    """
    Web UI dashboard management.

    Provides:
    - Start dashboard server
    - Stop dashboard server
    """
    pass


@dashboard_cli.command(name='start')
@click.option('--host', '-h', default='localhost', help='Dashboard host')
@click.option('--port', '-p', default=9000, help='Dashboard port')
def start_dashboard(host: str, port: int):
    """
    Start the web dashboard server.

    Example:
        kiva dashboard start
        kiva dashboard start --port 8080
    """
    server = DashboardServer(host, port)
    server.start()
    click.echo(click.style(f"Dashboard started at http://{host}:{port}", fg="green"))
    click.echo("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        click.echo("Dashboard stopped.")