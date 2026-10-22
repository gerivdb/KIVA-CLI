"""KIVA-012 S3 — Unit tests for python_helper."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# IntentionHash: 0xKIVA_TEST_HERMETIC_PATH_20261022
# ADR: ADR-2026-10-22-002
#
# Ce test importait `scripts.python_helper` comme PAQUET NAMESPACE. Or le
# `__path__` d'un paquet namespace se FIGE au premier import : selon l'ordre
# de collecte et selon les clones presents sur `sys.path`, `scripts` pouvait
# pointer vers `WAZAA\src\scripts` et l'import echouait alors
# (`ModuleNotFoundError: No module named 'scripts.python_helper'`).
#
# Correction : chargement explicite du fichier, par chemin. Le test porte
# desormais sur le code reellement present dans le depot, sans dependre ni
# de l'ordre de collecte, ni de la presence d'un clone frere sur sys.path.
_KIVA_ROOT = Path(__file__).resolve().parents[2]
if str(_KIVA_ROOT) not in sys.path:
    sys.path.insert(0, str(_KIVA_ROOT))

_MODULE_PATH = _KIVA_ROOT / "scripts" / "python_helper.py"
_spec = importlib.util.spec_from_file_location("kiva_python_helper", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None, f"module introuvable : {_MODULE_PATH}"
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

_find_executable = _module._find_executable
get_python_executable = _module.get_python_executable


def test_get_python_executable_returns_string():
    result = get_python_executable()
    assert isinstance(result, str)
    assert len(result) > 0


def test_find_executable_finds_python_when_available():
    python = _find_executable("python")
    if python:
        assert os.path.exists(python)
    else:
        pytest.skip("python not in PATH on this environment")
