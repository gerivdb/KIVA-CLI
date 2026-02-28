# KIVA CLI - Deploy Commands
import click
from ..core.deployment_manager import DeploymentManager

@click.group()
def deploy():
    '''Deployment management commands.'''
    pass

@deploy.command()
@click.argument('target')
@click.option('--env', default='staging', help='Target environment')
@click.option('--strategy', default='rolling', help='Deployment strategy')
@click.option('--dry-run', is_flag=True, help='Simulate deployment')
def staging(target: str, env: str, strategy: str, dry_run: bool):
    '''Deploy to staging environment.'''
    manager = DeploymentManager()
    result = manager.deploy(target, env, strategy, dry_run)
    
    if result.success:
        click.secho(f"✅ Deployment successful: {target} → {env}", fg='green')
        click.echo(f"URL: {result.deployment_url}")
    else:
        click.secho(f"❌ Deployment failed: {result.error}", fg='red', err=True)
        raise click.Abort()
