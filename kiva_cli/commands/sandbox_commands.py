#!/usr/bin/env python3
"""
OpenSandbox Commands - KIVA CLI

Provides commands for secure sandbox execution.
"""

import click
from kiva_cli.core.opensandbox_manager import OpenSandboxManager


@click.group(name='sandbox')
def sandbox_cli():
    """
    OpenSandbox secure execution.

    Provides:
    - Execute scripts in sandbox
    - Execute commands in sandbox
    - View sandbox stats
    - Cleanup sandbox
    """
    pass


@sandbox_cli.command(name='exec')
@click.argument('script_path')
@click.option('--timeout', '-t', default=60, help='Execution timeout in seconds')
def exec_script(script_path: str, timeout: int):
    """
    Execute a script in sandbox.

    SCRIPT_PATH: Path to the script

    Example:
        kiva sandbox exec C:\\scripts\\test.ps1
    """
    mgr = OpenSandboxManager()
    result = mgr.execute_script(script_path, timeout)
    
    click.echo("")
    click.echo(click.style(f"Sandbox Execution: {script_path}", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Success: {click.style('Yes' if result.success else 'No', fg='green' if result.success else 'red')}")
    click.echo(f"Exit Code: {result.exit_code}")
    if result.stdout:
        click.echo(f"\nStdout:\n{result.stdout[:500]}")
    if result.stderr:
        click.echo(f"\nStderr:\n{result.stderr[:500]}")
    click.echo("")


@sandbox_cli.command(name='cmd')
@click.argument('command')
@click.option('--args', '-a', multiple=True, help='Command arguments')
@click.option('--timeout', '-t', default=30, help='Timeout in seconds')
def exec_command(command: str, args: tuple, timeout: int):
    """
    Execute a command in sandbox.

    COMMAND: Command to execute

    Example:
        kiva sandbox cmd python --args --version
    """
    mgr = OpenSandboxManager()
    result = mgr.execute_command(command, list(args), timeout)
    
    click.echo("")
    click.echo(click.style(f"Sandbox Command: {command}", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Success: {click.style('Yes' if result.success else 'No', fg='green' if result.success else 'red')}")
    click.echo(f"Exit Code: {result.exit_code}")
    if result.stdout:
        click.echo(f"\nStdout:\n{result.stdout[:500]}")
    if result.stderr:
        click.echo(f"\nStderr:\n{result.stderr[:500]}")
    click.echo("")


@sandbox_cli.command(name='status')
def sandbox_status():
    """Check sandbox status."""
    mgr = OpenSandboxManager()
    stats = mgr.get_stats()
    
    click.echo("")
    click.echo(click.style("OpenSandbox Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Sandbox Dir: {stats['sandbox_dir']}")
    click.echo(f"Executions: {stats['executions']}")
    click.echo("")


@sandbox_cli.command(name='clean')
def sandbox_clean():
    """Cleanup sandbox data."""
    mgr = OpenSandboxManager()
    mgr.cleanup()
    click.echo(click.style("Sandbox cleaned up.", fg="green"))