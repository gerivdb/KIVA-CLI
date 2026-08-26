#!/usr/bin/env python3
"""Tests for repo_commands.RepoDiscovery and compare_with_registry.

Focus: pure discovery logic with temp dirs + monkeypatched subprocess.
"""
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from kiva_cli.commands.repo_commands import RepoDiscovery


def _make_fake_repo(base: Path, name: str) -> Path:
    repo = base / name
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    return repo


def test_discover_repos_finds_single_repo(tmp_path):
    _make_fake_repo(tmp_path, "alpha")
    disc = RepoDiscovery([str(tmp_path)])
    repos = disc.discover_repos()
    assert len(repos) == 1
    assert repos[0]["name"] == "alpha"
    assert repos[0]["path"] == str(tmp_path / "alpha")


def test_discover_repos_recurses_into_subdirs(tmp_path):
    # repo at top level
    _make_fake_repo(tmp_path, "top")
    # nested repo
    nested = tmp_path / "group"
    nested.mkdir()
    _make_fake_repo(nested, "deep")
    disc = RepoDiscovery([str(tmp_path)])
    names = {r["name"] for r in disc.discover_repos()}
    assert names == {"top", "deep"}


def test_discover_repos_skips_dot_dirs(tmp_path):
    dot = tmp_path / ".cache"
    dot.mkdir()
    _make_fake_repo(dot, "hidden")
    disc = RepoDiscovery([str(tmp_path)])
    assert disc.discover_repos() == []


def test_discover_repos_missing_scan_dir_is_skipped(tmp_path):
    missing = tmp_path / "does_not_exist"
    disc = RepoDiscovery([str(missing)])
    assert disc.discover_repos() == []


def test_discover_repos_gets_remote_url(tmp_path):
    _make_fake_repo(tmp_path, "beta")
    disc = RepoDiscovery([str(tmp_path)])
    with mock.patch("subprocess.run") as mrun:
        mrun.return_value = subprocess.CompletedProcess(
            ["git"], 0, stdout="https://github.com/gerivdb/beta.git\n", stderr=""
        )
        repos = disc.discover_repos()
    assert repos[0]["remote"] == "https://github.com/gerivdb/beta.git"


def test_get_repo_info_returns_none_on_subprocess_failure(tmp_path):
    _make_fake_repo(tmp_path, "gamma")
    disc = RepoDiscovery([str(tmp_path)])
    with mock.patch("subprocess.run", side_effect=FileNotFoundError):
        repos = disc.discover_repos()
    # Still discovers the repo, remote just empty
    assert repos[0]["name"] == "gamma"
    assert repos[0]["remote"] == ""


def test_compare_with_registry_new_and_existing(tmp_path):
    _make_fake_repo(tmp_path, "newrepo")
    disc = RepoDiscovery([str(tmp_path)])
    discovered = disc.discover_repos()

    registered = {
        "other": {"local_path": str(tmp_path / "other"), "remote_url": "https://github.com/gerivdb/other.git"},
    }
    new_repos, existing = disc.compare_with_registry(discovered, registered)
    assert len(new_repos) == 1
    assert new_repos[0]["name"] == "newrepo"
    assert existing == []


def test_compare_with_registry_matches_by_path(tmp_path):
    _make_fake_repo(tmp_path, "known")
    disc = RepoDiscovery([str(tmp_path)])
    discovered = disc.discover_repos()
    registered = {
        "known": {"local_path": str(tmp_path / "known"), "remote_url": ""},
    }
    new_repos, existing = disc.compare_with_registry(discovered, registered)
    assert new_repos == []
    assert len(existing) == 1


def test_compare_with_registry_matches_by_remote(tmp_path):
    _make_fake_repo(tmp_path, "remoteknown")
    disc = RepoDiscovery([str(tmp_path)])
    with mock.patch("subprocess.run") as mrun:
        mrun.return_value = subprocess.CompletedProcess(
            ["git"], 0, stdout="https://github.com/gerivdb/remoteknown.git\n", stderr=""
        )
        discovered = disc.discover_repos()
    registered = {
        "remoteknown": {"local_path": "/elsewhere", "remote_url": "https://github.com/gerivdb/remoteknown.git"},
    }
    new_repos, existing = disc.compare_with_registry(discovered, registered)
    assert new_repos == []
    assert len(existing) == 1
