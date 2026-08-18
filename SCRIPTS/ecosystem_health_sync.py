#!/usr/bin/env python3
"""
Ecosystem-wide Git Health Sync
Synchronizes ALL git repositories in the gerivdb ecosystem
"""

import subprocess
import os
import json
import requests
from datetime import datetime

# All valid strata directories
VALID_STRATES = [
    "D:\\DO\\WEB\\TOOLS\\L0-CANON",
    "D:\\DO\\WEB\\TOOLS\\L0-INFRASTRUCTURE",
    "D:\\DO\\WEB\\TOOLS\\L1-INFRA",
    "D:\\DO\\WEB\\TOOLS\\L2-PLATFORM",
    "D:\\DO\\WEB\\TOOLS\\L3-CITIZENS",
    "D:\\DO\\WEB\\TOOLS\\L4-TOOLS",
    "D:\\DO\\WEB\\TOOLS\\L5-ARCHIVE",
    "D:\\DO\\WEB",
    "C:\\DevTools",
]

def _github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        token = _token_from_gh_keyring()
    if not token:
        raise RuntimeError("GITHUB_TOKEN/gh keyring requis pour créer des PRs en BDCP")
    return token

def _github_headers():
    return {
        "Authorization": f"Bearer {_github_token()}",
        "Accept": "application/vnd.github+json",
    }

def run_cmd(cmd, cwd=None):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def _token_from_gh_keyring():
    """Fallback: read token from gh keyring when GITHUB_TOKEN/ GH_TOKEN are not set"""
    gh_path = None
    for candidate in ["gh", "C:\\gh\\bin\\gh.exe", os.path.expandvars("%LOCALAPPDATA%\\Programs\\gh\\bin\\gh.exe")]:
        if os.path.exists(candidate):
            gh_path = candidate
            break
    if not gh_path:
        return None
    token_out = subprocess.run(f"{gh_path} auth token", shell=True, capture_output=True, text=True)
    if token_out.returncode != 0:
        return None
    token = token_out.stdout.strip()
    return token if token else None

def find_all_git_repos():
    """Find all git repositories in the ecosystem"""
    repos = []
    
    for base_path in VALID_STRATES:
        if os.path.exists(base_path):
            # Find all .git directories
            for root, dirs, files in os.walk(base_path):
                if '.git' in dirs:
                    repo_path = root
                    # Avoid duplicates
                    if repo_path not in repos:
                        repos.append(repo_path)
    
    return repos

def get_active_branch(repo_path):
    """Get the currently active branch"""
    stdout, code = run_cmd("git branch --show-current", repo_path)
    return stdout.strip() if code == 0 else "unknown"

def get_behind_ahead(repo_path):
    """Get behind/ahead count"""
    stdout, code = run_cmd("git rev-list --left-right --count origin/main...HEAD 2>/dev/null", repo_path)
    if stdout and code == 0:
        parts = stdout.split()
        if len(parts) == 2:
            return int(parts[0]), int(parts[1])  # behind, ahead
    return 0, 0

def sync_repo(repo_path):
    """Sync a single repository"""
    name = os.path.basename(repo_path)
    print(f"[SYNC] Processing {name}...")
    
    result = {
        "path": repo_path,
        "name": name,
        "status": "unknown",
        "current_branch": None,
        "behind": 0,
        "ahead": 0,
        "actions": []
    }
    
    # Check if it's a git repo
    stdout, code = run_cmd("git rev-parse --git-dir", repo_path)
    if code != 0:
        result["status"] = "not_a_git_repo"
        return result
    
    # Get current branch
    current_branch = get_active_branch(repo_path)
    result["current_branch"] = current_branch
    
    # Fetch first
    run_cmd("git fetch origin", repo_path)
    
    # Get behind/ahead
    behind, ahead = get_behind_ahead(repo_path)
    result["behind"] = behind
    result["ahead"] = ahead
    
    if behind > 0 or ahead > 0:
        print(f"[SYNC] {name}: behind={behind}, ahead={ahead}")
        
        # If we're on main and ahead, create intermediate branch
        if current_branch == "main" and ahead > 0:
            intermediate_branch = f"feat/sync-{name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Create intermediate branch
            run_cmd(f"git checkout -b {intermediate_branch}", repo_path)
            result["actions"].append(f"created_intermediate_branch:{intermediate_branch}")
            
            # Push intermediate branch
            push_result = subprocess.run(
                f'git push -u origin {intermediate_branch}',
                shell=True, cwd=repo_path, capture_output=True, text=True
            )
            
            if push_result.returncode == 0:
                result["actions"].append("pushed_intermediate_branch")

                # Create PR via GitHub API
                try:
                    url = f"https://api.github.com/repos/gerivdb/{name.split('/')[-1]}/pulls"
                    payload = {
                        "title": f"sync: {name} workspace sync",
                        "body": "Automated sync of {name} workspace files",
                        "head": intermediate_branch,
                        "base": "main",
                    }
                    pr_resp = requests.post(url, headers=_github_headers(), json=payload, timeout=30)
                    pr_resp.raise_for_status()
                    result["actions"].append("created_pr")
                except Exception as e:
                    result["actions"].append(f"pr_failed:{e}")
            else:
                result["actions"].append(f"push_failed:{push_result.stderr[:100]}")
            
            result["status"] = "needs_pr"
        elif behind > 0:
            # Pull remote changes
            pull_result = subprocess.run(
                f'git pull origin main',
                shell=True, cwd=repo_path, capture_output=True, text=True
            )
            
            if pull_result.returncode == 0:
                result["actions"].append("pulled_main")
                result["status"] = "synced"
            else:
                result["actions"].append(f"pull_failed:{pull_result.stderr[:100]}")
                result["status"] = "pull_failed"
        elif ahead > 0:
            # Need to create PR or stash
            result["status"] = "ahead_needs_action"
        else:
            result["status"] = "in_sync"
    else:
        result["status"] = "in_sync"
    
    return result

def run_ecosystem_sync():
    """Run full ecosystem sync"""
    print(f"[ECOSYNC] Starting ecosystem-wide sync at {datetime.now()}")
    
    repos = find_all_git_repos()
    print(f"[ECOSYNC] Found {len(repos)} git repositories")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "repos_scanned": len(repos),
        "results": []
    }
    
    for repo_path in repos:
        result = sync_repo(repo_path)
        report["results"].append(result)
    
    # Write report
    report_path = "D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\REPO-STANDARDS\\reports\\ecosystem_sync_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"[ECOSYNC] Report written to {report_path}")
    print(f"[ECOSYNC] Ecosystem sync complete")
    
    return report

if __name__ == "__main__":
    run_ecosystem_sync()