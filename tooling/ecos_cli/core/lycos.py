#!/usr/bin/env python3
"""
LYCOS - Code Intelligence Integration for KIVA-CLI
E5620 compatible (no AVX required)
"""
import subprocess
import sys
from pathlib import Path

LYCOS_REPO = "gerivdb/LYCOS"
LYCOS_LOCAL = Path("C:/DevTools/LYCOS")  # or configurable


def run_lycos(args):
    """Run lycos command"""
    lycos_exe = LYCOS_LOCAL / "src" / "lycos.py"
    
    if not lycos_exe.exists():
        return f"Error: LYCOS not found at {lycos_exe}"
    
    result = subprocess.run(
        [sys.executable, str(lycos_exe)] + args,
        capture_output=True,
        text=True
    )
    return result.stdout or result.stderr


def index_repo(repo_path):
    """Index a repository"""
    return run_lycos(["index", repo_path])


def search(query):
    """Search code"""
    return run_lycos(["search", query])


def tree():
    """List indexed files"""
    return run_lycos(["tree"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: lycos.py <index|search|tree> [args...]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "index":
        print(index_repo(sys.argv[2] if len(sys.argv) > 2 else "."))
    elif cmd == "search":
        print(search(sys.argv[2] if len(sys.argv) > 2 else ""))
    elif cmd == "tree":
        print(tree())
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)