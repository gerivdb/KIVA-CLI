#!/usr/bin/env python3
"""
φ-CPS Analytics Commands - KIVA CLI

Provides commands for φ-CPS analytics, drift detection, and reporting.
"""

import click
from tools.core.phi_cps_analytics import PhiCPSAnalytics


@click.group(name='phi-cps')
def phi_cps_cli():
    """
    φ-CPS analytics and drift detection.

    Provides:
    - View current φ-CPS status
    - Check drift history
    - Generate analytics reports
    - Verify IntentHash chain
    """
    pass


@phi_cps_cli.command(name='status')
@click.option('--component', '-c', default=None, help='Filter by component')
def status(component: str):
    """
    View current φ-CPS status.

    Example:
        kiva phi-cps status
        kiva phi-cps status --component DevTools
    """
    analytics = PhiCPSAnalytics()
    current = analytics.get_current_status(component)
    
    click.echo("")
    click.echo(click.style("φ-CPS Current Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    
    status_color = {"OK": "green", "WARNING": "yellow", "CRITICAL": "red", "EMERGENCY": "red"}.get(current.get("status", ""), "white")
    click.echo(f"Status:   {click.style(current.get('status', 'N/A'), fg=status_color)}")
    click.echo(f"φ Value:  {current.get('phi_value', 'N/A')}")
    click.echo(f"Drift:    {current.get('drift', 'N/A')}")
    click.echo(f"Component: {current.get('component', 'N/A')}")
    click.echo(f"Level:    {current.get('level', 'N/A')}")
    click.echo(f"Hash:     {current.get('intent_hash', 'N/A')}")
    click.echo("")


@phi_cps_cli.command(name='alerts')
@click.option('--component', '-c', default=None, help='Filter by component')
def alerts(component: str):
    """
    View active φ-CPS alerts.

    Example:
        kiva phi-cps alerts
    """
    analytics = PhiCPSAnalytics()
    alert_list = analytics.get_alerts(component)
    
    click.echo("")
    click.echo(click.style(f"Active Alerts ({len(alert_list)})", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    
    if not alert_list:
        click.echo(click.style("  No active alerts.", fg="green"))
    else:
        for alert in alert_list[-10:]:
            color = {"WARNING": "yellow", "CRITICAL": "red", "EMERGENCY": "red"}.get(alert.status, "white")
            click.echo(f"  {click.style(f'[{alert.status}]', fg=color)} {alert.component} - Drift: {alert.drift * 100:.2f}%")
    
    click.echo("")


@phi_cps_cli.command(name='report')
@click.option('--output', '-o', default=None, help='Output file path')
def report(output: str):
    """
    Generate φ-CPS analytics report.

    Example:
        kiva phi-cps report
        kiva phi-cps report -o report.txt
    """
    analytics = PhiCPSAnalytics()
    report_text = analytics.generate_report(output)
    
    click.echo(report_text)
    
    if output:
        click.echo(click.style(f"Report saved to: {output}", fg="green"))


@phi_cps_cli.command(name='summary')
def summary():
    """
    View φ-CPS summary statistics.

    Example:
        kiva phi-cps summary
    """
    analytics = PhiCPSAnalytics()
    s = analytics.get_summary()
    
    click.echo("")
    click.echo(click.style("Phi-CPS Summary", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Total Metrics: {s['total_metrics']}")
    click.echo(f"Status:        {s['status']}")
    click.echo(f"Active Alerts: {s['alerts']}")
    click.echo(f"Avg Drift:     {s['avg_drift'] * 100:.2f}%")
    click.echo("")
    click.echo("Thresholds:")
    click.echo(f"  WARNING:   2%")
    click.echo(f"  CRITICAL:  5%")
    click.echo(f"  EMERGENCY: 10%")
    click.echo("")
    click.echo("Thresholds:")
    click.echo(f"  WARNING:   2%")
    click.echo(f"  CRITICAL:  5%")
    click.echo(f"  EMERGENCY: 10%")
    click.echo("")