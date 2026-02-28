# KIVA CLI - Project Commands
import click
from ..core.project_manager import ProjectManager

@click.group()
def project():
    '''Project lifecycle management commands.'''
    pass

@project.command()
@click.option('--template', required=True, help='Project template')
@click.option('--name', required=True, help='Project name')
@click.option('--path', default='.', help='Target directory')
def init(template: str, name: str, path: str):
    '''Initialize new project from template.'''
    manager = ProjectManager()
    result = manager.init_project(template=template, name=name, path=path)
    
    if result.success:
        click.secho(f"✅ Project '{name}' initialized", fg='green')
    else:
        click.secho(f"❌ Error: {result.error}", fg='red', err=True)
        raise click.Abort()
