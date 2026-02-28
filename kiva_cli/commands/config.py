# KIVA CLI - Config Commands
import click
from ..core.config_manager import ConfigManager

@click.group()
def config():
    '''Configuration management commands.'''
    pass

@config.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--strict/--no-strict', default=True, help='Strict validation')
@click.option('--schema', help='Custom JSON schema file')
def validate(file: str, strict: bool, schema: str):
    '''Validate configuration files.'''
    manager = ConfigManager()
    result = manager.validate_config(file, strict, schema)
    
    if result.success:
        click.secho(f"✅ Configuration valid: {file}", fg='green')
    else:
        click.secho(f"❌ Configuration invalid", fg='red', err=True)
        for error in result.errors:
            click.echo(f"  - {error}", err=True)
        raise click.Abort()
