#!/usr/bin/env python3
"""
Ecosystem Maintenance Daemon
Automated maintenance for multi-repo ecosystem with TRASH management
"""

import subprocess
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

# Valid strata directories
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

# TRASH directory
TRASH_DIR = "D:\\DO\\WEB\\TOOLS\\.TRASH"

def run_cmd(cmd, cwd=None):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode

def is_valid_stratum(path):
    """Check if path is within a valid stratum"""
    for stratum in VALID_STRATES:
        if path.startswith(stratum):
            return True
    return False

def diff_repo_contents(repo_path, canonique_path):
    """Compare contents of illegitimate repo with canonical"""
    if not os.path.exists(repo_path):
        return {"status": "not_found", "files": []}
    
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        for filename in filenames:
            filepath = os.path.join(root, filename)
            relpath = os.path.relpath(filepath, repo_path)
            files.append(relpath)
    
    return {
        "status": "found",
        "path": repo_path,
        "file_count": len(files),
        "files": files[:50]
    }

def find_illegitimate_clones(base_path):
    """Find git repos outside valid strata"""
    illegitimate = []
    
    if os.path.exists(base_path):
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                if not is_valid_stratum(item_path):
                    git_dir = os.path.join(item_path, ".git")
                    if os.path.exists(git_dir):
                        diff_result = diff_repo_contents(item_path, None)
                        illegitimate.append({
                            "path": item_path,
                            "name": item,
                            "type": "git_repo_outside_stratum",
                            "diff": diff_result
                        })
    
    return illegitimate

def find_orphan_branches(repo_path):
    """Find branches without PRs"""
    branches = []
    stdout, code = run_cmd("git branch", repo_path)
    for line in stdout.split('\n'):
        line = line.strip()
        if line.startswith('*'):
            line = line[1:].strip()
        if line in ['main', 'master', 'HEAD', '']:
            continue
        if line and not line.startswith('origin/'):
            branch_name = line.strip()
            stdout2, _ = run_cmd(f"gh pr list --head {branch_name} --state open --json number --repo gerivdb/REPO-STANDARDS", repo_path)
            if '[]' in stdout2:
                branches.append(branch_name)
    return branches

def find_untracked_files(repo_path):
    """Find untracked files"""
    stdout, code = run_cmd("git status --porcelain", repo_path)
    untracked = []
    for line in stdout.split('\n'):
        if line.startswith('??'):
            filepath = line[2:].strip()
            untracked.append(filepath)
    return untracked

def move_to_trash(item_path, item_name, reason):
    """Move item to TRASH directory with metadata"""
    os.makedirs(TRASH_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trash_name = f"{timestamp}_{item_name}"
    trash_path = os.path.join(TRASH_DIR, trash_name)
    
    metadata = {
        "original_path": item_path,
        "original_name": item_name,
        "moved_at": datetime.now().isoformat(),
        "reason": reason,
        "status": "pending_review"
    }
    
    try:
        shutil.copytree(item_path, trash_path)
        with open(os.path.join(trash_path, ".trash_metadata.json"), 'w') as f:
            json.dump(metadata, f, indent=2)
        return {"success": True, "trash_path": trash_path, "metadata": metadata}
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_intermediate_branch_and_merge(repo_path, branch_name, commit_message=""):
    """Create intermediate feat branch for commits that need PR merge"""
    print(f"[MAINTENANCE] Creating intermediate branch for {branch_name}")
    
    result = subprocess.run(
        f'git checkout -b feat/maintenance-{branch_name}-intermediate',
        shell=True, cwd=repo_path, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"[MAINTENANCE] Failed to create branch: {result.stderr}")
        return False
    
    subprocess.run('git add .', shell=True, cwd=repo_path, capture_output=True, text=True)
    
    result = subprocess.run(f'git status --porcelain', shell=True, cwd=repo_path, capture_output=True, text=True)
    
    if result.stdout.strip():
        subprocess.run(f'git commit -m "{commit_message}"', shell=True, cwd=repo_path, capture_output=True, text=True)
    
    subprocess.run(f'git push -u origin HEAD', shell=True, cwd=repo_path, capture_output=True, text=True)
    
    print(f"[MAINTENANCE] Intermediate branch created")
    return True

def run_maintenance():
    """Run full ecosystem maintenance"""
    print(f"[MAINTENANCE] Starting ecosystem maintenance at {datetime.now()}")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "illegitimate_clones": [],
        "orphan_branches": {},
        "untracked_files": {},
        "trash_operations": [],
        "intermediate_branches": [],
        "merge_failures": [],
        "actions_taken": []
    }
    
    print("[MAINTENANCE] Scanning for illegitimate clones...")
    illegitimate = find_illegitimate_clones("D:\\DO\\WEB\\TOOLS")
    report["illegitimate_clones"] = illegitimate
    
    for clone in illegitimate:
        print(f"[MAINTENANCE] Found illegitimate clone: {clone['path']}")
        result = move_to_trash(clone["path"], clone["name"], "illegitimate_clone_outside_stratum")
        report["trash_operations"].append(result)
    
    print("[MAINTENANCE] Checking REPO-STANDARDS for orphan branches...")
    orphans = find_orphan_branches("D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\REPO-STANDARDS")
    if orphans:
        report["orphan_branches"]["REPO-STANDARDS"] = orphans
        print(f"[MAINTENANCE] Found {len(orphans)} orphan branches")
    
    print("[MAINTENANCE] Checking for untracked files...")
    untracked = find_untracked_files("D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\REPO-STANDARDS")
    if untracked:
        report["untracked_files"]["REPO-STANDARDS"] = untracked[:20]
        print(f"[MAINTENANCE] Found {len(untracked)} untracked files")
    
    if untracked:
        print("[MAINTENANCE] Creating intermediate branch for untracked files...")
        create_intermediate_branch_and_merge(
            "D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\REPO-STANDARDS",
            "untracked-files",
            "chore: add untracked files from maintenance scan"
        )
        report["intermediate_branches"].append("untracked-files")
    
    report_path = "D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\REPO-STANDARDS\\reports\\maintenance_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"[MAINTENANCE] Report written to {report_path}")
    print(f"[MAINTENANCE] Maintenance complete")
    
    return report

if __name__ == "__main__":
    run_maintenance()