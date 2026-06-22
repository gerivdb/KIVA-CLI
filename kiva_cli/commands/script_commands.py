#!/usr/bin/env python3
"""
Script Maturation Commands - KIVA CLI

Integrates ScriptMaturationManager into KIVA CLI.
Provides script lifecycle management commands.
"""

import click
import sys
from pathlib import Path
from typing import Optional

try:
    from kiva_cli.core.script_maturation_manager import ScriptMaturationManager
except ImportError:
    import sys
    from kiva_cli.core.script_maturation_manager import ScriptMaturationManager


@click.group(name='script')
def script_cli():
    """
    Script maturation and lifecycle management.

    Provides:
    - Progressive maturation (Skeleton -> Production)
    - Queue management for batch processing
    - Worker orchestration (background processing)
    - Maturity level tracking
    """
    pass


@script_cli.command(name='mature')
@click.argument('script_name')
@click.option('--target-level', '-l', default=4, type=int, help='Target maturity level (0-4)')
@click.option('--scripts-path', '-p', default='C:\\DevTools\\bin', help='Path to scripts directory')
def mature_script(script_name: str, target_level: int, scripts_path: str):
    """
    Promote a script to target maturity level.

    SCRIPT_NAME: Name of the script to mature (e.g., my-script.ps1)
    """
    manager = ScriptMaturationManager()
    current_level = manager.get_script_level(script_name, scripts_path)
    click.echo(f"Current level: {current_level} ({manager.MATURITY_LEVELS.get(current_level, 'Unknown')})")
    click.echo(f"Target level: {target_level} ({manager.MATURITY_LEVELS.get(target_level, 'Unknown')})")

    if current_level >= target_level:
        click.echo(click.style("Script already at target level.", fg="yellow"))
        return

    success = manager.promote_script(script_name, target_level, scripts_path)
    if success:
        click.echo(click.style(f"Successfully promoted {script_name} to level {target_level}", fg="green"))
    else:
        click.echo(click.style(f"Failed to promote {script_name}", fg="red"))
        sys.exit(1)


@script_cli.command(name='queue')
@click.option('--action', '-a', default='status', type=click.Choice(['status', 'add', 'remove', 'process']), help='Queue action')
@click.option('--script', '-s', default=None, help='Script name for add/remove actions')
@click.option('--target-level', '-l', default=4, type=int, help='Target level for add action')
def queue_action(action: str, script: Optional[str], target_level: int):
    """
    Manage script maturation queue.

    Actions:
    - status: Show current queue status
    - add: Add script to queue (requires --script)
    - remove: Remove script from queue (requires --script)
    - process: Process next script in queue
    """
    manager = ScriptMaturationManager()

    if action == 'status':
        status = manager.get_queue_status()
        click.echo("")
        click.echo(click.style("Script Maturation Queue Status", fg="cyan"))
        click.echo(click.style("=" * 40, fg="cyan"))

        worker_status = status["worker"]
        if worker_status["running"]:
            click.echo(f"Worker: {click.style(f'Running (PID: {worker_status["pid"]})', fg='green')}")
        else:
            click.echo(f"Worker: {click.style('Stopped', fg='red')}")

        click.echo(f"Queue: {status['queue_count']} items")
        processing = status["processing"]
        if processing:
            click.echo(f"Processing: {click.style(processing['script'], fg='yellow')}")
        else:
            click.echo("Processing: None")
        click.echo(f"Completed: {status['completed_count']}")
        click.echo("")

        if status["pending"]:
            click.echo(click.style("Pending:", fg="yellow"))
            for item in status["pending"]:
                click.echo(f"  - {item['script']} -> Level {item['targetLevel']}")

        if status["completed"]:
            click.echo(click.style("Recently Completed:", fg="green"))
            for item in status["completed"]:
                click.echo(f"  - {item['script']}")

    elif action == 'add':
        if not script:
            click.echo(click.style("Error: --script is required for add action", fg="red"))
            sys.exit(1)
        success = manager.add_to_queue(script, target_level)
        if success:
            click.echo(click.style(f"Added {script} to queue (target level {target_level})", fg="green"))
        else:
            click.echo(click.style(f"Failed to add {script} to queue", fg="yellow"))

    elif action == 'remove':
        if not script:
            click.echo(click.style("Error: --script is required for remove action", fg="red"))
            sys.exit(1)
        success = manager.remove_from_queue(script)
        if success:
            click.echo(click.style(f"Removed {script} from queue", fg="green"))
        else:
            click.echo(click.style(f"Script not found in queue: {script}", fg="yellow"))

    elif action == 'process':
        success = manager.process_queue()
        if success:
            click.echo(click.style("Script processed successfully", fg="green"))
        else:
            click.echo(click.style("No scripts to process or processing failed", fg="yellow"))


@script_cli.command(name='worker')
@click.option('--action', '-a', default='status', type=click.Choice(['status', 'start', 'stop']), help='Worker action')
def worker_action(action: str):
    """
    Manage background maturation worker.

    Actions:
    - status: Show worker status
    - start: Start background worker
    - stop: Stop background worker
    """
    manager = ScriptMaturationManager()

    if action == 'status':
        status = manager.get_worker_status()
        if status["running"]:
            click.echo(click.style(f"Worker running (PID: {status['pid']})", fg="green"))
        else:
            click.echo(click.style("Worker stopped", fg="red"))

    elif action == 'start':
        success = manager.start_worker()
        if success:
            click.echo(click.style("Worker started", fg="green"))
        else:
            click.echo(click.style("Failed to start worker", fg="red"))
            sys.exit(1)

    elif action == 'stop':
        success = manager.stop_worker()
        if success:
            click.echo(click.style("Worker stopped", fg="green"))
        else:
            click.echo(click.style("Failed to stop worker", fg="red"))
            sys.exit(1)


@script_cli.command(name='level')
@click.argument('script_name')
@click.option('--scripts-path', '-p', default='C:\\DevTools\\bin', help='Path to scripts directory')
def check_level(script_name: str, scripts_path: str):
    """
    Check current maturity level of a script.

    SCRIPT_NAME: Name of the script to check
    """
    manager = ScriptMaturationManager()
    level = manager.get_script_level(script_name, scripts_path)
    level_name = manager.MATURITY_LEVELS.get(level, "Unknown")
    click.echo(f"{script_name}: Level {level} ({level_name})")
