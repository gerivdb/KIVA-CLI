# KIVA CLI - Deployment Commands
import os
import click
from ..core.deployment_manager import DeploymentManager

# Legacy compatibility functions
from .legacy_compat import check_deployment_status, execute_deployment, validate_config


def deploy_project(project: str, environment: str = "staging",
                   validate: bool = True) -> dict:
    """Deploy a project to specified environment (legacy dict wrapper)."""
    if validate and not validate_config({"app_name": project}):
        return {
            "status": "FAILED",
            "message": "Validation failed for project configuration",
        }
    try:
        result = execute_deployment(project=project, environment=environment)
        if isinstance(result, dict) and result.get("status") == "FAILED":
            return result
        return {
            "status": "SUCCESS",
            "deployment_id": result.get("deployment_id", "dep-{}-{}-{}".format(project, environment, os.getpid())),
            "project": project,
            "environment": environment,
        }
    except Exception as exc:
        return {
            "status": "FAILED",
            "error": str(exc),
            "project": project,
            "environment": environment,
        }

@click.group()
def deploy():
    '''Deployment management commands.'''
    pass

@deploy.command()
@click.argument('target')  # e.g., 'api', 'frontend'
@click.option('--env', default='staging', help='Environment (staging, production)')
@click.option('--strategy', default='rolling', help='Deployment strategy (rolling, blue-green, canary)')
@click.option('--dry-run', is_flag=True, help='Simulate deployment')
@click.option('--no-health-check', is_flag=True, help='Skip health checks')
def staging(target: str, env: str, strategy: str, dry_run: bool, no_health_check: bool):
    '''Deploy to staging environment.
    
    Examples:
        kiva deploy staging api
        kiva deploy staging frontend --strategy=blue-green --dry-run
    '''
    manager = DeploymentManager()
    
    if dry_run:
        click.secho("📊 DRY RUN MODE - No actual deployment", fg='yellow')
    
    result = manager.deploy(
        target=target,
        env=env,
        strategy=strategy,
        dry_run=dry_run,
        health_check=not no_health_check
    )
    
    if result.success:
        click.secho(f"✅ Deployment successful: {target} → {env}", fg='green')
        click.echo(f"  Version: {result.version}")
        click.echo(f"  URL: {result.deployment_url}")
        click.echo(f"  Strategy: {result.strategy}")
        click.echo(f"  Duration: {result.duration_seconds:.2f}s")
        if result.health_check_passed:
            click.secho("  ✅ Health checks passed", fg='green')
        if result.warnings:
            for warning in result.warnings:
                click.secho(f"  ⚠️  {warning}", fg='yellow')
    else:
        click.secho(f"❌ Deployment failed: {result.error}", fg='red', err=True)
        raise click.Abort()

@deploy.command()
@click.argument('target')
@click.option('--env', default='production', help='Environment')
@click.option('--strategy', default='blue-green', help='Deployment strategy')
@click.confirmation_option(prompt='Deploy to PRODUCTION. Are you sure?')
def production(target: str, env: str, strategy: str):
    '''Deploy to production environment (requires confirmation).
    
    Example:
        kiva deploy production api --strategy=canary
    '''
    manager = DeploymentManager()
    
    result = manager.deploy(
        target=target,
        env=env,
        strategy=strategy,
        dry_run=False,
        health_check=True
    )
    
    if result.success:
        click.secho(f"🚀 Production deployment successful: {target}", fg='green', bold=True)
        click.echo(f"  Version: {result.version}")
        click.echo(f"  URL: {result.deployment_url}")
        if result.warnings:
            for warning in result.warnings:
                click.secho(f"  ⚠️  {warning}", fg='yellow')
    else:
        click.secho(f"❌ Deployment failed: {result.error}", fg='red', err=True)
        raise click.Abort()

@deploy.command()
@click.argument('deployment_id')
@click.option('--to-version', required=True, help='Target version to rollback to')
@click.confirmation_option(prompt='Rollback deployment. Are you sure?')
def rollback(deployment_id: str, to_version: str):
    '''Rollback deployment to previous version.
    
    Example:
        kiva deploy rollback api-v1.2.0 --to-version=v1.1.0
    '''
    manager = DeploymentManager()
    result = manager.rollback(
        deployment_id=deployment_id,
        to_version=to_version
    )
    
    if result.success:
        click.secho(f"⏪ Rollback successful: {deployment_id} → {to_version}", fg='green')
        if result.warnings:
            for warning in result.warnings:
                click.echo(f"  {warning}")
    else:
        click.secho(f"❌ Rollback failed: {result.error}", fg='red', err=True)
        raise click.Abort()

@deploy.command()
@click.argument('deployment_id')
def status(deployment_id: str):
    '''Get deployment status.
    
    Example:
        kiva deploy status api-v1.2.0
    '''
    manager = DeploymentManager()
    status_info = manager.get_deployment_status(deployment_id)
    
    if status_info:
        click.secho(f"📊 Deployment Status: {deployment_id}", fg='blue')
        for key, value in status_info.items():
            click.echo(f"  {key}: {value}")
    else:
        click.secho(f"❌ Deployment not found: {deployment_id}", fg='red', err=True)
