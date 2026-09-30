"""KIVA-012 S3 — Cross-platform shell command helpers.

Provides wrappers for common shell operations that differ between
Unix and Windows PowerShell.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import List, Optional


def is_windows() -> bool:
    return platform.system() == "Windows"


def normalize_shell_command(cmd: str) -> str:
    """Normalize a shell command string for cross-platform compatibility.

    Handles common Unix commands that don't exist in PowerShell:
    - head -> Select-Object -First
    - tail -> Select-Object -Last
    """
    if not is_windows():
        return cmd

    # Replace Unix-style pipes with PowerShell equivalents
    replacements = [
        ("| head -", "| Select-Object -First "),
        ("| tail -", "| Select-Object -Last "),
    ]

    result = cmd
    for old, new in replacements:
        result = result.replace(old, new)

    return result


def run_command(
    cmd: str,
    cwd: Optional[Path] = None,
    check: bool = False,
    capture_output: bool = False,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """Run a shell command with cross-platform normalization.

    Args:
        cmd: Command string to execute
        cwd: Working directory
        check: Raise on non-zero exit code
        capture_output: Capture stdout/stderr
        text: Return strings instead of bytes

    Returns:
        CompletedProcess result
    """
    normalized = normalize_shell_command(cmd)

    return subprocess.run(
        normalized,
        cwd=cwd,
        check=check,
        capture_output=capture_output,
        text=text,
        shell=True,
    )


def run_pipeline(
    commands: List[str],
    cwd: Optional[Path] = None,
    stop_on_error: bool = True,
) -> List[subprocess.CompletedProcess]:
    """Run a sequence of commands, stopping on first failure if requested.

    Each command is normalized for the current platform before execution.
    """
    results = []
    for cmd in commands:
        result = run_command(cmd, cwd=cwd, capture_output=True, check=False)
        results.append(result)

        if stop_on_error and result.returncode != 0:
            break

    return results
