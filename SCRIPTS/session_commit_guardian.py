#!/usr/bin/env python3
"""
Session Commit Guardian - Détecte et traite les uncommitted changes
en fin de conversation KiloCode.
"""

import subprocess
import sys
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class RepoStatus:
    path: str
    name: str
    uncommitted: List[str]
    branches_to_merge: List[str]
    open_prs: List[int]
    error: Optional[str] = None

def load_active_repos(sot_path: str = "D:/DO/WEB/TOOLS/L1-INFRA/known_repositories.yaml") -> List[Dict]:
    """Charge les dépôts actifs depuis SOT."""
    try:
        with open(sot_path) as f:
            data = yaml.safe_load(f)
            return data.get('repositories', []) if isinstance(data, dict) else data
    except FileNotFoundError:
        return []

def check_repo_status(repo_path: str, repo_name: str) -> RepoStatus:
    """Vérifie le status git d'un dépôt."""
    result = RepoStatus(
        path=repo_path,
        name=repo_name,
        uncommitted=[],
        branches_to_merge=[],
        open_prs=[]
    )
    
    try:
        # Vérifier les uncommitted changes
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        if proc.stdout.strip():
            result.uncommitted = [
                line for line in proc.stdout.strip().split('\n') 
                if line.strip()
            ]
        
        # Vérifier les branches à merger
        proc = subprocess.run(
            ["git", "branch", "--merged"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        result.branches_to_merge = [
            b.strip().replace('* ', '') 
            for b in proc.stdout.split('\n') 
            if b.strip() and 'main' not in b and 'master' not in b
        ]
        
    except subprocess.TimeoutExpired:
        result.error = "Timeout lors de la vérification"
    except Exception as e:
        result.error = str(e)
    
    return result

def process_uncommitted(repo_status: RepoStatus, repo_info: Dict, dry_run: bool = False) -> str:
    """Traite les uncommitted changes."""
    if not repo_status.uncommitted:
        return "clean"
    
    # Déterminer le feat thématique
    repo_name = repo_info.get('full_name', repo_status.name).split('/')[-1]
    feat_name = f"feat/session-{repo_name}"
    
    if dry_run:
        return f"[DRY-RUN] uncommitted changes détectés, commit dans {feat_name}"
    
    try:
        # Commit atomique
        subprocess.run(["git", "add", "-A"], cwd=repo_status.path, check=True)
        
        subprocess.run([
            "git", "commit", "-m", 
            f"feat: session auto-commit\n\n{feat_name}"
        ], cwd=repo_status.path, check=True)
        
        return f"committed to {feat_name}"
    except subprocess.CalledProcessError as e:
        return f"error: {e}"
    except Exception as e:
        return f"error: {e}"

def scan_all_repos(dry_run: bool = False) -> List[Dict]:
    """Scanne tous les dépôts actifs."""
    repos = load_active_repos()
    results = []
    
    for repo in repos:
        repo_path = repo.get('local_path', '')
        if not repo_path or not Path(repo_path).exists():
            continue
        
        repo_name = repo.get('full_name', 'unknown')
        status = check_repo_status(repo_path, repo_name)
        action = process_uncommitted(status, repo, dry_run)
        
        results.append({
            'repo': repo_name,
            'path': repo_path,
            'uncommitted_count': len(status.uncommitted),
            'uncommitted': status.uncommitted[:5],  # Limité pour le rapport
            'branches_to_merge': status.branches_to_merge,
            'action': action,
            'error': status.error
        })
    
    return results

def main():
    """Point d'entrée principal."""
    dry_run = "--dry-run" in sys.argv
    
    print("[SESSION_COMMIT_GUARDIAN] Vérification des uncommitted changes...")
    
    results = scan_all_repos(dry_run)
    
    # Rapport
    print("\n[SESSION_COMMIT_GUARDIAN] Rapport de fin de session")
    print("=" * 60)
    
    clean_count = 0
    for r in results:
        status_icon = "[OK]" if r['action'] == "clean" else "[WARN]"
        print(f"  {status_icon} {r['repo']}: {r['action']}")
        if r['uncommitted_count'] > 0:
            print(f"      -> {r['uncommitted_count']} uncommitted changes")
        clean_count += 1 if r['action'] == "clean" else 0
    
    print("\n" + "=" * 60)
    print(f"[SESSION_COMMIT_GUARDIAN] Resume: {clean_count}/{len(results)} depot propres")
    
    # Retourner le code de sortie
    if all(r['action'] == "clean" for r in results):
        print("[SESSION_COMMIT_GUARDIAN] [OK] Session clean")
        return 0
    else:
        print("[SESSION_COMMIT_GUARDIAN] [WARN] Des uncommitted changes restent")
        return 1

if __name__ == "__main__":
    sys.exit(main())