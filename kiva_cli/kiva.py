#!/usr/bin/env python3
"""
KIVA CLI - Main Entry Point

ECOS-CLI unified command-line interface for project automation,
workflow orchestration, and entity lifecycle management.
"""

import click
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import command groups
try:
    from kiva_cli.commands.project_commands import project_cli
except ImportError:
    project_cli = None

try:
    from kiva_cli.commands.wal_commands import wal_cli
except ImportError:
    wal_cli = None

try:
    from kiva_cli.commands.citizen_commands import citizen_cli
except ImportError:
    citizen_cli = None


@click.group()
@click.version_option(version='0.3.0', prog_name='KIVA-CLI')
def cli():
    """
    KIVA-CLI - ECOS Project Automation & Workflow Orchestration
    
    Unified CLI for:
    - Project scaffolding and lifecycle management
    - Global WAL (Write-Ahead Log) event tracking
    - Citizen (entity) registration and validation
    - Cross-repository synchronization
    - φ-CPS drift monitoring
    """
    pass


# Register command groups
if project_cli:
    cli.add_command(project_cli, name='project')

if wal_cli:
    cli.add_command(wal_cli, name='wal')

if citizen_cli:
    cli.add_command(citizen_cli, name='citizen')


if __name__ == '__main__':
    cli()
