"""KIVA nexus commands — gouvernance .nexus/ pour les repos ECOS.

Groupe : kiva nexus
Sous-groupes / commandes :
  kiva nexus tracking init <REPO> [--path PATH] [--dry-run]
  kiva nexus drift check   [--repo REPO] [--since HOURS] [--phi-only] [--status-scan]

Extensions futures :
  kiva nexus status <REPO>
  kiva nexus reciprocity <REPO>
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import click

# KIVA-012 S1 — Pipeline Registry
from kiva_cli.core.pipeline_registry import (
    PipelineRecord,
    PipelineRegistryStore,
    discover_pipelines,
    compute_schema_hash,
)

# ---------------------------------------------------------------------------
# Chemins canoniques par défaut (L0-CANON sur D:\DO\WEB\TOOLS)
# ---------------------------------------------------------------------------
_L0_CANON_ROOT = Path(r"D:\DO\WEB\TOOLS\L0-CANON")

_REPO_TIER: dict[str, str] = {
    "BLO": "L0-CANON",
    "WAZAA": "L0-CANON",
    "COMET": "L0-CANON",
    "GOVERNANCE-HUB": "L0-CANON",
    "LYCOS": "L1-ACTIVE",
    "CodeDB-E5620": "L1-ACTIVE",
    "NEXUS": "L0-CANON",
    "ONTOLOGY": "L0-CANON",
    "BRAIN": "L1-ACTIVE",
    "ECOYSTEM": "L0-CANON",
    "KIVA-CLI": "L0-CANON",
    "FLUENCE": "L1-ACTIVE",
    "DevTools": "L1-ACTIVE",
}

_REPO_OWNER = "gerivdb"
_NEXUS_SOT = "gerivdb/NEXUS"
_ECOS_ROOT_SOT = "gerivdb/ECOYSTEM — ECOS_ROOT.json"

# Seuil φ-CPS drift (aligné sur GlobalWALManager default)
_PHI_DRIFT_THRESHOLD = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _intent_hash(repo: str, ts: str) -> str:
    raw = f"nexus.tracking.init::{repo}::{ts}"
    return "0x" + hashlib.sha256(raw.encode()).hexdigest()[:32].upper()


def _default_path(repo: str) -> Path:
    tier = _REPO_TIER.get(repo, "L1-ACTIVE")
    return _L0_CANON_ROOT.parent / tier / repo


def _severity_icon(phi_cps_alert: bool, validation_state: str) -> str:
    if phi_cps_alert:
        return "[!]"
    if validation_state in ("FAILED", "INVALID"):
        return "[x]"
    if validation_state == "PENDING":
        return "[?]"
    return "[ok]"


# ---------------------------------------------------------------------------
# Template TRACKING.md
# ---------------------------------------------------------------------------

def _tracking_md(repo: str, ts: str) -> str:
    tier = _REPO_TIER.get(repo, "L1-ACTIVE")
    return f"""# .nexus/TRACKING.md — {repo}

> **SOT** : `{_NEXUS_SOT}` (prime)
> **ECOS_ROOT** : `{_ECOS_ROOT_SOT}`
> Généré par : `kiva nexus tracking init {repo}`
> Généré le : `{ts}`

---

## Identité

| Champ | Valeur |
|-------|--------|
| Repo | `{repo}` |
| Owner | `{_REPO_OWNER}` |
| Tier | `{tier}` |
| GitHub | `https://github.com/{_REPO_OWNER}/{repo}` |

---

## État courant

| Sprint actif | Statut | Dernière sync NEXUS |
|-------------|--------|---------------------|
| — | `UNTRACKED` | `{ts}` |

---

## Dépendances déclarées

> À compléter manuellement ou via `kiva nexus status {repo}`

- `NEXUS` (SOT global)
- `ECOYSTEM` (ECOS_ROOT.json)

---

## Historique

| Date | Action | Auteur |
|------|--------|--------|
| `{ts}` | `.nexus/` initialisé (P1.4) | `kiva nexus tracking init` |

---

*Ce fichier est gouverné par NEXUS. Ne pas modifier manuellement le bloc "Identité".*
"""


# ---------------------------------------------------------------------------
# Template STATUS.yaml
# ---------------------------------------------------------------------------

def _status_yaml(repo: str, ts: str, intent_hash: str) -> str:
    tier = _REPO_TIER.get(repo, "L1-ACTIVE")
    return f"""# .nexus/STATUS.yaml — {repo}
# SOT: {_NEXUS_SOT}
# Généré par: kiva nexus tracking init {repo}
# Généré le: {ts}

repo: {repo}
owner: {_REPO_OWNER}
tier: {tier}
github_url: https://github.com/{_REPO_OWNER}/{repo}

nexus_status: UNTRACKED
last_synced_at: "{ts}"
conflict_flag: false

operational_owner: gerivdb
canonical_source: {_NEXUS_SOT}
ecos_root_sot: {_ECOS_ROOT_SOT}

entity_type: REPO
nexus_version: "1.9.0"

intent_hash: "{intent_hash}"

# Extensions futures
# sprint_active: ~
# phi_cps_score: ~
# drift_delta: ~
# reciprocity_score: ~
"""


# ---------------------------------------------------------------------------
# Groupe Click
# ---------------------------------------------------------------------------

@click.group(name="nexus")
def nexus_cli():
    """Gouvernance NEXUS — gestion des fichiers .nexus/ et drift detection.

    Commandes disponibles :
      tracking init <REPO>   Initialise .nexus/TRACKING.md + STATUS.yaml
      drift check            Détecte les dérives φ-CPS et les alertes WAL

    Extensions futures :
      status <REPO>          Affiche l'état NEXUS d'un repo
      reciprocity <REPO>     Calcule le score de réciprocité
    """
    pass


# ---------------------------------------------------------------------------
# Sous-groupe: kiva nexus pipeline   (KIVA-012 S1)
# ---------------------------------------------------------------------------

@nexus_cli.group(name="pipeline")
def pipeline_cli():
    """Gouvernance des pipelines KIVA (list, validate, show, history, drift, prune)."""
    pass


# ---------------------------------------------------------------------------
# kiva nexus pipeline list
# ---------------------------------------------------------------------------

@pipeline_cli.command(name="list")
@click.option(
    "--pipelines-dir",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Répertoire contenant les *.yaml (défaut: .kiva/pipelines)",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Sortie JSON machine-readable")
def pipeline_list(pipelines_dir: Path | None, as_json: bool):
    """Liste les pipelines découverts avec métadonnées du registry."""
    store = PipelineRegistryStore()
    base = pipelines_dir
    pipelines = discover_pipelines(base)

    records = []
    for p in pipelines:
        name = p.stem
        rec = store.get_record(name)
        if rec is None:
            # Créer un enregistrement minimal pour l'affichage
            schema_h = compute_schema_hash(p)
            rec = PipelineRecord(
                name=name,
                schema_hash=schema_h,
                step_count=0,  # sera enrichi plus tard
            )

        records.append({
            "name": rec.name,
            "version": rec.version,
            "nexus_status": rec.nexus_status,
            "steps": rec.step_count,
            "last_run": rec.last_run_at or "-",
            "last_status": rec.last_status or "-",
            "schema_hash": rec.schema_hash,
        })

    if as_json:
        click.echo(json.dumps(records, indent=2, ensure_ascii=False))
        return

    if not records:
        click.echo("Aucun pipeline trouvé dans .kiva/pipelines/")
        return

    click.echo("Nom              Ver  Statut   Steps  Dernier run          Statut run   Schema")
    click.echo("-" * 90)
    for r in records:
        click.echo(
            f"{r['name']:<16} {r['version']:<4} {r['nexus_status']:<8} "
            f"{r['steps']:<6} {r['last_run']:<20} {r['last_status']:<12} {r['schema_hash']}"
        )


# ---------------------------------------------------------------------------
# kiva nexus pipeline validate
# ---------------------------------------------------------------------------

@pipeline_cli.command(name="validate")
@click.argument("name")
def pipeline_validate(name: str):
    """Valide le DAG et la structure d'un pipeline."""
    from kiva_cli.core.pipeline_loader import load_pipeline, detect_cycles

    # Cherche le fichier
    candidates = discover_pipelines()
    target = None
    for p in candidates:
        if p.stem == name:
            target = p
            break

    if target is None:
        click.echo(f"[FAIL] Pipeline '{name}' introuvable dans .kiva/pipelines/", err=True)
        sys.exit(2)

    try:
        pipeline = load_pipeline(target)
        cycles = detect_cycles(pipeline.steps)
        if cycles:
            click.echo(f"[FAIL] Cycles détectés : {cycles}", err=True)
            sys.exit(1)

        click.echo(f"[OK] {name} valide ({len(pipeline.steps)} steps, pas de cycle)")
        sys.exit(0)
    except Exception as exc:
        click.echo(f"[FAIL] {name} : {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# kiva nexus pipeline show
# ---------------------------------------------------------------------------

@pipeline_cli.command(name="show")
@click.argument("name")
def pipeline_show(name: str):
    """Affiche les métadonnées complètes d'un pipeline depuis le registry."""
    store = PipelineRegistryStore()
    rec = store.get_record(name)

    if rec is None:
        click.echo(f"Pipeline '{name}' inconnu dans le registry.", err=True)
        # Try to see if the YAML exists at least
        candidates = discover_pipelines()
        if any(p.stem == name for p in candidates):
            click.echo(f"  (Le fichier .kiva/pipelines/{name}.yaml existe mais n'a jamais été exécuté)")
        return

    click.echo(f"\n=== Pipeline: {rec.name} ===")
    click.echo(f"  Version            : {rec.version}")
    click.echo(f"  Nexus Status       : {rec.nexus_status}")
    click.echo(f"  Schema Hash        : {rec.schema_hash}")
    click.echo(f"  Steps              : {rec.step_count}")
    click.echo(f"  Owner              : {rec.operational_owner}")
    click.echo(f"  Registered         : {rec.registered_at or '-'}")
    click.echo("")
    click.echo("--- Runtime ---")
    click.echo(f"  Last run           : {rec.last_run_at or '-'}")
    click.echo(f"  Last status        : {rec.last_status or '-'}")
    click.echo(f"  Last success       : {rec.last_success_at or '-'}")
    click.echo(f"  Last intent hash   : {rec.last_intent_hash or '-'}")
    click.echo(f"  Total runs         : {rec.total_runs}")
    click.echo(f"  Success runs       : {rec.success_runs}")
    rate = (rec.success_runs / rec.total_runs * 100) if rec.total_runs else 0.0
    click.echo(f"  Success rate       : {rate:.1f}%")
    click.echo(f"  Avg duration       : {rec.avg_duration_s:.2f}s")


# ---------------------------------------------------------------------------
# kiva nexus pipeline history
# ---------------------------------------------------------------------------

@pipeline_cli.command(name="history")
@click.argument("name")
@click.option("--limit", default=10, show_default=True, help="Nombre max d'exécutions à afficher")
def pipeline_history(name: str, limit: int):
    """Affiche l'historique des exécutions d'un pipeline depuis le WAL."""
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
    except Exception as exc:
        click.echo(f"[ERROR] WAL inaccessible : {exc}", err=True)
        return

    try:
        events = wal.query_events(event_type="PIPELINE_RUN", limit=limit * 2)  # overfetch then filter
    except Exception as exc:
        click.echo(f"[WARN] Impossible de requêter le WAL : {exc}")
        return

    # Filter client-side for this pipeline
    relevant = []
    for ev in events:
        payload = ev.get("payload") or {}
        if payload.get("pipeline_name") == name:
            relevant.append(ev)
            if len(relevant) >= limit:
                break

    if not relevant:
        click.echo(f"Aucune exécution trouvée pour le pipeline '{name}'.")
        return

    click.echo(f"\n=== Historique {name} (dernières {len(relevant)}) ===")
    for ev in relevant:
        payload = ev.get("payload", {})
        ts = ev.get("timestamp", "")
        status = payload.get("status", "?")
        dur = payload.get("duration_s", 0)
        click.echo(f"  {ts}  {status:<10}  {dur:6.2f}s")


# ---------------------------------------------------------------------------
# kiva nexus pipeline drift   (KIVA-012 S3)
# ---------------------------------------------------------------------------

@pipeline_cli.command(name="drift")
@click.option(
    "--pipelines-dir",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    default=None,
    help="Répertoire racine contenant .kiva/pipelines/ (défaut: cwd)",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Sortie JSON machine-readable")
@click.option("--fail-on-drift", is_flag=True, default=False, help="Exit 1 si au moins un drift détecté")
def pipeline_drift(pipelines_dir: Path | None, as_json: bool, fail_on_drift: bool):
    """Détecte les dérives de schema_hash (YAML courant vs dernier run SUCCESS).

    Compare le schema_hash enregistré lors du dernier SUCCESS avec
    le hash calculé sur le YAML courant. Un drift = le YAML a changé
    depuis le dernier run réussi.

    Exit codes :
      0 = aucun drift
      1 = au moins un drift détecté (avec --fail-on-drift)
      2 = store ou YAML inaccessible
    """
    import json as json_mod

    try:
        store = PipelineRegistryStore()
    except Exception as exc:
        click.echo(f"[ERROR] Store inaccessible : {exc}", err=True)
        sys.exit(2)

    try:
        report = store.compute_drift_report(pipelines_root=pipelines_dir)
    except Exception as exc:
        click.echo(f"[ERROR] compute_drift_report() : {exc}", err=True)
        sys.exit(2)

    if as_json:
        click.echo(json_mod.dumps(report, indent=2, ensure_ascii=False))
        if fail_on_drift and any(r["drifted"] for r in report):
            sys.exit(1)
        return

    drifted = [r for r in report if r["drifted"]]
    stable = [r for r in report if not r["drifted"]]

    click.echo(f"\n=== kiva nexus pipeline drift ===")
    click.echo(f"  Pipelines scannés : {len(report)}")
    click.echo(f"  Driftés           : {len(drifted)}")
    click.echo(f"  Stables           : {len(stable)}")
    click.echo("")

    if drifted:
        click.echo("--- Dérives détectées ---")
        for r in drifted:
            click.echo(f"  [DRIFT] {r['name']}")
            click.echo(f"          registry : {r['registry_hash']}")
            click.echo(f"          current  : {r['current_hash']}")
            click.echo(f"          dernier SUCCESS : {r['last_success_at']}")
            click.echo(f"          yaml     : {r['yaml_path']}")
        click.echo("")

    if stable:
        click.echo("--- Stables ---")
        for r in stable:
            click.echo(f"  [OK]    {r['name']}  hash={r['current_hash']}  last_success={r['last_success_at']}")
        click.echo("")

    if not drifted:
        click.echo("[OK] Aucun drift détecté — tous les pipelines sont stables.")
    else:
        click.echo(f"[!!] {len(drifted)} pipeline(s) drifté(s) — relancer ou mettre à jour le registry.")

    if fail_on_drift and drifted:
        sys.exit(1)


# ---------------------------------------------------------------------------
# kiva nexus pipeline prune   (KIVA-012 S4)
# ---------------------------------------------------------------------------

@pipeline_cli.command(name="prune")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Affiche les orphelins sans les supprimer.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Supprime sans confirmation interactive.",
)
@click.option(
    "--name",
    "names",
    multiple=True,
    help="Supprime uniquement les pipelines spécifiés (répétable).",
)
@click.option("--json", "as_json", is_flag=True, default=False, help="Sortie JSON machine-readable.")
def pipeline_prune(dry_run: bool, force: bool, names: tuple[str, ...], as_json: bool):
    """Supprime les pipelines orphelins du registry.

    Un pipeline est orphelin si :
      - total_runs == 0 (jamais exécuté)
      - operational_owner manquant
      - dernier run > 30 jours

    Modes :
      kiva nexus pipeline prune --dry-run         → aperçu uniquement
      kiva nexus pipeline prune                   → confirmation interactive
      kiva nexus pipeline prune --force           → suppression directe
      kiva nexus pipeline prune --name build      → cible spécifique

    Exit codes :
      0 = OK (rien à supprimer ou suppression réussie)
      1 = annulé par l'utilisateur
      2 = store inaccessible
    """
    import json as json_mod

    try:
        store = PipelineRegistryStore()
    except Exception as exc:
        click.echo(f"[ERROR] Store inaccessible : {exc}", err=True)
        sys.exit(2)

    # -- Déterminer les cibles -----------------------------------------------
    if names:
        # Mode ciblé : prune uniquement les noms explicites
        targets = []
        for n in names:
            rec = store.get_record(n)
            if rec is None:
                click.echo(f"[WARN] Pipeline '{n}' introuvable dans le registry.", err=True)
            else:
                targets.append(rec)
    else:
        # Mode auto : tous les orphelins
        targets = store.find_orphans()

    # -- Sortie JSON ---------------------------------------------------------
    if as_json:
        payload = [
            {
                "name": r.name,
                "total_runs": r.total_runs,
                "last_run_at": r.last_run_at,
                "operational_owner": r.operational_owner,
                "nexus_status": r.nexus_status,
                "would_delete": not dry_run,
            }
            for r in targets
        ]
        click.echo(json_mod.dumps(payload, indent=2, ensure_ascii=False))
        if not dry_run and targets and (force or _confirm_prune(targets)):
            for r in targets:
                store.delete_record(r.name)
        return

    # -- Affichage -----------------------------------------------------------
    click.echo(f"\n=== kiva nexus pipeline prune {'(DRY-RUN)' if dry_run else ''} ===")

    if not targets:
        click.echo("  Aucun pipeline orphelin trouvé — registry propre.")
        return

    click.echo(f"\n  {len(targets)} pipeline(s) orphelin(s) :\n")
    click.echo(f"  {'Nom':<20} {'Runs':>6}  {'Dernier run':<22}  {'Owner':<16}  Raison")
    click.echo("  " + "-" * 82)
    for r in targets:
        reason = _orphan_reason(r)
        last_run = r.last_run_at or "-"
        click.echo(
            f"  {r.name:<20} {r.total_runs:>6}  {last_run:<22}  {r.operational_owner or '(none)':<16}  {reason}"
        )
    click.echo("")

    if dry_run:
        click.echo(f"  [DRY-RUN] {len(targets)} entrée(s) seraient supprimées. Relancer sans --dry-run pour confirmer.")
        return

    # -- Confirmation / suppression ------------------------------------------
    if not force:
        if not _confirm_prune(targets):
            click.echo("  Annulé.")
            sys.exit(1)

    deleted = 0
    for r in targets:
        if store.delete_record(r.name):
            click.echo(f"  [OK] Supprimé : {r.name}")
            deleted += 1
        else:
            click.echo(f"  [WARN] Déjà absent : {r.name}")

    click.echo(f"\n  [DONE] {deleted}/{len(targets)} entrée(s) supprimée(s) du registry.")


def _orphan_reason(rec: PipelineRecord) -> str:
    """Retourne la raison principale pour laquelle un record est orphelin."""
    if rec.total_runs == 0:
        return "jamais exécuté"
    if not rec.operational_owner or rec.operational_owner.strip() == "":
        return "pas d'owner"
    if rec.last_run_at:
        try:
            last = time.mktime(time.strptime(rec.last_run_at, "%Y-%m-%dT%H:%M:%SZ"))
            stale_days = int((time.time() - last) / 86400)
            return f"inactif depuis {stale_days}j"
        except ValueError:
            return "date invalide"
    return "inconnu"


def _confirm_prune(targets: list) -> bool:
    """Confirmation interactive avant suppression."""
    try:
        answer = click.prompt(
            f"  Supprimer {len(targets)} entrée(s) ? [y/N]",
            default="N",
            show_default=False,
        )
        return answer.strip().lower() in ("y", "yes", "o", "oui")
    except (click.Abort, EOFError):
        return False


# ---------------------------------------------------------------------------
# nexus tracking
# ---------------------------------------------------------------------------

@nexus_cli.group(name="tracking")
def tracking_cli():
    """Gestion des fichiers .nexus/TRACKING.md et STATUS.yaml."""
    pass


@tracking_cli.command(name="init")
@click.argument("repo")
@click.option(
    "--path", "repo_path",
    default=None,
    help="Chemin local du repo (override L0-CANON autodétection).",
    type=click.Path()
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Affiche les fichiers sans les écrire."
)
def tracking_init(repo: str, repo_path: Optional[str], dry_run: bool):
    """Initialise .nexus/TRACKING.md + .nexus/STATUS.yaml pour REPO.

    Exemple :

      kiva nexus tracking init BLO

      kiva nexus tracking init WAZAA --path D:\\DO\\WEB\\TOOLS\\L0-CANON\\WAZAA

      kiva nexus tracking init COMET --dry-run
    """
    ts = _now_iso()
    ih = _intent_hash(repo, ts)

    if repo_path:
        base = Path(repo_path)
    else:
        base = _default_path(repo)

    nexus_dir = base / ".nexus"
    tracking_file = nexus_dir / "TRACKING.md"
    status_file = nexus_dir / "STATUS.yaml"

    tracking_content = _tracking_md(repo, ts)
    status_content = _status_yaml(repo, ts, ih)

    click.echo(f"\n{'[DRY-RUN] ' if dry_run else ''}kiva nexus tracking init :: {repo}")
    click.echo(f"  Tier      : {_REPO_TIER.get(repo, 'L1-ACTIVE')}")
    click.echo(f"  Path      : {base}")
    click.echo(f"  .nexus/   : {nexus_dir}")
    click.echo(f"  Timestamp : {ts}")
    click.echo(f"  Hash      : {ih}")

    if dry_run:
        click.echo("\n--- TRACKING.md (preview) ---")
        click.echo(tracking_content[:400] + "...")
        click.echo("\n--- STATUS.yaml (preview) ---")
        click.echo(status_content[:400] + "...")
        click.echo("\n[DRY-RUN] Aucun fichier écrit.")
        return

    if not base.exists():
        click.echo(f"\n  [WARN] Répertoire introuvable : {base}")
        click.echo("   -> Utilisez --path pour spécifier le chemin correct.")
        click.echo("   -> Ou clonez le repo en premier.")
        sys.exit(1)

    nexus_dir.mkdir(parents=True, exist_ok=True)

    for fpath, content, label in [
        (tracking_file, tracking_content, "TRACKING.md"),
        (status_file, status_content, "STATUS.yaml"),
    ]:
        if fpath.exists():
            click.echo(f"  [SKIP] {label} existe deja - non ecrase. Utilisez --force pour forcer.")
        else:
            fpath.write_text(content, encoding="utf-8")
            click.echo(f"  [OK] {label} cree : {fpath}")

    click.echo(f"\n[OK] .nexus/ initialise pour {repo}")
    click.echo(f"   -> git add {nexus_dir} && git commit -m 'chore(nexus): init .nexus/ tracking [{repo}]'")
    click.echo(f"   -> git push origin main")


# ---------------------------------------------------------------------------
# nexus drift
# ---------------------------------------------------------------------------

@nexus_cli.group(name="drift")
def drift_cli():
    """Detection de derive NEXUS (phi-CPS + alertes WAL)."""
    pass


@drift_cli.command(name="check")
@click.option(
    "--repo", "repo_filter",
    default=None,
    help="Filtrer les alertes WAL pour un repo specifique."
)
@click.option(
    "--since",
    default=24,
    show_default=True,
    type=int,
    help="Fenetre de recherche en heures (defaut: 24h)."
)
@click.option(
    "--phi-only",
    is_flag=True,
    default=False,
    help="Afficher uniquement les evenements avec phi_cps_alert=True."
)
@click.option(
    "--status-scan",
    is_flag=True,
    default=False,
    help="Scanner aussi les .nexus/STATUS.yaml des repos en L0-CANON."
)
@click.option(
    "--limit",
    default=20,
    show_default=True,
    type=int,
    help="Nombre max d'evenements WAL a afficher."
)
def drift_check(
    repo_filter: Optional[str],
    since: int,
    phi_only: bool,
    status_scan: bool,
    limit: int,
):
    """Detecte les derives phi-CPS et signale les alertes WAL NEXUS.

    Sources consultees :
      1. WAL global (~/.kiva/global_wal.db) — phi_cps_alert + validation_state
      2. (optionnel) .nexus/STATUS.yaml de chaque repo L0-CANON

    Exemples :

      kiva nexus drift check

      kiva nexus drift check --repo BLO --since 48

      kiva nexus drift check --phi-only

      kiva nexus drift check --status-scan
    """
    # -- Connexion WAL -------------------------------------------------------
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
    except Exception as exc:
        click.echo(f"[ERROR] WAL inaccessible : {exc}", err=True)
        sys.exit(1)

    # -- 1. Drift phi-CPS global ---------------------------------------------
    click.echo("\n=== kiva nexus drift check ===")
    click.echo(f"    WAL     : ~/.kiva/global_wal.db")
    click.echo(f"    Fenetre : dernières {since}h")
    if repo_filter:
        click.echo(f"    Repo    : {repo_filter}")
    click.echo("")

    try:
        drift = wal.get_drift()
        abs_drift = drift.get("absolute_drift", 0.0)
        rel_drift = drift.get("relative_drift", 0.0)
        exceeded = drift.get("threshold_exceeded", False)
        alert_count = drift.get("alert_count", 0)
        total_events = drift.get("events_since_baseline", 0)

        drift_icon = "[!!]"
        drift_ok = "[OK]"
        phi_icon = drift_icon if exceeded else drift_ok

        click.echo("--- phi-CPS global ---")
        click.echo(f"  baseline   : {drift.get('baseline_phi', 0.0):.6f}")
        click.echo(f"  current    : {drift.get('current_phi', 0.0):.6f}")
        click.echo(f"  delta      : {abs_drift:+.6f}  (relative: {rel_drift:+.2%})")
        click.echo(f"  threshold  : +/-{_PHI_DRIFT_THRESHOLD:.2%}")
        click.echo(f"  status     : {phi_icon} {'DRIFT DETECTE' if exceeded else 'STABLE'}")
        click.echo(f"  alerts     : {alert_count} / {total_events} events")
        click.echo("")
    except Exception as exc:
        click.echo(f"  [WARN] get_drift() indisponible : {exc}")
        click.echo("")

    # -- 2. Evenements WAL avec alertes --------------------------------------
    start_time = (
        datetime.now(timezone.utc) - timedelta(hours=since)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    try:
        events = wal.query_events(
            repo=repo_filter,
            start_time=start_time,
            phi_cps_alert_only=phi_only,
            limit=limit,
        )
    except Exception as exc:
        click.echo(f"  [WARN] query_events() indisponible : {exc}")
        events = []

    # Filtrage supplémentaire : si pas --phi-only, on remonte tous les events
    # mais on met en valeur ceux avec phi_cps_alert
    click.echo(f"--- Evenements WAL (dernières {since}h{', phi-only' if phi_only else ''}) ---")

    if not events:
        click.echo("  (aucun evenement dans cette fenetre)")
    else:
        header = f"  {'Timestamp':<22} {'Type':<22} {'Repos':<28} {'phi_delta':>10}  {'State':<10}  Alerte"
        sep = "  " + "-" * (len(header) - 2)
        click.echo(header)
        click.echo(sep)
        for ev in events:
            ts_str = str(ev.get("timestamp", "-"))[:19]
            etype = str(ev.get("event_type", "-"))[:20]
            repos = ev.get("repositories", [])
            repos_str = ", ".join(repos)[:26] if repos else "-"
            phi_delta = ev.get("phi_cps_delta", 0.0)
            vstate = str(ev.get("validation_state", "-"))[:10]
            is_alert = ev.get("phi_cps_alert", False)
            icon = _severity_icon(is_alert, vstate)
            click.echo(
                f"  {ts_str:<22} {etype:<22} {repos_str:<28} {phi_delta:>+10.6f}  {vstate:<10}  {icon}"
            )
    click.echo("")

    # -- 3. Scan .nexus/STATUS.yaml (optionnel) ------------------------------
    if status_scan:
        click.echo("--- Scan .nexus/STATUS.yaml (L0-CANON) ---")
        found_any = False
        for tier_dir in [_L0_CANON_ROOT, _L0_CANON_ROOT.parent / "L1-ACTIVE"]:
            if not tier_dir.exists():
                continue
            for status_file in sorted(tier_dir.glob("*/.nexus/STATUS.yaml")):
                found_any = True
                repo_name = status_file.parent.parent.name
                # Filtre repo si spécifié
                if repo_filter and repo_filter.lower() not in repo_name.lower():
                    continue
                try:
                    import yaml  # type: ignore
                    data = yaml.safe_load(status_file.read_text(encoding="utf-8"))
                except ImportError:
                    # Fallback: lecture brute pour nexus_status + last_synced_at
                    data = {}
                    for line in status_file.read_text(encoding="utf-8").splitlines():
                        if ":" in line and not line.strip().startswith("#"):
                            k, _, v = line.partition(":")
                            data[k.strip()] = v.strip().strip('"')
                except Exception:
                    data = {}

                nexus_status = data.get("nexus_status", "UNKNOWN")
                last_sync = data.get("last_synced_at", "-")
                conflict = data.get("conflict_flag", "false")
                conflict_flag = str(conflict).lower() not in ("false", "0", "")

                status_icon = "[!!]" if conflict_flag else (
                    "[?]" if nexus_status in ("UNTRACKED", "UNKNOWN") else "[ok]"
                )
                click.echo(
                    f"  {status_icon}  {repo_name:<24} status={nexus_status:<14} "
                    f"sync={str(last_sync)[:19]}  conflict={conflict}"
                )
        if not found_any:
            click.echo("  (aucun .nexus/STATUS.yaml trouvé dans L0-CANON / L1-ACTIVE)")
        click.echo("")

    # -- 4. Pipeline schema drift (S3) ----------------------------------------
    click.echo("--- Pipeline schema drift ---")
    try:
        store = PipelineRegistryStore()
        pdrift = store.compute_drift_report()
        pd_count = sum(1 for r in pdrift if r["drifted"])
        if pd_count:
            click.echo(f"  [!!] {pd_count} pipeline(s) avec schema_hash drifté :")
            for r in pdrift:
                if r["drifted"]:
                    click.echo(f"       - {r['name']}  (last_success={r['last_success_at']})")
        else:
            click.echo(f"  [OK] {len(pdrift)} pipeline(s) stables (aucun schema drift)")
    except Exception as exc:
        click.echo(f"  [WARN] Pipeline drift check indisponible : {exc}")
    click.echo("")

    # -- 5. Résumé final -------------------------------------------------------
    click.echo("--- Résumé ---")
    if exceeded:
        click.echo("  [!!] DRIFT phi-CPS detecte — verifier les deltas et les pipelines recents")
    if alert_count and alert_count > 0:
        click.echo(f"  [!]  {alert_count} alerte(s) phi_cps enregistree(s) dans le WAL")
    if not exceeded and (not alert_count or alert_count == 0):
        click.echo("  [OK] Aucune derive detectee dans la fenetre analysee")
    click.echo("")
