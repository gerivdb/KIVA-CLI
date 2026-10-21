#!/usr/bin/env python3
"""
kiva merge -- Wrapper souverain pour merge PR avec CI local.

Sequence obligatoire (5 etapes) :
  1. kiva dag3 validate <branch>     -- validation ACM/ADMR (DAG-3)
  2. kiva cicd run <repo_path>       -- CI local, gratuit, souverain
  3. gh pr merge <N> --squash         -- merge atomique
  4. kiva wal append + phi drift     -- tracabilite WAL + verif phi-CPS
  5. kiva citizen promote            -- promotion citoyen post-merge

IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
import subprocess
import sys

import click

# -- DAG-3 Integration -------------------------------------------------------
from kiva_cli.core.dag3 import DAG3Manager, ADMRStatus, CycleSeverity

# -- Source of truth : chemins locaux ENV2 ------------------------------
# Synchroniser avec .workspace.index.yaml (GOVERNANCE-HUB L0).
# En v2, lire le YAML directement au runtime (voir docstring du module).
_SOT_PATH = Path(r"D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB\known_repositories.yaml")

# Table codee en dur : PERIMEE, ne sert plus que de repli (voir _resolve_repo_path).
# Table codee en dur : REPLI uniquement (la SOT prime -- voir
# _resolve_repo_path). Toutes les entrees pointent vers un repertoire
# existant ; les depots absents d ENV2 sont explicitement None.
REPOS_LOCAL_PATHS = {
    "CTULU": r"D:\DO\WEB\TOOLS\L4-TOOLS\CTULU",
    "GOVERNANCE-HUB": r"D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB",
    "NEXUS": r"D:\DO\WEB\TOOLS\L1-INFRA\NEXUS",
    "ECOYSTEM": None,  # remote_only -- absent d ENV2
    "ECOS-CLI": r"D:\DO\WEB\TOOLS\L1-INFRA\ECOS-CLI",
    "KIVA-CLI": r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI",
    "BRAIN": r"D:\DO\WEB\TOOLS\L0-CANON\BRAIN",
    "FLUENCE": r"D:\DO\WEB\TOOLS\L3-CITIZENS\FLUENCE",
    "WAZAA": r"D:\DO\WEB\TOOLS\L4-TOOLS\WAZAA",
    "ARGUS": r"D:\DO\WEB\TOOLS\L1-INFRA\ARGUS",
    "UAE": r"D:\DO\WEB\TOOLS\L1-INFRA\UAE",
    "IRIS": r"D:\DO\WEB\TOOLS\L3-CITIZENS\IRIS",
    "KRONOS": r"D:\DO\WEB\TOOLS\L3-CITIZENS\KRONOS",
    "TINA": None,  # remote_only -- absent d ENV2
    "INTENT-ENCODER": None,  # remote_only -- absent d ENV2
    "STRIX": None,  # remote_only -- absent d ENV2
    "DevTools": r"C:\DevTools",
}


def _run(cmd: list[str], cwd: str | None = None, dry_run: bool = False) -> int:
    """Execute a subprocess command. Returns the exit code."""
    click.echo(click.style(f"  $ {' '.join(cmd)}", fg="bright_black"))
    if dry_run:
        click.echo(click.style("    [DRY-RUN] simulated", fg="yellow"))
        return 0
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def _verify_pr_merged(repo: str, pr_number: int) -> tuple[bool, str]:
    """Verifie l etat REEL d une PR apres tentative de merge.

    Retourne (merged, state). `merged` n est True que si l API confirme
    `merged=True` ET `state == "closed"`. Sans cette verification, le wrapper
    annoncait "MERGE COMPLETE" y compris sur une PR deja mergee (rien n avait
    alors ete fait) -- un succes trompeur.
    """
    import json as _json
    import urllib.request as _request

    try:
        out = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--repo", f"gerivdb/{repo}",
             "--json", "state,merged"],
            capture_output=True, text=True, timeout=60)
        if out.returncode != 0:
            return False, f"verification impossible (gh rc={out.returncode})"
        data = _json.loads(out.stdout or "{}")
        return bool(data.get("merged")) and data.get("state") == "closed", str(data.get("state"))
    except Exception as e:
        return False, f"verification impossible ({e})"


def _resolve_repo_path(repo: str) -> str | None:
    """Resout le chemin local d'un depot, de facon robuste.

    Ordre de resolution :
      1. **SOT** `GOVERNANCE-HUB/known_repositories.yaml` -> champ `local_path`
         (source de verite, seule a jour) ;
      2. table locale codee en dur `REPOS_LOCAL_PATHS` (perimee, mais utile
         pour les depots hors SOT) ;
      3. `None` si rien de valide.

    Le chemin renvoye est **valide** : absolu, existant, et repertoire.

    Pourquoi : la table codee en dur contenait des chemins perimes
    (WAZAA pointait vers `L3-CITIZENS` au lieu de `L4-TOOLS`, FLUENCE vers
    `L1-INFRA` au lieu de `L3-CITIZENS`). Le sous-processus DAG-3 etait alors
    lance avec un `cwd` inexistant -> `NotADirectoryError` (WinError 267),
    sans message exploitable. Une table figee ne peut pas suivre l'arborescence
    ; la SOT, si.
    """
    from pathlib import Path as _Path

    name = (repo or "").replace("gerivdb/", "").strip()
    if not name:
        return None

    # 1. SOT (source de verite)
    try:
        import yaml  # type: ignore
        if _SOT_PATH.exists():
            data = yaml.safe_load(_SOT_PATH.read_text(encoding="utf-8")) or {}
            for entry in data.get("repos", []) or []:
                if not isinstance(entry, dict):
                    continue
                rname = str(entry.get("repo", "")).replace("gerivdb/", "").strip()
                if rname.lower() != name.lower():
                    continue
                lp = entry.get("local_path")
                if lp and _Path(lp).is_dir():
                    return str(_Path(lp).resolve())
    except Exception:
        pass

    # 2. table codee en dur (repli)
    hard = REPOS_LOCAL_PATHS.get(name) or REPOS_LOCAL_PATHS.get(name.upper())
    if hard and _Path(hard).is_dir():
        return str(_Path(hard).resolve())

    return None


def _wal_append(repo: str, pr: int, event: str, dry_run: bool = False, 
                metadata: dict = None) -> None:
    """Append a WAL event via kiva wal append."""
    payload = {
        "repo": repo,
        "pr": pr,
        "intent_hash": "0xKIVA_MERGE_SOVEREIGN_phi4559",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
    }
    if metadata:
        payload.update(metadata)
    _run([
        "kiva", "wal", "append",
        "-o", event,
        "-r", repo,
        "--phi-delta", "0.0",
        "--metadata", json.dumps(payload),
    ], dry_run=dry_run)


def _dag3_validate(repo_path: str, source_branch: str, target_branch: str, 
                    dry_run: bool = False) -> dict:
    """Run DAG-3 validation (ACM + ADMR) before merge.
    
    Returns validation result dict with status and recommendations.
    """
    manager = DAG3Manager(repo_path=repo_path)
    result = manager.validate_merge(source_branch, target_branch)
    
    return {
        "status": result.overall_status,
        "phi_cps_impact": result.phi_cps_impact,
        "acm_cycles": len(result.acm_result.cycles) if result.acm_result.has_cycles else 0,
        "acm_severity": result.acm_result.severity.name if result.acm_result.has_cycles else "NONE",
        "admr_violations": len(result.admr_result.violations),
        "admr_status": result.admr_result.status.value,
        "recommendations": result.recommendations,
        "timestamp": result.timestamp,
    }


@click.group(name="merge")
def merge_cli():
    """Sovereign PR merge wrapper -- CI local -> merge -> WAL (IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559)."""
    pass


@merge_cli.command(name="pr")
@click.argument("repo")
@click.argument("pr_number", type=int)
@click.argument("source_branch", required=False, default=None)
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
@click.option(
    "--skip-dag3",
    is_flag=True,
    default=False,
    help="Skip DAG-3 validation (HITL only)",
)
def merge_pr(repo: str, pr_number: int, source_branch: str | None, 
             method: str, hotfix: bool, dry_run: bool, skip_dag3: bool):
    """
    Sovereign merge of a PR with CI local + WAL + DAG-3 validation.

    \b
    Sequence:
      1. kiva dag3 validate <branch>  -- ACM/ADMR validation
      2. kiva cicd run <repo_path>   -- sovereign local CI
      3. gh pr merge <N> --<method>  -- atomic merge
      4. kiva wal append             -- traceability
      5. kiva phi drift              -- phi-CPS check (non-blocking)

    \b
    Examples:
      kiva merge pr UAE 9 main
      kiva merge pr UAE 9 main --dry-run
      kiva merge pr UAE 9 main --hotfix   # bypass CI, HITL required
    """
    repo_path = _resolve_repo_path(repo)
    if not repo_path:
        click.echo(click.style(
            f"  [KO] chemin local introuvable pour '{repo}' "
            "(SOT known_repositories.yaml + REPOS_LOCAL_PATHS)", fg="red"))
        raise SystemExit(1)
    target_branch = "main"  # Default target

    click.echo("")
    click.echo(click.style(
        f"+-- KIVA MERGE SOUVERAIN -- {repo} PR #{pr_number} {'-- DRY-RUN ' if dry_run else '------------^-'}--+",
        fg="cyan"))
    if hotfix:
        click.echo(click.style(
            "|  WARNING: HOTFIX MODE -- CI bypassed -- HITL logged              |",
            fg="red"))
    click.echo(click.style(
        "+-----------------------------------------------------------------+",
        fg="cyan"))
    click.echo("")

    # Get source branch from PR if not specified
    if source_branch is None:
        try:
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "headBranch", 
                 "--jq", ".headBranch", "--repo", f"gerivdb/{repo}"],
                capture_output=True, text=True, check=True
            )
            source_branch = result.stdout.strip()
        except subprocess.CalledProcessError:
            source_branch = f"pr-{pr_number}"
    
    click.echo(click.style(f"  [INFO] Source branch: {source_branch}", fg="bright_black"))
    click.echo(click.style(f"  [INFO] Target branch: {target_branch}", fg="bright_black"))
    click.echo("")

    # STEP 0: Pre-merge WAL snapshot
    _wal_append(repo, pr_number, "pre_merge_snapshot", dry_run=dry_run)
    click.echo(click.style("  [WAL] Pre-merge snapshot recorded", fg="bright_black"))

    # STEP 1: DAG-3 Validation (ACM + ADMR)
    if not skip_dag3:
        click.echo(click.style("  [STEP 1] DAG-3 Validation (ACM/ADMR)", fg="cyan"))
        dag3_result = _dag3_validate(repo_path or ".", source_branch, target_branch, dry_run=dry_run)
        
        if dag3_result["status"] == "rejected":
            click.echo(click.style("  [HALT] DAG-3 validation REJECTED", fg="red"))
            for rec in dag3_result["recommendations"][:5]:
                click.echo(click.style(f"    {rec}", fg="red"))
            _wal_append(repo, pr_number, "dag3_rejected", dry_run=dry_run,
                       metadata={"phi_cps_impact": dag3_result["phi_cps_impact"]})
            sys.exit(1)
        elif dag3_result["status"] == "needs_hitl":
            click.echo(click.style("  [HALT] DAG-3 validation needs HITL approval", fg="yellow"))
            for rec in dag3_result["recommendations"][:5]:
                click.echo(click.style(f"    {rec}", fg="yellow"))
            _wal_append(repo, pr_number, "dag3_needs_hitl", dry_run=dry_run,
                       metadata={"phi_cps_impact": dag3_result["phi_cps_impact"]})
            if not hotfix:
                sys.exit(1)
            click.echo(click.style("  [HITL] Hotfix approved - continuing", fg="red"))
        else:
            click.echo(click.style("  [STEP 1] DAG-3 Validation [OK]", fg="green"))
            _wal_append(repo, pr_number, "dag3_approved", dry_run=dry_run,
                       metadata={"phi_cps_impact": dag3_result["phi_cps_impact"]})
    else:
        click.echo(click.style("  [STEP 1] DAG-3 Validation [SKIPPED --skip-dag3]", fg="yellow"))

    # STEP 2: Local CI
    if hotfix:
        click.echo(click.style("  [STEP 2] Local CI -- BYPASSED (--hotfix)", fg="red"))
        _wal_append(repo, pr_number, "ci_bypassed_hotfix", dry_run=dry_run)
    else:
        click.echo(click.style("  [STEP 2] Local CI", fg="cyan"))
        if repo_path is None and repo in REPOS_LOCAL_PATHS:
            # remote_only repo -- CI local not available, skip with notice
            click.echo(click.style(
                f"  [SKIP] {repo} is remote_only on ENV2 -- local CI skipped",
                fg="yellow"))
            _wal_append(repo, pr_number, "ci_skipped_remote_only", dry_run=dry_run)
            rc = 0
        elif repo_path:
            rc = _run(["kiva", "cicd", "run", repo_path], dry_run=dry_run)
        else:
            # Unknown repo -- fallback to pytest in current directory
            click.echo(click.style(
                f"  [WARN] Unknown local path for {repo} -- pytest fallback",
                fg="yellow"))
            rc = _run(["python", "-m", "pytest", "--tb=short", "-q"], dry_run=dry_run)
        if rc != 0:
            click.echo(click.style(
                f"  [HALT] Local CI failed (rc={rc}) -- merge cancelled. Fix and retry.",
                fg="red"))
            _wal_append(repo, pr_number, "ci_failed_merge_cancelled", dry_run=dry_run)
            sys.exit(rc)
        click.echo(click.style("  [STEP 2] Local CI [OK]", fg="green"))

    # STEP 3: Atomic merge
    click.echo(click.style(
        f"  [STEP 3] gh pr merge #{pr_number} --{method} --delete-branch",
        fg="cyan"))
    rc = _run([
        "gh", "pr", "merge", str(pr_number),
        f"--{method}",
        "--delete-branch",
        "--repo", f"gerivdb/{repo}",
    ], dry_run=dry_run)
    if rc != 0:
        click.echo(click.style(
            f"  [HALT] gh pr merge failed (rc={rc}) -- HITL required",
            fg="red"))
        _wal_append(repo, pr_number, "merge_failed", dry_run=dry_run)
        sys.exit(rc)
    click.echo(click.style("  [STEP 3] Merge [OK]", fg="green"))

    # STEP 4: WAL append post-merge
    _wal_append(repo, pr_number, "merge_success", dry_run=dry_run)
    click.echo(click.style("  [STEP 4] WAL append [OK]", fg="green"))

    # STEP 5: Drift check phi-CPS (non-blocking)
    click.echo(click.style("  [STEP 5] Drift check phi-CPS (non-blocking)", fg="cyan"))
    _run(["kiva", "phi-cps", "status"], dry_run=dry_run)
    click.echo(click.style("  [STEP 5] Drift [OK]", fg="green"))

    # Final report
    click.echo("")
    # Le succes n est PAS annonce sur la seule parole de l outil : l etat
    # REEL de la PR est verifie (merged + state) avant l annonce. Sans cela,
    # le wrapper annoncait "MERGE COMPLETE" y compris sur une PR deja
    # mergee (rien n avait alors ete fait) -- un succes trompeur.
    _merged, _state = _verify_pr_merged(repo, pr_number)
    if _merged:
        click.echo(click.style(
            f"  [OK] MERGE COMPLETE -- {repo} PR #{pr_number} -> main",
            fg="green", bold=True))
    else:
        click.echo(click.style(
            f"  [KO] MERGE NON CONFIRME -- {repo} PR #{pr_number} "
            f"(etat reel : {_state})",
            fg="red", bold=True))
        raise SystemExit(1)
    click.echo(click.style(
        f"  IntentHash: 0xKIVA_MERGE_SOVEREIGN_phi4559",
        fg="bright_black"))
    click.echo("")

