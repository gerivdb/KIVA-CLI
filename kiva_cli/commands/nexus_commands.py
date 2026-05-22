"""KIVA nexus commands — gouvernance .nexus/ pour les repos ECOS.

Groupe : kiva nexus
Sous-groupe : kiva nexus tracking

Commandes :
  kiva nexus tracking init <REPO> [--path PATH] [--dry-run]

Extensions futures :
  kiva nexus status <REPO>
  kiva nexus drift check
  kiva nexus reciprocity <REPO>
"""

from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

# ---------------------------------------------------------------------------
# Chemins canoniques par défaut (L0-CANON sur D:\DO\WEB\TOOLS)
# ---------------------------------------------------------------------------
_L0_CANON_ROOT = Path(r"D:\DO\WEB\TOOLS\L0-CANON")

# Tier par défaut par repo (extensible)
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
    """Gouvernance NEXUS — gestion des fichiers .nexus/ par repo.

    Commandes disponibles :
      tracking init <REPO>   Initialise .nexus/TRACKING.md + STATUS.yaml

    Extensions futures :
      status <REPO>          Affiche l'état NEXUS d'un repo
      drift check            Détecte les dérives de sync
      reciprocity <REPO>     Calcule le score de réciprocité
    """
    pass


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

    # Résolution du chemin
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

    # Vérification que le repo existe localement
    if not base.exists():
        click.echo(f"\n⚠️  Répertoire introuvable : {base}")
        click.echo("   → Utilisez --path pour spécifier le chemin correct.")
        click.echo("   → Ou clonez le repo en premier.")
        sys.exit(1)

    # Création du dossier .nexus/
    nexus_dir.mkdir(parents=True, exist_ok=True)

    # Écriture des fichiers (sans écraser si déjà existants)
    for fpath, content, label in [
        (tracking_file, tracking_content, "TRACKING.md"),
        (status_file, status_content, "STATUS.yaml"),
    ]:
        if fpath.exists():
            click.echo(f"  ⚠️  {label} existe déjà — non écrasé. Utilisez --force pour forcer.")
        else:
            fpath.write_text(content, encoding="utf-8")
            click.echo(f"  ✅ {label} créé : {fpath}")

    click.echo(f"\n✅ .nexus/ initialisé pour {repo}")
    click.echo(f"   → git add {nexus_dir} && git commit -m 'chore(nexus): init .nexus/ tracking [{repo}]'")
    click.echo(f"   → git push origin main")
