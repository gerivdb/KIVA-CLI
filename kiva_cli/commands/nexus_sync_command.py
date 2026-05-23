"""
kiva nexus sync — NEXUS Weekly Sync Orchestrator
IntentHash: 0xKIVA_NEXUS_SYNC_LOCAL_20260522
Statut: CONFORME_NEXUS | Remplace: nexus-weekly-sync GHA (désactivé volontairement)
Exécution locale via Task Scheduler Windows (lundi 6h) ou à la demande.

Usage:
    kiva nexus sync
    kiva nexus sync --dry-run
    kiva nexus sync --repo D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS
    kiva nexus sync --skip-watchdog
"""

import click
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# ─── Constantes ────────────────────────────────────────────────────────────────
_L0_CANON_ROOT = Path("D:/DO/WEB/TOOLS/L0-CANON")
_DEFAULT_NEXUS  = _L0_CANON_ROOT / "NEXUS"

PIPELINE = [
    {
        "name":    "nexus_sync",
        "script":  "tools/nexus_sync.py",
        "args":    ["--generate"],
        "label":   "[1/5] Sync registre NEXUS",
        "fatal":   True,
    },
    {
        "name":    "nexus_changelog_gen",
        "script":  "tools/nexus_changelog_gen.py",
        "args":    [],
        "label":   "[2/5] Génération CHANGELOG",
        "fatal":   True,
    },
    {
        "name":    "nexus_readme_gen",
        "script":  "tools/nexus_readme_gen.py",
        "args":    [],
        "label":   "[3/5] Génération README",
        "fatal":   True,
    },
    {
        "name":    "nexus_validate",
        "script":  "tools/nexus_validate.py",
        "args":    ["--check", "drift", "--create-issues"],
        "label":   "[4/5] Validation + drift check",
        "fatal":   True,
    },
    {
        "name":    "nexus_watchdog",
        "script":  "tools/nexus_watchdog.py",
        "args":    ["--create-issues"],
        "label":   "[5/5] Watchdog intégrité",
        "fatal":   False,   # continue-on-error intentionnel
    },
]


def _run_step(step: dict, nexus_root: Path, dry_run: bool, python: str) -> bool:
    """
    Exécute un step du pipeline.
    Retourne True si succès (ou non-fatal), False si échec fatal.
    """
    script = nexus_root / step["script"]
    cmd    = [python, str(script)] + step["args"]
    tag    = "DRY-RUN" if dry_run else "RUN"

    click.echo(f"\n{'='*60}")
    click.echo(f"  {step['label']}")
    click.echo(f"  [{tag}] {' '.join(cmd)}")

    if dry_run:
        click.secho("  -> SKIPPED (dry-run)", fg="yellow")
        return True

    if not script.exists():
        click.secho(f"  ERROR: script introuvable: {script}", fg="red")
        return not step["fatal"]

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        if step["fatal"]:
            click.secho(f"  FATAL (exit {result.returncode}) — pipeline interrompu", fg="red")
            return False
        else:
            click.secho(
                f"  WARNING (exit {result.returncode}) — non-fatal, pipeline continue",
                fg="yellow"
            )

    return True


@click.command("sync")
@click.option("--dry-run",       is_flag=True,  help="Simule le pipeline sans exécuter")
@click.option("--repo",          default=None,  help="Chemin absolu vers NEXUS (défaut: _L0_CANON_ROOT/NEXUS)")
@click.option("--skip-watchdog", is_flag=True,  help="Saute l'étape 5 (nexus_watchdog)")
@click.option("--python",        default=sys.executable, help="Interpréteur Python à utiliser")
def nexus_sync_cmd(dry_run, repo, skip_watchdog, python):
    """
    Enchaîne les 5 scripts du weekly sync NEXUS en local.

    Remplace le workflow GitHub Actions nexus-weekly-sync (GHA volontairement
    désactivé pour raisons budgétaires). Compatible Task Scheduler Windows.

    Pipeline:
      1. nexus_sync.py --generate
      2. nexus_changelog_gen.py
      3. nexus_readme_gen.py
      4. nexus_validate.py --check drift --create-issues
      5. nexus_watchdog.py --create-issues  [continue-on-error]
    """
    nexus_root = Path(repo) if repo else _DEFAULT_NEXUS

    click.secho("\n========================================", fg="cyan", bold=True)
    click.secho("  KIVA — nexus sync", fg="cyan", bold=True)
    click.secho(f"  Repo  : {nexus_root}", fg="cyan")
    click.secho(f"  Python: {python}", fg="cyan")
    click.secho(f"  Mode  : {'DRY-RUN' if dry_run else 'LIVE'}", fg="cyan")
    click.secho(f"  Start : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fg="cyan")
    click.secho("========================================\n", fg="cyan", bold=True)

    if not nexus_root.is_dir():
        click.secho(f"ERROR: NEXUS root introuvable: {nexus_root}", fg="red")
        sys.exit(1)

    steps   = [s for s in PIPELINE if not (skip_watchdog and s["name"] == "nexus_watchdog")]
    failed  = []
    success = 0

    for step in steps:
        ok = _run_step(step, nexus_root, dry_run, python)
        if ok:
            success += 1
        else:
            failed.append(step["name"])
            break  # step fatal: stop

    click.echo(f"\n{'='*60}")
    if not failed:
        click.secho(
            f"  NEXUS SYNC OK — {success}/{len(steps)} steps OK",
            fg="green", bold=True
        )
        sys.exit(0)
    else:
        click.secho(
            f"  NEXUS SYNC FAILED — {success}/{len(steps)} steps OK | Echec: {failed}",
            fg="red", bold=True
        )
        sys.exit(1)
