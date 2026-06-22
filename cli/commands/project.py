#!/usr/bin/env python3
"""
Project CLI Commands - KIVA-CLI Project Management Interface

Provides CLI commands for:
- scaffold: Create new projects from templates
- deploy: Deploy projects to targets
- status: Show project status
- lifecycle: Manage project lifecycle transitions
- list: List all projects
"""

import click
import sys
from pathlib import Path
from typing import Optional

try:
    from tools.core.project_manager import (
        ProjectManager,
        FrameworkType,
        LifecycleState,
        ValidationState
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tools.core.project_manager import (
        ProjectManager,
        FrameworkType,
        LifecycleState,
        ValidationState
    )


@click.group()
def project():
    """🚀 Project lifecycle management commands."""
    pass


@project.command()
@click.argument('name')
@click.option(
    '--framework',
    type=click.Choice([f.value for f in FrameworkType], case_sensitive=False),
    required=True,
    help='Project framework template'
)
@click.option(
    '--deps',
    multiple=True,
    help='Additional dependencies to include'
)
@click.option(
    '--workspace',
    type=click.Path(exists=True, file_okay=False),
    help='Workspace root directory'
)
def scaffold(name: str, framework: str, deps: tuple, workspace: Optional[str]):
    """
    🏗  Scaffold new project from framework template.
    
    Examples:
        ecos project scaffold my-api --framework fastapi
        ecos project scaffold web-app --framework react --deps typescript --deps tailwind
        ecos project scaffold go-svc --framework go_service
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    # Convert framework string to enum
    framework_enum = FrameworkType(framework)
    
    click.echo(f"🏗  Scaffolding project '{name}' with framework '{framework}'...")
    
    success, config, message = pm.scaffold_project(
        name=name,
        framework=framework_enum,
        additional_deps=list(deps) if deps else None
    )
    
    if success:
        click.echo(f"✅ {message}")
        click.echo(f"\n📁 Project location: {config.repo_path}")
        click.echo(f"🔗 IntentHash: {config.intent_hash}")
        click.echo(f"📊 φ-CPS delta: +{config.phi_cps_delta:.4f}")
        click.echo(f"🔍 Validation: {config.validation_state}")
        
        if config.validation_state == ValidationState.VALID.name:
            click.echo("\n✨ Project ready for development!")
            click.echo(f"\nNext steps:")
            click.echo(f"  cd {config.repo_path}")
            if framework == "fastapi":
                click.echo(f"  pip install -r requirements.txt")
                click.echo(f"  uvicorn main:app --reload")
            elif framework == "react":
                click.echo(f"  npm install")
                click.echo(f"  npm start")
            elif framework == "go_service":
                click.echo(f"  go mod tidy")
                click.echo(f"  go run main.go")
        else:
            click.echo(f"\n⚠️  Validation warning: {config.validation_state}")
    else:
        click.echo(f"❌ {message}", err=True)
        sys.exit(1)


@project.command()
@click.argument('name')
@click.option(
    '--target',
    type=click.Choice(['docker', 'kubernetes', 'lxc'], case_sensitive=False),
    default='docker',
    help='Deployment target'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Validate deployment without executing'
)
@click.option(
    '--workspace',
    type=click.Path(exists=True, file_okay=False),
    help='Workspace root directory'
)
def deploy(name: str, target: str, dry_run: bool, workspace: Optional[str]):
    """
    🚀 Deploy project to target environment.
    
    Examples:
        ecos project deploy my-api --target docker
        ecos project deploy web-app --target kubernetes --dry-run
        ecos project deploy go-svc --target lxc
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    mode_str = "[DRY-RUN] " if dry_run else ""
    click.echo(f"🚀 {mode_str}Deploying project '{name}' to '{target}'...")
    
    result = pm.deploy_project(
        project_name=name,
        target=target,
        dry_run=dry_run
    )
    
    if result.success:
        click.echo(f"✅ {result.message}")
        click.echo(f"\n🔗 IntentHash: {result.intent_hash}")
        click.echo(f"📊 φ-CPS delta: +{result.phi_cps_delta:.4f}")
        click.echo(f"🔍 Validation: {result.validation_state.name}")
        
        if result.artifacts:
            click.echo(f"\n📦 Artifacts generated:")
            for artifact in result.artifacts:
                click.echo(f"  • {artifact}")
        
        if not dry_run:
            click.echo(f"\n✨ Project deployed to {target} successfully!")
    else:
        click.echo(f"❌ {result.message}", err=True)
        sys.exit(1)


@project.command()
@click.argument('name')
@click.option(
    '--workspace',
    type=click.Path(exists=True, file_okay=False),
    help='Workspace root directory'
)
def status(name: str, workspace: Optional[str]):
    """
    📊 Show comprehensive project status.
    
    Examples:
        ecos project status my-api
        ecos project status web-app
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    project_status = pm.get_project_status(name)
    
    if not project_status:
        click.echo(f"❌ Project '{name}' not found", err=True)
        sys.exit(1)
    
    click.echo(f"\n📊 PROJECT STATUS: {name}")
    click.echo("=" * 60)
    
    click.echo(f"\n📁 Framework: {project_status['framework']}")
    click.echo(f"🔄 Lifecycle: {project_status['lifecycle_state']}")
    click.echo(f"✅ Validation: {project_status['validation_state']}")
    click.echo(f"\n🔗 IntentHash: {project_status['intent_hash']}")
    click.echo(f"📊 φ-CPS cumulative delta: +{project_status['phi_cps_delta']:.4f}")
    
    if project_status['deployment_targets']:
        click.echo(f"\n🚀 Deployment targets:")
        for target in project_status['deployment_targets']:
            click.echo(f"  • {target}")
    else:
        click.echo(f"\n⚠️  No deployments yet")
    
    click.echo(f"\n📅 Created: {project_status['created_at']}")
    click.echo(f"📅 Updated: {project_status['updated_at']}")


@project.command(name='list')
@click.option(
    '--framework',
    type=click.Choice([f.value for f in FrameworkType], case_sensitive=False),
    help='Filter by framework'
)
@click.option(
    '--lifecycle',
    type=click.Choice([s.name for s in LifecycleState], case_sensitive=False),
    help='Filter by lifecycle state'
)
@click.option(
    '--workspace',
    type=click.Path(exists=True, file_okay=False),
    help='Workspace root directory'
)
def list_projects(framework: Optional[str], lifecycle: Optional[str], workspace: Optional[str]):
    """
    📋 List all registered projects.
    
    Examples:
        ecos project list
        ecos project list --framework fastapi
        ecos project list --lifecycle ACTIVE
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    projects = pm.list_projects()
    
    # Apply filters
    if framework:
        projects = [p for p in projects if p.framework == framework]
    
    if lifecycle:
        projects = [p for p in projects if p.lifecycle_state == lifecycle]
    
    if not projects:
        click.echo("📋 No projects found")
        return
    
    click.echo(f"\n📋 REGISTERED PROJECTS ({len(projects)})")
    click.echo("=" * 80)
    
    for project in projects:
        lifecycle_icon = {
            "GENESIS": "🌱",
            "ACTIVE": "✅",
            "DEPRECATED": "⚠️",
            "ARCHIVED": "📦"
        }.get(project.lifecycle_state, "❓")
        
        validation_icon = {
            "VALID": "✅",
            "INVALID": "❌",
            "UNKNOWN": "❓"
        }.get(project.validation_state, "❓")
        
        click.echo(f"\n{lifecycle_icon} {project.name}")
        click.echo(f"   Framework: {project.framework}")
        click.echo(f"   State: {project.lifecycle_state} | Validation: {validation_icon} {project.validation_state}")
        click.echo(f"   φ-CPS Δ: +{project.phi_cps_delta:.4f}")
        
        if project.deployment_targets:
            click.echo(f"   Deployed to: {', '.join(project.deployment_targets)}")


@project.command()
@click.argument('name')
@click.argument(
    'new_state',
    type=click.Choice([s.name for s in LifecycleState], case_sensitive=False)
)
@click.option(
    '--workspace',
    type=click.Path(exists=True, file_okay=False),
    help='Workspace root directory'
)
def lifecycle(name: str, new_state: str, workspace: Optional[str]):
    """
    🔄 Transition project lifecycle state.
    
    Valid transitions:
      GENESIS → ACTIVE | ARCHIVED
      ACTIVE → DEPRECATED | ARCHIVED
      DEPRECATED → ACTIVE | ARCHIVED
      ARCHIVED → (terminal state)
    
    Examples:
        ecos project lifecycle my-api ACTIVE
        ecos project lifecycle old-app DEPRECATED
        ecos project lifecycle legacy-svc ARCHIVED
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    new_state_enum = LifecycleState[new_state]
    
    click.echo(f"🔄 Transitioning '{name}' to {new_state}...")
    
    success, message = pm.transition_lifecycle(name, new_state_enum)
    
    if success:
        click.echo(f"✅ {message}")
        
        # Show updated status
        project_status = pm.get_project_status(name)
        if project_status:
            click.echo(f"\n📊 Updated φ-CPS delta: +{project_status['phi_cps_delta']:.4f}")
    else:
        click.echo(f"❌ {message}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    project()
