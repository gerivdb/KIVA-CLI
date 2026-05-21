#!/usr/bin/env python3
"""
Skill Marketplace Commands - KIVA CLI

Provides commands for installing, updating, and managing skills.
"""

import click
from kiva_cli.core.skill_installer import SkillInstaller


@click.group(name='skill-market')
def skill_market_cli():
    """
    Skill marketplace management.

    Provides:
    - Install skills from registry
    - Update installed skills
    - Remove skills
    - List installed/available skills
    """
    pass


@skill_market_cli.command(name='list')
@click.option('--installed', '-i', is_flag=True, help='List installed skills')
def list_skills(installed: bool):
    """
    List skills (installed or available).

    Example:
        kiva skill-market list
        kiva skill-market list --installed
    """
    installer = SkillInstaller()
    
    if installed:
        skills = installer.list_installed()
        click.echo("")
        click.echo(click.style(f"Installed Skills ({len(skills)})", fg="cyan"))
        click.echo(click.style("=" * 60, fg="cyan"))
        
        for skill in skills:
            click.echo(f"\n  {click.style(skill.name, fg='green')}")
            click.echo(f"    Version: {skill.version}")
            click.echo(f"    Description: {skill.description}")
            click.echo(f"    Path: {skill.install_path}")
    else:
        skills = installer.list_available()
        click.echo("")
        click.echo(click.style(f"Available Skills ({len(skills)})", fg="cyan"))
        click.echo(click.style("=" * 60, fg="cyan"))
        
        for skill in skills:
            installed_marker = "[INSTALLED]" if skill["name"] in installer.installed_skills else ""
            click.echo(f"\n  {click.style(skill['name'], fg='green')} {installed_marker}")
            click.echo(f"    Version: {skill.get('version', 'N/A')}")
            click.echo(f"    Description: {skill.get('description', 'N/A')}")
            click.echo(f"    Repository: {skill.get('repository', 'N/A')}")
    
    click.echo("")


@skill_market_cli.command(name='install')
@click.argument('skill_name')
@click.option('--version', '-v', default=None, help='Specific version to install')
def install_skill(skill_name: str, version: str):
    """
    Install a skill from the registry.

    SKILL_NAME: Name of the skill to install

    Example:
        kiva skill-market install script-maturation
    """
    installer = SkillInstaller()
    success = installer.install_skill(skill_name, version)
    
    if success:
        click.echo(click.style(f"Skill '{skill_name}' installed successfully.", fg="green"))
    else:
        click.echo(click.style(f"Failed to install skill '{skill_name}'.", fg="red"))


@skill_market_cli.command(name='update')
@click.argument('skill_name')
def update_skill(skill_name: str):
    """
    Update an installed skill.

    SKILL_NAME: Name of the skill to update

    Example:
        kiva skill-market update script-maturation
    """
    installer = SkillInstaller()
    success = installer.update_skill(skill_name)
    
    if success:
        click.echo(click.style(f"Skill '{skill_name}' updated successfully.", fg="green"))
    else:
        click.echo(click.style(f"Failed to update skill '{skill_name}'.", fg="red"))


@skill_market_cli.command(name='remove')
@click.argument('skill_name')
def remove_skill(skill_name: str):
    """
    Remove an installed skill.

    SKILL_NAME: Name of the skill to remove

    Example:
        kiva skill-market remove script-maturation
    """
    installer = SkillInstaller()
    success = installer.remove_skill(skill_name)
    
    if success:
        click.echo(click.style(f"Skill '{skill_name}' removed successfully.", fg="green"))
    else:
        click.echo(click.style(f"Failed to remove skill '{skill_name}'.", fg="red"))


@skill_market_cli.command(name='info')
@click.argument('skill_name')
def skill_info(skill_name: str):
    """
    Get information about an installed skill.

    SKILL_NAME: Name of the skill

    Example:
        kiva skill-market info script-maturation
    """
    installer = SkillInstaller()
    skill = installer.get_skill_info(skill_name)
    
    if skill:
        click.echo("")
        click.echo(click.style(f"Skill: {skill.name}", fg="cyan"))
        click.echo(click.style("=" * 40, fg="cyan"))
        click.echo(f"Version: {skill.version}")
        click.echo(f"Description: {skill.description}")
        click.echo(f"Author: {skill.author}")
        click.echo(f"Path: {skill.install_path}")
        click.echo(f"Dependencies: {', '.join(skill.dependencies)}")
        click.echo("")
    else:
        click.echo(click.style(f"Skill '{skill_name}' not found.", fg="yellow"))