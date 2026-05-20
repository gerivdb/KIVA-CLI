#!/usr/bin/env python3
"""
Security Hardening Commands - KIVA CLI

Provides commands for security audits, AppArmor profiles, and secrets management.
"""

import click
from kiva_cli.core.security_manager import SecurityManager


@click.group(name='security')
def security_cli():
    """
    Security hardening and audit utilities.

    Provides:
    - Run security audits
    - Setup AppArmor profiles
    - Rotate secrets
    - Check security status
    """
    pass


@security_cli.command(name='audit')
@click.argument('repo_path')
def audit(repo_path: str):
    """
    Run security audit on a repository.

    REPO_PATH: Path to the repository

    Example:
        kiva security audit D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = SecurityManager()
    result = manager.run_security_audit(repo_path)
    
    click.echo("")
    click.echo(click.style("Security Audit Results", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Repository: {result['repo_path']}")
    click.echo(f"Status: {click.style(result['status'], fg='green' if result['status'] == 'PASS' else 'red')}")
    click.echo(f"Issues found: {result['issues_count']}")
    
    if result['issues']:
        click.echo("\nIssues:")
        for issue in result['issues'][:10]:
            severity_color = {"HIGH": "red", "MEDIUM": "yellow", "LOW": "white"}.get(issue['severity'], "white")
            click.echo(f"  {click.style(f'[{issue["severity"]}]', fg=severity_color)} {issue['message']}")
            click.echo(f"    File: {issue['file']}")
    
    click.echo("")


@security_cli.command(name='status')
@click.argument('repo_path')
def status(repo_path: str):
    """
    Check security status for a repository.

    REPO_PATH: Path to the repository

    Example:
        kiva security status D:\\DO\\WEB\\TOOLS\\KIVA-CLI
    """
    manager = SecurityManager()
    s = manager.get_security_status(repo_path)
    
    click.echo("")
    click.echo(click.style("Security Status", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Repository: {s['repo_path']}")
    click.echo(f"Status: {click.style(s['status'], fg='green' if s['status'] == 'PASS' else 'red')}")
    click.echo(f"Issues: {s['issues_count']}")
    click.echo("")


@security_cli.command(name='rotate')
@click.argument('secret_name')
@click.option('--repo', '-r', required=True, help='Repository path')
def rotate_secret(secret_name: str, repo: str):
    """
    Rotate a secret in a repository.

    SECRET_NAME: Name of the secret to rotate

    Example:
        kiva security rotate API_KEY --repo D:\\Repos\\my-repo
    """
    manager = SecurityManager()
    success = manager.rotate_secrets(repo, secret_name)
    
    if success:
        click.echo(click.style(f"Secret '{secret_name}' rotated successfully.", fg="green"))
    else:
        click.echo(click.style(f"Failed to rotate secret '{secret_name}'.", fg="red"))