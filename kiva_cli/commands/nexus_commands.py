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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import click

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

    # -- 4. Résumé final -----------------------------------------------------
    click.echo("--- Résumé ---")
    if exceeded:
        click.echo("  [!!] DRIFT phi-CPS detecte — verifier les deltas et les pipelines recents")
    if alert_count and alert_count > 0:
        click.echo(f"  [!]  {alert_count} alerte(s) phi_cps enregistree(s) dans le WAL")
    if not exceeded and (not alert_count or alert_count == 0):
        click.echo("  [OK] Aucune derive detectee dans la fenetre analysee")
    click.echo("")
