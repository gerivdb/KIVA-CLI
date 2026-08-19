#!/usr/bin/env python3
"""Tests for topos_commands pure helpers.

Focus: _find_ecos_roots and _parse_ecos_root with temp dir trees.
"""
import json
from pathlib import Path

import pytest

from kiva_cli.commands import topos_commands as tc


def _make_ecos_root(base: Path, name: str, deps=None) -> Path:
    repo = base / name
    repo.mkdir(parents=True, exist_ok=True)
    data = {"name": name, "layer": "L4", "dependencies": deps or []}
    (repo / "ECOS_ROOT.json").write_text(json.dumps(data), encoding="utf-8")
    return repo


def test_find_ecos_roots_finds_top_level(tmp_path):
    _make_ecos_root(tmp_path, "repoA")
    roots = tc._find_ecos_roots(str(tmp_path))
    assert len(roots) == 1
    assert roots[0].name == "ECOS_ROOT.json"


def test_find_ecos_roots_finds_nested(tmp_path):
    _make_ecos_root(tmp_path / "group" / "sub", "repoB")
    roots = tc._find_ecos_roots(str(tmp_path))
    assert len(roots) == 1


def test_find_ecos_roots_skips_excluded_dirs(tmp_path):
    # a .git dir containing ECOS_ROOT.json must be skipped
    g = tmp_path / ".git"
    g.mkdir()
    _make_ecos_root(g, "hidden")
    # a real repo
    _make_ecos_root(tmp_path, "real")
    roots = tc._find_ecos_roots(str(tmp_path))
    names = {r.parent.name for r in roots}
    assert names == {"real"}


def test_find_ecos_roots_empty(tmp_path):
    assert tc._find_ecos_roots(str(tmp_path)) == []


def test_parse_ecos_root_valid(tmp_path):
    p = _make_ecos_root(tmp_path, "repoC", deps=["X", "Y"])
    data = tc._parse_ecos_root(p / "ECOS_ROOT.json")
    assert data["name"] == "repoC"
    assert data["dependencies"] == ["X", "Y"]


def test_parse_ecos_root_missing_returns_empty(tmp_path):
    assert tc._parse_ecos_root(tmp_path / "nope.json") == {}


def test_parse_ecos_root_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    assert tc._parse_ecos_root(bad) == {}


def test_find_ecos_roots_multiple(tmp_path):
    _make_ecos_root(tmp_path, "r1")
    _make_ecos_root(tmp_path, "r2")
    _make_ecos_root(tmp_path / "nested", "r3")
    assert len(tc._find_ecos_roots(str(tmp_path))) == 3
