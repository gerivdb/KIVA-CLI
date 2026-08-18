"""GitHub native commands for KIVA-CLI.

httpx-only client, zero gh CLI dependency.
Auth via GITHUB_TOKEN env var with fallback to gh keyring.
JSON structured logging.
Respects --dry-run (zero write when active).

IntentHash: 0xKIVA_CLI_GITHUB_COMMANDS_20260605
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import httpx

from kiva_cli.core.github_token import get_github_token as _get_github_token

LOG = logging.getLogger("kiva_cli.github_commands")
GITHUB_API = "https://api.github.com"


def _gh_executable() -> str | None:
    """Return path to gh.exe if available."""
    candidates = [
        "gh",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\gh\bin\gh.exe"),
        r"C:\gh\bin\gh.exe",
    ]
    for candidate in candidates:
        if candidate == "gh":
            try:
                out = subprocess.run(
                    "command -v gh",
                    shell=True,
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and out.stdout.strip():
                    return out.stdout.strip()
            except Exception:
                pass
        elif os.path.exists(candidate):
            return candidate
    return None


@dataclass
class JsonLog:
    event: str
    repo: str
    pr: int
    payload: dict = field(default_factory=dict)

    def dump(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


def _headers() -> dict:
    token = _get_github_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "kiva-cli/0.1.0",
    }


def _request(
    method: str,
    path: str,
    *,
    dry_run: bool = False,
    repo: str = "",
    pr: int = 0,
    body: Optional[dict] = None,
    params: Optional[dict] = None,
) -> httpx.Response:
    url = f"{GITHUB_API}{path}"
    headers = _headers()
    json_body = body if method in {"POST", "PATCH", "PUT"} else None
    LOG.info(
        JsonLog(
            event="github_request",
            repo=repo,
            pr=pr,
            payload={"method": method, "url": url, "dry_run": dry_run, "params": params},
        ).dump()
    )
    if dry_run and method in {"POST", "PATCH", "PUT"}:
        raise RuntimeError("dry-run active: refusing write operation")
    with httpx.Client(timeout=60) as client:
        resp = client.request(method, url, headers=headers, json=json_body, params=params)
    return resp


def get_pr(repo: str, pr_number: int, *, dry_run: bool = False) -> dict:
    """Return PR metadata as dict."""
    resp = _request("GET", f"/repos/{repo}/pulls/{pr_number}", repo=repo, pr=pr_number, dry_run=dry_run)
    resp.raise_for_status()
    return resp.json()


def get_pr_diff(repo: str, pr_number: int, *, dry_run: bool = False) -> str:
    """Return raw unified diff for a PR."""
    resp = _request(
        "GET",
        f"/repos/{repo}/pulls/{pr_number}",
        repo=repo,
        pr=pr_number,
        dry_run=dry_run,
        params={"accept": "application/vnd.github.v3.diff"},
    )
    resp.raise_for_status()
    return resp.text


def post_review_comment(
    repo: str,
    pr_number: int,
    body: str,
    *,
    path: Optional[str] = None,
    line: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """Post an inline review comment on a PR."""
    if dry_run:
        raise RuntimeError("dry-run active: refusing write operation")
    comment: dict = {"body": body}
    if path is not None:
        comment["path"] = path
    if line is not None:
        comment["line"] = line
    payload = {
        "commit_id": get_pr(repo, pr_number, dry_run=dry_run)["head"]["sha"],
        "body": body if path is None else None,
        "event": "COMMENT",
        "comments": [] if path is None else [comment],
    }
    if path is None:
        payload.pop("comments")
    resp = _request(
        "POST",
        f"/repos/{repo}/pulls/{pr_number}/reviews",
        repo=repo,
        pr=pr_number,
        dry_run=dry_run,
        body=payload,
    )
    resp.raise_for_status()
    return resp.json()


def list_check_runs(repo: str, pr_number: int, *, dry_run: bool = False) -> list:
    """Return check runs for the PR head SHA."""
    pr = get_pr(repo, pr_number, dry_run=dry_run)
    sha = pr["head"]["sha"]
    resp = _request(
        "GET",
        f"/repos/{repo}/commits/{sha}/check-runs",
        repo=repo,
        pr=pr_number,
        dry_run=dry_run,
        params={"per_page": 100},
    )
    resp.raise_for_status()
    return resp.json().get("check_runs", [])


def get_pr_files(repo: str, pr_number: int, *, dry_run: bool = False) -> list:
    """Return list of files changed in a PR."""
    resp = _request(
        "GET",
        f"/repos/{repo}/pulls/{pr_number}/files",
        repo=repo,
        pr=pr_number,
        dry_run=dry_run,
        params={"per_page": 100},
    )
    resp.raise_for_status()
    return resp.json()


def poll_check_runs(
    repo: str,
    pr_number: int,
    *,
    timeout: int = 300,
    dry_run: bool = False,
) -> dict:
    """Poll until check runs complete or timeout."""
    deadline = time.time() + timeout
    last_status = None
    while time.time() < deadline:
        runs = list_check_runs(repo, pr_number, dry_run=dry_run)
        statuses = [run.get("status") for run in runs]
        last_status = statuses
        if all(status in {"completed"} for status in statuses):
            conclusions = [run.get("conclusion") for run in runs]
            return {"completed": True, "conclusions": conclusions, "check_runs": runs}
        time.sleep(5)
    return {"completed": False, "last_status": last_status}
