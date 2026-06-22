#!/usr/bin/env python3
"""
Scaffold Command - CLI Interface for FrameworkManager

Usage:
    kiva scaffold fastapi my-api --description "My FastAPI service"
    kiva scaffold react my-app --features "auth,routing"
    kiva scaffold go-service my-svc --output ./services/
"""

import click
from pathlib import Path
from typing import List
from kiva_cli.managers.framework_manager import FrameworkManager, TemplateConfig


@click.group(name="scaffold")
def scaffold_group():
    """Scaffold new projects from templates"""
    pass


@scaffold_group.command(name="fastapi")
@click.argument("name")
@click.option("--description", default="FastAPI application", help="Project description")
@click.option("--output", type=click.Path(), default=".", help="Output directory")
@click.option(
    "--features",
    default="auth,db,docs",
    help="Comma-separated features (auth,db,docs,celery,redis)"
)
def scaffold_fastapi(name: str, description: str, output: str, features: str):
    """Create new FastAPI project"""
    click.echo(f"🚀 Scaffolding FastAPI project: {name}")
    
    manager = FrameworkManager()
    
    config = TemplateConfig(
        name=name,
        framework="fastapi",
        description=description,
        target_path=Path(output) / name,
        features=features.split(","),
        metadata={
            "created_by": "kiva-cli",
            "version": "0.1.0"
        }
    )
    
    try:
        project_path = manager.scaffold_project(config)
        click.echo(f"✅ FastAPI project created at: {project_path}")
        click.echo("\n📝 Next steps:")
        click.echo(f"  cd {project_path}")
        click.echo("  pip install -r requirements.txt")
        click.echo("  uvicorn app.main:app --reload")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@scaffold_group.command(name="react")
@click.argument("name")
@click.option("--description", default="React application", help="Project description")
@click.option("--output", type=click.Path(), default=".", help="Output directory")
@click.option(
    "--features",
    default="routing,state-management",
    help="Comma-separated features"
)
def scaffold_react(name: str, description: str, output: str, features: str):
    """Create new React + TypeScript project"""
    click.echo(f"🚀 Scaffolding React project: {name}")
    
    manager = FrameworkManager()
    
    config = TemplateConfig(
        name=name,
        framework="react",
        description=description,
        target_path=Path(output) / name,
        features=features.split(","),
        metadata={
            "created_by": "kiva-cli",
            "version": "0.1.0"
        }
    )
    
    try:
        project_path = manager.scaffold_project(config)
        click.echo(f"✅ React project created at: {project_path}")
        click.echo("\n📝 Next steps:")
        click.echo(f"  cd {project_path}")
        click.echo("  npm install")
        click.echo("  npm run dev")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@scaffold_group.command(name="go-service")
@click.argument("name")
@click.option("--description", default="Go microservice", help="Project description")
@click.option("--output", type=click.Path(), default=".", help="Output directory")
@click.option(
    "--features",
    default="api,db",
    help="Comma-separated features"
)
def scaffold_go_service(name: str, description: str, output: str, features: str):
    """Create new Go microservice"""
    click.echo(f"🚀 Scaffolding Go service: {name}")
    
    manager = FrameworkManager()
    
    config = TemplateConfig(
        name=name,
        framework="go-service",
        description=description,
        target_path=Path(output) / name,
        features=features.split(","),
        metadata={
            "created_by": "kiva-cli",
            "version": "0.1.0"
        }
    )
    
    try:
        project_path = manager.scaffold_project(config)
        click.echo(f"✅ Go service created at: {project_path}")
        click.echo("\n📝 Next steps:")
        click.echo(f"  cd {project_path}")
        click.echo("  go mod download")
        click.echo("  make run")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@scaffold_group.command(name="list")
def list_templates():
    """List available project templates"""
    click.echo("📋 Available templates:\n")
    
    templates = [
        ("fastapi", "FastAPI + PostgreSQL + Alembic", "Python 3.11+"),
        ("react", "React + TypeScript + Vite + TailwindCSS", "Node 18+"),
        ("go-service", "Go + Gin + GORM", "Go 1.21+"),
    ]
    
    for name, desc, req in templates:
        click.echo(f"  • {name:15s} - {desc}")
        click.echo(f"    {' '*17}Requirements: {req}")
        click.echo()


if __name__ == "__main__":
    scaffold_group()
