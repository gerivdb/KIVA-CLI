#!/usr/bin/env python3
"""
Install MC-RNN pre-commit hook into a target repo.

Usage:
    python install-mc-rnn-hook.py <repo_path>

Copies .githooks/mc-rnn-pre-commit to <repo_path>/.githooks/pre-commit
and configures git to use it.
"""

import sys
import shutil
import subprocess
from pathlib import Path

HOOK_SOURCE = Path(__file__).parent.parent / ".githooks" / "mc-rnn-pre-commit"

def install_hook(repo_path: Path):
    """Install the MC-RNN pre-commit hook into a repo."""
    if not repo_path.exists():
        print(f"ERROR: Repo path does not exist: {repo_path}")
        sys.exit(1)

    git_dir = repo_path / ".git"
    if not git_dir.exists():
        print(f"ERROR: Not a git repo: {repo_path}")
        sys.exit(1)

    # Create .githooks directory
    hooks_dir = repo_path / ".githooks"
    hooks_dir.mkdir(exist_ok=True)

    # Copy hook
    dest = hooks_dir / "pre-commit"
    shutil.copy2(str(HOOK_SOURCE), str(dest))

    # Make executable (Windows: chmod not needed, but set read/write)
    dest.chmod(0o755)

    # Configure git to use .githooks
    result = subprocess.run(
        ["git", "config", "core.hooksPath", ".githooks"],
        capture_output=True, text=True, cwd=str(repo_path)
    )
    if result.returncode != 0:
        print(f"ERROR: Failed to configure hooksPath: {result.stderr}")
        sys.exit(1)

    print(f"Installed MC-RNN pre-commit hook into {repo_path}")
    print(f"  Hook: {dest}")
    print(f"  git config core.hooksPath = .githooks")

    # Verify
    result = subprocess.run(
        ["git", "config", "core.hooksPath"],
        capture_output=True, text=True, cwd=str(repo_path)
    )
    print(f"  Verified: core.hooksPath = {result.stdout.strip()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python install-mc-rnn-hook.py <repo_path>")
        print("\nExample:")
        print(r"  python install-mc-rnn-hook.py D:\DO\WEB\TOOLS\L4-TOOLS\LYCOS")
        sys.exit(1)

    install_hook(Path(sys.argv[1]))
