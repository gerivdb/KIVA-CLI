#!/usr/bin/env python3
"""CURX test runner for KIVA-CLI.

Runs CURX tests across TALEX, KG-L and VOLTX repos.

Usage:
    python run_curx_tests.py [--level 1|2|3] [--coverage] [--coverage-report]

IntentHash: 0xH0_CURX_KIVA_TEST_RUNNER_20260910T041100Z
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPOS = {
    "talex": Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\TALEX"),
    "kg-l": Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\KG-L"),
    "voltx": Path(r"D:\DO\WEB\TOOLS\L0-CANON\VOLTX"),
}

SEED_SCRIPT = REPOS["voltx"] / "seed_kg_l.py"
REPORTS_DIR = REPOS["voltx"] / "reports"

TEST_FILES = {
    "talex": [
        REPOS["talex"] / "tests" / "test_curx_decision_engine.py",
        REPOS["talex"] / "tests" / "test_curx_integration.py",
        REPOS["talex"] / "tests" / "test_curx_full_level_integration.py",
    ],
    "kg-l": [
        REPOS["kg-l"] / "tests" / "test_kg_l_narrator.py",
        REPOS["kg-l"] / "tests" / "test_curx_kg_l_integration.py",
    ],
    "voltx": [
        REPOS["voltx"] / "tests" / "test_curx_scorecard.py",
    ],
}


def run_pytest(repo_name: str, files: list[Path], coverage: bool = False, coverage_report: bool = False) -> tuple[int, Path | None]:
    cmd = [sys.executable, "-m", "pytest", "-v"]
    json_report_path = None
    if coverage or coverage_report:
        cmd += ["--cov=.", "--cov-branch"]
        if coverage_report:
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            json_report_path = REPORTS_DIR / f"curx_coverage_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            cmd += [
                "--cov-report=term-missing",
                f"--cov-report=json:{json_report_path}",
            ]
        else:
            cmd += ["--cov-report=term-missing"]
    cmd += [str(f) for f in files]

    print(f"\n{'='*60}")
    print(f"CURX tests — {repo_name.upper()}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=REPOS[repo_name], capture_output=False)
    return result.returncode, json_report_path


def _load_coverage_summary(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        totals = data.get("totals", {})
        return {
            "repo": path.parent.name,
            "coverage_percent": totals.get("percent_covered", 0.0),
            "missing_lines": totals.get("missing_lines", 0),
            "missing_branches": totals.get("missing_branches", 0),
        }
    except Exception as exc:
        return {"repo": path.parent.name, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="CURX test runner")
    parser.add_argument("--level", type=int, choices=[1, 2, 3], help="CURX level filter")
    parser.add_argument("--coverage", action="store_true", help="Enable coverage")
    parser.add_argument("--coverage-report", action="store_true", help="Enable coverage and save JSON report")
    args = parser.parse_args()

    if args.coverage_report:
        args.coverage = True

    # Seed KG-L with canonical graph before running CURX tests
    if SEED_SCRIPT.exists():
        print(f"\nSeeding KG-L from {SEED_SCRIPT}")
        subprocess.run([sys.executable, str(SEED_SCRIPT)], check=False)
    else:
        print(f"\nWarning: KG-L seed script not found at {SEED_SCRIPT}")

    failures = []
    coverage_summaries = []
    proof_lines = [
        f"CURX_TEST_PROOF timestamp={datetime.now(timezone.utc).isoformat()}Z",
        f"CURX_TEST_PROOF seed={SEED_SCRIPT.exists()}",
    ]
    for repo_name, files in TEST_FILES.items():
        rc, json_report_path = run_pytest(repo_name, files, args.coverage, args.coverage_report)
        proof_lines.append(f"CURX_TEST_PROOF repo={repo_name} rc={rc} coverage_json={json_report_path.name if json_report_path else 'None'}")
        if rc != 0:
            failures.append(repo_name)
        if json_report_path and json_report_path.exists():
            coverage_summaries.append(_load_coverage_summary(json_report_path))

    print(f"\n{'='*60}")
    proof_lines.append(f"CURX_TEST_PROOF failures={','.join(failures) if failures else 'None'}")
    proof_lines.append(f"CURX_TEST_PROOF status={'PASS' if not failures else 'FAIL'}")
    print("\n".join(proof_lines))
    if failures:
        print(f"FAILED repos: {', '.join(failures)}")
        return 1
    print("ALL CURX TESTS PASSED")

    if coverage_summaries:
        print("\nCoverage summary:")
        for summary in coverage_summaries:
            if "error" in summary:
                print(f"  {summary['repo']}: coverage report error: {summary['error']}")
            else:
                print(
                    f"  {summary['repo']}: {summary['coverage_percent']:.1f}% "
                    f"(missing_lines={summary['missing_lines']}, missing_branches={summary['missing_branches']})"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
