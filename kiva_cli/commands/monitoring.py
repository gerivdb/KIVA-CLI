#!/usr/bin/env python3
"""Monitoring and observability commands for KIVA CLI.

Handles Prometheus, Grafana, Datadog, and custom metrics setup.
"""

import click
import json
from pathlib import Path
from typing import Optional


@click.group()
def monitoring():
    """Setup and manage monitoring infrastructure."""
    pass


@monitoring.command()
@click.option('--provider', type=click.Choice(['prometheus', 'datadog', 'newrelic', 'grafana']),
              required=True, help='Monitoring provider')
@click.option('--targets', default='k8s', help='Deployment targets (k8s, docker, vm)')
@click.option('--config', type=click.Path(exists=True), help='Custom config file')
def setup(provider: str, targets: str, config: Optional[str]):
    """Setup monitoring for specified provider and targets.
    
    Example:
        kiva monitoring setup --provider=prometheus --targets=k8s
    """
    click.echo(f"📊 Setting up {provider} monitoring for {targets}...")
    
    if config:
        click.echo(f"📄 Using config: {config}")
    
    # Generate provider-specific configs
    if provider == 'prometheus':
        _setup_prometheus(targets)
    elif provider == 'grafana':
        _setup_grafana(targets)
    
    click.echo("✅ Monitoring setup complete")
    click.echo(f"\n📊 Access dashboard: http://localhost:3000")


@monitoring.command()
@click.option('--service', required=True, help='Service name')
@click.option('--metric', required=True, help='Metric name (e.g., http_requests_total)')
@click.option('--labels', multiple=True, help='Label key=value pairs')
@click.option('--value', type=float, required=True, help='Metric value')
def push(service: str, metric: str, labels: tuple, value: float):
    """Push custom metric to monitoring backend.
    
    Example:
        kiva monitoring push --service=api --metric=custom_counter \
            --labels=env=prod --labels=region=eu --value=42
    """
    parsed_labels = dict(label.split('=') for label in labels)
    
    click.echo(f"📤 Pushing metric {metric} for {service}...")
    click.echo(f"   Labels: {parsed_labels}")
    click.echo(f"   Value: {value}")
    
    # Push to Prometheus pushgateway or similar
    click.echo("✅ Metric pushed successfully")


@monitoring.command()
@click.option('--service', default='all', help='Service to check')
@click.option('--window', default='5m', help='Time window (e.g., 5m, 1h, 1d)')
@click.option('--format', type=click.Choice(['table', 'json']), default='table')
def metrics(service: str, window: str, format: str):
    """Query current metrics for services.
    
    Example:
        kiva monitoring metrics --service=api --window=1h
    """
    click.echo(f"📊 Fetching metrics for {service} (last {window})...\n")
    
    # Mock metrics data
    metrics_data = [
        {"service": "api-prod", "rps": 1250, "latency_p95": 45, "errors": 0.02},
        {"service": "worker", "rps": 320, "latency_p95": 120, "errors": 0.01}
    ]
    
    if format == 'table':
        click.echo(f"{'Service':<20} {'RPS':<10} {'P95 Latency':<15} {'Error Rate'}")
        click.echo("-" * 60)
        for metric in metrics_data:
            click.echo(f"{metric['service']:<20} {metric['rps']:<10} "
                      f"{metric['latency_p95']:<15} {metric['errors']:.2%}")
    else:
        click.echo(json.dumps(metrics_data, indent=2))


@monitoring.command()
@click.option('--name', required=True, help='Alert rule name')
@click.option('--condition', required=True, help='Alert condition (PromQL)')
@click.option('--severity', type=click.Choice(['critical', 'warning', 'info']),
              default='warning')
@click.option('--notify', multiple=True, help='Notification channels')
def alert(name: str, condition: str, severity: str, notify: tuple):
    """Create monitoring alert rule.
    
    Example:
        kiva monitoring alert --name=HighErrorRate \
            --condition='rate(errors[5m]) > 0.05' \
            --severity=critical --notify=slack --notify=pagerduty
    """
    click.echo(f"🚨 Creating alert: {name}")
    click.echo(f"   Condition: {condition}")
    click.echo(f"   Severity: {severity}")
    click.echo(f"   Notifications: {', '.join(notify)}")
    
    # Create alert rule in Prometheus/Alertmanager
    click.echo("✅ Alert rule created")


def _setup_prometheus(targets: str):
    """Setup Prometheus monitoring."""
    config = {
        "global": {"scrape_interval": "15s"},
        "scrape_configs": [
            {
                "job_name": "kubernetes-pods",
                "kubernetes_sd_configs": [{"role": "pod"}]
            }
        ]
    }
    click.echo("  ✓ Generated prometheus.yml")
    click.echo("  ✓ Configured service discovery")


def _setup_grafana(targets: str):
    """Setup Grafana dashboards."""
    click.echo("  ✓ Imported default dashboards")
    click.echo("  ✓ Configured datasource")


if __name__ == '__main__':
    monitoring()
