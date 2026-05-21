#!/usr/bin/env python3
"""CLI commands for DaemonManager.

Commands:
    ecos daemon register <name> --type <type> --script <path> [options]
    ecos daemon start <daemon_id>
    ecos daemon stop <daemon_id>
    ecos daemon restart <daemon_id>
    ecos daemon status <daemon_id>
    ecos daemon list [--type TYPE] [--state STATE]
    ecos daemon delete <daemon_id>
    ecos daemon logs <daemon_id> [--tail N]
    ecos daemon health <daemon_id>
"""

import click
import json
from pathlib import Path
from typing import Optional

from kiva_cli.core.daemon_manager import DaemonManager


@click.group()
def daemon():
    """Manage background daemons and services."""
    pass


@daemon.command()
@click.argument('name')
@click.option('--type', 'daemon_type', required=True, 
              type=click.Choice(['PYTHON_SCRIPT', 'POWERSHELL_SCRIPT', 'BASH_SCRIPT', 
                               'SYSTEM_SERVICE', 'DOCKER_CONTAINER', 'MONITORING_AGENT']))
@click.option('--script', 'script_path', help='Path to script file')
@click.option('--description', help='Daemon description')
@click.option('--schedule', help='Cron expression or interval (e.g., "*/5 * * * *", "30s")')
@click.option('--restart-policy', default='on-failure', 
              type=click.Choice(['no', 'on-failure', 'always']))
@click.option('--max-restarts', default=3, type=int, help='Maximum restart attempts')
@click.option('--cpu-limit', type=int, help='CPU limit (%)')
@click.option('--memory-limit', type=int, help='Memory limit (MB)')
def register(name: str, daemon_type: str, script_path: Optional[str], 
             description: Optional[str], schedule: Optional[str],
             restart_policy: str, max_restarts: int,
             cpu_limit: Optional[int], memory_limit: Optional[int]):
    """Register a new daemon."""
    try:
        manager = DaemonManager()
        
        resource_limits = {}
        if cpu_limit:
            resource_limits['cpu_percent'] = cpu_limit
        if memory_limit:
            resource_limits['memory_mb'] = memory_limit
        
        daemon_id = manager.register_daemon(
            name=name,
            daemon_type=daemon_type,
            script_path=script_path,
            description=description,
            schedule=schedule,
            resource_limits=resource_limits if resource_limits else None,
            restart_policy=restart_policy,
            max_restarts=max_restarts
        )
        
        click.echo(f"✅ Daemon registered: {daemon_id}")
        click.echo(f"   Name: {name}")
        click.echo(f"   Type: {daemon_type}")
        click.echo(f"   State: GENESIS")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@daemon.command()
@click.argument('daemon_id')
def start(daemon_id: str):
    """Start a daemon."""
    try:
        manager = DaemonManager()
        success = manager.start_daemon(daemon_id)
        
        if success:
            daemon = manager.get_daemon(daemon_id)
            click.echo(f"✅ Daemon started: {daemon_id}")
            click.echo(f"   PID: {daemon['pid']}")
            click.echo(f"   State: RUNNING")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@daemon.command()
@click.argument('daemon_id')
@click.option('--timeout', default=30, type=int, help='Stop timeout (seconds)')
def stop(daemon_id: str, timeout: int):
    """Stop a daemon."""
    try:
        manager = DaemonManager()
        success = manager.stop_daemon(daemon_id, timeout=timeout)
        
        if success:
            click.echo(f"✅ Daemon stopped: {daemon_id}")
            click.echo(f"   State: STOPPED")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@daemon.command()
@click.argument('daemon_id')
def restart(daemon_id: str):
    """Restart a daemon."""
    try:
        manager = DaemonManager()
        manager.stop_daemon(daemon_id)
        manager.start_daemon(daemon_id, force=True)
        
        daemon = manager.get_daemon(daemon_id)
        click.echo(f"✅ Daemon restarted: {daemon_id}")
        click.echo(f"   PID: {daemon['pid']}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@daemon.command()
@click.argument('daemon_id')
def status(daemon_id: str):
    """Get daemon status."""
    try:
        manager = DaemonManager()
        daemon = manager.get_daemon(daemon_id)
        
        if not daemon:
            click.echo(f"❌ Daemon not found: {daemon_id}", err=True)
            raise click.Abort()
        
        click.echo(f"Daemon: {daemon['name']}")
        click.echo(f"  ID: {daemon['daemon_id']}")
        click.echo(f"  Type: {daemon['daemon_type']}")
        click.echo(f"  Runtime State: {daemon['runtime_state']}")
        click.echo(f"  Validation: {daemon['validation_state']}")
        click.echo(f"  Lifecycle: {daemon['lifecycle_state']}")
        click.echo(f"  PID: {daemon['pid'] or 'N/A'}")
        click.echo(f"  φ-CPS: {daemon['phi_cps']}")
        click.echo(f"  Restarts: {daemon['restart_count']}/{daemon['max_restarts']}")
        click.echo(f"  Success: {daemon['success_count']}")
        click.echo(f"  Failures: {daemon['failure_count']}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@daemon.command()
@click.option('--type', 'daemon_type', help='Filter by daemon type')
@click.option('--state', 'runtime_state', help='Filter by runtime state')
@click.option('--lifecycle', 'lifecycle_state', help='Filter by lifecycle state')
@click.option('--limit', default=50, type=int, help='Maximum results')
def list(daemon_type: Optional[str], runtime_state: Optional[str], 
         lifecycle_state: Optional[str], limit: int):
    """List daemons."""
    try:
        manager = DaemonManager()
        daemons = manager.list_daemons(
            daemon_type=daemon_type,
            runtime_state=runtime_state,
            lifecycle_state=lifecycle_state,
            limit=limit
        )
        
        if not daemons:
            click.echo("No daemons found.")
            return
        
        click.echo(f"Found {len(daemons)} daemon(s):\n")
        
        for d in daemons:
            state_icon = {
                'RUNNING': '🟢',
                'STOPPED': '⚪',
                'FAILED': '🔴',
                'STARTING': '🟡',
                'STOPPING': '🟠'
            }.get(d['runtime_state'], '⚫')
            
            click.echo(f"{state_icon} {d['name']}")
            click.echo(f"   ID: {d['daemon_id']}")
            click.echo(f"   Type: {d['daemon_type']}")
            click.echo(f"   State: {d['runtime_state']}")
            click.echo(f"   PID: {d['pid'] or 'N/A'}")
            click.echo("")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    daemon()
