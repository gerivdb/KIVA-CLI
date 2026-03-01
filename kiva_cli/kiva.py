#!/usr/bin/env python3
"""
KIVA CLI - Project & Deployment Orchestrator
Main entry point for KIVA CLI commands
"""
import click
import sys
from pathlib import Path

from kiva_cli.core.project_manager import ProjectManager
from kiva_cli.core.deployment_manager import DeploymentManager
from kiva_cli.core.config_manager import ConfigManager

# Command groups
from kiva_cli.commands.scaffold import scaffold_group
from kiva_cli.commands.secrets import secrets
from kiva_cli.commands.monitoring import monitoring
from kiva_cli.commands.rollback import rollback_group
from kiva_cli.commands.health import health
from kiva_cli.commands.project_commands import project_cli  # NEW: Advanced ProjectManager integration

__version__ = "1.0.0"


@click.group()
@click.version_option(__version__)
def cli():
    """KIVA CLI - Project & Deployment Orchestrator
    
    Advanced capabilities:
    - Multi-framework project scaffolding
    - Base-3 ternary semantic validation
    - Base-4 lifecycle state management
    - φ-CPS drift tracking
    - IntentHash L0-L1 verification
    """
    pass


# Legacy project command (deprecated, use project_cli group)
@cli.command(name='project-legacy')
@click.argument("name")
@click.option("--template", "-t", default="fastapi", help="Project template (fastapi, react, go, rust)")
@click.option("--path", "-p", type=click.Path(), help="Target directory")
@click.option("--overwrite", is_flag=True, help="Overwrite existing directory")
def project_legacy(name, template, path, overwrite):
    """[DEPRECATED] Use 'ecos project scaffold' instead"""
    click.echo("⚠️  This command is deprecated. Use: ecos project scaffold")
    try:
        manager = ProjectManager()
        result = manager.init_project(
            name=name,
            template=template,
            target_dir=Path(path) if path else None,
            overwrite=overwrite
        )
        
        click.echo(f"✅ Project '{name}' created successfully!")
        click.echo(f"   Template: {result['template']}")
        click.echo(f"   Location: {result['project_path']}")
        click.echo(f"   Files: {result['count']}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--env", "-e", default="staging", help="Target environment (dev, staging, production)")
@click.option("--strategy", "-s", default="rolling", help="Deployment strategy")
@click.option("--dry-run", is_flag=True, help="Simulate deployment")
def deploy(project_path, env, strategy, dry_run):
    """Deploy project to environment (legacy interface)"""
    try:
        manager = DeploymentManager()
        result = manager.deploy(
            project_path=Path(project_path),
            environment=env,
            strategy=strategy,
            dry_run=dry_run
        )
        
        status_icon = "🔍" if dry_run else "✅"
        click.echo(f"{status_icon} Deployment {result['status']}")
        click.echo(f"   Workflow ID: {result['workflow_id']}")
        click.echo(f"   Version: {result['deployed_version']}")
        click.echo(f"   Environment: {result['environment']}")
        
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--schema", "-s", default="kiva-config", help="Schema name")
def config(config_file, schema):
    """Validate configuration file"""
    try:
        manager = ConfigManager()
        result = manager.validate(
            config_file=Path(config_file),
            schema_name=schema
        )
        
        if result["valid"]:
            click.echo(f"✅ Configuration is VALID")
        else:
            click.echo(f"❌ Configuration is INVALID")
            for error in result["errors"]:
                click.echo(f"   - {error}")
            sys.exit(1)
    
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


# Register command groups
cli.add_command(scaffold_group)
cli.add_command(secrets)
cli.add_command(monitoring)
cli.add_command(rollback_group)
cli.add_command(health)
cli.add_command(project_cli)  # NEW: Advanced ProjectManager CLI group


if __name__ == "__main__":
    cli()
