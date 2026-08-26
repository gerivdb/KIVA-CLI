#!/usr/bin/env python3
"""
rss_bulk_scan.py — Scan RSS-v2 conformite pour tous les repos gerivdb locaux
Utilise le parallelisme pour accelerer le scan
"""

import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

REPOS_ROOT = Path(r"D:\DO\WEB\TOOLS")
REPO_STANDARDS = REPOS_ROOT / "L4-TOOLS" / "REPO-STANDARDS"
RSS_LINT = REPOS_ROOT / "L4-TOOLS" / "CTULU" / "tools" / "rss-lint" / "rss_lint.py"

STRATES = [
    "L0-CANON",
    "L1-INFRA",
    "L2-PLATFORM",
    "L3-CITIZENS",
    "L4-TOOLS",
    "L5-ARCHIVE",
]

def scan_repo(repo_path_str: str) -> tuple:
    repo_path = Path(repo_path_str)
    if not (repo_path / ".git").exists():
        return (repo_path.name, "SKIP", "", 0)
    
    try:
        result = subprocess.run(
            [sys.executable, str(RSS_LINT), "--repo", str(repo_path)],
            capture_output=True,
            text=True,
            timeout=15
        )
        output = result.stdout + result.stderr
        is_pass = "[PASS]" in output
        return (
            repo_path.name,
            "PASS" if is_pass else "FAIL",
            output.strip() if not is_pass else "",
            1 if is_pass else 0
        )
    except subprocess.TimeoutExpired:
        return (repo_path.name, "TIMEOUT", "", 0)
    except Exception as e:
        return (repo_path.name, "ERROR", str(e)[:100], 0)

def main():
    # Collect all repos
    repos = []
    for strate in STRATES:
        strate_path = REPOS_ROOT / strate
        if not strate_path.exists():
            continue
        for repo_dir in sorted(strate_path.iterdir()):
            if repo_dir.is_dir() and (repo_dir / ".git").exists():
                repos.append((str(repo_dir), strate, repo_dir.name))
    
    print(f"Scanning {len(repos)} repos...")
    
    results = {}
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(scan_repo, r[0]): r for r in repos}
        for i, future in enumerate(as_completed(futures)):
            name, status, output, _ = future.result()
            strate = futures[future][1]
            results[name] = {"strate": strate, "status": status, "output": output}
            print(f"  [{i+1}/{len(repos)}] {name}: {status}")
    
    # Generate report
    total = len(results)
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = sum(1 for r in results.values() if r["status"] == "FAIL")
    
    lines = [
        "# RSS-v2 Bulk Scan Report",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Total**: {total} | **Pass**: {passed} | **Fail**: {failed}",
        "",
        "## All Repos",
        "",
        "| Repo | Strate | Status |",
        "|-------|--------|--------|",
    ]
    
    for name in sorted(results.keys()):
        r = results[name]
        emoji = r["status"]
        lines.append(f"| {name} | {r['strate']} | {emoji} |")
    
    lines.extend(["", "## Failed Repos", ""])
    for name in sorted(results.keys()):
        r = results[name]
        if r["status"] in ("FAIL", "TIMEOUT", "ERROR"):
            lines.append(f"### {name} ({r['strate']})")
            if r["output"]:
                lines.append("```")
                lines.append(r["output"][:300])
                lines.append("```")
            lines.append("")
    
    report_path = REPO_STANDARDS / "REPORTS" / f"rss-bulk-scan-{datetime.now().strftime('%Y%m%d')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {report_path}")
    print(f"Total: {total} | Pass: {passed} | Fail: {failed}")

if __name__ == "__main__":
    main()
