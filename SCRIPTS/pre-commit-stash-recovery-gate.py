#!/usr/bin/env python3
"""
pre-commit hook: refuse commits touching >100 files unless message contains [STASH-RECOVERY].

IntentHash: 0xPRE_COMMIT_STASH_RECOVERY_GATE_20260919
"""
import re
import subprocess
import sys

MAX_FILES = 100
TAG = "[STASH-RECOVERY]"


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


def main() -> int:
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
