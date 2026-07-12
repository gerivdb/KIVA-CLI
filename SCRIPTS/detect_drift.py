#!/usr/bin/env python3
"""
Détecte le drift des workflows/hooks vs KIVA-CLI main.
Appelé par ecosystem_sync --operation validate
"""
import subprocess
import sys
import json
from pathlib import Path

KIVA_CLI = "gerivdb/KIVA-CLI"
REUSABLE_WORKFLOWS = [
    "rss-v2-reusable.yml",
    "branch-gate.yml",
    "vyoa-verify-reusable.yml"
]

TEMPLATES = {
    "rss-lint.yml": "gerivdb/KIVA-CLI/.github/workflows/rss-v2-reusable.yml@gov-workflows/v1",
    "vyoa-verify.yml": "gerivdb/KIVA-CLI/.github/workflows/vyoa-verify-reusable.yml@gov-workflows/v1",
    "branch-gate.yml": "gerivdb/KIVA-CLI/.github/workflows/branch-gate.yml@gov-workflows/v1",
}

HOOKS = [
    "pre-commit", "pre-push", "commit-msg", 
    "post-commit", "post-push", "post-merge", "rules.sh"
]

def get_sha(repo, path):
    """Récupère le SHA d'un fichier via GitHub API"""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}", "--jq", ".sha"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def check_repo_drift(repo_name):
    """Vérifie le drift d'un repo vs KIVA-CLI"""
    drift_report = {
        "repo": repo_name,
        "workflows": {},
        "hooks": {},
        "has_drift": False
    }
    
    # Check workflows
    for wf_name, template_ref in TEMPLATES.items():
        kiva_sha = get_sha(KIVA_CLI, f".github/workflows/{wf_name}")
        repo_sha = get_sha(repo_name, f".github/workflows/{wf_name}")
        
        if repo_sha is None:
            drift_report["workflows"][wf_name] = {"status": "missing", "drift": True}
            drift_report["has_drift"] = True
        elif kiva_sha and repo_sha != kiva_sha:
            drift_report["workflows"][wf_name] = {
                "status": "drift", "drift": True, 
                "kiva_sha": kiva_sha[:8], "repo_sha": repo_sha[:8]
            }
            drift_report["has_drift"] = True
        else:
            drift_report["workflows"][wf_name] = {"status": "synced", "drift": False}
    
    # Check hooks
    for hook in HOOKS:
        kiva_sha = get_sha(KIVA_CLI, f".githooks/{hook}")
        repo_sha = get_sha(repo_name, f".githooks/{hook}")
        
        if repo_sha is None:
            drift_report["hooks"][hook] = {"status": "missing", "drift": True}
            drift_report["has_drift"] = True
        elif kiva_sha and repo_sha != kiva_sha:
            drift_report["hooks"][hook] = {
                "status": "drift", "drift": True,
                "kiva_sha": kiva_sha[:8], "repo_sha": repo_sha[:8]
            }
            drift_report["has_drift"] = True
        else:
            drift_report["hooks"][hook] = {"status": "synced", "drift": False}
    
    return drift_report

def main():
    KNOWN_REPOS = "D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml"
    import yaml
    with open(KNOWN_REPOS) as f:
        data = yaml.safe_load(f)
    
    all_reports = []
    for tier in ["P0_REPOS", "P1_REPOS", "P2_REPOS", "P3_REPOS", "P4_REPOS"]:
        for repo in data.get(tier, []):
            if repo.get("status") == "ACTIVE" and repo.get("enforcement_mode", {}).get("ci") != "none":
                print(f"[DRIFT] Checking {repo['name']}...")
                report = check_repo_drift(repo["full_name"])
                all_reports.append(report)
                if report["has_drift"]:
                    print(f"  [DRIFT] {repo['name']}")
    
    # Summary
    drifted = [r for r in all_reports if r["has_drift"]]
    print(f"\n[DRIFT REPORT] {len(drifted)}/{len(all_reports)} repos have drift")
    
    if drifted:
        for r in drifted:
            print(f"  - {r['repo']}")
            for wf, info in r["workflows"].items():
                if info["drift"]:
                    print(f"    WORKFLOW {wf}: {info['status']} (KIVA:{info.get('kiva_sha','?')} vs REPO:{info.get('repo_sha','?')})")
            for hk, info in r["hooks"].items():
                if info["drift"]:
                    print(f"    HOOK {hk}: {info['status']}")
    
    # Write report
    with open("drift-report.json", "w") as f:
        json.dump(all_reports, f, indent=2)
    
    sys.exit(1 if drifted else 0)

if __name__ == "__main__":
    main()