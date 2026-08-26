"""Tests unitaires pour kiva_cli/commands/delivery_commands.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

_KIVA_ROOT = Path(r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI")
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
