#!/usr/bin/env python3
"""
Gate Command - KIVA CLI

Phi-CPS merge gate: blocks merge if drift exceeds threshold.
Used as local CI gate replacing GitHub Actions for all ECOS repos.
"""

import sys
import click
from kiva_cli.core.phi_cps_analytics import PhiCPSAnalytics

THRESHOLD_WARNING   = 0.02   # 2%
THRESHOLD_CRITICAL  = 0.05   # 5%  <- merge blocked above this
THRESHOLD_EMERGENCY = 0.10   # 10%


@click.group(name='gate')
def gate_cli():
    """
    Merge gate based on phi-CPS drift.

    Blocks merge if drift exceeds CRITICAL threshold (5%).
    Use in pre-push hooks and CI pipelines.
    """
    pass


@gate_cli.command(name='check')
@click.option('--repo', '-r', required=True, help='Target repository name (e.g. ECOS-CLI)')
@click.option('--base', '-b', default='main', show_default=True, help='Base branch')
@click.option('--head', '-h', default=None, help='Head branch (default: current branch)')
@click.option('--threshold', '-t', default=THRESHOLD_CRITICAL, show_default=True,
              help='Drift threshold (0.0-1.0). Merge blocked if exceeded.')
@click.option('--strict', is_flag=True, default=False,
              help='Strict mode: block on WARNING (2%) instead of CRITICAL (5%)')
def check(repo: str, base: str, head: str, threshold: float, strict: bool):
    """
    Check phi-CPS drift and gate merge.

    Exit codes:
      0 = PASS  (drift <= threshold)
      1 = FAIL  (drift > threshold)
      2 = ERROR (analytics unavailable)

    Examples:
        kiva gate check --repo ECOS-CLI
        kiva gate check --repo FLUENCE --base main --head develop
        kiva gate check --repo BRAIN --strict
    """
    effective_threshold = THRESHOLD_WARNING if strict else threshold

    click.echo("")
    click.echo(click.style(f"KIVA Gate - phi-CPS Check", fg="cyan"))
    click.echo(click.style("=" * 40, fg="cyan"))
    click.echo(f"Repo:      {repo}")
    click.echo(f"Base:      {base}")
    click.echo(f"Head:      {head or '(current branch)'}")
    click.echo(f"Threshold: {effective_threshold * 100:.0f}% ({'STRICT/WARNING' if strict else 'CRITICAL'})")
    click.echo("")

    try:
        analytics = PhiCPSAnalytics()
        current = analytics.get_current_status(component=repo)
        drift = current.get('drift', None)

        if drift is None:
            click.echo(click.style("[ERROR] phi-CPS drift unavailable - WAL not initialized?", fg="red"))
            click.echo(click.style("        Run: kiva phi-cps status", fg="yellow"))
            sys.exit(2)

        # Normalize drift (may be stored as 0.032 or 3.2)
        drift_normalized = drift if drift <= 1.0 else drift / 100.0
        drift_pct = drift_normalized * 100

        # Determine level
        if drift_normalized >= THRESHOLD_EMERGENCY:
            level, color = "EMERGENCY", "red"
        elif drift_normalized >= THRESHOLD_CRITICAL:
            level, color = "CRITICAL", "red"
        elif drift_normalized >= THRESHOLD_WARNING:
            level, color = "WARNING", "yellow"
        else:
            level, color = "OK", "green"

        click.echo(f"phi Value: {current.get('phi_value', 'N/A')}")
        click.echo(f"Drift:     {click.style(f'{drift_pct:.2f}%', fg=color)} [{level}]")
        click.echo(f"Hash:      {current.get('intent_hash', 'N/A')}")
        click.echo("")

        if drift_normalized > effective_threshold:
            click.echo(click.style(f"[FAIL] Merge BLOCKED - drift {drift_pct:.2f}% > threshold {effective_threshold * 100:.0f}%", fg="red"))
            click.echo(click.style(f"       Resolve phi-CPS drift before merging {head or 'HEAD'} -> {base}", fg="yellow"))
            sys.exit(1)
        else:
            click.echo(click.style(f"[PASS] Merge ALLOWED - drift {drift_pct:.2f}% <= threshold {effective_threshold * 100:.0f}%", fg="green"))
            sys.exit(0)

    except Exception as e:
        click.echo(click.style(f"[ERROR] Gate check failed: {e}", fg="red"))
        sys.exit(2)


@gate_cli.command(name='status')
@click.option('--repo', '-r', required=True, help='Target repository name')
def gate_status(repo: str):
    """
    Quick gate status without blocking.

    Example:
        kiva gate status --repo ECOS-CLI
    """
    try:
        analytics = PhiCPSAnalytics()
        current = analytics.get_current_status(component=repo)
        drift = current.get('drift', None)

        if drift is None:
            click.echo(f"[GATE:{repo}] UNKNOWN - WAL not initialized")
            return

        drift_normalized = drift if drift <= 1.0 else drift / 100.0
        drift_pct = drift_normalized * 100

        if drift_normalized >= THRESHOLD_CRITICAL:
            verdict = click.style("BLOCKED", fg="red")
        else:
            verdict = click.style("OPEN", fg="green")

        click.echo(f"[GATE:{repo}] {verdict} | drift={drift_pct:.2f}% | phi={current.get('phi_value', '?')}")

    except Exception as e:
        click.echo(f"[GATE:{repo}] ERROR - {e}")
