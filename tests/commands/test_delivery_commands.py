"""Tests unitaires pour kiva_cli/commands/delivery_commands.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

# IntentionHash: 0xKIVA_TEST_HERMETIC_PATH_20261022
# ADR: ADR-2026-10-22-002
#
# Ce test inscrivait le chemin ABSOLU du clone principal
# (D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI) en tete de `sys.path`. Consequence :
# `import kiva_cli` etait ensuite detourne vers ce clone pour TOUTE la
# session pytest, y compris quand on executait la suite depuis un worktree
# isole. Les modules du worktree n'etaient alors jamais testes, et la
# collecte echouait sur les modules qui n'existent pas dans l'autre clone
# (constat : `cannot import name 'PIPELINE_TIMEOUT_SECONDS'`, `cannot import
# name '_resolve_repo_path'`).
#
# Correction : la racine du depot est derivee du fichier lui-meme. Le test
# s'execute alors contre le code reellement present sous test.
_KIVA_ROOT = Path(__file__).resolve().parents[2]
if str(_KIVA_ROOT) not in sys.path:
    sys.path.insert(0, str(_KIVA_ROOT))

from kiva_cli.commands.delivery_commands import deliver_cli


_LP = Path(r"D:\DO\WEB\TOOLS\L6-WORK\LP")


@pytest.fixture()
def runner():
    return CliRunner()


def test_deliver_help(runner: CliRunner):
    result = runner.invoke(deliver_cli, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output.lower()


def test_deliver_run_lp(runner: CliRunner):
    result = runner.invoke(deliver_cli, ["run", str(_LP), "--workflow", "build"])
    assert result.exit_code == 0
    assert "[OK]" in result.output


def test_deliver_run_missing_repo(runner: CliRunner):
    result = runner.invoke(deliver_cli, ["run", r"D:\DO\WEB\TOOLS\L6-WORK\LP-NON-EXISTANT"])
    assert result.exit_code != 0
