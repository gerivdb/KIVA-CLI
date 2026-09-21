"""KIVA-012 S3 — Unit tests for python_helper."""
from __future__ import annotations

import os
import sys

import pytest

from scripts.python_helper import _find_executable, get_python_executable


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
