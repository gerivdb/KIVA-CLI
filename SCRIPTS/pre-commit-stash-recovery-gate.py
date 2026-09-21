#!/usr/bin/env python3
"""
pre-commit hook: refuse commits touching >100 files unless message contains [STASH-RECOVERY].
Also validates that configured hook paths exist in .pre-commit-config.yaml.

IntentHash: 0xPRE_COMMIT_STASH_RECOVERY_GATE_20260919
"""
import os
import re
import subprocess
import sys
from pathlib import Path

MAX_FILES = 100
TAG = "[STASH-RECOVERY]"
CONFIG_FILE = ".pre-commit-config.yaml"


def get_commit_message() -> str:
    """Read commit message from .git/COMMIT_EDITMSG or args."""
    msg_file = ".git/COMMIT_EDITMSG"
    try:
        with open(msg_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def count_changed_files() -> int:
    """Count modified, added, deleted files in staging area."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
        )
        files = [line.strip() for line in out.splitlines() if line.strip()]
        return len(files)
    except Exception:
        return 0


def validate_hook_paths() -> list[str]:
    """Validate that hook entry paths in .pre-commit-config.yaml exist.
    
    Returns list of missing paths.
    """
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        return []
    
    missing = []
    content = config_path.read_text(encoding="utf-8")
    
    # Simple regex to find entry: lines in local hooks
    # Matches: entry: python path/to/script.py or entry: path/to/script.sh
    pattern = r"entry:\s*(?:python\s+)?([^\s\n]+)"
    matches = re.findall(pattern, content)
    
    for match in matches:
        # Skip if it's a known command or contains placeholders
        if any(char in match for char in ["{", "}", "$", "\\"]):
            continue
        if match.startswith("python") or match.startswith("bash"):
            continue
        if not Path(match).exists():
            missing.append(match)
    
    return missing


def main() -> int:
    # Validate hook paths first
    missing_paths = validate_hook_paths()
    if missing_paths:
        print("[PRE-COMMIT BLOCK] Missing hook entry paths in .pre-commit-config.yaml:")
        for path in missing_paths:
            print(f"  - {path}")
        print("Fix the paths or remove the hooks before committing.")
        return 1

    # Check file count
    msg = get_commit_message()
    changed = count_changed_files()

    if changed > MAX_FILES and TAG not in msg:
        print(
            f"[PRE-COMMIT BLOCK] Commit touches {changed} files (> {MAX_FILES}) "
            f"without '{TAG}' tag in message."
        )
        print("If this is a stash recovery, add the tag to the commit message.")
        print("Otherwise, split the commit into smaller chunks.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
