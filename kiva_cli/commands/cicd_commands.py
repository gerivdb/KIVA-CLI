#!/usr/bin/env python3
"""
CI/CD Commands - KIVA CLI

Provides commands for CI/CD integration and pipeline management.
"""

import click
from kiva_cli.core.cicd_manager import CICDManager


@click.group(name='cicd')
def cicd_cli():
    """
    CI/CD integration and pipeline management.

    Provides:
    - Setup GitHub Actions workflows
    - Configure self-hosted runners
    - Run CI pipelines locally
    - Check pipeline status
    - Run NEXUS Sync Agent v2 (dry-run or live)
    """
    pass


@cicd_cli.command(name='setup')
@click.argument('repo_path')
@click.option('--pipeline', '-p', default='ecos-ci', help='Pipeline name')
def setup(repo_path: str, pipeline: str):
    """
    Setup GitHub Actions workflow for a repository.

    REPO_PATH: Path to the repository

    Example:
        kiva cicd setup D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = CICDManager()
    success = manager.setup_github_actions(repo_path, pipeline)

    if success:
        click.echo(click.style("GitHub Actions workflow setup successfully.", fg="green"))
    else:
        click.echo(click.style("Failed to setup workflow.", fg="red"))


@cicd_cli.command(name='run')
@click.argument('repo_path')
def run_pipeline(repo_path: str):
    """
    Run CI pipeline locally for testing.

    REPO_PATH: Path to the repository

    Example:
        kiva cicd run D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = CICDManager()
    success = manager.run_ci_pipeline(repo_path)

    if success:
        click.echo(click.style("CI pipeline passed!", fg="green"))
    else:
        click.echo(click.style("CI pipeline failed!", fg="red"))


@cicd_cli.command(name='status')
@click.argument('repo_path')
def status(repo_path: str):
    """
    Check CI pipeline status for a repository.

    REPO_PATH: Path to the repository

    Example:
        kiva cicd status D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = CICDManager()
    info = manager.get_pipeline_status(repo_path)

    click.echo("")
    click.echo(click.style("CI/CD Pipeline Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Repository: {info['repo_path']}")
    click.echo(f"Workflows: {info['workflows_count']}")
    for wf in info['workflows']:
        click.echo(f"  - {wf}")
    click.echo("")


@cicd_cli.command(name='nexus-sync')
@click.option(
    '--dry-run',
    is_flag=True,
    default=True,
    show_default=True,
    help='Simulation sans écriture (recommandé pour le premier run)',
)
@click.option(
    '--repo',
    default=None,
    metavar='REPO',
    help='Filtrer sur un repo spécifique (ex: KIVA-CLI)',
)
@click.pass_context
def nexus_sync(ctx: click.Context, dry_run: bool, repo: str | None) -> None:
    """
    Lance le NEXUS Sync Agent v2 depuis KIVA-CLI (PRD-KIVA-006).

    Par défaut, effectue un dry-run qui génère un rapport markdown
    sans modifier quoi que ce soit.

    Exemples:
        kiva cicd nexus-sync --dry-run
        kiva cicd nexus-sync --dry-run --repo KIVA-CLI
        kiva cicd nexus-sync  # dry-run activé par défaut
    """
    from kiva_cli.core.nexus_sync_orchestrator import NexusSyncOrchestrator

    orch = NexusSyncOrchestrator()
    mode = "(dry-run) " if dry_run else ""
    click.echo(click.style(f"🔄 NEXUS Sync v2 {mode}en cours...", fg="cyan"))

    result = orch.run(dry_run=dry_run, repo_filter=repo)

    if result.success:
        click.echo(click.style(f"✅ Sync {mode}terminé", fg="green"))
        if result.report_path:
            click.echo(f"📄 Rapport : {result.report_path}")
        if result.stdout:
            click.echo(result.stdout)
    else:
        click.echo(click.style(f"❌ Échec : {result.stderr}", fg="red"), err=True)
        ctx.exit(1)
