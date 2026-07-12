#!/usr/bin/env python3
"""
Conformance Dashboard — Agrège santé gouvernance de tous repos ACTIVE.
"""
import subprocess
import yaml
import json
from datetime import datetime
from pathlib import Path

METRICS = {
    "rss_lint": {"workflow": "rss-lint.yml", "check": "conclusion"},
    "branch_gate": {"workflow": "branch-gate.yml", "check": "conclusion"},
    "vyoa_verify": {"workflow": "vyoa-verify.yml", "check": "conclusion"},
    "branch_protection": {"api": "branches/main/protection", "check": "required_status_checks"},
    "hooks_version": {"api": "contents/.githooks/pre-push", "check": "sha"},
    "workflows_drift": {"compare": "KIVA-CLI main SHA vs repo workflow SHA"},
}

def read_active_repos():
    with open("GOVERNANCE-HUB/known_repositories.yaml") as f:
        data = yaml.safe_load(f)
    active = []
    for tier in ["P0_REPOS", "P1_REPOS", "P2_REPOS", "P3_REPOS"]:
        for repo in data.get(tier, []):
            if repo.get("status") == "ACTIVE" and repo.get("local_path"):
                em = repo.get("enforcement_mode", {})
                if em.get("ci") != "none":
                    active.append({
                        "name": repo["full_name"],
                        "layer": repo.get("layer"),
                        "logical_layers": repo.get("logical_layers", []),
                        "enforcement_mode": em
                    })
    return active

def check_workflow_status(repo, workflow_name):
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/actions/workflows/{workflow_name}/runs", "--jq", ".workflow_runs[0].conclusion"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return "unknown"

def check_branch_protection(repo):
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/branches/main/protection", "--jq", ".required_status_checks.contexts[]?"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        contexts = [c for c in result.stdout.strip().split('\n') if c]
        return {"configured": True, "contexts": contexts}
    return {"configured": False, "contexts": []}

def check_hooks_sha(repo, hook_name):
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/.githooks/{hook_name}", "--jq", ".sha"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None

def check_workflow_drift(repo, workflow_file):
    # Get repo workflow SHA
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/.github/workflows/{workflow_file}", "--jq", ".sha"],
        capture_output=True, text=True
    )
    repo_sha = result.stdout.strip() if result.returncode == 0 else None
    
    # Get KIVA-CLI workflow SHA
    result = subprocess.run(
        ["gh", "api", f"repos/gerivdb/KIVA-CLI/contents/.github/workflows/{workflow_file}", "--jq", ".sha"],
        capture_output=True, text=True
    )
    kiva_sha = result.stdout.strip() if result.returncode == 0 else None
    
    return {
        "repo_sha": repo_sha,
        "kiva_sha": kiva_sha,
        "drift": repo_sha != kiva_sha
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="GOVERNANCE-HUB/known_repositories.yaml")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    active_repos = read_active_repos()
    timestamp = datetime.utcnow().isoformat() + "Z"
    date_str = datetime.utcnow().strftime("%Y%m%d")
    
    report = {
        "generated_at": timestamp,
        "total_repos": len(active_repos),
        "repos": {}
    }
    
    summary = {
        "rss_lint_pass": 0, "rss_lint_fail": 0, "rss_lint_unknown": 0,
        "branch_gate_pass": 0, "branch_gate_fail": 0, "branch_gate_unknown": 0,
        "vyoa_verify_pass": 0, "vyoa_verify_fail": 0, "vyoa_verify_unknown": 0,
        "protection_configured": 0, "protection_missing": 0,
        "hooks_current": 0, "hooks_drift": 0, "hooks_missing": 0,
        "workflows_current": 0, "workflows_drift": 0,
    }
    
    for repo_info in active_repos:
        repo = repo_info["name"]
        print(f"[SCAN] {repo}")
        
        repo_report = {
            "layer": repo_info["layer"],
            "logical_layers": repo_info["logical_layers"],
            "rss_lint": check_workflow_status(repo, "rss-lint.yml"),
            "branch_gate": check_workflow_status(repo, "branch-gate.yml"),
            "vyoa_verify": check_workflow_status(repo, "vyoa-verify.yml"),
            "branch_protection": check_branch_protection(repo),
            "hooks": {
                "pre-push": check_hooks_sha(repo, "pre-push"),
                "pre-commit": check_hooks_sha(repo, "pre-commit"),
                "commit-msg": check_hooks_sha(repo, "commit-msg"),
                "post-commit": check_hooks_sha(repo, "post-commit"),
                "post-push": check_hooks_sha(repo, "post-push"),
                "post-merge": check_hooks_sha(repo, "post-merge"),
                "rules_sh": check_hooks_sha(repo, "rules.sh"),
            },
            "workflow_drift": {
                "rss-lint.yml": check_workflow_drift(repo, "rss-lint.yml"),
                "branch-gate.yml": check_workflow_drift(repo, "branch-gate.yml"),
                "vyoa-verify.yml": check_workflow_drift(repo, "vyoa-verify.yml"),
            }
        }
        
        report["repos"][repo] = repo_report
        
        # Update summary
        for key in ["rss_lint", "branch_gate", "vyoa_verify"]:
            val = repo_report[key]
            if val == "success":
                summary[f"{key}_pass"] += 1
            elif val == "failure":
                summary[f"{key}_fail"] += 1
            else:
                summary[f"{key}_unknown"] += 1
        
        if repo_report["branch_protection"]["configured"]:
            summary["protection_configured"] += 1
        else:
            summary["protection_missing"] += 1
        
        hooks_shas = [v for v in repo_report["hooks"].values() if v]
        if len(hooks_shas) == 7:
            summary["hooks_current"] += 1
        elif len(hooks_shas) > 0:
            summary["hooks_drift"] += 1
        else:
            summary["hooks_missing"] += 1
        
        drifts = [w for w in repo_report["workflow_drift"].values() if w["drift"]]
        if drifts:
            summary["workflows_drift"] += 1
        else:
            summary["workflows_current"] += 1
    
    report["summary"] = summary
    
    # Write JSON
    out_json = Path(f"conformance-{date_str}.json")
    out_json.write_text(json.dumps(report, indent=2))
    
    # Write Markdown
    out_md = Path(f"conformance-{date_str}.md")
    md = f"""# Conformance Dashboard — {date_str}

**Generated**: {timestamp}
**Total Repos**: {len(active_repos)}

## Summary

| Metric | Pass | Fail | Unknown/Missing |
|--------|------|------|-----------------|
| RSS Lint | {summary['rss_lint_pass']} | {summary['rss_lint_fail']} | {summary['rss_lint_unknown']} |
| Branch Gate | {summary['branch_gate_pass']} | {summary['branch_gate_fail']} | {summary['branch_gate_unknown']} |
| VYOA Verify | {summary['vyoa_verify_pass']} | {summary['vyoa_verify_fail']} | {summary['vyoa_verify_unknown']} |
| Branch Protection | {summary['protection_configured']} | {summary['protection_missing']} | - |
| Hooks (7/7) | {summary['hooks_current']} | {summary['hooks_missing']} | {summary['hooks_drift']} |
| Workflows (no drift) | {summary['workflows_current']} | {summary['workflows_drift']} | - |

## Repos Requiring Attention

"""
    for repo, data in report["repos"].items():
        issues = []
        if data["rss_lint"] == "failure": issues.append("RSS Lint")
        if data["branch_gate"] == "failure": issues.append("Branch Gate")
        if data["vyoa_verify"] == "failure": issues.append("VYOA")
        if not data["branch_protection"]["configured"]: issues.append("No Branch Protection")
        if len([v for v in data["hooks"].values() if v]) < 7: issues.append("Missing Hooks")
        if any(w["drift"] for w in data["workflow_drift"].values()): issues.append("Workflow Drift")
        
        if issues:
            md += f"- **{repo}** ({data['layer']}): {', '.join(issues)}\n"
    
    out_md.write_text(md)
    
    # Write Badge SVG
    total_checks = sum(summary.values())
    passed = (summary['rss_lint_pass'] + summary['branch_gate_pass'] + 
              summary['vyoa_verify_pass'] + summary['protection_configured'] +
              summary['hooks_current'] + summary['workflows_current'])
    rate = round(passed / total_checks * 100) if total_checks > 0 else 0
    
    badge = f"""<svg xmlns="http://www.w3.org/2000/svg" width="200" height="20">
  <rect width="200" height="20" fill="#444"/>
  <rect width="{rate*2}" height="20" fill="#28a745"/>
  <text x="100" y="14" text-anchor="middle" fill="white" font-family="sans-serif" font-size="11">
    Conformance: {rate}%
  </text>
</svg>"""
    Path(f"conformance-badge-{date_str}.svg").write_text(badge)
    
    print(f"[DONE] Dashboard written: {out_json}, {out_md}, badge.svg")
    print(f"Overall conformance: {rate}%")

if __name__ == "__main__":
    main()