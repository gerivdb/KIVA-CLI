"""KIVA-012 S3 — File editing helpers for safe modifications."""
from __future__ import annotations

from pathlib import Path


def insert_line_before(filepath: Path, marker: str, new_line: str) -> bool:
    """Insert a new line before the first line containing marker.

    Args:
        filepath: Target file path
        marker: Text to search for in existing lines
        new_line: Line to insert before the marker

    Returns:
        True if line was inserted, False if marker not found
    """
    lines = filepath.read_text(encoding="utf-8").splitlines()

    for idx, line in enumerate(lines):
        if marker in line:
            lines.insert(idx, new_line)
            filepath.write_text("\n".join(lines), encoding="utf-8")
            return True

    return False


def insert_line_after(filepath: Path, marker: str, new_line: str) -> bool:
    """Insert a new line after the first line containing marker."""
    lines = filepath.read_text(encoding="utf-8").splitlines()

    for idx, line in enumerate(lines):
        if marker in line:
            lines.insert(idx + 1, new_line)
            filepath.write_text("\n".join(lines), encoding="utf-8")
            return True

    return False


def replace_line(filepath: Path, marker: str, new_line: str) -> bool:
    """Replace the first line containing marker with new_line."""
    lines = filepath.read_text(encoding="utf-8").splitlines()

    for idx, line in enumerate(lines):
        if marker in line:
            lines[idx] = new_line
            filepath.write_text("\n".join(lines), encoding="utf-8")
            return True

    return False
