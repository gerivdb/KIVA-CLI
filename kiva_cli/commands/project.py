# KIVA CLI - Project Commands
import click
from ..core.project_manager import ProjectManager

@click.group()
def project():
    '''Project lifecycle management commands.'''
    pass

@project.command()
@click.option('--template', required=True, help='Project template (fastapi, react, go, rust)')
@click.option('--name', required=True, help='Project name')
@click.option('--path', default='.', help='Target directory')
def init(template: str, name: str, path: str):
    '''Initialize new project from template.
    
    Examples:
        kiva project init --template=fastapi --name=my-api
        kiva project init --template=react --name=my-app --path=./frontend
    '''
    manager = ProjectManager()
    result = manager.init_project(template=template, name=name, path=path)
    
    if result.success:
        click.secho(f"✅ Project '{name}' initialized successfully", fg='green')
        click.echo(f"  Path: {result.project_path}")
        click.echo(f"  Template: {template}")
        if result.files_created:
            click.echo(f"  Files created: {len(result.files_created)}")
        if result.warnings:
            for warning in result.warnings:
                click.secho(f"  ⚠️  {warning}", fg='yellow')
    else:
        click.secho(f"❌ Error: {result.error}", fg='red', err=True)
        raise click.Abort()

@project.command()
@click.option('--type', 'element_type', required=True, help='Element type (component, service, model)')
@click.option('--name', required=True, help='Element name')
@click.option('--typescript/--no-typescript', default=False, help='Use TypeScript (React)')
@click.option('--path', default='.', help='Project directory')
def scaffold(element_type: str, name: str, typescript: bool, path: str):
    '''Scaffold project elements (components, services, models).
    
    Examples:
        kiva project scaffold --type=component --name=Button
        kiva project scaffold --type=service --name=AuthService --typescript
    '''
    manager = ProjectManager()
    result = manager.scaffold_element(
        element_type=element_type,
        name=name,
        typescript=typescript,
        project_path=path
    )
    
    if result.success:
        click.secho(f"✅ {element_type.capitalize()} '{name}' scaffolded", fg='green')
        if result.files_created:
            for file in result.files_created:
                click.echo(f"  Created: {file}")
    else:
        click.secho(f"❌ Error: {result.error}", fg='red', err=True)
        raise click.Abort()

@project.command('list')
@click.option('--path', default='.', help='Directory to scan')
def list_projects(path: str):
    '''List projects in directory.
    
    Example:
        kiva project list --path=~/projects
    '''
    manager = ProjectManager()
    result = manager.list_projects(path=path)
    
    if result.success:
        click.secho("📁 Projects found:", fg='blue')
        if result.warnings:
            for warning in result.warnings:
                click.echo(f"  {warning}")
    else:
        click.secho(f"❌ Error: {result.error}", fg='red', err=True)

@project.command()
@click.option('--name', required=True, help='Project name')
@click.option('--path', default='.', help='Projects directory')
@click.confirmation_option(prompt='Are you sure you want to delete this project?')
def clean(name: str, path: str):
    '''Delete project directory (with confirmation).
    
    Example:
        kiva project clean --name=my-old-project
    '''
    from pathlib import Path
    import shutil
    
    project_path = Path(path) / name
    if not project_path.exists():
        click.secho(f"❌ Project not found: {project_path}", fg='red', err=True)
        raise click.Abort()
    
    try:
        shutil.rmtree(project_path)
        click.secho(f"✅ Project '{name}' deleted", fg='green')
    except Exception as e:
        click.secho(f"❌ Deletion failed: {e}", fg='red', err=True)
        raise click.Abort()
