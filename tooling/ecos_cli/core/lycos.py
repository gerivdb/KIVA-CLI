#!/usr/bin/env python3
"""
LYCOS - Code Intelligence Integration for KIVA-CLI
E5620 compatible (no AVX required)

Commands:
- lycos index <repo_path>  # Index a repository
- lycos search <query>   # Search code
- lycos tree            # List indexed files
- lycos outline <file> # Show file outline
- lycos watch          # Watch for changes
- lycos update        # Update index
"""
import subprocess
import sys
import os
from pathlib import Path

__version__ = "1.0.0"


def get_lycos_path():
    """Get path to lycos.py"""
    paths = [
        Path("C:/DevTools/LYCOS/src/lycos.py"),
        Path("D:/DO/WEB/TOOLS/L4-TOOLS/LYCOS/src/lycos.py"),
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def run_lycos(args):
    """Run lycos command"""
    lycos_exe = get_lycos_path()
    if not lycos_exe:
        return "Error: LYCOS not found"
    result = subprocess.run(
        [sys.executable, str(lycos_exe)] + args,
        capture_output=True, text=True
    )
    return result.stdout or result.stderr


def main():
    if len(sys.argv) < 2:
        print("LYCOS v1.0.0 - Commands: index, search, tree, outline, watch, update")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "index":
        print(run_lycos(["build"]))
    elif cmd == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        print(run_lycos(["search", q]))
    elif cmd == "tree":
        print(run_lycos(["tree"]))
    elif cmd == "outline":
        f = sys.argv[2] if len(sys.argv) > 2 else ""
        print(run_lycos(["outline", f]))
    elif cmd == "watch":
        print("Watch: Not implemented")
    elif cmd == "update":
        print(run_lycos(["build"]))
    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()