#!/usr/bin/env python3
"""
Skill Discovery Commands - KIVA CLI

Provides commands for discovering, verifying, registering skills,
and creating issues in concerned repositories.
"""

import click
from kiva_cli.core.skill_discovery_manager import SkillDiscoveryManager, SkillInfo


@click.group(name='skill-discovery')
def skill_discovery_cli():
    """
    Skill discovery and registration utilities.

    Provides:
    - Discover new skills from ecosystem
    - Verify skill existence
    - Register skills in SKILLS registry
    - Find concerned repositories
    - Create issues/EPICs automatically
    """
    pass


@skill_discovery_cli.command(name='discover')
def discover_skills():
    """
    Discover potential skills from the ecosystem.

    Scans KIVA-CLI commands, DevTools, and citizen definitions.

    Example:
        kiva skill-discovery discover
    """
    manager = SkillDiscoveryManager()
    discovered = manager.discover_skills()
    
    if not discovered:
        click.echo(click.style("No new skills discovered.", fg="yellow"))
        return
    
    click.echo("")
    click.echo(click.style(f"Discovered {len(discovered)} potential skills", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    for skill in discovered:
        registered = "[REG]" if manager.verify_skill(skill.name) else "[NEW]"
        click.echo(f"\n  {registered} {click.style(skill.name, fg='green')}")
        click.echo(f"    Description: {skill.description}")
        click.echo(f"    Capabilities: {', '.join(skill.capabilities)}")
        click.echo(f"    Repos served: {', '.join(skill.repos_served)}")
    
    click.echo("")


@skill_discovery_cli.command(name='verify')
@click.argument('skill_name')
def verify_skill(skill_name: str):
    """
    Verify if a skill exists in the registry.

    SKILL_NAME: Name of the skill to verify

    Example:
        kiva skill-discovery verify script-maturation
    """
    manager = SkillDiscoveryManager()
    exists = manager.verify_skill(skill_name)
    
    if exists:
        click.echo(click.style(f"Skill '{skill_name}' is registered.", fg="green"))
        skill = manager.skills[skill_name]
        click.echo(f"  Capabilities: {', '.join(skill.capabilities)}")
        click.echo(f"  Repos served: {', '.join(skill.repos_served)}")
    else:
        click.echo(click.style(f"Skill '{skill_name}' is NOT registered.", fg="yellow"))


@skill_discovery_cli.command(name='register')
@click.argument('skill_name')
@click.option('--description', '-d', default='', help='Skill description')
@click.option('--capabilities', '-c', multiple=True, help='Skill capabilities')
@click.option('--repos-served', '-r', multiple=True, help='Repositories served')
def register_skill(skill_name: str, description: str, capabilities: tuple, repos_served: tuple):
    """
    Register a new skill in the SKILLS registry.

    SKILL_NAME: Name of the skill

    Example:
        kiva skill-discovery register my-skill -d "Does something" -c cap1 -r repo1
    """
    manager = SkillDiscoveryManager()
    
    if manager.verify_skill(skill_name):
        click.echo(click.style(f"Skill '{skill_name}' already registered.", fg="yellow"))
        return
    
    skill = SkillInfo({
        "name": skill_name,
        "description": description or f"Skill: {skill_name}",
        "capabilities": list(capabilities) if capabilities else [f"{skill_name}_operations"],
        "repos_served": list(repos_served) if repos_served else []
    })
    
    success = manager.register_skill(skill)
    if success:
        click.echo(click.style(f"Skill '{skill_name}' registered successfully.", fg="green"))
    else:
        click.echo(click.style(f"Failed to register skill '{skill_name}'.", fg="red"))


@skill_discovery_cli.command(name='relate')
@click.argument('skill_name')
def relate_skill(skill_name: str):
    """
    Find repositories concerned by a skill.

    Uses ontology:
    - skill.repos_served ∩ repo.name ≠ ∅
    - skill.capabilities ∩ repo.needs ≠ ∅

    SKILL_NAME: Name of the skill

    Example:
        kiva skill-discovery relate script-maturation
    """
    manager = SkillDiscoveryManager()
    
    if not manager.verify_skill(skill_name):
        click.echo(click.style(f"Skill '{skill_name}' not found.", fg="red"))
        return
    
    skill = manager.skills[skill_name]
    concerned_repos = manager.find_concerned_repos(skill)
    
    click.echo("")
    click.echo(click.style(f"Repositories concerned by '{skill_name}'", fg="cyan"))
    click.echo(click.style("=" * 60, fg="cyan"))
    
    if not concerned_repos:
        click.echo(click.style("  No concerned repositories found.", fg="yellow"))
    else:
        for repo in concerned_repos:
            click.echo(f"  {click.style(repo.name, fg='green')}")
            click.echo(f"    Local: {repo.local_path}")
            click.echo(f"    Remote: {repo.remote_url}")
    
    click.echo("")


@skill_discovery_cli.command(name='export')
@click.option('--output', '-o', default=None, help='Output file path')
def export_ontology(output: str):
    """
    Export skill ontology as YAML.

    Example:
        kiva skill-discovery export
        kiva skill-discovery export -o skill-ontology.yaml
    """
    manager = SkillDiscoveryManager()
    
    output_path = output or "skill-ontology.yaml"
    manager.export_skill_ontology(output_path)
    
    click.echo(click.style(f"Skill ontology exported to: {output_path}", fg="green"))