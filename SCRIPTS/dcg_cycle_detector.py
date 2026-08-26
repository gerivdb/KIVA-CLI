#!/usr/bin/env python3
"""
DCG Cycle Detector - Detection de cycles dans les Directed Cyclic Graphs.

Ce script analyse un DAG Git et deteche les cycles implicites ou explicites
dans les dependances (DCG - Directed Cyclic Graph).

Usage:
    python scripts/dcg_cycle_detector.py --dag <dag.json> --output <cycles.json>

Refs: ADR-001, ADR-003, EPIC-192
IntentHash: 0xDCG_CYCLE_DETECTOR_20260707
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple


@dataclass
class Cycle:
    """Cycle detecte dans un DCG."""
    cycle_id: str
    commits: List[str]
    length: int
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    detected_at: str
    description: str = ""


@dataclass
class DCGAnalysis:
    """Resultat de l'analyse DCG."""
    cycles: List[Cycle] = field(default_factory=list)
    total_commits: int = 0
    total_cycles: int = 0
    cycle_density: float = 0.0
    feedback_loops: List[List[str]] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "cycles": [asdict(c) for c in self.cycles],
            "total_commits": self.total_commits,
            "total_cycles": self.total_cycles,
            "cycle_density": self.cycle_density,
            "feedback_loops": self.feedback_loops,
            "metadata": self.metadata
        }


def load_dag(dag_path: Path) -> dict:
    """Charge le DAG depuis un fichier JSON."""
    with open(dag_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_adjacency_list(dag: dict) -> Dict[str, Set[str]]:
    """Construit la liste d'adjacence du graphe."""
    adj = defaultdict(set)
    
    for sha, commit in dag.get("commits", {}).items():
        for parent in commit.get("parents", []):
            adj[parent].add(sha)
        for child in commit.get("children", []):
            adj[sha].add(child)
    
    return adj


def detect_cycles_tarjan(adj: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Detecte les cycles en utilisant l'algorithme de Tarjan.
    Retourne les cycles trouves.
    """
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = {}
    sccs = []
    
    def strongconnect(node):
        index[node] = index_counter[0]
        lowlink[node] = index_counter[0]
        index_counter[0] += 1
        stack.append(node)
        on_stack[node] = True
        
        for successor in adj.get(node, set()):
            if successor not in index:
                strongconnect(successor)
                lowlink[node] = min(lowlink[node], lowlink[successor])
            elif on_stack.get(successor, False):
                lowlink[node] = min(lowlink[node], index[successor])
        
        if lowlink[node] == index[node]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == node:
                    break
            if len(scc) > 1:
                sccs.append(scc)
    
    for node in adj:
        if node not in index:
            strongconnect(node)
    
    return sccs


def detect_cycles_dfs(adj: Dict[str, Set[str]]) -> List[List[str]]:
    """
    Detecte les cycles en utilisant DFS.
    Alternative a Tarjan pour de petits graphes.
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in adj.get(node, set()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Cycle detecte
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
        
        path.pop()
        rec_stack.remove(node)
    
    for node in adj:
        if node not in visited:
            dfs(node)
    
    return cycles


def analyze_cycles(cycles: List[List[str]], dag: dict) -> DCGAnalysis:
    """Analyse les cycles et classe leur severite."""
    analysis = DCGAnalysis()
    analysis.total_commits = len(dag.get("commits", {}))
    analysis.total_cycles = len(cycles)
    
    if analysis.total_commits > 0:
        analysis.cycle_density = analysis.total_cycles / analysis.total_commits
    
    for i, cycle in enumerate(cycles):
        # Determiner la severite
        if len(cycle) > 5:
            severity = "CRITICAL"
        elif len(cycle) > 3:
            severity = "HIGH"
        elif len(cycle) > 2:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        # Extraire les messages de commits pour la description
        commit_info = []
        for sha in cycle[:-1]:  # Dernier est le doublon
            commit = dag.get("commits", {}).get(sha, {})
            msg = commit.get("message", sha[:8])[:50]
            commit_info.append(f"{sha[:8]}: {msg}")
        
        cycle_obj = Cycle(
            cycle_id=f"cycle_{i+1:03d}",
            commits=cycle[:-1],
            length=len(cycle) - 1,
            severity=severity,
            detected_at=datetime.now().isoformat(),
            description=" -> ".join(commit_info)
        )
        analysis.cycles.append(cycle_obj)
    
    # Identifier les feedback loops (cycles > 3)
    analysis.feedback_loops = [
        c[:-1] for c in cycles if len(c) > 3
    ]
    
    analysis.metadata = {
        "algorithm": "tarjan_scc",
        "version": "1.0",
        "generated_at": datetime.now().isoformat()
    }
    
    return analysis


def main():
    parser = argparse.ArgumentParser(description="DCG Cycle Detector")
    parser.add_argument("--dag", required=True, help="Path to DAG JSON file")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--method", default="tarjan", choices=["tarjan", "dfs"],
                        help="Detection algorithm (default: tarjan)")
    args = parser.parse_args()
    
    dag_path = Path(args.dag)
    if not dag_path.exists():
        print(f"Error: DAG file does not exist: {dag_path}")
        return 1
    
    try:
        dag = load_dag(dag_path)
        adj = build_adjacency_list(dag)
        
        if args.method == "tarjan":
            cycles = detect_cycles_tarjan(adj)
        else:
            cycles = detect_cycles_dfs(adj)
        
        analysis = analyze_cycles(cycles, dag)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Analyse DCG terminee:")
        print(f"   - Cycles detects: {analysis.total_cycles}")
        print(f"   - Densite cyclique: {analysis.cycle_density:.4f}")
        print(f"   - Feedback loops: {len(analysis.feedback_loops)}")
        print(f"[OK] Sauvegarde dans: {output_path}")
        return 0
        
    except Exception as e:
        print(f"[ERR] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())