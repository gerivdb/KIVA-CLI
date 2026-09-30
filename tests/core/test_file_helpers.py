"""KIVA-012 S3 — Unit tests for file_helpers."""
from __future__ import annotations

from pathlib import Path

from kiva_cli.core.file_helpers import insert_line_after, insert_line_before, replace_line


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "sample.txt"
    p.write_text(content, encoding="utf-8")
    return p


def test_insert_line_before_inserts_once(tmp_path: Path):
    p = _write(tmp_path, "alpha\nbeta\ngamma\n")
    assert insert_line_before(p, "beta", "INSERTED")
    assert p.read_text(encoding="utf-8").splitlines() == ["alpha", "INSERTED", "beta", "gamma"]


def test_insert_line_after_inserts_once(tmp_path: Path):
    p = _write(tmp_path, "alpha\nbeta\ngamma\n")
    assert insert_line_after(p, "beta", "INSERTED")
    assert p.read_text(encoding="utf-8").splitlines() == ["alpha", "beta", "INSERTED", "gamma"]


def test_replace_line_replaces_first_match(tmp_path: Path):
    p = _write(tmp_path, "alpha\nbeta\ngamma\n")
    assert replace_line(p, "beta", "REPLACED")
    assert p.read_text(encoding="utf-8").splitlines() == ["alpha", "REPLACED", "gamma"]


def test_insert_line_before_returns_false_when_marker_missing(tmp_path: Path):
    p = _write(tmp_path, "alpha\n")
    assert insert_line_before(p, "missing", "INSERTED") is False
    assert p.read_text(encoding="utf-8") == "alpha\n"
