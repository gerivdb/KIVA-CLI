#!/usr/bin/env python3
"""
Citizen CLI Commands - Entity Lifecycle Management

Provides CLI interface for CitizenManager:
- register: Create new entity
- promote: Upgrade entity level
- demote: Downgrade or archive entity
- list: Query citizens with filters
- export: Export registry to file
- validate: Update validation state
- sync: Cross-repo synchronization
"""

import click
import json
from pathlib import Path
from typing import Optional
from tabulate import tabulate

try:
    from kiva_cli.core.citizen_manager import (
        CitizenManager,
        EntityLevel,
        EntityType,
        LifecycleState,
        ValidationState
    )
except ImportError:
    CitizenManager = None
    EntityLevel = None
    EntityType = None
    LifecycleState = None
    ValidationState = None


@click.group(name='citizen')
def citizen_cli():
    """Citizen Manager - Entity Lifecycle & Validation."""
    pass


@citizen_cli.command(name='register')
@click.option('--name', required=True, help='Entity name')
@click.option('--type', 'entity_type', required=True,
              type=click.Choice(['PROJECT', 'SERVICE', 'COMPONENT', 'TOOL', 
                                 'LIBRARY', 'FRAMEWORK', 'WORKFLOW', 'AGENT'],
                                case_sensitive=False),
              help='Entity type')
@click.option('--repo', required=True, help='Repository name')
@click.option('--level', default='L0_GENESIS',
              type=click.Choice(['L0_GENESIS', 'L1_VALIDATED', 'L2_OPERATIONAL',
                                 'L3_PRODUCTION', 'L4_CRITICAL', 'L5_LEGACY']),
              help='Initial entity level')
@click.option('--metadata', type=str, help='JSON metadata')
def register_citizen(name: str, entity_type: str, repo: str, 
                     level: str, metadata: Optional[str]):
    """Register new citizen (entity)."""
    if not CitizenManager:
        click.echo("❌ CitizenManager not available", err=True)
        return
    
    manager = CitizenManager()
    
    # Parse metadata
    meta_dict = None
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except json.JSONDecodeError:
            click.echo("❌ Invalid JSON metadata", err=True)
            return
    
    # Register citizen
    try:
        citizen = manager.register_citizen(
            name=name,
            entity_type=EntityType[entity_type.upper()],
            repo=repo,
            entity_level=EntityLevel[level],
            metadata=meta_dict
        )
        
        click.echo(f"✅ Citizen registered: {citizen.citizen_id}")
        click.echo(f"   Name: {citizen.name}")
        click.echo(f"   Type: {citizen.entity_type}")
        click.echo(f"   Level: {citizen.entity_level}")
        click.echo(f"   Repository: {citizen.repo}")
        click.echo(f"   φ-CPS: {citizen.phi_cps:.4f}")
        click.echo(f"   IntentHash: {citizen.intent_hash}")
        
    except Exception as e:
        click.echo(f"❌ Registration failed: {str(e)}", err=True)


@citizen_cli.command(name='promote')
@click.argument('citizen_id')
@click.option('--level', required=True,
              type=click.Choice(['L1_VALIDATED', 'L2_OPERATIONAL',
                                 'L3_PRODUCTION', 'L4_CRITICAL']),
              help='Target entity level')
def promote_citizen(citizen_id: str, level: str):
    """Promote citizen to higher level."""
    if not CitizenManager:
        click.echo("❌ CitizenManager not available", err=True)
        return
    
    manager = CitizenManager()
    
    success, message, updated = manager.promote_entity(
        citizen_id=citizen_id,
        target_level=EntityLevel[level]
    )
    
    if success:
        click.echo(f"✅ {message}")
        if updated:
            click.echo(f"   New level: {updated.entity_level}")
            click.echo(f"   φ-CPS: {updated.phi_cps:.4f}")
    else:
        click.echo(f"❌ {message}", err=True)


@citizen_cli.command(name='demote')
@click.argument('citizen_id')
@click.option('--level', required=True,
              type=click.Choice(['L0_GENESIS', 'L1_VALIDATED', 'L2_OPERATIONAL',
                                 'L3_PRODUCTION', 'L5_LEGACY']),
              help='Target entity level')
@click.option('--reason', required=True, help='Reason for demotion')
def demote_citizen(citizen_id: str, level: str, reason: str):
    """Demote citizen to lower level or archive."""
    if not CitizenManager:
        click.echo("❌ CitizenManager not available", err=True)
        return
    
    manager = CitizenManager()
    
    success, message, updated = manager.demote_entity(
        citizen_id=citizen_id,
        target_level=EntityLevel[level],
        reason=reason
    )
    
    if success:
        click.echo(f"✅ {message}")
        if updated:
            click.echo(f"   New level: {updated.entity_level}")
            click.echo(f"   φ-CPS: {updated.phi_cps:.4f}")
            click.echo(f"   Reason: {reason}")
    else:
        click.echo(f"❌ {message}", err=True)


@citizen_cli.command(name='list')
@click.option('--repo', help='Filter by repository')
@click.option('--level',
              type=click.Choice(['L0_GENESIS', 'L1_VALIDATED', 'L2_OPERATIONAL',
                                 'L3_PRODUCTION', 'L4_CRITICAL', 'L5_LEGACY']),
              help='Filter by entity level')
@click.option('--state',
              type=click.Choice(['GENESIS', 'ACTIVE', 'DEPRECATED', 'ARCHIVED']),
              help='Filter by lifecycle state')
@click.option('--limit', default=50, help='Maximum results (default: 50)')
@click.option('--format', 'output_format', default='table',
              type=click.Choice(['table', 'json']),
              help='Output format')
def list_citizens(repo: Optional[str], level: Optional[str], 
                  state: Optional[str], limit: int, output_format: str):
    """List citizens with filters."""
    if not CitizenManager:
        click.echo("❌ CitizenManager not available", err=True)
        return
    
    manager = CitizenManager()
    
    # Parse filters
    entity_level = EntityLevel[level] if level else None
    lifecycle_state = LifecycleState[state] if state else None
    
    # Query citizens
    citizens = manager.list_citizens(
        repo=repo,
        entity_level=entity_level,
        lifecycle_state=lifecycle_state,
        limit=limit
    )
    
    if not citizens:
        click.echo("No citizens found")
        return
    
    # Output
    if output_format == 'json':
        citizens_data = [
            {
                'citizen_id': c.citizen_id,
                'name': c.name,
                'type': c.entity_type,
                'level': c.entity_level,
                'lifecycle': c.lifecycle_state,
                'validation': c.validation_state,
                'repo': c.repo,
                'phi_cps': c.phi_cps,
                'created_at': c.created_at
            }
            for c in citizens
        ]
        click.echo(json.dumps(citizens_data, indent=2))
    
    else:  # table format
        headers = ['ID', 'Name', 'Type', 'Level', 'State', 'Repo', 'φ-CPS']
        rows = [
            [
                c.citizen_id[:12] + '...',
                c.name[:20],
                c.entity_type,
                c.entity_level,
                c.lifecycle_state,
                c.repo,
                f"{c.phi_cps:.4f}"
            ]
            for c in citizens
        ]
        
        click.echo(f"\n✅ Found {len(citizens)} citizen(s):\n")
        click.echo(tabulate(rows, headers=headers, tablefmt='grid'))


@citizen_cli.command(name='export')
@click.argument('output_path', type=click.Path())
@click.option('--format', 'output_format', default='json',
              type=click.Choice(['json', 'csv']),
              help='Export format')
def export_registry(output_path: str, output_format: str):
    """Export citizen registry to file."""
    if not CitizenManager:
        click.echo("❌ CitizenManager not available", err=True)
        return
    
    manager = CitizenManager()
    
    output_file = Path(output_path)
    
    success = manager.export_registry(
        output_path=output_file,
        format=output_format
    )
    
    if success:
        click.echo(f"✅ Registry exported: {output_file}")
        click.echo(f"   Format: {output_format}")
    else:
        click.echo(f"❌ Export failed", err=True)


@citizen_cli.command(name='validate')
@click.argument('citizen_id')
@click.option('--state', required=True,
              type=click.Choice(['PENDING', 'VALID', 'INVALID']),
              help='Validation state')
def validate_citizen(citizen_id: str, state: str):
    """Update citizen validation state."""
    if not CitizenManager:
        click.echo("❌ CitizenManager not available", err=True)
        return
    
    manager = CitizenManager()
    
    # Map string to ValidationState
    if ValidationState:
        validation_state = ValidationState[state]
    else:
        validation_state = state
    
    success, message = manager.validate_entity(
        citizen_id=citizen_id,
        validation_state=validation_state
    )
    
    if success:
        click.echo(f"✅ {message}")
    else:
        click.echo(f"❌ {message}", err=True)


@citizen_cli.command(name='sync')
@click.option('--repos', help='Comma-separated list of repos (default: all ecosystem-1)')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
def sync_repos(repos: Optional[str], dry_run: bool):
    """Synchronize citizens across repositories."""
    click.echo("🔄 Cross-repo synchronization initiated...")
    
    # Import sync script
    try:
        import subprocess
        import sys
        
        # Build command
        cmd = [sys.executable, 'scripts/cross_repo_sync.py']
        
        if repos:
            cmd.extend(['--repos', repos])
        
        if dry_run:
            cmd.append('--dry-run')
        
        # Execute
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        click.echo(result.stdout)
        
        if result.returncode != 0:
            click.echo(result.stderr, err=True)
            click.echo("❌ Sync failed", err=True)
        else:
            click.echo("✅ Sync completed")
    
    except Exception as e:
        click.echo(f"❌ Sync error: {str(e)}", err=True)
