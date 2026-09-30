"""KIVA-012 S3 — Unit tests for shell_helpers."""
from __future__ import annotations

import platform
import pytest

from kiva_cli.core.shell_helpers import normalize_shell_command, is_windows


def test_is_windows_reflects_platform():
    assert is_windows() == (platform.system() == "Windows")


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("git diff | head -20", "git diff | Select-Object -First 20"),
        ("git log | tail -5", "git log | Select-Object -Last 5"),
        ("echo hello", "echo hello"),
    ],
)
def test_normalize_shell_command_replaces_head_tail(cmd, expected):
    if is_windows():
        assert normalize_shell_command(cmd) == expected
    else:
        assert normalize_shell_command(cmd) == cmd


def test_normalize_shell_command_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr("kiva_cli.core.shell_helpers.is_windows", lambda: False)
    cmd = "git diff | head -20"
    assert normalize_shell_command(cmd) == cmd
