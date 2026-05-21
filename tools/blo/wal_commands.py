"""
CLI commands for GlobalWALManager operations
"""

import click
import json
from datetime import datetime, timedelta
from tabulate import tabulate
from kiva_cli.core.global_wal_manager import (
    GlobalWALManager, EventType, Severity, ValidationState
)

@click.group()
def wal():
    """Global Write-Ahead Log management commands"""
    pass

@wal.command()
@click.option('--type', 'event_type', type=click.Choice(['COMPONENT_IMPLEMENTATION', 'VALIDATION', 'DEPLOYMENT', 'INCIDENT']), required=True)
@click.option('--ecosystem', required=True)
@click.option('--repos', required=True, help='Comma-separated repository names')
@click.option('--phi-baseline', type=float, required=True)
@click.option('--phi-current', type=float, required=True)
@click.option('--parent-hash', default=None)
@click.option('--severity', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']), default='INFO')
@click.option('--description', default='')
def append(event_type: str, ecosystem: str, repos: str, phi_baseline: float, phi_current: float, parent_hash: str, severity: str, description: str):
    """Append a new event to WAL"""
    manager = GlobalWALManager()
    repositories = [r.strip() for r in repos.split(',')]
    
    event_id = manager.append_event(
        event_type=EventType[event_type],
        ecosystem_id=ecosystem,
        repositories=repositories,
        phi_cps_baseline=phi_baseline,
        phi_cps_current=phi_current,
        parent_intent_hash=parent_hash,
        severity=Severity[severity],
        description=description
    )
    
    event = manager.get_event(event_id)
    
    click.echo(f"✅ Event appended: {event_id}")
    click.echo(f"   IntentHash: {event['intent_hash']}")
    click.echo(f"   φ-CPS delta: {event['phi_cps_delta']:.4f}")
    
    if event['phi_cps_alert']:
        click.echo(f"   ⚠️ WARNING: φ-CPS alert triggered (delta > {event['phi_cps_threshold']})")

@wal.command()
@click.option('--event-id', required=True)
@click.option('--type', 'operation_type', required=True)
@click.option('--repo', required=True)
@click.option('--status', type=click.Choice(['PENDING', 'SUCCESS', 'FAILED']), required=True)
@click.option('--path', default=None)
@click.option('--commit', default=None)
@click.option('--duration', type=int, default=None)
def add_operation(event_id: str, operation_type: str, repo: str, status: str, path: str, commit: str, duration: int):
    """Add an operation to an event"""
    manager = GlobalWALManager()
    
    operation_id = manager.add_operation(
        event_id=event_id,
        operation_type=operation_type,
        repository=repo,
        status=ValidationState[status],
        path=path,
        commit_sha=commit,
        duration_ms=duration
    )
    
    click.echo(f"✅ Operation added: {operation_id}")
    click.echo(f"   Event: {event_id}")
    click.echo(f"   Repository: {repo}")
    click.echo(f"   Status: {status}")

@wal.command()
@click.option('--event-id', required=True)
def get(event_id: str):
    """Get event details"""
    manager = GlobalWALManager()
    event = manager.get_event(event_id)
    
    if not event:
        click.echo(f"❌ Event {event_id} not found")
        return
    
    state_icons = {
        'PENDING': '⚪',
        'SUCCESS': '✅',
        'FAILED': '❌'
    }
    
    icon = state_icons.get(event['validation_state'], '?')
    click.echo(f"{icon} Event: {event['event_id']}")
    click.echo(f"   IntentHash: {event['intent_hash']}")
    click.echo(f"   Timestamp: {event['timestamp']}")
    click.echo(f"   Type: {event['event_type']}")
    click.echo(f"   Severity: {event['severity']}")
    click.echo(f"   Ecosystem: {event['ecosystem_id']}")
    click.echo(f"   Repositories: {', '.join(event['repositories'])}")
    click.echo(f"   φ-CPS: {event['phi_cps_baseline']:.3f} → {event['phi_cps_current']:.3f} (delta {event['phi_cps_delta']:+.4f})")
    click.echo(f"   Alert: {'Yes' if event['phi_cps_alert'] else 'No'}")
    click.echo(f"   Validation: {event['validation_state']}")
    click.echo(f"   Auto-approved: {event['auto_approved']}")
    
    if event['operations']:
        click.echo(f"\n   Operations ({len(event['operations'])}):")
        for op in event['operations']:
            op_icon = state_icons.get(op['status'], '?')
            click.echo(f"   {op_icon} {op['operation_type']} ({op['repository']}) - {op['status']}")

@wal.command()
@click.option('--ecosystem', default=None)
@click.option('--type', 'event_type', type=click.Choice(['COMPONENT_IMPLEMENTATION', 'VALIDATION', 'DEPLOYMENT', 'INCIDENT']))
@click.option('--severity', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']))
@click.option('--repo', default=None)
@click.option('--days', type=int, default=7, help='Last N days')
@click.option('--alerts-only', is_flag=True)
@click.option('--limit', type=int, default=50)
def query(ecosystem: str, event_type: str, severity: str, repo: str, days: int, alerts_only: bool, limit: int):
    """Query events with filters"""
    manager = GlobalWALManager()
    
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    filters = {
        'ecosystem_id': ecosystem,
        'start_date': start_date,
        'repository': repo,
        'phi_cps_alert_only': alerts_only,
        'limit': limit
    }
    
    if event_type:
        filters['event_type'] = EventType[event_type]
    
    if severity:
        filters['severity'] = Severity[severity]
    
    events = manager.query_events(**filters)
    
    if not events:
        click.echo("No events found")
        return
    
    table_data = []
    for e in events:
        alert_icon = '⚠️' if e['phi_cps_alert'] else ''
        table_data.append([
            e['event_id'][:12],
            e['timestamp'][:19],
            e['event_type'][:20],
            e['severity'],
            f"{e['phi_cps_delta']:+.4f}",
            alert_icon,
            e['validation_state']
        ])
    
    click.echo(tabulate(
        table_data,
        headers=['Event ID', 'Timestamp', 'Type', 'Severity', 'φ-CPS Δ', 'Alert', 'Status'],
        tablefmt='grid'
    ))

@wal.command()
@click.option('--ecosystem', default=None)
@click.option('--days', type=int, default=30)
def stats(ecosystem: str, days: int):
    """Get WAL statistics"""
    manager = GlobalWALManager()
    
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    stats = manager.get_statistics(
        ecosystem_id=ecosystem,
        start_date=start_date
    )
    
    click.echo(f"WAL Statistics (last {days} days):\n")
    click.echo(f"Total events: {stats['total_events']}")
    click.echo(f"φ-CPS alerts: {stats['phi_cps_alerts']}")
    click.echo(f"Rollbacks: {stats['rollbacks']}")
    click.echo(f"Avg φ-CPS delta: {stats['avg_phi_delta']:+.4f}")
    click.echo(f"Success rate: {stats['success_rate']:.1%}\n")
    
    if stats['events_by_type']:
        click.echo("Events by type:")
        for etype, count in stats['events_by_type'].items():
            click.echo(f"   {etype}: {count}")
        click.echo("")
    
    if stats['events_by_severity']:
        click.echo("Events by severity:")
        for sev, count in stats['events_by_severity'].items():
            click.echo(f"   {sev}: {count}")

@wal.command()
@click.option('--format', type=click.Choice(['json', 'csv', 'markdown']), default='json')
@click.option('--output', required=True)
@click.option('--ecosystem', default=None)
@click.option('--days', type=int, default=30)
def export(format: str, output: str, ecosystem: str, days: int):
    """Export events to file"""
    manager = GlobalWALManager()
    
    start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
    
    output_path = manager.export_events(
        format=format,
        output_path=output,
        ecosystem_id=ecosystem,
        start_date=start_date
    )
    
    click.echo(f"✅ Events exported to: {output_path}")
