#!/usr/bin/env python3
"""
Vérifie la CI constitutionnelle pour repos L0/L1/L2.
Appelé par ecosystem_sync --operation enforce
"""
import subprocess
import sys
import yaml
from pathlib import Path

REQUIRED_WORKFLOWS = [
    "rss-lint.yml",
    "branch-gate.yml", 
    "vyoa-verify.yml"
]

REQUIRED_CONTEXTS = [
    "RSS-v2 Linter",
    "BRGS — Branch Ownership Check",
    "BRANCH-GOVERNOR — Branch Naming Check",
    "VYOA Verify"
]

def check_workflow_exists(repo, workflow_name):
    """Vérifie si le workflow existe dans le repo"""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/.github/workflows/{workflow_name}"],
        capture_output=True, text=True
    )
    return result.returncode == 0

def check_workflow_scripts_exist(repo):
    """Vérifie que les scripts référencés dans les workflows existent"""
    # Pour l'instant, on vérifie juste que le repo a les scripts de base
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/scripts"],
        capture_output=True, text=True
    )
    return result.returncode == 0

def check_branch_protection(repo):
    """Vérifie la branch protection main"""
    result = subprocess.run(
        ["gh", "api", f"repos/{repo}/branches/main/protection", "--jq", ".required_status_checks.contexts[]?"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False, "No branch protection"
    
    contexts = result.stdout.strip().split('\n')
    missing = [c for c in REQUIRED_CONTEXTS if c not in contexts]
    return len(missing) == 0, f"Missing contexts: {missing}" if missing else "OK"

def main():
    KNOWN_REPOS = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml")
    
    with open(KNOWN_REPOS) as f:
        data = yaml.safe_load(f)
    
    constitutional_repos = []
    for tier in ["P0_REPOS", "P1_REPOS", "P2_REPOS"]:
        for repo in data.get(tier, []):
            layer = repo.get("layer", "")
            if layer in ["L0_CONSTITUTIONAL", "L0-CANON", "L1_CAUSALITY", "L1_INFRA", "L2_COMPOSITION", "L2b_QUALIFIER", "L2b_SENSOR"]:
                if repo.get("status") == "ACTIVE":
                    constitutional_repos.append(repo)
    
    print(f"[CONSTITUTIONAL-CI] Checking {len(constitutional_repos)} constitutional repos...")
    
    violations = []
    
    for repo in constitutional_repos:
        name = repo["full_name"]
        print(f"\n[CHECK] {name} ({repo.get('layer')})")
        
        # 1. Workflows
        missing_workflows = []
        for wf in REQUIRED_WORKFLOWS:
            if not check_workflow_exists(name, wf):
                missing_workflows.append(wf)
        
        if missing_workflows:
            violations.append(f"{name}: missing workflows {missing_workflows}")
            print(f"  [FAIL] Missing workflows: {missing_workflows}")
        else:
            print(f"  [OK] All workflows present")
        
        # 2. Branch protection
        prot_ok, prot_msg = check_branch_protection(name)
        if not prot_ok:
            violations.append(f"{name}: branch protection - {prot_msg}")
            print(f"  [FAIL] Branch protection: {prot_msg}")
        else:
            print(f"  [OK] Branch protection")
        
        # 3. Scripts exist (basic check)
        if not check_workflow_scripts_exist(name):
            violations.append(f"{name}: missing scripts/ directory")
            print(f"  [FAIL] Missing scripts/")
        else:
            print(f"  [OK] Scripts directory exists")
    
    # Report
    if violations:
        print(f"\n[CONSTITUTIONAL-CI] VIOLATIONS: {len(violations)}")
        for v in violations:
            print(f"  - {v}")
        
        # Downgrade logic would go here
        print("\n[ENFORCE] Downgrading enforcement_mode.ci to 'hooks-only' for violators...")
        # TODO: Update known_repositories.yaml
        
        sys.exit(1)
    
    print(f"\n[OK] All {len(constitutional_repos)} constitutional repos compliant")
    sys.exit(0)

if __name__ == "__main__":
    main()