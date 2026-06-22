"""KIVA nexus commands — gouvernance .nexus/ pour les repos ECOS.

Groupe : kiva nexus
Sous-groupes / commandes :
  kiva nexus tracking init <REPO> [--path PATH] [--dry-run]
  kiva nexus drift check   [--repo REPO] [--since HOURS] [--phi-only] [--status-scan]
  kiva nexus query <path>  [--section status|tracking|wal|all] [--format json|yaml|table]
  kiva nexus mutate --op <op> --path <path> [--data <json>] [--dry-run]
  kiva nexus status <repo>
  kiva nexus pipeline <subcmd>
  kiva nexus sync [--dry-run] [--skip-watchdog]
"""

from __future__ import annotations

import hashlib
import json as json_mod
import os
import subprocess
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
# Chemins canoniques par défaut (L0-CANON sur D:\\DO\\WEB\\TOOLS)
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


def _read_yaml_file(path: Path) -> dict:
    """Lit un fichier YAML et retourne un dict. Fallback: parsing manuel."""
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except ImportError:
        data = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, _, v = line.partition(":")
                data[k.strip()] = v.strip().strip('"').strip("'")
        return data
    except Exception:
        return {}


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
# Groupe Click principal
# ---------------------------------------------------------------------------

@click.group(name="nexus")
def nexus_cli():
    """Gouvernance NEXUS — gestion des fichiers .nexus/ et drift detection.

    Commandes disponibles :
      tracking init <REPO>   Initialise .nexus/TRACKING.md + STATUS.yaml
      drift check            Détecte les dérives φ-CPS et les alertes WAL
      query <path>           Lit l'état NEXUS (STATUS.yaml, TRACKING.md, WAL)
      mutate --op <op>       Écrit / mute un champ NEXUS
      status <repo>          Affiche l'état condensé d'un repo
      pipeline               Gouvernance des pipelines (list, validate, drift, prune)
      sync                   Enchaîne les 5 scripts du weekly sync NEXUS
    """
    pass


# ===========================================================================
# SOUS-GROUPE: kiva nexus query
# ===========================================================================

@nexus_cli.command(name="query")
@click.argument("path", type=click.Path(exists=False))
@click.option(
    "--section",
    type=click.Choice(["status", "tracking", "wal", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="Section à lire",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "yaml", "table"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Format de sortie",
)
@click.option(
    "--since",
    default=24,
    show_default=True,
    type=int,
    help="Fenêtre WAL en heures (uniquement si section=wal ou all)",
)
def nexus_query(path: str, section: str, fmt: str, since: int):
    """Lit l'état NEXUS d'un repo ou d'un fichier .nexus/.

    Équivalent API : GET /api/v3/query?path=<path>

    Le PATH peut être :
      - Un chemin vers un repo (lit .nexus/STATUS.yaml + TRACKING.md)
      - Un chemin vers un fichier .nexus/STATUS.yaml spécifique
      - Un chemin vers un fichier .nexus/TRACKING.md

    Exemples :

      kiva nexus query D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS

      kiva nexus query D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS\\.nexus\\STATUS.yaml

      kiva nexus query D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS --section status

      kiva nexus query D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS --section wal --since 48

      kiva nexus query D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS --format yaml
    """
    target = Path(path)
    result: dict = {"path": str(target), "timestamp": _now_iso()}

    # -- Déterminer le repo root et les chemins .nexus/ ------------------------
    if target.is_file():
        if target.name == "STATUS.yaml":
            nexus_dir = target.parent
            repo_root = nexus_dir.parent
        elif target.name == "TRACKING.md":
            nexus_dir = target.parent
            repo_root = nexus_dir.parent
        else:
            # Fichier quelconque — lire brut
            result["content"] = target.read_text(encoding="utf-8")
            _output(result, fmt)
            return
    elif target.is_dir():
        # Si on pointe vers .nexus/ directement
        if target.name == ".nexus":
            nexus_dir = target
            repo_root = target.parent
        else:
            # Repo root — chercher .nexus/
            repo_root = target
            nexus_dir = target / ".nexus"
    else:
        click.echo(f"[ERROR] Chemin introuvable : {target}", err=True)
        sys.exit(1)

    repo_name = repo_root.name
    status_file = nexus_dir / "STATUS.yaml"
    tracking_file = nexus_dir / "TRACKING.md"

    # -- Section: status (STATUS.yaml) ----------------------------------------
    if section in ("status", "all"):
        if status_file.exists():
            status_data = _read_yaml_file(status_file)
            result["status"] = status_data
        else:
            result["status"] = None
            result["status_missing"] = str(status_file)

    # -- Section: tracking (TRACKING.md) --------------------------------------
    if section in ("tracking", "all"):
        if tracking_file.exists():
            result["tracking"] = {
                "file": str(tracking_file),
                "content": tracking_file.read_text(encoding="utf-8"),
            }
        else:
            result["tracking"] = None
            result["tracking_missing"] = str(tracking_file)

    # -- Section: wal (événements WAL) ----------------------------------------
    if section in ("wal", "all"):
        try:
            from kiva_cli.core.global_wal_manager import GlobalWALManager
            wal = GlobalWALManager()
            start_time = (
                datetime.now(timezone.utc) - timedelta(hours=since)
            ).strftime("%Y-%m-%dT%H:%M:%S")
            events = wal.query_events(
                repo=repo_name,
                start_time=start_time,
                limit=50,
            )
            result["wal_events"] = events
            result["wal_count"] = len(events)
        except Exception as exc:
            result["wal_events"] = []
            result["wal_error"] = str(exc)

    # -- Sortie ---------------------------------------------------------------
    _output(result, fmt)


def _output(data: dict, fmt: str) -> None:
    """Formate et affiche le résultat."""
    if fmt == "json":
        click.echo(json_mod.dumps(data, indent=2, ensure_ascii=False, default=str))
    elif fmt == "yaml":
        try:
            import yaml  # type: ignore
            click.echo(yaml.dump(data, default_flow_style=False, allow_unicode=True))
        except ImportError:
            click.echo(json_mod.dumps(data, indent=2, ensure_ascii=False, default=str))
    elif fmt == "table":
        # Affichage tabulaire simplifié
        for key, value in data.items():
            if isinstance(value, dict):
                click.echo(f"\n[{key}]")
                for k, v in value.items():
                    click.echo(f"  {k}: {v}")
            elif isinstance(value, list):
                click.echo(f"\n[{key}] ({len(value)} items)")
                for item in value[:10]:
                    click.echo(f"  - {item}")
            else:
                click.echo(f"{key}: {value}")


# ===========================================================================
# SOUS-GROUPE: kiva nexus mutate
# ===========================================================================

@nexus_cli.command(name="mutate")
@click.option(
    "--op",
    required=True,
    type=click.Choice(
        ["update_status", "create_tracking", "set_field", "set_conflict"],
        case_sensitive=False,
    ),
    help="Opération de mutation",
)
@click.option(
    "--path",
    "repo_path",
    required=True,
    type=click.Path(exists=False),
    help="Chemin du repo cible",
)
@click.option(
    "--data",
    default=None,
    help="Données JSON pour la mutation (ex: '{\"nexus_status\": \"ACTIVE\"}')",
)
@click.option(
    "--field",
    default=None,
    help="Chemin du champ (dot notation) pour set_field (ex: nexus_status)",
)
@click.option(
    "--value",
    default=None,
    help="Nouvelle valeur pour set_field",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simule sans écrire",
)
def nexus_mutate(op: str, repo_path: str, data: Optional[str], field: Optional[str], value: Optional[str], dry_run: bool):
    """Écrit / mute un champ NEXUS.

    Équivalent API : POST /api/v3/mutate

    Opérations supportées :
      update_status   Met à jour nexus_status dans STATUS.yaml
      create_tracking Crée .nexus/TRACKING.md + STATUS.yaml (idem tracking init)
      set_field       Modifie un champ spécifique (dot notation)
      set_conflict    Active/désactive conflict_flag

    Exemples :

      kiva nexus mutate --op update_status --path D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS --data '{"nexus_status": "ACTIVE"}'

      kiva nexus mutate --op set_field --path D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS --field nexus_status --value CONFLICT

      kiva nexus mutate --op set_conflict --path D:\\DO\\WEB\\TOOLS\\L0-CANON\\NEXUS --value true

      kiva nexus mutate --op create_tracking --path D:\\DO\\WEB\\TOOLS\\L0-CANON\\BLO

      kiva nexus mutate --op update_status --path D:\\...\\NEXUS --data '{"nexus_status":"ACTIVE"}' --dry-run
    """
    target = Path(repo_path)
    nexus_dir = target / ".nexus" if target.is_dir() else target.parent
    status_file = nexus_dir / "STATUS.yaml"
    ts = _now_iso()

    click.echo(f"\n{'[DRY-RUN] ' if dry_run else ''}kiva nexus mutate :: {op}")
    click.echo(f"  Path : {target}")
    click.echo(f"  Time : {ts}")

    if op == "create_tracking":
        _mutate_create_tracking(target, nexus_dir, dry_run)
        return

    # Les autres ops nécessitent un STATUS.yaml existant
    if not status_file.exists():
        click.echo(f"[ERROR] STATUS.yaml introuvable : {status_file}", err=True)
        click.echo("  -> Créez d'abord avec: kiva nexus mutate --op create_tracking --path ...", err=True)
        sys.exit(1)

    status_data = _read_yaml_file(status_file)

    if op == "update_status":
        payload = json_mod.loads(data) if data else {}
        if not payload:
            click.echo("[ERROR] --data requis pour update_status", err=True)
            sys.exit(1)
        _mutate_update_status(status_file, status_data, payload, dry_run)

    elif op == "set_field":
        if not field or value is None:
            click.echo("[ERROR] --field et --value requis pour set_field", err=True)
            sys.exit(1)
        _mutate_set_field(status_file, status_data, field, value, dry_run)

    elif op == "set_conflict":
        val = value.lower() in ("true", "1", "yes") if value else False
        _mutate_set_field(status_file, status_data, "conflict_flag", val, dry_run)

    else:
        click.echo(f"[ERROR] Opération inconnue : {op}", err=True)
        sys.exit(1)


def _mutate_create_tracking(repo_root: Path, nexus_dir: Path, dry_run: bool) -> None:
    """Crée .nexus/TRACKING.md + STATUS.yaml."""
    repo_name = repo_root.name
    ts = _now_iso()
    ih = _intent_hash(repo_name, ts)

    tracking_file = nexus_dir / "TRACKING.md"
    status_file = nexus_dir / "STATUS.yaml"

    click.echo(f"  Repo : {repo_name}")
    click.echo(f"  Tier : {_REPO_TIER.get(repo_name, 'L1-ACTIVE')}")
    click.echo(f"  Hash : {ih}")

    if dry_run:
        click.echo("\n  [DRY-RUN] Fichiers qui seraient créés :")
        click.echo(f"    - {tracking_file}")
        click.echo(f"    - {status_file}")
        return

    nexus_dir.mkdir(parents=True, exist_ok=True)

    if not tracking_file.exists():
        tracking_file.write_text(_tracking_md(repo_name, ts), encoding="utf-8")
        click.echo(f"  [OK] TRACKING.md créé")
    else:
        click.echo(f"  [SKIP] TRACKING.md existe déjà")

    if not status_file.exists():
        status_file.write_text(_status_yaml(repo_name, ts, ih), encoding="utf-8")
        click.echo(f"  [OK] STATUS.yaml créé")
    else:
        click.echo(f"  [SKIP] STATUS.yaml existe déjà")


def _mutate_update_status(status_file: Path, status_data: dict, payload: dict, dry_run: bool) -> None:
    """Met à jour des champs dans STATUS.yaml."""
    allowed_keys = {"nexus_status", "conflict_flag", "operational_owner", "sprint_active", "phi_cps_score"}
    changes = {}

    for key, value in payload.items():
        if key not in allowed_keys:
            click.echo(f"  [WARN] Champ non autorisé ignoré : {key}")
            continue
        old = status_data.get(key)
        if old != value:
            changes[key] = {"old": old, "new": value}
            status_data[key] = value

    if not changes:
        click.echo("  [OK] Aucun changement détecté")
        return

    click.echo(f"  Changements :")
    for k, v in changes.items():
        click.echo(f"    {k}: {v['old']} → {v['new']}")

    if dry_run:
        click.echo("  [DRY-RUN] Fichier non modifié")
        return

    # Écriture YAML manuelle (préserver le format)
    _write_status_yaml(status_file, status_data)
    click.echo(f"  [OK] STATUS.yaml mis à jour : {status_file}")


def _mutate_set_field(status_file: Path, status_data: dict, field: str, value, dry_run: bool) -> None:
    """Modifie un champ spécifique dans STATUS.yaml (dot notation supportée)."""
    # Support dot notation simple (ex: "nexus_status" ou "metadata.owner")
    keys = field.split(".")
    target = status_data
    for k in keys[:-1]:
        if k not in target or not isinstance(target[k], dict):
            target[k] = {}
        target = target[k]

    old = target.get(keys[-1])
    target[keys[-1]] = value

    click.echo(f"  {field}: {old} → {value}")

    if dry_run:
        click.echo("  [DRY-RUN] Fichier non modifié")
        return

    _write_status_yaml(status_file, status_data)
    click.echo(f"  [OK] STATUS.yaml mis à jour : {status_file}")


def _write_status_yaml(path: Path, data: dict) -> None:
    """Écrit un STATUS.yaml en préservant le format attendu."""
    lines = [
        f"# .nexus/STATUS.yaml — {data.get('repo', 'unknown')}",
        f"# SOT: {_NEXUS_SOT}",
        f"# Généré par: kiva nexus mutate",
        f"# Généré le: {_now_iso()}",
        "",
        f"repo: {data.get('repo', '')}",
        f"owner: {data.get('owner', _REPO_OWNER)}",
        f"tier: {data.get('tier', 'L1-ACTIVE')}",
        f"github_url: {data.get('github_url', '')}",
        "",
        f"nexus_status: {data.get('nexus_status', 'UNTRACKED')}",
        f'last_synced_at: "{data.get("last_synced_at", _now_iso())}"',
        f"conflict_flag: {str(data.get('conflict_flag', False)).lower()}",
        "",
        f"operational_owner: {data.get('operational_owner', 'gerivdb')}",
        f"canonical_source: {data.get('canonical_source', _NEXUS_SOT)}",
        f"ecos_root_sot: {data.get('ecos_root_sot', _ECOS_ROOT_SOT)}",
        "",
        f"entity_type: {data.get('entity_type', 'REPO')}",
        f'nexus_version: "{data.get("nexus_version", "3.0.0")}"',
        "",
        f'intent_hash: "{data.get("intent_hash", "")}"',
    ]

    # Champs optionnels
    for opt in ("sprint_active", "phi_cps_score", "drift_delta", "reciprocity_score"):
        if opt in data and data[opt] is not None:
            val = data[opt]
            if isinstance(val, str):
                lines.append(f'{opt}: "{val}"')
            else:
                lines.append(f"{opt}: {val}")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ===========================================================================
# SOUS-GROUPE: kiva nexus status
# ===========================================================================

@nexus_cli.command(name="status")
@click.argument("repo")
def nexus_status(repo: str):
    """Affiche l'état condensé d'un repo.

    Équivalent API : GET /api/v3/status/<repo>

    Exemple :

      kiva nexus status NEXUS
    """
    repo_path = _default_path(repo)
    nexus_dir = repo_path / ".nexus"
    status_file = nexus_dir / "STATUS.yaml"

    click.echo(f"\n=== kiva nexus status :: {repo} ===")
    click.echo(f"  Tier   : {_REPO_TIER.get(repo, 'L1-ACTIVE')}")
    click.echo(f"  Path   : {repo_path}")
    click.echo(f"  .nexus : {nexus_dir}")

    if not status_file.exists():
        click.echo(f"\n  [!!] Aucun STATUS.yaml trouvé — repo non tracké")
        click.echo(f"  -> Initialiser : kiva nexus mutate --op create_tracking --path {repo_path}")
        return

    data = _read_yaml_file(status_file)
    nexus_status_val = data.get("nexus_status", "UNKNOWN")
    last_sync = data.get("last_synced_at", "-")
    conflict = str(data.get("conflict_flag", "false")).lower() not in ("false", "0", "")

    status_icon = "[!!]" if conflict else ("[?]" if nexus_status_val in ("UNTRACKED", "UNKNOWN") else "[ok]")

    click.echo(f"\n  {status_icon} nexus_status    : {nexus_status_val}")
    click.echo(f"     last_synced_at  : {last_sync}")
    click.echo(f"     conflict_flag   : {conflict}")
    click.echo(f"     owner           : {data.get('operational_owner', '-')}")
    click.echo(f"     intent_hash     : {data.get('intent_hash', '-')}")


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
            schema_h = compute_schema_hash(p)
            rec = PipelineRecord(
                name=name,
                schema_hash=schema_h,
                step_count=0,
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
        click.echo(json_mod.dumps(records, indent=2, ensure_ascii=False))
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
        events = wal.query_events(event_type="PIPELINE_RUN", limit=limit * 2)
    except Exception as exc:
        click.echo(f"[WARN] Impossible de requêter le WAL : {exc}")
        return

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
    """Détecte les dérives de schema_hash (YAML courant vs dernier run SUCCESS)."""
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
@click.option("--dry-run", is_flag=True, default=False, help="Affiche les orphelins sans les supprimer.")
@click.option("--force", is_flag=True, default=False, help="Supprime sans confirmation interactive.")
@click.option("--name", "names", multiple=True, help="Supprime uniquement les pipelines spécifiés (répétable).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Sortie JSON machine-readable.")
def pipeline_prune(dry_run: bool, force: bool, names: tuple[str, ...], as_json: bool):
    """Supprime les pipelines orphelins du registry."""
    try:
        store = PipelineRegistryStore()
    except Exception as exc:
        click.echo(f"[ERROR] Store inaccessible : {exc}", err=True)
        sys.exit(2)

    if names:
        targets = []
        for n in names:
            rec = store.get_record(n)
            if rec is None:
                click.echo(f"[WARN] Pipeline '{n}' introuvable dans le registry.", err=True)
            else:
                targets.append(rec)
    else:
        targets = store.find_orphans()

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
# kiva nexus sync  — NEXUS Weekly Sync (remplace GHA nexus-weekly-sync)
# ---------------------------------------------------------------------------

_NEXUS_ROOT_DEFAULT = _L0_CANON_ROOT / "NEXUS"

_NEXUS_SYNC_PIPELINE = [
    {
        "name":   "nexus_sync",
        "script": "tools/nexus_sync.py",
        "args":   ["--generate"],
        "label":  "[1/5] Sync registre NEXUS",
        "fatal":  True,
    },
    {
        "name":   "nexus_changelog_gen",
        "script": "tools/nexus_changelog_gen.py",
        "args":   [],
        "label":  "[2/5] Changelog",
        "fatal":  True,
    },
    {
        "name":   "nexus_readme_gen",
        "script": "tools/nexus_readme_gen.py",
        "args":   [],
        "label":  "[3/5] README",
        "fatal":  True,
    },
    {
        "name":   "nexus_validate",
        "script": "tools/nexus_validate.py",
        "args":   ["--check", "drift", "--create-issues"],
        "label":  "[4/5] Validation + drift",
        "fatal":  True,
    },
    {
        "name":   "nexus_watchdog",
        "script": "tools/nexus_watchdog.py",
        "args":   ["--create-issues"],
        "label":  "[5/5] Watchdog intégrité",
        "fatal":  False,
    },
]


def _run_sync_step(step: dict, nexus_root: Path, dry_run: bool, python_exe: str) -> bool:
    script = nexus_root / step["script"]
    cmd = [python_exe, str(script)] + step["args"]
    tag = "DRY-RUN" if dry_run else "RUN"

    click.echo(f"\n  {step['label']}")
    click.echo(f"  [{tag}] {' '.join(str(c) for c in cmd)}")

    if dry_run:
        click.secho("  -> skipped (dry-run)", fg="yellow")
        return True

    if not script.exists():
        click.secho(f"  [ERROR] script introuvable : {script}", fg="red")
        return not step["fatal"]

    result = subprocess.run(cmd, text=True)

    if result.returncode != 0:
        if step["fatal"]:
            click.secho(f"  [FATAL] exit {result.returncode} — pipeline interrompu", fg="red")
            return False
        click.secho(
            f"  [WARN] exit {result.returncode} — non-fatal, pipeline continue", fg="yellow"
        )

    return True


@nexus_cli.command(name="sync")
@click.option("--dry-run", is_flag=True, help="Simule sans exécuter aucun script.")
@click.option("--repo", default=None, type=click.Path(), help="Chemin NEXUS (défaut: L0-CANON/NEXUS).")
@click.option("--skip-watchdog", is_flag=True, help="Saute l'étape 5 (nexus_watchdog).")
@click.option("--python", default=sys.executable, help="Interpréteur Python (défaut: courant).")
def nexus_sync(dry_run: bool, repo: Optional[str], skip_watchdog: bool, python: str):
    """Enchaîne les 5 scripts du weekly sync NEXUS en local."""
    nexus_root = Path(repo) if repo else _NEXUS_ROOT_DEFAULT

    click.secho("\n" + "=" * 56, fg="cyan", bold=True)
    click.secho("  KIVA — nexus sync", fg="cyan", bold=True)
    click.secho(f"  Repo  : {nexus_root}", fg="cyan")
    click.secho(f"  Mode  : {'DRY-RUN' if dry_run else 'LIVE'}", fg="cyan")
    click.secho(f"  Start : {_now_iso()}", fg="cyan")
    click.secho("=" * 56 + "\n", fg="cyan", bold=True)

    if not dry_run and not nexus_root.is_dir():
        click.secho(f"[ERROR] NEXUS root introuvable : {nexus_root}", fg="red")
        sys.exit(1)

    steps = [s for s in _NEXUS_SYNC_PIPELINE if not (skip_watchdog and s["name"] == "nexus_watchdog")]
    success = 0
    failed: list[str] = []

    for step in steps:
        ok = _run_sync_step(step, nexus_root, dry_run, python)
        if ok:
            success += 1
        else:
            failed.append(step["name"])
            break

    click.echo("\n" + "═" * 56)
    if not failed:
        click.secho(f"  NEXUS SYNC OK — {success}/{len(steps)} steps", fg="green", bold=True)
        sys.exit(0)
    else:
        click.secho(
            f"  NEXUS SYNC FAILED — {success}/{len(steps)} steps | Echec: {failed}",
            fg="red", bold=True,
        )
        sys.exit(1)


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
            click.echo(f"  [SKIP] {label} existe deja - non ecrase.")
        else:
            fpath.write_text(content, encoding="utf-8")
            click.echo(f"  [OK] {label} cree : {fpath}")

    click.echo(f"\n[OK] .nexus/ initialise pour {repo}")


# ---------------------------------------------------------------------------
# nexus drift
# ---------------------------------------------------------------------------

@nexus_cli.group(name="drift")
def drift_cli():
    """Detection de derive NEXUS (phi-CPS + alertes WAL)."""
    pass


@drift_cli.command(name="check")
@click.option("--repo", "repo_filter", default=None, help="Filtrer les alertes WAL pour un repo specifique.")
@click.option("--since", default=24, show_default=True, type=int, help="Fenetre de recherche en heures (defaut: 24h).")
@click.option("--phi-only", is_flag=True, default=False, help="Afficher uniquement les evenements avec phi_cps_alert=True.")
@click.option("--status-scan", is_flag=True, default=False, help="Scanner aussi les .nexus/STATUS.yaml des repos en L0-CANON.")
@click.option("--limit", default=20, show_default=True, type=int, help="Nombre max d'evenements WAL a afficher.")
def drift_check(repo_filter: Optional[str], since: int, phi_only: bool, status_scan: bool, limit: int):
    """Detecte les derives phi-CPS et signale les alertes WAL NEXUS."""
    try:
        from kiva_cli.core.global_wal_manager import GlobalWALManager
        wal = GlobalWALManager()
    except Exception as exc:
        click.echo(f"[ERROR] WAL inaccessible : {exc}", err=True)
        sys.exit(1)

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

        drift_icon = "[!!]" if exceeded else "[OK]"
        click.echo("--- phi-CPS global ---")
        click.echo(f"  baseline   : {drift.get('baseline_phi', 0.0):.6f}")
        click.echo(f"  current    : {drift.get('current_phi', 0.0):.6f}")
        click.echo(f"  delta      : {abs_drift:+.6f}  (relative: {rel_drift:+.2%})")
        click.echo(f"  threshold  : +/-{_PHI_DRIFT_THRESHOLD:.2%}")
        click.echo(f"  status     : {drift_icon} {'DRIFT DETECTE' if exceeded else 'STABLE'}")
        click.echo(f"  alerts     : {alert_count} / {total_events} events")
        click.echo("")
    except Exception as exc:
        click.echo(f"  [WARN] get_drift() indisponible : {exc}")
        click.echo("")

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

    if status_scan:
        click.echo("--- Scan .nexus/STATUS.yaml (L0-CANON) ---")
        found_any = False
        for tier_dir in [_L0_CANON_ROOT, _L0_CANON_ROOT.parent / "L1-ACTIVE"]:
            if not tier_dir.exists():
                continue
            for status_file in sorted(tier_dir.glob("*/.nexus/STATUS.yaml")):
                found_any = True
                repo_name = status_file.parent.parent.name
                if repo_filter and repo_filter.lower() not in repo_name.lower():
                    continue
                data = _read_yaml_file(status_file)
                nexus_status = data.get("nexus_status", "UNKNOWN")
                last_sync = data.get("last_synced_at", "-")
                conflict = str(data.get("conflict_flag", "false")).lower() not in ("false", "0", "")
                status_icon = "[!!]" if conflict else ("[?]" if nexus_status in ("UNTRACKED", "UNKNOWN") else "[ok]")
                click.echo(
                    f"  {status_icon}  {repo_name:<24} status={nexus_status:<14} "
                    f"sync={str(last_sync)[:19]}  conflict={conflict}"
                )
        if not found_any:
            click.echo("  (aucun .nexus/STATUS.yaml trouvé dans L0-CANON / L1-ACTIVE)")
        click.echo("")

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

    click.echo("--- Résumé ---")
    if exceeded:
        click.echo("  [!!] DRIFT phi-CPS detecte — verifier les deltas et les pipelines recents")
    if alert_count and alert_count > 0:
        click.echo(f"  [!]  {alert_count} alerte(s) phi_cps enregistree(s) dans le WAL")
    if not exceeded and (not alert_count or alert_count == 0):
        click.echo("  [OK] Aucune derive detectee dans la fenetre analysee")
    click.echo("")


# ---------------------------------------------------------------------------
# kiva nexus sync (import depuis nexus_sync_command)
# ---------------------------------------------------------------------------
from .nexus_sync_command import nexus_sync_cmd  # noqa: E402

nexus_cli.add_command(nexus_sync_cmd)
