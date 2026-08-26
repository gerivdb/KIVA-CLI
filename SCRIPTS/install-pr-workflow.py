#!/usr/bin/env python3
"""
Install PR merge workflow components into target repositories.

This script installs:
- .githooks/pre-push (with PR reminder + auto-merge orchestrator via KIVA-CLI)
- .github/workflows/pr-lifecycle-gate.yml (branch audit, deprecated, kept for compat only)
- scripts/pr-auto-merge-orchestrator.py (v2.0, KIVA-CLI aware)
- scripts/conflict_resolver_engine.py (v2.0)

Note: GitHub Actions is NOT used in gerivdb ecosystem. CI is local via KIVA-CLI only.
The .github/workflows/pr-lifecycle-gate.yml file is kept for compatibility but
should NOT be enabled by default.

Usage:
    python install-pr-workflow.py --repo <path> [--repo <path> ...]
    python install-pr-workflow.py --all-active-repos

Version: 1.0.0
Date: 2026-07-14
IntentHash: 0xINSTALL_PR_WORKFLOW_20260714
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Paths relative to REPO-STANDARDS
REPO_STANDARDS_ROOT = Path(__file__).parent.parent

HOOK_SOURCE = REPO_STANDARDS_ROOT / ".githooks" / "pre-push"
WORKFLOW_SOURCE = REPO_STANDARDS_ROOT / ".github" / "workflows" / "pr-lifecycle-gate.yml"
ORCHESTRATOR_SOURCE = REPO_STANDARDS_ROOT / "scripts" / "pr-auto-merge-orchestrator.py"
CONFLICT_RESOLVER_SOURCE = REPO_STANDARDS_ROOT / "scripts" / "conflict_resolver_engine.py"


def run_cmd(cmd: str, cwd: Optional[Path] = None) -> tuple[str, int]:
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def install_hook(repo_path: Path) -> bool:
    """Install pre-push hook into target repo"""
    if not HOOK_SOURCE.exists():
        print(f"[ERROR] Hook source not found: {HOOK_SOURCE}")
        return False
    
    hook_target = repo_path / ".githooks" / "pre-push"
    hook_target.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(HOOK_SOURCE, hook_target)
    
    # Make executable on Unix-like systems
    if sys.platform != "win32":
        os.chmod(hook_target, 0o755)
    
    print(f"[OK] Hook installed: {hook_target}")
    return True


def install_workflow(repo_path: Path) -> bool:
    """Install GitHub Action workflow into target repo"""
    if not WORKFLOW_SOURCE.exists():
        print(f"[ERROR] Workflow source not found: {WORKFLOW_SOURCE}")
        return False
    
    workflow_target = repo_path / ".github" / "workflows" / "pr-lifecycle-gate.yml"
    workflow_target.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(WORKFLOW_SOURCE, workflow_target)
    
    print(f"[OK] Workflow installed: {workflow_target}")
    return True


def install_scripts(repo_path: Path) -> bool:
    """Install automation scripts into target repo"""
    scripts = [
        (ORCHESTRATOR_SOURCE, "scripts/pr-auto-merge-orchestrator.py"),
        (CONFLICT_RESOLVER_SOURCE, "scripts/conflict_resolver_engine.py"),
    ]
    
    all_ok = True
    for source, relative_target in scripts:
        if not source.exists():
            print(f"[ERROR] Script source not found: {source}")
            all_ok = False
            continue
        
        target = repo_path / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        print(f"[OK] Script installed: {target}")
    
    return all_ok


def install_all(repo_path: Path) -> bool:
    """Install all PR workflow components into target repo"""
    print(f"\n[INSTALL] Installing PR workflow into: {repo_path}")
    
    if not repo_path.exists() or not (repo_path / ".git").exists():
        print(f"[ERROR] Not a git repository: {repo_path}")
        return False
    
    results = [
        install_hook(repo_path),
        install_workflow(repo_path),
        install_scripts(repo_path),
    ]
    
    if all(results):
        print(f"[OK] PR workflow installed successfully in {repo_path}")
        return True
    else:
        print(f"[WARN] Partial installation in {repo_path}")
        return False


def get_active_repos_from_ecos_root() -> List[Path]:
    """Get list of active repos from ECOS_ROOT.json"""
    ecos_root_path = REPO_STANDARDS_ROOT / "ECOS_ROOT.json"
    
    if not ecos_root_path.exists():
        print(f"[ERROR] ECOS_ROOT.json not found: {ecos_root_path}")
        return []
    
    try:
        with open(ecos_root_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse ECOS_ROOT.json: {e}")
        return []
    
    repos = []
    repos_data = data.get('repos', {})
    
    for repo_name, repo_info in repos_data.items():
        # Skip archived repos
        if repo_info.get('archived', False):
            continue
        
        # Get local path
        local_path = repo_info.get('path')
        if not local_path:
            continue
        
        path = Path(local_path)
        if path.exists() and (path / '.git').exists():
            repos.append(path)
        else:
            print(f"[WARN] Repo path not found or not a git repo: {path}")
    
    return repos


def main():
    parser = argparse.ArgumentParser(description="Install PR merge workflow into repos")
    parser.add_argument("--repo", action='append', help="Target repo path (can be repeated)")
    parser.add_argument("--all-active-repos", action='store_true', help="Install in all active repos from ECOS_ROOT.json")
    args = parser.parse_args()
    
    repos = []
    
    if args.all_active_repos:
        repos = get_active_repos_from_ecos_root()
        print(f"[INSTALL] Found {len(repos)} active repos from ECOS_ROOT.json")
    elif args.repo:
        repos = [Path(r) for r in args.repo]
    else:
        # Default: current directory
        repos = [Path.cwd()]
    
    if not repos:
        print("[ERROR] No repos to install into")
        sys.exit(1)
    
    success_count = 0
    for repo_path in repos:
        if install_all(repo_path):
            success_count += 1
    
    print(f"\n[INSTALL] Summary: {success_count}/{len(repos)} repos installed successfully")
    
    if success_count < len(repos):
        sys.exit(1)


if __name__ == "__main__":
    main()
