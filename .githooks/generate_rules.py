#!/usr/bin/env python3
"""
generate_rules.py - Generate .githooks/rules.sh from multi-repo-governance.yaml

Reads the branch_routing section of the governance manifest and produces
a bash-sourced rules.sh file with FORBIDDEN_PATHS, ALLOWED_PREFIXES,
REDIRECT_MAP, and GUARD_MODE variables.

Usage:
    python .githooks/generate_rules.py <manifest_path> <repo_name> [output_path]

Arguments:
    manifest_path   Path to multi-repo-governance.yaml
    repo_name       Name of the repository (must match branch_routing.repositories key)
    output_path     Output path for rules.sh (default: .githooks/rules.sh)

IntentHash: 0xBRG_GENERATE_RULES_20260526
Version: 1.0.0
"""

import datetime
import os
import re
import sys
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# --- Constants ----------------------------------------------------------------

HOOK_VERSION = "1.0.0"
HOOK_INTENT_HASH = "0xBRG_GENERATE_RULES_20260526"


def _read_existing_rules(output_path: Path) -> dict:
    """Lit les valeurs deja presentes dans un rules.sh existant.

    Sert a PRESERVER la politique locale quand le manifeste ne porte pas
    d'entree pour le depot (routage global). Retourne un dict possiblement
    vide : {FORBIDDEN_PATHS: [...], ALLOWED_PREFIXES: [...], REDIRECT_MAP: [...]}

    Correle le defaut 1 d'ADR-2026-10-12-001 : le manifeste route des BRANCHES,
    pas des depots, donc la recherche par nom echoue toujours.
    """
    values = {}
    try:
        if not output_path.exists():
            return values
        text = output_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values

    for name in ("FORBIDDEN_PATHS", "ALLOWED_PREFIXES", "REDIRECT_MAP"):
        # Prefixe `export ` optionnel : les rules.sh heritage l'utilisent.
        m = re.search(rf'^(?:export\s+)?{name}="([^"]*)"',
                      text, flags=re.MULTILINE | re.DOTALL)
        if not m:
            continue
        parts = [p.strip() for p in re.split(r"[|\n]", m.group(1)) if p.strip()]
        if parts:
            values[name] = parts
    return values


def generate_rules(manifest_path: str, repo_name: str, output_path: str) -> None:
    """Generate rules.sh from the governance manifest for a specific repository."""
    manifest_path = Path(manifest_path)
    output_path = Path(output_path)

    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    if HAS_YAML:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error: Invalid YAML in manifest: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: PyYAML required - pip install pyyaml", file=sys.stderr)
        sys.exit(1)

    routing = manifest.get("branch_routing", {})
    repos = routing.get("repositories", {})

    # `repo_name` accepte trois formes, car le manifeste route des BRANCHES,
    # pas des dpts :
    #   1. une cl de routage exacte            -> `fix/*`
    #   2. une branche matchant une cl         -> `fix/gateway-foo`
    #   3. un nom de dpt                     -> `GATEWAY-MANAGER`
    # Les formes 1 et 2 sont les seules ancres dans le manifeste ; la forme 3
    # retombe sur le routage global (toutes les cls), car aucun dpt n'a
    # d'entre propre.
    repo_config = repos.get(repo_name)
    if repo_config is None:
        import fnmatch
        for key, cfg in repos.items():
            if fnmatch.fnmatch(repo_name, key):
                repo_config = cfg
                repo_name = key
                break
    if repo_config is None:
        repo_config = {"_routing_scope": "global"}
        repo_name = "(routage global)"
    # True quand aucun routage propre n'a ete trouve. Dans ce cas, seule la
    # preservation du rules.sh existant evite une regression silencieuse.
    _uses_global_fallback = repo_config.get("_routing_scope") == "global"

    forbidden = repo_config.get("forbidden_paths", [])
    redirects = repo_config.get("redirect_map", {})

    # --- Preservation de la politique locale (correctif generateur) ------
    # Le manifeste est indexe par PATRON DE BRANCHE (`feat/*`, `fix/*`,
    # `main`), pas par nom de depot : la recherche par nom echoue donc
    # TOUJOURS et retombe sur un routage global vide.
    #
    # Mesure du defaut, sur KIVA : regenerer produisait
    #     FORBIDDEN_PATHS=""       -> Guard 3 entierement desactive
    #     ALLOWED_PREFIXES 13 -> 5 -> politique locale detruite
    #
    # Correctif : en routage global, si un rules.sh existe deja avec une
    # politique, on la PRESERVE. Un generateur qui ecrase une politique par
    # du vide est un defaut, pas une regeneration. Un depot jamais genere
    # n'est pas affecte : rien a preserver, et aucun fichier n'est ecrit.
    _existing = _read_existing_rules(output_path) if _uses_global_fallback else {}

    if not forbidden and _existing.get("FORBIDDEN_PATHS"):
        forbidden = _existing["FORBIDDEN_PATHS"]
        print("[generate_rules] politique locale preservee : FORBIDDEN_PATHS "
              f"({len(forbidden)} entrees) -- le manifeste n'a pas d'entree "
              "pour ce depot")

    if not redirects and _existing.get("REDIRECT_MAP"):
        redirects = dict(
            item.split(":", 1) for item in _existing["REDIRECT_MAP"] if ":" in item
        )

    # Les prfixes autoriss ne sont PAS un champ du manifeste : ils sont
    # dductibles des cls de routage elles-mmes. `main` -> `main`,
    # `release/*` -> `release/`, etc. Une branche qui ne matche aucune cl de
    # routage n'est routable pour aucun dpt.
    prefixes = repo_config.get("allowed_branch_prefixes")
    if not prefixes:
        derived = []
        for key in repos:
            derived.append(key[:-2] if key.endswith("/*") else key)
        prefixes = sorted(set(derived))

    # Normalisation du sparateur (ADR-2026-10-12-001). Le manifeste peut fournir
    # des prfixes NUS (`feat` sans slash) et la drivation `key[:-2]` aussi :
    # sans slash, `feat` matche `feature-x` dans le glob du garde (faux positif).
    # On force le slash final sur tout prfixe non-trunk, quelle que soit sa
    # source (manifeste ou drivation), pour rendre le sparateur tanche.
    # `main`/`develop` restent exacts (branches trunk, pas de glob).
    _trunk = {"main", "develop", "dev", "master"}
    _norm = set()
    for _p in prefixes:
        _p = ("" if _p is None else str(_p)).strip()
        if not _p:
            continue
        if _p in _trunk:
            _norm.add(_p)
        elif not _p.endswith("/"):
            _norm.add(_p + "/")
        else:
            _norm.add(_p)
    prefixes = sorted(_norm)

    # Preservation des prefixes : si la derivation globale en produit moins que
    # la politique locale, la locale gagne (meme regle que FORBIDDEN_PATHS).
    if _existing.get("ALLOWED_PREFIXES") and len(_existing["ALLOWED_PREFIXES"]) > len(prefixes):
        prefixes = _existing["ALLOWED_PREFIXES"]
        print("[generate_rules] politique locale preservee : ALLOWED_PREFIXES "
              f"({len(prefixes)} entrees, derivation globale insuffisante)")

    # --- Avertissement anti-degradation ----------------------------------
    # Un FORBIDDEN_PATHS vide desactive Guard 3. On ne peut pas toujours
    # l'eviter : un depot sans politique et un manifeste sans entree pour ce
    # depot produisent legitimement du vide. Dans ce cas on AVERTIT
    # bruyamment plutot que d'echouer, pour ne pas casser les usages qui n'ont
    # rien a preserver.
    #
    # La protection reelle contre la destruction est la PRESERVATION
    # ci-dessus : des qu'un rules.sh porte une politique, elle est reprise.
    if not forbidden:
        print("[generate_rules] [WARN] FORBIDDEN_PATHS sera vide : Guard 3 "
              "sera inopérant.", file=sys.stderr)
        print("[generate_rules] [WARN] Ni le manifeste ni un rules.sh local ne "
              "fournissent de politique pour ce dépôt.", file=sys.stderr)

    redirects = repo_config.get("redirect_map", {})

    forbidden_str = "|".join(forbidden) if forbidden else ""
    prefixes_str = "|".join(prefixes) if prefixes else ""
    redirect_items = [f"{k}:{v}" for k, v in redirects.items()]
    redirect_str = "|".join(redirect_items) if redirect_items else ""

    now = datetime.datetime.now().isoformat()
    brgs_version = routing.get("version", "3.0")

    content = f"""# .githooks/rules.sh - Auto-generated from multi-repo-governance.yaml
# DO NOT EDIT MANUALLY - Run: python .githooks/generate_rules.py
# Generated: {now}
# BRGS Version: {brgs_version}
# Repository: {repo_name}
# IntentHash: {HOOK_INTENT_HASH}

BRGS_VERSION="{brgs_version}"
GUARD_MODE="BLOCK"
TARGET_REPO="{repo_name}"

# Forbidden paths (pipe-separated globs)
FORBIDDEN_PATHS="{forbidden_str}"

# Allowed branch prefixes (pipe-separated)
ALLOWED_PREFIXES="{prefixes_str}"

# Redirect map (format: source_path:target_repo|...)
REDIRECT_MAP="{redirect_str}"
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"[generate_rules] Generated {output_path} for {repo_name}")
    print(f"  Forbidden paths : {len(forbidden)}")
    print(f"  Allowed prefixes: {len(prefixes)}")
    print(f"  Redirects       : {len(redirects)}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("Usage: python generate_rules.py <manifest_path> <repo_name> [output_path]")
        sys.exit(1)

    manifest_path = sys.argv[1]
    repo_name = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else ".githooks/rules.sh"

    generate_rules(manifest_path, repo_name, output_path)


if __name__ == "__main__":
    main()
