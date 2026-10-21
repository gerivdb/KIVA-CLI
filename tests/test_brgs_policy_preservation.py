"""Non-regression de la PRESERVATION de la politique locale BRGS.

Contexte (incident 2026-10-12, recadence 2026-10-21) :
le hook `pre-push` regenere `.githooks/rules.sh` depuis le manifeste GLOBAL
(`GOVERNANCE-HUB/multi-repo-governance.yaml`). Ce manifeste route des
BRANCHES (`feat/*`), pas des depots : l'entree `feat/*` ne porte aucun
`forbidden_paths`. La regeneration produisait donc

    FORBIDDEN_PATHS=""            -> Guard 3 entierement desactive
    ALLOWED_PREFIXES (5)          -> politique locale reduite

et ecrisait une politique locale saine (11 interdits / 13 prefixes).
C'est exactement ce que constate le commit 368e416 ("restaurer la politique
locale sur 7 depots du Lot 3") : le correctif avait ete applique AU MANUEL,
sans corriger la CAUSE (la regeneration automatique).

Ces tests verrouillent la cause :
  1. la politique locale est PRESERVEE quand le manifeste n'en fournit pas ;
  2. le manifeste reste prioritaire quand il en fournit une ;
  3. un depot jamais genere n'est pas affecte (pas d'ecrasement) ;
  4. les prefixes suivent la meme regle de preservation.

IntentHash: 0xBRG_POLICY_PRESERVATION_20261021
"""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / ".githooks" / "generate_rules.py"

# Manifeste GLOBAL : route des branches, aucune entree ne porte de
# `forbidden_paths` pour un depot donne.
MANIFEST_GLOBAL_BRANCH = """\
branch_routing:
  repositories:
    main:
      role: critical
    "feat/*":
      role: development
    "fix/*":
      role: development
    "ci/*":
      role: cicd
"""

# Manifeste portant une politique explicite pour la branche : elle doit
# PRIMER sur la politique locale.
MANIFEST_WITH_POLICY = """\
branch_routing:
  repositories:
    main:
      role: critical
    "feat/*":
      role: development
      forbidden_paths:
        - "SPEC/"
        - "config/schemas/"
"""

POLICY_LOCAL = (
    'EPICS/|PRD/|ADR/|INTENTS/|SPEC/|docs/architecture/|config/schemas/|'
    '.githooks/|.kilocode/|.github/workflows/|notebooklm/output/'
)
PREFIXES_LOCAL = (
    "feat/|fix/|docs/|chore/|refactor/|perf/|test/|hotfix/|emergency/|"
    "release/|experiment/|deploy/|rollback/"
)


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_preserve_under_test", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen():
    return _load_generator()


def _write_manifest(tmp_path: Path, content: str) -> Path:
    mf = tmp_path / "m.yaml"
    mf.write_text(content, encoding="utf-8")
    return mf


def _write_existing_rules(tmp_path: Path, forbidden: str, prefixes: str) -> Path:
    out = tmp_path / "r.sh"
    out.write_text(
        "# .githooks/rules.sh - Auto-generated\n"
        f'FORBIDDEN_PATHS="{forbidden}"\n'
        f'ALLOWED_PREFIXES="{prefixes}"\n'
        'REDIRECT_MAP=""\n',
        encoding="utf-8",
    )
    return out


def _read(out: Path) -> dict:
    data = {}
    for line in out.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        data[key.strip()] = val.strip().strip('"')
    return data


# ---------------------------------------------------------------------------
# 1. Preservation : le manifeste ne fournit pas de politique
# ---------------------------------------------------------------------------

def test_forbidden_paths_preserved_when_manifest_has_none(gen, tmp_path):
    """Le cas exact de l'incident : routage `feat/*` sans `forbidden_paths`."""
    mf = _write_manifest(tmp_path, MANIFEST_GLOBAL_BRANCH)
    out = _write_existing_rules(tmp_path, POLICY_LOCAL, PREFIXES_LOCAL)

    gen.generate_rules(str(mf), "feat/brgs-hooks-RAGX", str(out))

    data = _read(out)
    assert data["FORBIDDEN_PATHS"], "FORBIDDEN_PATHS vide -> Guard 3 desactive"
    assert len(data["FORBIDDEN_PATHS"].split("|")) == 11
    assert "notebooklm/output/" in data["FORBIDDEN_PATHS"]
    assert ".githooks/" in data["FORBIDDEN_PATHS"]


def test_prefixes_preserved_when_global_derivation_is_poorer(gen, tmp_path):
    """La derivation globale (5) est plus pauvre que la locale (13) : la locale gagne."""
    mf = _write_manifest(tmp_path, MANIFEST_GLOBAL_BRANCH)
    out = _write_existing_rules(tmp_path, POLICY_LOCAL, PREFIXES_LOCAL)

    gen.generate_rules(str(mf), "feat/brgs-hooks-RAGX", str(out))

    data = _read(out)
    assert len(data["ALLOWED_PREFIXES"].split("|")) == 13
    for p in ("feat/", "docs/", "chore/", "hotfix/", "rollback/"):
        assert p in data["ALLOWED_PREFIXES"]


# ---------------------------------------------------------------------------
# 2. Le manifeste reste prioritaire quand il fournit une politique
# ---------------------------------------------------------------------------

def test_manifest_policy_wins_over_local(gen, tmp_path):
    mf = _write_manifest(tmp_path, MANIFEST_WITH_POLICY)
    out = _write_existing_rules(tmp_path, POLICY_LOCAL, PREFIXES_LOCAL)

    gen.generate_rules(str(mf), "feat/brgs-hooks-RAGX", str(out))

    data = _read(out)
    assert data["FORBIDDEN_PATHS"] == "SPEC/|config/schemas/"


# ---------------------------------------------------------------------------
# 3. Un depot jamais genere n'est pas affecte
# ---------------------------------------------------------------------------

def test_untouched_depot_is_not_polluted(gen, tmp_path):
    """Pas de rules.sh prealable -> rien a preserver, et rien n'est invente."""
    mf = _write_manifest(tmp_path, MANIFEST_GLOBAL_BRANCH)
    out = tmp_path / "absent.sh"

    gen.generate_rules(str(mf), "feat/nouvelle-branche", str(out))

    data = _read(out)
    assert data["FORBIDDEN_PATHS"] == ""
    # La derivation globale reste appliquee (main, feat/, fix/, ci/) : pas de
    # pollution par une politique qui n'appartient pas a ce depot.
    assert len(data["ALLOWED_PREFIXES"].split("|")) == 4
