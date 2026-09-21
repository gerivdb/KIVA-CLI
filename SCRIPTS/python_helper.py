#!/usr/bin/env python3
"""
KIVA-012 S3 — Python executable detection helper for Windows.

On ENV2, `py` is the preferred Python launcher and `python` may not be
in PATH. This helper normalizes Python invocation cross-platform.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_python_executable() -> str:
    """Return the preferred Python executable for this environment.

    Priority:
    1. KIVA_PYTHON env var if set
    2. `py` launcher if available (Windows preferred)
    3. `python` if available
    4. `sys.executable` as fallback
    """
    env_python = os.environ.get("KIVA_PYTHON")
    if env_python:
        return env_python

    # Prefer `py` on Windows
    if sys.platform == "win32":
        py = _find_executable("py")
        if py:
            return py

    python = _find_executable("python")
    if python:
        return python

    return sys.executable


def _find_executable(name: str) -> str | None:
    """Find an executable in PATH."""
    path = os.environ.get("PATH", "")
    for dirname in path.split(os.pathsep):
        candidate = Path(dirname) / name
        if candidate.exists():
            return str(candidate)
        # On Windows, try with .exe extension
        if sys.platform == "win32":
            candidate_exe = candidate.with_suffix(".exe")
            if candidate_exe.exists():
                return str(candidate_exe)
    return None


def run_python(script: str, *args: str) -> int:
    """Run a Python script with the detected Python executable.

    Args:
        script: Path to the Python script
        *args: Arguments to pass to the script

    Returns:
        Exit code
    """
    python = get_python_executable()
    cmd = [python, script, *args]
    return os.execv(python, cmd)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Python executable: {get_python_executable()}")
        sys.exit(0)

    sys.exit(run_python(sys.argv[1], *sys.argv[2:]))
