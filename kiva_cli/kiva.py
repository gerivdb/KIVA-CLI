# KIVA CLI - Main Entry Point
import click
from .commands import project, deploy, config

@click.group()
@click.version_option(version='0.1.0')
def cli():
    '''KIVA CLI - Projects & Applications Orchestrator for Ecosystem-1.'''
    pass

# Register command groups
cli.add_command(project.project)
cli.add_command(deploy.deploy)
cli.add_command(config.config)

if __name__ == '__main__':
    cli()
