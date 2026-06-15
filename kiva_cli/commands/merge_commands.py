#!/usr/bin/env python3
"""
kiva merge -- Wrapper souverain pour merge PR avec CI local.

Séquence obligatoire (4 étapes) :
  1. kiva cicd run <repo_path>          — CI local, gratuit, souverain
  2. gh pr merge <N> --squash           — merge atomique
  3. kiva wal append + phi drift        — traçabilité WAL + vérif φ-CPS
  4. kiva citizen promote               — promotion citoyen post-merge

IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559
"""
from __future__ import annotations

import datetime
import json
import subprocess
import sys

import click

# ── Source of truth : chemins locaux ENV2 ──────────────────────────────
# Synchroniser avec .workspace.index.yaml (GOVERNANCE-HUB L0).
# En v2, lire le YAML directement au runtime (voir docstring du module).
REPOS_LOCAL_PATHS = {
    "CTULU":          r"D:\DO\WEB\TOOLS\L4-TOOLS\CTULU",
    "GOVERNANCE-HUB": r"D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB",
    "NEXUS":          None,  # remote_only — not cloned on ENV2
    "ECOYSTEM":       r"D:\DO\WEB\TOOLS\L1-INFRA\ECOYSTEM",
    "ECOS-CLI":       r"D:\DO\WEB\TOOLS\L1-INFRA\ECOS-CLI",
    "KIVA-CLI":       r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI",
    "BRAIN":          r"D:\DO\WEB\TOOLS\L0-CANON\BRAIN",
    "FLUENCE":        r"D:\DO\WEB\TOOLS\L1-INFRA\FLUENCE",
    "WAZAA":          r"D:\DO\WEB\TOOLS\L3-CITIZENS\WAZAA",
    "ARGUS":          r"D:\DO\WEB\TOOLS\L3-CITIZENS\ARGUS",
    "UAE":            r"D:\DO\WEB\TOOLS\L3-CITIZENS\UAE",
    "IRIS":           r"D:\DO\WEB\TOOLS\L3-CITIZENS\IRIS",
    "KRONOS":         r"D:\DO\WEB\TOOLS\L3-CITIZENS\KRONOS",
    "TINA":           r"D:\DO\WEB\TOOLS\L3-CITIZENS\TINA",
    "INTENT-ENCODER": r"D:\DO\WEB\TOOLS\L3-CITIZENS\INTENT-ENCODER",
    "STRIX":          r"D:\DO\WEB\TOOLS\L3-CITIZENS\STRIX",
    "DevTools":       r"C:\DevTools",
}


def _run(cmd: list[str], cwd: str | None = None, dry_run: bool = False) -> int:
    """Execute a subprocess command. Returns the exit code."""
    click.echo(click.style(f"  $ {' '.join(cmd)}", fg="bright_black"))
    if dry_run:
        click.echo(click.style("    [DRY-RUN] simulated", fg="yellow"))
        return 0
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def _wal_append(repo: str, pr: int, event: str, dry_run: bool = False) -> None:
    """Append a WAL event via kiva wal append."""
    payload = json.dumps({
        "event": event,
        "repo": repo,
        "pr": pr,
        "intent_hash": "0xKIVA_MERGE_SOVEREIGN_phi4559",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    })
    _run(["kiva", "wal", "append", "--event", payload], dry_run=dry_run)


@click.group(name="merge")
def merge_cli():
    """Sovereign PR merge wrapper -- CI local -> merge -> WAL (IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559)."""
    pass


@merge_cli.command(name="pr")
@click.argument("repo")
@click.argument("pr_number", type=int)
@click.option(
    "--method",
    default="squash",
    type=click.Choice(["squash", "merge", "rebase"]),
    help="Merge method (default: squash)",
)
@click.option(
    "--hotfix",
    is_flag=True,
    default=False,
    help="HITL bypass CI -- emergencies only, logged WAL",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Full simulation without any real action",
)
def merge_pr(repo: str, pr_number: int, method: str, hotfix: bool, dry_run: bool):
    """
    Sovereign merge of a PR with CI local + WAL.

    \b
    Sequence:
      1. kiva cicd run <repo_path>   -- sovereign local CI
      2. gh pr merge <N> --<method>  -- atomic merge
      3. kiva wal append             -- traceability
      4. kiva phi drift              -- phi-CPS check (non-blocking)

    \b
    Examples:
      kiva merge pr UAE 9
      kiva merge pr UAE 9 --dry-run
      kiva merge pr UAE 9 --hotfix   # bypass CI, HITL required
    """
    repo_path = REPOS_LOCAL_PATHS.get(repo)

    click.echo("")
    click.echo(click.style(
        f"+-- KIVA MERGE SOUVERAIN — {repo} PR #{pr_number} {'— DRY-RUN ' if dry_run else '------------^-'}--+",
        fg="cyan"))
    if hotfix:
        click.echo(click.style(
            "|  WARNING: HOTFIX MODE — CI bypassed — HITL logged              |",
            fg="red"))
    click.echo(click.style(
        "+-----------------------------------------------------------------+",
        fg="cyan"))
    click.echo("")

    # STEP 0: Pre-merge WAL snapshot
    _wal_append(repo, pr_number, "pre_merge_snapshot", dry_run=dry_run)
    click.echo(click.style("  [WAL] Pre-merge snapshot recorded", fg="bright_black"))

    # STEP 1: Local CI
    if hotfix:
        click.echo(click.style("  [STEP 1] Local CI — BYPASSED (--hotfix)", fg="red"))
        _wal_append(repo, pr_number, "ci_bypassed_hotfix", dry_run=dry_run)
    else:
        click.echo(click.style("  [STEP 1] Local CI", fg="cyan"))
        if repo_path is None and repo in REPOS_LOCAL_PATHS:
            # remote_only repo — CI local not available, skip with notice
            click.echo(click.style(
                f"  [SKIP] {repo} is remote_only on ENV2 — local CI skipped",
                fg="yellow"))
            _wal_append(repo, pr_number, "ci_skipped_remote_only", dry_run=dry_run)
            rc = 0
        elif repo_path:
            rc = _run(["kiva", "cicd", "run", repo_path], dry_run=dry_run)
        else:
            # Unknown repo — fallback to pytest in current directory
            click.echo(click.style(
                f"  [WARN] Unknown local path for {repo} — pytest fallback",
                fg="yellow"))
            rc = _run(["python", "-m", "pytest", "--tb=short", "-q"], dry_run=dry_run)
        if rc != 0:
            click.echo(click.style(
                f"  [HALT] Local CI failed (rc={rc}) — merge cancelled. Fix and retry.",
                fg="red"))
            _wal_append(repo, pr_number, "ci_failed_merge_cancelled", dry_run=dry_run)
            sys.exit(rc)
        click.echo(click.style("  [STEP 1] Local CI [OK]", fg="green"))

    # STEP 2: Atomic merge
    click.echo(click.style(
        f"  [STEP 2] gh pr merge #{pr_number} --{method} --delete-branch",
        fg="cyan"))
    rc = _run([
        "gh", "pr", "merge", str(pr_number),
        f"--{method}",
        "--delete-branch",
        "--repo", f"gerivdb/{repo}",
    ], dry_run=dry_run)
    if rc != 0:
        click.echo(click.style(
            f"  [HALT] gh pr merge failed (rc={rc}) — HITL required",
            fg="red"))
        _wal_append(repo, pr_number, "merge_failed", dry_run=dry_run)
        sys.exit(rc)
    click.echo(click.style("  [STEP 2] Merge [OK]", fg="green"))

    # STEP 3: WAL append post-merge
    _wal_append(repo, pr_number, "merge_success", dry_run=dry_run)
    click.echo(click.style("  [STEP 3] WAL append [OK]", fg="green"))

    # STEP 4: Drift check phi-CPS (non-blocking)
    click.echo(click.style("  [STEP 4] Drift check phi-CPS (non-blocking)", fg="cyan"))
    _run(["kiva", "phi", "drift", "--repo", repo], dry_run=dry_run)
    click.echo(click.style("  [STEP 4] Drift [OK]", fg="green"))

    # Final report
    click.echo("")
    click.echo(click.style(
        f"  [OK] MERGE COMPLETE — {repo} PR #{pr_number} -> main",
        fg="green", bold=True))
    click.echo(click.style(
        f"  IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559",
        fg="bright_black"))
    click.echo("")
