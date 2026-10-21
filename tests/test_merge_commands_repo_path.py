"""Non-regression : resolution du chemin local et verification du merge (Bloc 1).

Reproduit le defaut observe : la table codee en dur pointait vers des
chemins perimes (WAZAA -> L3-CITIZENS au lieu de L4-TOOLS), ce qui
provoquait `NotADirectoryError` (WinError 267) lors de la validation DAG-3.
"""
from __future__ import annotations

import pathlib

import pytest

from kiva_cli.commands.merge_commands import (
    REPOS_LOCAL_PATHS,
    _resolve_repo_path,
    _verify_pr_merged,
)


def test_repo_path_connu_est_resolu_et_valide():
    """Un depot connu du parc doit resoudre vers un repertoire existant."""
    path = _resolve_repo_path("KIVA-CLI")
    assert path is not None, "KIVA-CLI doit etre resolvable"
    assert pathlib.Path(path).is_dir(), f"chemin inexistant : {path}"
    assert pathlib.Path(path).is_absolute(), "le chemin doit etre absolu"


def test_repo_path_est_insensible_a_la_casse_et_au_prefixe():
    assert _resolve_repo_path("kiva-cli") is not None
    assert _resolve_repo_path("gerivdb/KIVA-CLI") is not None


def test_repo_inconnu_ne_crashe_pas():
    """Un depot inconnu doit retourner None, jamais lever (c etait le crash)."""
    assert _resolve_repo_path("REPO-QUI-N-EXISTE-PAS-12345") is None
    assert _resolve_repo_path("") is None


def test_chemins_de_la_table_codee_en_dur_sont_valides_ou_absents():
    """Aucun chemin code en dur ne doit pointer vers un repertoire absent.

    C est le controle de non-regression du defaut d origine : la table
    figee contenait des chemins perimes.
    """
    invalides = [name for name, path in REPOS_LOCAL_PATHS.items()
                 if path is not None and not pathlib.Path(path).is_dir()]
    # Les entrees None (remote_only) sont exclues par construction.
    assert not invalides, f"chemins perimes dans la table codee en dur : {invalides}"


def test_verify_pr_merged_ne_pretend_jamais_un_succes_sur_pr_inexistante():
    """Une PR inexistante ne doit jamais etre rapportee comme mergee."""
    merged, state = _verify_pr_merged("KIVA-CLI", 999999)
    assert merged is False
    assert isinstance(state, str) and state
