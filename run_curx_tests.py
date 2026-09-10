#!/usr/bin/env python3
"""CURX test runner for KIVA-CLI.

Runs CURX tests across TALEX, KG-L and VOLTX repos.

Usage:
    python run_curx_tests.py [--level 1|2|3] [--coverage]

IntentHash: 0xH0_CURX_KIVA_TEST_RUNNER_20260910T010500Z
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPOS = {
    "talex": Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\TALEX"),
    "kg-l": Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\KG-L"),
    "voltx": Path(r"D:\DO\WEB\TOOLS\L0-CANON\VOLTX"),
}

TEST_FILES = {
    "talex": [
        REPOS["talex"] / "tests" / "test_curx_decision_engine.py",
        REPOS["talex"] / "tests" / "test_curx_integration.py",
    ],
    "kg-l": [
        REPOS["kg-l"] / "tests" / "test_kg_l_narrator.py",
        REPOS["kg-l"] / "tests" / "test_curx_kg_l_integration.py",
    ],
    "voltx": [
        REPOS["voltx"] / "tests" / "test_curx_scorecard.py",
    ],
}


def run_pytest(repo_name: str, files: list[Path], coverage: bool = False) -> int:
    cmd = [sys.executable, "-m", "pytest", "-v"]
    if coverage:
        cmd += ["--cov=.", "--cov-report=term-missing"]
    cmd += [str(f) for f in files]
    
    print(f"\n{'='*60}")
    print(f"CURX tests — {repo_name.upper()}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, cwd=REPOS[repo_name], capture_output=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="CURX test runner")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], help="CURX level filter")
    parser.add_argument("--coverage", action="store_true", help="Enable coverage")
    args = parser.parse_args()
    
    failures = []
    for repo_name, files in TEST_FILES.items():
        rc = run_pytest(repo_name, files, args.coverage)
        if rc != 0:
            failures.append(repo_name)
    
    print(f"\n{'='*60}")
    if failures:
        print(f"FAILED repos: {', '.join(failures)}")
        return 1
    print("ALL CURX TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
