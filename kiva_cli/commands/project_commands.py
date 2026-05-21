#!/usr/bin/env python3
"""
Project Commands Module - KIVA CLI

Integrates ProjectManager with base-3/4 validation into KIVA CLI.
Provides full project lifecycle management commands.
"""

import click
import sys
from pathlib import Path
from typing import Optional

try:
    from kiva_cli.core.project_manager import (
        ProjectManager,
        FrameworkType,
        LifecycleState,
        ValidationState
    )
except ImportError:
    # Fallback import path
    import sys
    from kiva_cli.core.project_manager import (
        ProjectManager,
        FrameworkType,
        LifecycleState,
        ValidationState
    )


@click.group(name='project')
def project_cli():
    """
    🚀 Advanced project lifecycle management.
    
    Provides:
    - Multi-framework scaffolding (FastAPI, React, Go, Python libs)
    - Deployment automation (Docker, Kubernetes, LXC)
    - Base-3 ternary semantic validation
    - Base-4 lifecycle state transitions
    - φ-CPS drift tracking
    - IntentHash L0-L1 verification
    """
    pass


@project_cli.command(name='scaffold')
@click.argument('name')
@click.option(
    '--framework', '--fw',
    type=click.Choice([f.value for f in FrameworkType], case_sensitive=False),
    required=True,
    help='Project framework template'
)
@click.option(
    '--deps',
    multiple=True,
    help='Additional dependencies (repeatable)'
)
@click.option(
    '--workspace',
    type=click.Path(exists=True, file_okay=False),
    help='Workspace root directory'
)
def scaffold_project(name: str, framework: str, deps: tuple, workspace: Optional[str]):
    """
    🏗️  Scaffold new project from framework template.
    
    Supported frameworks:
    - fastapi: Python FastAPI microservice
    - react: React frontend application
    - go_service: Go microservice
    - python_lib: Python library package
    - docker_compose: Docker Compose multi-service
    - lxc_container: LXC container configuration
    
    Examples:
        ecos project scaffold my-api --framework fastapi
        ecos project scaffold webapp --framework react --deps typescript
        ecos project scaffold svc --framework go_service --workspace ~/projects
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    framework_enum = FrameworkType(framework)
    
    click.echo(f"\n🏗️  Scaffolding project '{name}' [framework={framework}]")
    click.echo("─" * 60)
    
    success, config, message = pm.scaffold_project(
        name=name,
        framework=framework_enum,
        additional_deps=list(deps) if deps else None
    )
    
    if success:
        click.echo(f"\n✅ {message}")
        click.echo(f"\n📊 PROJECT METADATA:")
        click.echo(f"   📁 Location: {config.repo_path}")
        click.echo(f"   🔗 IntentHash: {config.intent_hash}")
        click.echo(f"   📈 φ-CPS delta: +{config.phi_cps_delta:.4f}")
        click.echo(f"   ✅ Validation: {config.validation_state}")
        click.echo(f"   🔄 Lifecycle: {config.lifecycle_state}")
        
        if config.dependencies:
            click.echo(f"\n📦 Dependencies: {', '.join(config.dependencies)}")
        
        if config.validation_state == ValidationState.VALID.name:
            click.echo(f"\n🎯 NEXT STEPS:")
            click.echo(f"   cd {config.repo_path}")
            
            if framework == "fastapi":
                click.echo(f"   pip install -r requirements.txt")
                click.echo(f"   uvicorn main:app --reload")
            elif framework == "react":
                click.echo(f"   npm install && npm start")
            elif framework == "go_service":
                click.echo(f"   go mod tidy && go run main.go")
            elif framework == "python_lib":
                click.echo(f"   pip install -e .")
            
            click.echo(f"\n   Deploy with: ecos project deploy {name} --target docker")
        else:
            click.echo(f"\n⚠️  Validation state: {config.validation_state}")
            click.echo(f"   Run validation: ecos project status {name}")
    else:
        click.echo(f"\n❌ {message}", err=True)
        sys.exit(1)


@project_cli.command(name='deploy')
@click.argument('name')
@click.option(
    '--target', '-t',
    type=click.Choice(['docker', 'kubernetes', 'lxc'], case_sensitive=False),
    default='docker',
    help='Deployment target environment'
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
def deploy_project(name: str, target: str, dry_run: bool, workspace: Optional[str]):
    """
    🚀 Deploy project to target environment.
    
    Deployment targets:
    - docker: Containerize and build Docker image
    - kubernetes: Deploy to Kubernetes cluster (K8s manifests)
    - lxc: Deploy as LXC system container
    
    Examples:
        ecos project deploy my-api --target docker
        ecos project deploy webapp --target kubernetes --dry-run
        ecos project deploy legacy-svc --target lxc
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    mode_str = "[DRY-RUN] " if dry_run else ""
    
    click.echo(f"\n🚀 {mode_str}Deploying '{name}' to '{target}'")
    click.echo("─" * 60)
    
    result = pm.deploy_project(
        project_name=name,
        target=target,
        dry_run=dry_run
    )
    
    if result.success:
        click.echo(f"\n✅ {result.message}")
        click.echo(f"\n📊 DEPLOYMENT METADATA:")
        click.echo(f"   🎯 Target: {result.target}")
        click.echo(f"   🔗 IntentHash: {result.intent_hash}")
        click.echo(f"   📈 φ-CPS delta: +{result.phi_cps_delta:.4f}")
        click.echo(f"   ✅ Validation: {result.validation_state.name}")
        
        if result.artifacts:
            click.echo(f"\n📦 ARTIFACTS:")
            for artifact in result.artifacts:
                click.echo(f"   • {artifact}")
        
        if not dry_run:
            click.echo(f"\n🎉 Deployment completed successfully!")
            
            if target == "docker":
                click.echo(f"\n   Run container: docker run {name}:latest")
            elif target == "kubernetes":
                click.echo(f"\n   Check status: kubectl get pods -l app={name}")
            elif target == "lxc":
                click.echo(f"\n   Access container: lxc-attach -n {name}")
    else:
        click.echo(f"\n❌ {result.message}", err=True)
        click.echo(f"\n🔍 DIAGNOSTICS:")
        click.echo(f"   Validation: {result.validation_state.name}")
        sys.exit(1)


@project_cli.command(name='status')
@click.argument('name')
@click.option(
    '--workspace',
    type=click.Path(exists=True, file_okay=False),
    help='Workspace root directory'
)
def project_status(name: str, workspace: Optional[str]):
    """
    📊 Show comprehensive project status.
    
    Displays:
    - Framework and lifecycle state
    - Validation status (base-3 ternary)
    - IntentHash and φ-CPS metrics
    - Deployment history
    - Timestamps
    
    Examples:
        ecos project status my-api
        ecos project status webapp --workspace ~/dev
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    project_status_data = pm.get_project_status(name)
    
    if not project_status_data:
        click.echo(f"\n❌ Project '{name}' not found in registry", err=True)
        click.echo(f"\n💡 List all projects: ecos project list")
        sys.exit(1)
    
    click.echo(f"\n📊 PROJECT STATUS: {name}")
    click.echo("═" * 70)
    
    # Framework & States
    click.echo(f"\n🔧 CONFIGURATION:")
    click.echo(f"   Framework: {project_status_data['framework']}")
    click.echo(f"   Lifecycle: {project_status_data['lifecycle_state']}")
    
    validation_icons = {
        "VALID": "✅",
        "INVALID": "❌",
        "UNKNOWN": "⚠️"
    }
    validation_icon = validation_icons.get(project_status_data['validation_state'], "❓")
    click.echo(f"   Validation: {validation_icon} {project_status_data['validation_state']}")
    
    # Metrics
    click.echo(f"\n📈 METRICS:")
    click.echo(f"   IntentHash: {project_status_data['intent_hash']}")
    click.echo(f"   φ-CPS cumulative Δ: +{project_status_data['phi_cps_delta']:.4f}")
    
    # Deployments
    if project_status_data['deployment_targets']:
        click.echo(f"\n🚀 DEPLOYMENTS:")
        for idx, target in enumerate(project_status_data['deployment_targets'], 1):
            click.echo(f"   {idx}. {target}")
    else:
        click.echo(f"\n⚠️  No deployments recorded")
        click.echo(f"   Deploy with: ecos project deploy {name} --target docker")
    
    # Timestamps
    click.echo(f"\n📅 HISTORY:")
    click.echo(f"   Created: {project_status_data['created_at']}")
    click.echo(f"   Updated: {project_status_data['updated_at']}")


@project_cli.command(name='list')
@click.option(
    '--framework', '--fw',
    type=click.Choice([f.value for f in FrameworkType], case_sensitive=False),
    help='Filter by framework type'
)
@click.option(
    '--lifecycle', '--state',
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
        ecos project list --framework go_service --lifecycle DEPRECATED
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    projects = pm.list_projects()
    
    # Apply filters
    if framework:
        projects = [p for p in projects if p.framework == framework]
    
    if lifecycle:
        projects = [p for p in projects if p.lifecycle_state == lifecycle]
    
    filter_info = []
    if framework:
        filter_info.append(f"framework={framework}")
    if lifecycle:
        filter_info.append(f"lifecycle={lifecycle}")
    
    filters_str = f" [{', '.join(filter_info)}]" if filter_info else ""
    
    click.echo(f"\n📋 REGISTERED PROJECTS ({len(projects)}){filters_str}")
    click.echo("═" * 80)
    
    if not projects:
        click.echo(f"\n⚠️  No projects found")
        if framework or lifecycle:
            click.echo(f"\n💡 Try without filters: ecos project list")
        else:
            click.echo(f"\n💡 Create project: ecos project scaffold <name> --framework fastapi")
        return
    
    for idx, project in enumerate(projects, 1):
        lifecycle_icons = {
            "GENESIS": "🌱",
            "ACTIVE": "✅",
            "DEPRECATED": "⚠️",
            "ARCHIVED": "📦"
        }
        
        validation_icons = {
            "VALID": "✅",
            "INVALID": "❌",
            "UNKNOWN": "❓"
        }
        
        lifecycle_icon = lifecycle_icons.get(project.lifecycle_state, "❓")
        validation_icon = validation_icons.get(project.validation_state, "❓")
        
        click.echo(f"\n{idx}. {lifecycle_icon} {project.name}")
        click.echo(f"   Framework: {project.framework}")
        click.echo(f"   State: {project.lifecycle_state} | Validation: {validation_icon} {project.validation_state}")
        click.echo(f"   φ-CPS Δ: +{project.phi_cps_delta:.4f}")
        
        if project.deployment_targets:
            targets_str = ", ".join(project.deployment_targets)
            click.echo(f"   Deployed: {targets_str}")


@project_cli.command(name='lifecycle')
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
def lifecycle_transition(name: str, new_state: str, workspace: Optional[str]):
    """
    🔄 Transition project lifecycle state (base-4).
    
    Valid transitions:
    - GENESIS → ACTIVE | ARCHIVED
    - ACTIVE → DEPRECATED | ARCHIVED
    - DEPRECATED → ACTIVE | ARCHIVED
    - ARCHIVED → (terminal state, no transitions)
    
    Examples:
        ecos project lifecycle my-api ACTIVE
        ecos project lifecycle old-service DEPRECATED
        ecos project lifecycle legacy-app ARCHIVED
    """
    workspace_path = Path(workspace) if workspace else None
    pm = ProjectManager(workspace_root=workspace_path)
    
    new_state_enum = LifecycleState[new_state]
    
    click.echo(f"\n🔄 Transitioning '{name}' to {new_state}")
    click.echo("─" * 60)
    
    success, message = pm.transition_lifecycle(name, new_state_enum)
    
    if success:
        click.echo(f"\n✅ {message}")
        
        # Show updated metrics
        project_status_data = pm.get_project_status(name)
        if project_status_data:
            click.echo(f"\n📈 UPDATED METRICS:")
            click.echo(f"   φ-CPS cumulative Δ: +{project_status_data['phi_cps_delta']:.4f}")
            click.echo(f"   Lifecycle: {project_status_data['lifecycle_state']}")
    else:
        click.echo(f"\n❌ {message}", err=True)
        click.echo(f"\n💡 View valid transitions: ecos project lifecycle --help")
        sys.exit(1)


if __name__ == '__main__':
    project_cli()
