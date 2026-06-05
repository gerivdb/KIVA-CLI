"""Tests for github_commands.py — httpx client, zero gh CLI."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from kiva_cli.commands.github_commands import (
    JsonLog,
    get_pr,
    get_pr_diff,
    list_check_runs,
    get_pr_files,
    poll_check_runs,
    post_review_comment,
)


REPO = "gerivdb/GOVERNANCE-HUB"
PR = 42


def test_json_log_roundtrip():
    log = JsonLog(event="test", repo=REPO, pr=PR, payload={"ok": True})
    raw = log.dump()
    data = json.loads(raw)
    assert data["event"] == "test"
    assert data["repo"] == REPO
    assert data["pr"] == PR
    assert data["payload"]["ok"] is True


def _mock_response(status_code=200, json_data=None, text=""):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


@patch("kiva_cli.commands.github_commands.httpx.Client")
def test_get_pr(mock_client_cls):
    mock_client = MagicMock()
    mock_client.request.return_value = _mock_response(json_data={"number": PR, "head": {"sha": "abc123"}})
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = get_pr(REPO, PR)
    assert result["number"] == PR
    assert result["head"]["sha"] == "abc123"


@patch("kiva_cli.commands.github_commands.httpx.Client")
def test_get_pr_diff(mock_client_cls):
    mock_client = MagicMock()
    mock_client.request.return_value = _mock_response(text="diff --git a/x b/y\n")
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = get_pr_diff(REPO, PR)
    assert "diff --git" in result


@patch("kiva_cli.commands.github_commands.httpx.Client")
def test_post_review_comment_inline(mock_client_cls):
    mock_client = MagicMock()
    mock_client.request.return_value = _mock_response(json_data={"id": 999})
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = post_review_comment(REPO, PR, body="LGTM", path="README.md", line=10)
    assert result["id"] == 999


@patch("kiva_cli.commands.github_commands.httpx.Client")
def test_list_check_runs(mock_client_cls):
    mock_client = MagicMock()
    mock_client.request.return_value = _mock_response(json_data={"check_runs": [{"name": "CI", "status": "completed"}]})
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = list_check_runs(REPO, PR)
    assert len(result) == 1
    assert result[0]["name"] == "CI"


@patch("kiva_cli.commands.github_commands.httpx.Client")
def test_get_pr_files(mock_client_cls):
    mock_client = MagicMock()
    mock_client.request.return_value = _mock_response(json_data=[{"filename": "x.py"}])
    mock_client_cls.return_value.__enter__.return_value = mock_client

    result = get_pr_files(REPO, PR)
    assert result[0]["filename"] == "x.py"


@patch("kiva_cli.commands.github_commands.list_check_runs")
def test_poll_check_runs_completed(mock_list):
    mock_list.return_value = [{"name": "CI", "status": "completed", "conclusion": "success"}]
    result = poll_check_runs(REPO, PR, timeout=10)
    assert result["completed"] is True
    assert result["conclusions"] == ["success"]


def test_dry_run_blocks_write():
    with pytest.raises(RuntimeError, match="dry-run active"):
        post_review_comment(REPO, PR, body="x", dry_run=True)
