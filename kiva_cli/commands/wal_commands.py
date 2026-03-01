#!/usr/bin/env python3
"""
WAL Commands Module - KIVA CLI

Global WAL (Write-Ahead Log) management commands.
Provides CLI interface for event tracking, drift monitoring, and audit.
"""

import click
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import json

try:
    from tools.core.global_wal_manager import (
        GlobalWALManager,
        ValidationState,
        EventStatus,
        WALEvent
    )
except ImportError:
    # Fallback import
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tools.core.global_wal_manager import (
        GlobalWALManager,
        ValidationState,
        EventStatus,
        WALEvent
    )


@click.group(name='wal')
def wal_cli():
    """
    📜 Global WAL (Write-Ahead Log) management.
    
    Provides:
    - Cross-repo event tracking
    - IntentHash¹¹ chain validation
    - φ-CPS drift monitoring
    - Automatic rollback detection
    - Complete audit trail
    """
    pass


@wal_cli.command(name='append')
@click.option(
    '--operation', '-o',
    required=True,
    help='Operation type (e.g., SCAFFOLD_PROJECT, DEPLOY_DOCKER)'
)
@click.option(
    '--repo', '-r',
    required=True,
    help='Repository name (e.g., KIVA-CLI)'
)
@click.option(
    '--phi-delta',
    type=float,
    required=True,
    help='φ-CPS delta for this operation'
)
@click.option(
    '--commit-sha',
    help='Git commit SHA (if applicable)'
)
@click.option(
    '--parent-hash',
    help='Parent IntentHash for chain continuity'
)
@click.option(
    '--validation',
    type=click.Choice(['UNKNOWN', 'VALID', 'INVALID'], case_sensitive=False),
    default='VALID',
    help='Validation state (base-3 ternary)'
)
@click.option(
    '--status',
    type=click.Choice(['PENDING', 'SUCCESS', 'FAILED'], case_sensitive=False),
    default='SUCCESS',
    help='Event execution status'
)
@click.option(
    '--metadata',
    help='JSON metadata string'
)
def append_event(
    operation: str,
    repo: str,
    phi_delta: float,
    commit_sha: Optional[str],
    parent_hash: Optional[str],
    validation: str,
    status: str,
    metadata: Optional[str]
):
    """
    ➕ Append event to Global WAL.
    
    Examples:
        ecos wal append --operation SCAFFOLD_PROJECT \
                        --repo KIVA-CLI \
                        --phi-delta 0.018
        
        ecos wal append -o DEPLOY_DOCKER -r my-api \
                        --phi-delta 0.012 \
                        --commit-sha abc123 \
                        --parent-hash 0x1234567890ABCDEF
    """
    wal = GlobalWALManager()
    
    # Parse metadata
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            click.echo(f"❌ Invalid JSON metadata: {metadata}", err=True)
            sys.exit(1)
    
    validation_state = ValidationState[validation]
    event_status = EventStatus[status]
    
    click.echo(f"\n➕ Appending event to Global WAL")
    click.echo("─" * 60)
    
    event = wal.append_event(
        operation=operation,
        repo=repo,
        phi_cps_delta=phi_delta,
        commit_sha=commit_sha,
        parent_intent_hash=parent_hash,
        metadata=metadata_dict,
        validation_state=validation_state,
        status=event_status
    )
    
    click.echo(f"\n✅ Event appended successfully!")
    click.echo(f"\n📊 EVENT METADATA:")
    click.echo(f"   🆔 Event ID: {event.event_id}")
    click.echo(f"   🔗 IntentHash: {event.intent_hash}")
    click.echo(f"   📈 φ-CPS delta: +{event.phi_cps_delta:.4f}")
    click.echo(f"   📈 φ-CPS current: {event.phi_cps_current:.4f}")
    click.echo(f"   ✅ Validation: {event.validation_state}")
    click.echo(f"   🟢 Status: {event.status}")
    
    if parent_hash:
        click.echo(f"   🔗 Parent: {parent_hash}")
    
    # Check drift
    drift = wal.get_drift()
    if drift["threshold_exceeded"]:
        click.echo(f"\n⚠️  φ-CPS DRIFT THRESHOLD EXCEEDED!")
        click.echo(f"   Drift: {drift['relative_drift']:.2%} (> {drift['threshold']:.0%})")
        click.echo(f"   🛑 Rollback recommended: ecos wal rollback --reason drift_exceeded")


@wal_cli.command(name='query')
@click.option(
    '--repo', '-r',
    help='Filter by repository name'
)
@click.option(
    '--operation', '-o',
    help='Filter by operation type'
)
@click.option(
    '--status',
    type=click.Choice(['PENDING', 'SUCCESS', 'FAILED'], case_sensitive=False),
    help='Filter by event status'
)
@click.option(
    '--hours',
    type=int,
    help='Show events from last N hours'
)
@click.option(
    '--limit', '-n',
    type=int,
    default=20,
    help='Maximum results (default: 20)'
)
def query_events(
    repo: Optional[str],
    operation: Optional[str],
    status: Optional[str],
    hours: Optional[int],
    limit: int
):
    """
    🔍 Query WAL events with filters.
    
    Examples:
        ecos wal query
        ecos wal query --repo KIVA-CLI --limit 10
        ecos wal query --operation DEPLOY_DOCKER --hours 24
        ecos wal query --status FAILED
    """
    wal = GlobalWALManager()
    
    # Calculate time range
    start_time = None
    if hours:
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    event_status = EventStatus[status] if status else None
    
    events = wal.query_events(
        repo=repo,
        operation=operation,
        start_time=start_time,
        status=event_status,
        limit=limit
    )
    
    # Build filter description
    filters = []
    if repo:
        filters.append(f"repo={repo}")
    if operation:
        filters.append(f"operation={operation}")
    if status:
        filters.append(f"status={status}")
    if hours:
        filters.append(f"last {hours}h")
    
    filters_str = f" [{', '.join(filters)}]" if filters else ""
    
    click.echo(f"\n📊 WAL EVENTS ({len(events)}){filters_str}")
    click.echo("═" * 80)
    
    if not events:
        click.echo(f"\n⚠️  No events found")
        if filters:
            click.echo(f"\n💡 Try without filters: ecos wal query")
        return
    
    for idx, event in enumerate(events, 1):
        status_icons = {
            "PENDING": "🔵",
            "SUCCESS": "✅",
            "FAILED": "❌"
        }
        
        validation_icons = {
            "VALID": "✅",
            "INVALID": "❌",
            "UNKNOWN": "❓"
        }
        
        status_icon = status_icons.get(event.status, "❓")
        validation_icon = validation_icons.get(event.validation_state, "❓")
        
        # Format timestamp
        timestamp = datetime.fromisoformat(event.timestamp)
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        click.echo(f"\n{idx}. {status_icon} {event.operation}")
        click.echo(f"   Repo: {event.repo}")
        click.echo(f"   IntentHash: {event.intent_hash}")
        click.echo(f"   φ-CPS: {event.phi_cps_current:.4f} (Δ +{event.phi_cps_delta:.4f})")
        click.echo(f"   Validation: {validation_icon} {event.validation_state}")
        click.echo(f"   Timestamp: {time_str}")
        
        if event.commit_sha:
            click.echo(f"   Commit: {event.commit_sha[:8]}")
        
        if event.parent_intent_hash:
            click.echo(f"   Parent: {event.parent_intent_hash}")


@wal_cli.command(name='drift')
def check_drift():
    """
    📈 Check φ-CPS drift metrics.
    
    Examples:
        ecos wal drift
    """
    wal = GlobalWALManager()
    drift = wal.get_drift()
    
    click.echo(f"\n📈 φ-CPS DRIFT METRICS")
    click.echo("═" * 60)
    
    click.echo(f"\n📊 BASELINE:")
    click.echo(f"   φ-CPS baseline: {drift['baseline_phi']:.4f}")
    click.echo(f"   Events since baseline: {drift['events_since_baseline']}")
    
    click.echo(f"\n📈 CURRENT:")
    click.echo(f"   φ-CPS current: {drift['current_phi']:.4f}")
    click.echo(f"   Absolute drift: +{drift['absolute_drift']:.4f}")
    click.echo(f"   Relative drift: {drift['relative_drift']:.2%}")
    
    click.echo(f"\n🎯 THRESHOLD:")
    click.echo(f"   Threshold: {drift['threshold']:.0%}")
    
    if drift["threshold_exceeded"]:
        click.echo(f"   Status: ❌ EXCEEDED")
        click.echo(f"\n⚠️  φ-CPS DRIFT CRITICAL!")
        click.echo(f"   Drift: {drift['relative_drift']:.2%} > {drift['threshold']:.0%}")
        click.echo(f"\n🛑 RECOMMENDED ACTIONS:")
        click.echo(f"   1. Review recent operations: ecos wal query --limit 10")
        click.echo(f"   2. Create rollback point: ecos wal rollback --reason drift_exceeded")
        click.echo(f"   3. Prepare baseline reset: ecos phi prepare-reset")
    else:
        click.echo(f"   Status: ✅ WITHIN LIMITS")
        click.echo(f"\n✅ φ-CPS drift is healthy")


@wal_cli.command(name='chain')
@click.argument('intent_hash')
@click.option(
    '--parent',
    help='Expected parent IntentHash'
)
def verify_chain(intent_hash: str, parent: Optional[str]):
    """
    🔗 Verify IntentHash chain continuity.
    
    Examples:
        ecos wal chain 0x1234567890ABCDEF
        ecos wal chain 0x1234567890ABCDEF --parent 0xABCDEF1234567890
    """
    wal = GlobalWALManager()
    
    click.echo(f"\n🔗 INTENTHASH CHAIN VERIFICATION")
    click.echo("─" * 60)
    
    is_valid, message = wal.validate_chain(
        intent_hash=intent_hash,
        parent_intent_hash=parent
    )
    
    if is_valid:
        click.echo(f"\n✅ {message}")
        
        # Query event details
        events = wal.query_events(limit=1000)
        
        # Find event in chain
        target_event = None
        parent_event = None
        
        for event in events:
            if event.intent_hash == intent_hash:
                target_event = event
            if parent and event.intent_hash == parent:
                parent_event = event
        
        if target_event:
            click.echo(f"\n📊 EVENT DETAILS:")
            click.echo(f"   Operation: {target_event.operation}")
            click.echo(f"   Repo: {target_event.repo}")
            click.echo(f"   φ-CPS: {target_event.phi_cps_current:.4f}")
            click.echo(f"   Validation: {target_event.validation_state}")
        
        if parent_event:
            click.echo(f"\n🔗 PARENT EVENT:")
            click.echo(f"   Operation: {parent_event.operation}")
            click.echo(f"   φ-CPS: {parent_event.phi_cps_current:.4f}")
    else:
        click.echo(f"\n❌ {message}", err=True)
        click.echo(f"\n💡 Check event exists: ecos wal query --limit 100")
        sys.exit(1)


@wal_cli.command(name='rollback')
@click.option(
    '--reason', '-r',
    required=True,
    help='Reason for rollback point creation'
)
@click.option(
    '--metadata',
    help='JSON metadata string'
)
def create_rollback(reason: str, metadata: Optional[str]):
    """
    🔄 Create rollback point (snapshot).
    
    Examples:
        ecos wal rollback --reason "Before major deployment"
        ecos wal rollback -r drift_exceeded
    """
    wal = GlobalWALManager()
    
    # Parse metadata
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            click.echo(f"❌ Invalid JSON metadata: {metadata}", err=True)
            sys.exit(1)
    
    click.echo(f"\n🔄 Creating rollback point")
    click.echo("─" * 60)
    
    rollback_id = wal.create_rollback_point(
        reason=reason,
        metadata=metadata_dict
    )
    
    current_phi = wal._get_current_phi_cps()
    
    click.echo(f"\n✅ Rollback point created!")
    click.echo(f"\n📊 ROLLBACK METADATA:")
    click.echo(f"   🆔 Rollback ID: {rollback_id}")
    click.echo(f"   📈 φ-CPS snapshot: {current_phi:.4f}")
    click.echo(f"   📝 Reason: {reason}")
    
    drift = wal.get_drift()
    click.echo(f"\n📈 Current drift: {drift['relative_drift']:.2%}")
    
    if drift["threshold_exceeded"]:
        click.echo(f"\n⚠️  Drift threshold exceeded")
        click.echo(f"   Consider baseline reset: ecos phi prepare-reset")


@wal_cli.command(name='export')
@click.argument(
    'output_path',
    type=click.Path()
)
@click.option(
    '--format', '-f',
    type=click.Choice(['json', 'csv'], case_sensitive=False),
    default='json',
    help='Output format (default: json)'
)
def export_audit(output_path: str, format: str):
    """
    💾 Export audit trail to file.
    
    Examples:
        ecos wal export audit.json
        ecos wal export audit.csv --format csv
    """
    wal = GlobalWALManager()
    
    output_file = Path(output_path)
    
    click.echo(f"\n💾 Exporting audit trail to {output_file}")
    click.echo("─" * 60)
    
    success = wal.export_audit(
        output_path=output_file,
        format=format.lower()
    )
    
    if success:
        click.echo(f"\n✅ Audit trail exported successfully!")
        click.echo(f"\n📄 File: {output_file.absolute()}")
        click.echo(f"   Format: {format.upper()}")
        
        # Show file size
        if output_file.exists():
            size_bytes = output_file.stat().st_size
            size_kb = size_bytes / 1024
            click.echo(f"   Size: {size_kb:.2f} KB")
    else:
        click.echo(f"\n❌ Export failed", err=True)
        sys.exit(1)


if __name__ == '__main__':
    wal_cli()
