#!/usr/bin/env python3
"""KIVA-CLI main entry point.

ECOS-CLI unified command-line interface for:
- Project scaffolding (ProjectManager)
- Event tracking (GlobalWALManager)
- Entity lifecycle (CitizenManager)
- Skill registry (SkillManager)
"""

import click
from kiva_cli.commands.project_commands import project_cli
from kiva_cli.commands.wal_commands import wal_cli
from kiva_cli.commands.citizen_commands import citizen_cli
from kiva_cli.commands.skill_commands import skill_cli


@click.group()
@click.version_option(version="0.4.0", prog_name="KIVA-CLI")
def cli():
    """KIVA-CLI - ECOS unified command-line interface.
    
    Provides:
    - Project scaffolding and management
    - Cross-repo event tracking with φ-CPS
    - Entity lifecycle management (L0-L5)
    - Reusable skill registry and execution
    """
    pass


# Register command groups
cli.add_command(project_cli, name="project")
cli.add_command(wal_cli, name="wal")
cli.add_command(citizen_cli, name="citizen")
cli.add_command(skill_cli, name="skill")


if __name__ == "__main__":
    cli()
