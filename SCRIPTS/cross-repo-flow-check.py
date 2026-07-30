#!/usr/bin/env python3
"""
Cross-Repo Flow Check - Détecte les violations de flow cross-repo.

Usage:
    python scripts/cross-repo-flow-check.py --repo <path>
    python scripts/cross-repo-flow-check.py --path scripts/ --lint

Refs: INTENT-089, ADR-095, KiloRule bash-cwd-persistence.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


FORBIDDEN_PATTERNS = [
    (r"\bcd\s+[\"']?[\w\\/]", "cd command (use git -C instead)"),
    (r"Set-Location\s+[\"']?[\w\\/]", "Set-Location (use git -C instead)"),
    (r"git\s+-C\s+[\"']?\.\.?/", "Relative path in git -C (use absolute path)"),
]


def check_repo_commands(repo_path: Path) -> list[dict]:
    issues = []
    for file in repo_path.rglob("*.sh"):
        content = file.read_text(encoding="utf-8", errors="ignore")
        for pattern, desc in FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append({"file": str(file), "pattern": desc, "matches": len(matches)})
    return issues


def lint_scripts(path: Path) -> list[dict]:
    issues = []
    for file in path.rglob("*.sh"):
        if file.is_dir():
            continue
        content = file.read_text(encoding="utf-8", errors="ignore")
        for line in content.splitlines():
            for pattern, desc in FORBIDDEN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({"file": str(file), "line": line.strip(), "pattern": desc})
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-Repo Flow Check")
    parser.add_argument("--repo", help="Path to git repository")
    parser.add_argument("--path", help="Path to lint")
    parser.add_argument("--lint", action="store_true", help="Lint mode")
    args = parser.parse_args()

    issues = []

    if args.lint and args.path:
        issues = lint_scripts(Path(args.path))
    elif args.repo:
        issues = check_repo_commands(Path(args.repo))
    else:
        print("[ERR] --repo or --path --lint required")
        return 1

    if issues:
        print(f"[ERR] Found {len(issues)} cross-repo flow violations:")
        for issue in issues[:20]:
            file_info = issue.get("file", "")
            line_info = issue.get("line", "")
            pattern = issue.get("pattern", "")
            print(f"  - {file_info}: {pattern}")
            if line_info:
                print(f"    {line_info}")
        return 1

    print("[OK] No cross-repo flow violations found")
    return 0


if __name__ == "__main__":
    exit(main())
