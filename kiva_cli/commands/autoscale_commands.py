#!/usr/bin/env python3
"""
Auto-Scaling Commands - KIVA CLI

Provides commands for managing auto-scaling policies.
"""

import click
from kiva_cli.core.autoscaling_manager import AutoScalingManager


@click.group(name='autoscale')
def autoscale_cli():
    """
    Auto-scaling policy management.

    Provides:
    - Create scaling policies
    - Delete policies
    - List policies
    - Evaluate policies
    """
    pass


@autoscale_cli.command(name='create')
@click.argument('name')
@click.option('--service', '-s', required=True, help='Target service')
@click.option('--min', default=1, help='Min instances')
@click.option('--max', default=10, help='Max instances')
@click.option('--cpu-threshold', default=80, help='CPU threshold %')
@click.option('--memory-threshold', default=85, help='Memory threshold %')
def create_policy(name: str, service: str, min: int, max: int, cpu_threshold: int, memory_threshold: int):
    """
    Create a scaling policy.

    NAME: Policy name

    Example:
        kiva autoscale create my-policy --service api --max 20
    """
    mgr = AutoScalingManager()
    mgr.create_policy(name, service, min, max, cpu_threshold, memory_threshold)
    click.echo(click.style(f"Policy '{name}' created for {service}", fg="green"))


@autoscale_cli.command(name='list')
def list_policies():
    """
    List all scaling policies.

    Example:
        kiva autoscale list
    """
    mgr = AutoScalingManager()
    policies = mgr.list_policies()
    
    click.echo("")
    click.echo(click.style(f"Scaling Policies ({len(policies)})", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for p in policies:
        click.echo(f"  {click.style(p.name, fg='green')}")
        click.echo(f"    Service: {p.service}")
        click.echo(f"    Instances: {p.min_instances} - {p.max_instances}")
        click.echo(f"    CPU Threshold: {p.cpu_threshold}%")
        click.echo(f"    Memory Threshold: {p.memory_threshold}%")
    
    click.echo("")


@autoscale_cli.command(name='delete')
@click.argument('name')
def delete_policy(name: str):
    """
    Delete a scaling policy.

    NAME: Policy name

    Example:
        kiva autoscale delete my-policy
    """
    mgr = AutoScalingManager()
    success = mgr.delete_policy(name)
    
    if success:
        click.echo(click.style(f"Policy '{name}' deleted.", fg="green"))
    else:
        click.echo(click.style(f"Policy '{name}' not found.", fg="yellow"))


@autoscale_cli.command(name='evaluate')
@click.argument('name')
@click.option('--cpu', default=50, help='Current CPU %')
@click.option('--memory', default=50, help='Current Memory %')
@click.option('--instances', default=1, help='Current instances')
def evaluate_policy(name: str, cpu: int, memory: int, instances: int):
    """
    Evaluate a scaling policy.

    NAME: Policy name

    Example:
        kiva autoscale evaluate my-policy --cpu 90 --memory 90
    """
    mgr = AutoScalingManager()
    result = mgr.evaluate_policy(name, cpu, memory, instances)
    
    click.echo("")
    click.echo(click.style(f"Policy Evaluation: {name}", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Action: {click.style(result['action'], fg='green' if result['action'] != 'none' else 'white')}")
    click.echo(f"Reason: {result['reason']}")
    if 'new_instances' in result:
        click.echo(f"Instances: {result['current_instances']} -> {result['new_instances']}")
    click.echo("")