#!/usr/bin/env python3
"""
Fragility Scorer - Evaluation de la fragilite des depots Git.

Ce script calcule un score de fragilite base sur :
- Densite de cycles (DCG)
- Complexite des branches
- Nombre de commits recents
- Ratio de modifications par fichier

Usage:
    python scripts/fragility_scorer.py --dag <dag.json> --cycles <cycles.json> --output <score.json>

Refs: ADR-005, ADR-007
IntentHash: 0xFRAGILITY_SCORER_20260707
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class FragilityMetrics:
    """Metriques de fragilite d'un depot."""
    score: float = 0.0  # 0-100
    grade: str = "A"    # A, B, C, D, E
    factors: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class FragilityAnalysis:
    """Resultat complet d'analyse de fragilite."""
    repo_name: str
    metrics: FragilityMetrics
    cycle_density: float
    branch_complexity: float
    commit_frequency: float
    file_churn: float
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "metrics": asdict(self.metrics),
            "cycle_density": self.cycle_density,
            "branch_complexity": self.branch_complexity,
            "commit_frequency": self.commit_frequency,
            "file_churn": self.file_churn,
            "metadata": self.metadata
        }


def load_json(path: Path) -> dict:
    """Charge un fichier JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_cycle_factor(cycle_density: float) -> Tuple[float, str]:
    """Calcule le facteur de fragilite lie aux cycles."""
    if cycle_density == 0:
        return 0.0, "Aucun cycle detecte"
    elif cycle_density < 0.01:
        return 5.0, "Faible densite cyclique"
    elif cycle_density < 0.05:
        return 15.0, "Densite cyclique moderee"
    elif cycle_density < 0.1:
        return 30.0, "Densite cyclique elevee"
    else:
        return 50.0, "Densite cyclique critique"


def calculate_branch_factor(dag: dict, cycles: dict) -> Tuple[float, str]:
    """Calcule le facteur de complexite des branches."""
    branches = dag.get("branches", {})
    active_branches = [b for b in branches if not b.startswith("remotes/")]
    
    branch_count = len(active_branches)
    cycle_count = len(cycles.get("cycles", []))
    
    # Complexite = nombre de branches + cycles
    complexity = branch_count + cycle_count * 0.5
    
    if complexity < 3:
        return 0.0, "Faible complexite de branche"
    elif complexity < 10:
        return 5.0, "Complexite moderee"
    elif complexity < 20:
        return 15.0, "Complexite elevee"
    else:
        return 30.0, "Complexite critique"


def calculate_commit_frequency(dag: dict, days: int = 30) -> Tuple[float, str]:
    """Calcule la frequence de commits recents."""
    commits = dag.get("commits", {})
    recent_commits = 0
    cutoff = datetime.now() - timedelta(days=days)
    
    for commit in commits.values():
        try:
            commit_date = datetime.fromisoformat(commit.get("date", "").replace("Z", "+00:00"))
            if commit_date > cutoff:
                recent_commits += 1
        except (ValueError, TypeError):
            continue
    
    frequency = recent_commits / days
    
    if frequency < 0.5:
        return 0.0, "Frequence de commits faible"
    elif frequency < 2.0:
        return 5.0, "Frequence de commits moderee"
    elif frequency < 5.0:
        return 10.0, "Frequence de commits elevee"
    else:
        return 20.0, "Frequence de commits tres elevee (risque de fragilite)"


def calculate_file_churn(dag: dict) -> Tuple[float, str]:
    """Calcule le churn de fichiers (approximation)."""
    # Approximation: ratio commits/fichiers base sur la longueur du message
    total_commits = len(dag.get("commits", {}))
    
    # Estimation: plus les messages sont courts, plus le churn est eleve
    short_messages = 0
    for commit in dag.get("commits", {}).values():
        msg = commit.get("message", "")
        if len(msg) < 50:
            short_messages += 1
    
    churn_ratio = short_messages / max(total_commits, 1) if total_commits > 0 else 0
    
    if churn_ratio < 0.3:
        return 0.0, "Churn de fichiers faible"
    elif churn_ratio < 0.6:
        return 10.0, "Churn modere"
    else:
        return 25.0, "Churn eleve (risque de fragilite)"


def compute_grade(score: float) -> str:
    """Convertit le score en grade (A-E)."""
    if score < 10:
        return "A"
    elif score < 25:
        return "B"
    elif score < 45:
        return "C"
    elif score < 70:
        return "D"
    else:
        return "E"


def generate_recommendations(factors: Dict[str, float], score: float) -> List[str]:
    """Genere des recommandations basees sur les facteurs."""
    recommendations = []
    
    if score >= 70:
        recommendations.append("[WARN] ACTION URGENTE: Reducir la complexite du depot")
    
    if factors.get("cycle_density", 0) > 30:
        recommendations.append("- Identifier et resoudre les cycles critiques")
        recommendations.append("- Utiliser des outils de detection de dependances")
    
    if factors.get("branch_complexity", 0) > 15:
        recommendations.append("- Nettoyer les branches inactives")
        recommendations.append("- Renforcer la revue de code PR")
    
    if factors.get("commit_frequency", 0) > 10:
        recommendations.append("- Surveiller la charge de travail")
        recommendations.append("- Documenter les changements majeurs")
    
    if factors.get("file_churn", 0) > 20:
        recommendations.append("- Ameliorer la stabilite des interfaces")
        recommendations.append("- Ajouter des tests de regression")
    
    if not recommendations:
        recommendations.append("[OK] Le depot est bien maintenu")
    
    return recommendations


def analyze_fragility(repo_name: str, dag: dict, cycles: dict) -> FragilityAnalysis:
    """Effectue l'analyse complete de fragilite."""
    # Calculer les facteurs
    cycle_factor, _ = calculate_cycle_factor(cycles.get("cycle_density", 0))
    branch_factor, _ = calculate_branch_factor(dag, cycles)
    commit_factor, _ = calculate_commit_frequency(dag)
    churn_factor, _ = calculate_file_churn(dag)
    
    factors = {
        "cycle_density": cycle_factor,
        "branch_complexity": branch_factor,
        "commit_frequency": commit_factor,
        "file_churn": churn_factor
    }
    
    # Score total (0-100)
    score = min(100, sum(factors.values()))
    
    metrics = FragilityMetrics(
        score=score,
        grade=compute_grade(score),
        factors=factors,
        recommendations=generate_recommendations(factors, score)
    )
    
    return FragilityAnalysis(
        repo_name=repo_name,
        metrics=metrics,
        cycle_density=cycles.get("cycle_density", 0),
        branch_complexity=len(dag.get("branches", {})),
        commit_frequency=sum(factors.values()) / 4,  # Approximation
        file_churn=churn_factor,
        metadata={
            "generated_at": datetime.now().isoformat(),
            "analysis_version": "1.0"
        }
    )


def main():
    parser = argparse.ArgumentParser(description="Fragility Scorer")
    parser.add_argument("--dag", required=True, help="Path to DAG JSON file")
    parser.add_argument("--cycles", required=True, help="Path to cycles JSON file")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--repo", default="unknown", help="Repository name")
    args = parser.parse_args()
    
    try:
        dag = load_json(Path(args.dag))
        cycles = load_json(Path(args.cycles))
        
        analysis = analyze_fragility(args.repo, dag, cycles)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analysis.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Analyse de fragilite terminee:")
        print(f"   - Score: {analysis.metrics.score:.1f}/100")
        print(f"   - Grade: {analysis.metrics.grade}")
        print(f"   - Recommandations: {len(analysis.metrics.recommendations)}")
        print(f"[OK] Sauvegarde dans: {output_path}")
        return 0
        
    except Exception as e:
        print(f"[ERR] Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())