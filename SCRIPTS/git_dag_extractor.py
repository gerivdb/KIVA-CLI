#!/usr/bin/env python3
"""
Git DAG Extractor - Extraction Git -> DAG pour CI/CD.

Ce script extrait les donnees Git d'un depot et les convertit en
graphe DAG (Directed Acyclic Graph) pour l'analyse de dependances.

Usage:
    python scripts/git_dag_extractor.py --repo <path> --output <file.json>

Refs: ADR-001, ADR-002, ADR-004
IntentHash: 0xGIT_DAG_EXTRACTOR_20260707
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class GitCommit:
    """Commit Git represente comme noeud DAG."""
    sha: str
    message: str
    author: str
    date: str
    parents: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)


@dataclass
class GitDAG:
    """Graphe DAG des commits Git."""
    commits: Dict[str, GitCommit] = field(default_factory=dict)
    branches: Dict[str, List[str]] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    root_commits: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "commits": {k: asdict(v) for k, v in self.commits.items()},
            "branches": self.branches,
            "tags": self.tags,
            "root_commits": self.root_commits,
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_commits": len(self.commits),
                "total_branches": len(self.branches),
            }
        }


def run_git_command(args: List[str], cwd: Optional[Path] = None) -> str:
    """Execute une commande Git et retourne la sortie."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=cwd
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {result.stderr}")
    return result.stdout.strip()


def extract_commits(repo_path: Path) -> GitDAG:
    """Extrait le DAG des commits d'un depot Git."""
    dag = GitDAG()
    
    # Recuperer tous les commits avec leurs parents
    log_output = run_git_command(
        ["log", "--all", "--pretty=format:%H|%s|%an|%ad|%P", "--date=iso"],
        cwd=repo_path
    )
    
    for line in log_output.split("\n"):
        if not line:
            continue
        
        parts = line.split("|")
        if len(parts) < 4:
            continue
        
        sha, message, author, date = parts[0], parts[1], parts[2], parts[3]
        parents = parts[4].split() if len(parts) > 4 else []
        
        commit = GitCommit(
            sha=sha,
            message=message,
            author=author,
            date=date,
            parents=parents
        )
        dag.commits[sha] = commit
        
        # Construire les relations enfant
        for parent in parents:
            if parent in dag.commits:
                dag.commits[parent].children.append(sha)
    
    # Identifier les commits racines (pas de parents)
    dag.root_commits = [
        sha for sha, commit in dag.commits.items()
        if not commit.parents
    ]
    
    # Recuperer les branches
    branches_output = run_git_command(["branch", "-a", "--format=%(refname:short)"], cwd=repo_path)
    for branch in branches_output.split("\n"):
        if not branch:
            continue
        branch_name = branch.replace("remotes/", "")
        if branch_name not in dag.branches:
            dag.branches[branch_name] = []
    
    # Recuperer les tags
    tags_output = run_git_command(["tag", "-l"], cwd=repo_path)
    for tag in tags_output.split("\n"):
        if not tag:
            continue
        try:
            tag_sha = run_git_command(["rev-parse", tag], cwd=repo_path)
            dag.tags[tag] = tag_sha
            if tag_sha in dag.commits:
                dag.commits[tag_sha].message = f"[tag: {tag}] {dag.commits[tag_sha].message}"
        except RuntimeError:
            pass
    
    return dag


def main():
    parser = argparse.ArgumentParser(description="Git DAG Extractor")
    parser.add_argument("--repo", required=True, help="Path to Git repository")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()
    
    repo_path = Path(args.repo)
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        return 1
    
    try:
        dag = extract_commits(repo_path)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dag.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"[OK] DAG extrait: {len(dag.commits)} commits, {len(dag.branches)} branches, {len(dag.tags)} tags")
        print(f"[OK] Sauvegarde dans: {output_path}")
        return 0
        
    except Exception as e:
        print(f"[ERR] Erreur: {e}")
        return 1


if __name__ == "__main__":
    exit(main())