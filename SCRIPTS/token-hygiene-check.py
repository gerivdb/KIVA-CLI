#!/usr/bin/env python3
"""
Token Hygiene Check - Détecte et purge les tokens exposés.

Usage:
    python scripts/token-hygiene-check.py --repo <path>
    python scripts/token-hygiene-check.py --repo <path> --fix

Refs: INTENT-091, ADR-001, KiloRule gitignore-matrix.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


TOKEN_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9_]{36,}"),  # GitHub PAT
    re.compile(r"gho_[A-Za-z0-9_]{36,}"),  # GitHub OAuth
    re.compile(r"github_pat_[A-Za-z0-9_]{22,}_[A-Za-z0-9_]{59}"),  # GitHub fine-grained
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key
    re.compile(r"sk-[A-Za-z0-9]{48,}"),  # OpenAI API key
]


def check_remote(repo_path: Path) -> list[dict]:
    result = subprocess.run(
        ["git", "remote", "-v"],
        capture_output=True,
        text=True,
        cwd=str(repo_path),
    )
    issues = []
    if result.returncode != 0:
        return issues
    for line in result.stdout.splitlines():
        for pattern in TOKEN_PATTERNS:
            if pattern.search(line):
                issues.append({"type": "remote", "content": line.strip(), "pattern": pattern.pattern})
    return issues


def check_file(path: Path) -> list[dict]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    issues = []
    for pattern in TOKEN_PATTERNS:
        for match in pattern.finditer(content):
            issues.append({
                "type": "file",
                "file": str(path),
                "match": match.group(),
                "pattern": pattern.pattern,
            })
    return issues


def scan_repo(repo_path: Path) -> list[dict]:
    issues = []
    issues.extend(check_remote(repo_path))
    for file in repo_path.rglob("*"):
        if file.is_file() and file.suffix in (".py", ".sh", ".ps1", ".json", ".yaml", ".yml", ".md", ".txt"):
            issues.extend(check_file(file))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Token Hygiene Check")
    parser.add_argument("--repo", required=True, help="Path to git repository")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix (remove token from remote)")
    args = parser.parse_args()

    repo_path = Path(args.repo)
    if not repo_path.exists() or not (repo_path / ".git").exists():
        print(f"[ERR] Not a git repository: {repo_path}")
        return 1

    issues = scan_repo(repo_path)
    if not issues:
        print("[OK] No exposed tokens found")
        return 0

    print(f"[ERR] Found {len(issues)} exposed token(s):")
    for issue in issues[:20]:
        print(f"  - {issue.get('type')}: {issue.get('content') or issue.get('file')}")

    if args.fix:
        print("\n[ACTION] Fix not implemented - manual intervention required")
        print("  For remotes: git remote set-url origin <url_without_token>")
        print("  For files: review and remove exposed credentials")
    return 1


if __name__ == "__main__":
    exit(main())
