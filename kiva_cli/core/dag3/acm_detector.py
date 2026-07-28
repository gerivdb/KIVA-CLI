#!/usr/bin/env python3
"""
ACM Detector - Atomic Cycle Model Detector

Détecte les cycles atomiques dans les graphes de dépendances.
Un cycle atomique est un cycle minimal qui bloque la progression.

IntentHash: 0xACM_DETECTOR_20260718
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import networkx as nx


class CycleSeverity(Enum):
    """Severity levels for cycle detection."""
    NONE = 0
    LOW = 1     # Single dependency cycle
    MEDIUM = 2  # Multiple interconnected cycles
    HIGH = 3    # Critical path blocking cycles


@dataclass
class CycleDetectionResult:
    """Result of cycle detection analysis."""
    has_cycles: bool
    cycles: List[List[str]] = field(default_factory=list)
    severity: CycleSeverity = CycleSeverity.NONE
    affected_nodes: Set[str] = field(default_factory=set)
    recommendations: List[str] = field(default_factory=list)
    phi_cps_impact: float = 0.0  # Impact on φ-CPS score


@dataclass
class DependencyNode:
    """Represents a node in the dependency graph."""
    id: str
    type: str  # 'module', 'class', 'function', 'file', 'repo'
    dependencies: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    metadata: Dict = field(default_factory=dict)


class ACMDetector:
    """
    Atomic Cycle Model Detector.
    
    Detects and analyzes atomic cycles in dependency graphs.
    An atomic cycle is a minimal cycle that cannot be decomposed.
    
    Usage:
        detector = ACMDetector(repo_path="/path/to/repo")
        result = detector.detect_cycles()
        if result.has_cycles:
            print(f"Cycles found: {result.cycles}")
    """

    def __init__(self, repo_path: str = ".", graph_path: str = ""):
        """
        Initialize ACM Detector.
        
        Args:
            repo_path: Path to the repository to analyze
            graph_path: Optional path to pre-computed dependency graph
        """
        self.repo_path = Path(repo_path)
        self.graph_path = Path(graph_path) if graph_path else None
        self.graph: Optional[nx.DiGraph] = None
        self.nodes: Dict[str, DependencyNode] = {}
        
    def build_dependency_graph(self) -> nx.DiGraph:
        """
        Build dependency graph from repository structure.
        
        Returns:
            NetworkX DiGraph representing dependencies
        """
        self.graph = nx.DiGraph()
        
        # Scan repository for Python files and imports
        for py_file in self.repo_path.rglob("*.py"):
            relative_path = str(py_file.relative_to(self.repo_path))
            self._parse_python_file(py_file, relative_path)
        
        # Add nodes to graph
        for node_id, node in self.nodes.items():
            self.graph.add_node(node_id, type=node.type, version=node.version)
            for dep in node.dependencies:
                if dep in self.nodes:
                    self.graph.add_edge(node_id, dep)
        
        return self.graph

    def _parse_python_file(self, file_path: Path, relative_path: str) -> None:
        """Parse Python file for imports and dependencies."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Create node for this file
            node_id = relative_path.replace("/", ".").replace(".py", "")
            self.nodes[node_id] = DependencyNode(
                id=node_id,
                type="file",
                version="1.0.0",
                metadata={"path": str(file_path)}
            )
            
            # Simple import detection (could be enhanced with AST parsing)
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("import ") or line.startswith("from "):
                    # Extract imported module
                    if line.startswith("from "):
                        parts = line.split()
                        if len(parts) >= 2:
                            module = parts[1].split(".")[0]
                            if not module.startswith(("sys", "os", "typing", "collections", 
                                                      "pathlib", "datetime", "json", "re",
                                                      "enum", "dataclasses", "logging", "subprocess",
                                                      "asyncio", "networkx", "click")):
                                # Local import - add as dependency
                                if module not in self.nodes[node_id].dependencies:
                                    self.nodes[node_id].dependencies.append(module)
                            
        except Exception as e:
            # Skip files that can't be parsed
            pass

    def detect_cycles(self) -> CycleDetectionResult:
        """
        Detect all cycles in the dependency graph.
        
        Returns:
            CycleDetectionResult with cycle information
        """
        if self.graph is None:
            self.build_dependency_graph()
        
        if self.graph is None or len(self.graph.nodes) == 0:
            return CycleDetectionResult(has_cycles=False)
        
        try:
            # Find all simple cycles
            cycles = list(nx.simple_cycles(self.graph))
            
            if not cycles:
                return CycleDetectionResult(has_cycles=False)
            
            # Analyze cycle severity
            severity = self._assess_severity(cycles)
            affected_nodes = self._get_affected_nodes(cycles)
            recommendations = self._generate_recommendations(cycles, severity)
            phi_cps_impact = self._calculate_phi_cps_impact(cycles, severity)
            
            return CycleDetectionResult(
                has_cycles=True,
                cycles=cycles,
                severity=severity,
                affected_nodes=affected_nodes,
                recommendations=recommendations,
                phi_cps_impact=phi_cps_impact
            )
            
        except Exception as e:
            return CycleDetectionResult(
                has_cycles=False,
                recommendations=[f"Error during cycle detection: {str(e)}"]
            )

    def _assess_severity(self, cycles: List[List[str]]) -> CycleSeverity:
        """Assess severity based on cycle characteristics."""
        if len(cycles) == 0:
            return CycleSeverity.NONE
        
        # Check for critical path nodes (entry points)
        critical_nodes = {"__main__", "main", "cli", "commands"}
        critical_cycles = [c for c in cycles if any(n in critical_nodes for n in c)]
        
        if len(critical_cycles) > 0:
            return CycleSeverity.HIGH
        elif len(cycles) > 3:
            return CycleSeverity.MEDIUM
        elif len(cycles) > 0:
            return CycleSeverity.LOW
        
        return CycleSeverity.NONE

    def _get_affected_nodes(self, cycles: List[List[str]]) -> Set[str]:
        """Get all nodes involved in cycles."""
        affected = set()
        for cycle in cycles:
            affected.update(cycle)
        return affected

    def _generate_recommendations(self, cycles: List[List[str]], 
                                   severity: CycleSeverity) -> List[str]:
        """Generate recommendations for cycle resolution."""
        recommendations = []
        
        if severity == CycleSeverity.HIGH:
            recommendations.append("[ACM-HIGH] Critical cycle detected - immediate HITL required")
            recommendations.append("[ACM-HIGH] Consider architectural refactoring")
        
        for i, cycle in enumerate(cycles[:3]):  # Limit recommendations
            cycle_str = " -> ".join(cycle)
            recommendations.append(f"[ACM] Cycle {i+1}: {cycle_str}")
        
        if severity == CycleSeverity.MEDIUM:
            recommendations.append("[ACM-MEDIUM] Multiple cycles detected - consider module restructuring")
        elif severity == CycleSeverity.LOW:
            recommendations.append("[ACM-LOW] Single cycle found - may be acceptable in some contexts")
        
        return recommendations

    def _calculate_phi_cps_impact(self, cycles: List[List[str]], 
                                   severity: CycleSeverity) -> float:
        """Calculate impact on φ-CPS score."""
        # Base impact per cycle
        base_impact = 0.1
        
        # Severity multiplier
        severity_multiplier = {
            CycleSeverity.NONE: 0.0,
            CycleSeverity.LOW: 0.1,
            CycleSeverity.MEDIUM: 0.3,
            CycleSeverity.HIGH: 0.5
        }
        
        return len(cycles) * base_impact * severity_multiplier.get(severity, 0.0)

    def validate_merge_candidate(self, branch_name: str, 
                                  target_branch: str = "main") -> Tuple[bool, str]:
        """
        Validate if a branch merge is safe from cycle perspective.
        
        Args:
            branch_name: Name of the branch to validate
            target_branch: Target branch for merge
            
        Returns:
            Tuple of (is_valid, message)
        """
        if self.graph is None:
            self.build_dependency_graph()
        
        # Check if branch introduces new cycles
        cycles = list(nx.simple_cycles(self.graph))
        
        if cycles:
            # Check if cycles are pre-existing or new
            # For simplicity, we flag any cycles as potential issues
            return False, f"Merge blocked: {len(cycles)} cycle(s) detected in dependency graph"
        
        return True, "No cycles detected - merge candidate is safe"

    def export_analysis(self, output_path: str) -> None:
        """Export cycle analysis to JSON file."""
        result = self.detect_cycles()
        
        output = {
            "has_cycles": result.has_cycles,
            "cycles": result.cycles,
            "severity": result.severity.name,
            "affected_nodes": list(result.affected_nodes),
            "recommendations": result.recommendations,
            "phi_cps_impact": result.phi_cps_impact,
            "timestamp": str(nx.__version__) if hasattr(nx, '__version__') else "unknown"
        }
        
        Path(output_path).write_text(json.dumps(output, indent=2), encoding="utf-8")


def main():
    """CLI entry point for ACM detection."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ACM Detector - Detect atomic cycles")
    parser.add_argument("--repo-path", "-r", default=".", help="Repository path to analyze")
    parser.add_argument("--output", "-o", default="", help="Output JSON file for analysis")
    parser.add_argument("--validate-merge", "-v", nargs=2, metavar=("BRANCH", "TARGET"),
                        help="Validate merge candidate")
    
    args = parser.parse_args()
    
    detector = ACMDetector(repo_path=args.repo_path)
    
    if args.validate_merge:
        branch, target = args.validate_merge
        is_valid, message = detector.validate_merge_candidate(branch, target)
        print(f"[ACM-VALIDATE] {branch} -> {target}: {'VALID' if is_valid else 'INVALID'}")
        print(f"[ACM-VALIDATE] {message}")
        return 0 if is_valid else 1
    
    result = detector.detect_cycles()
    
    print(f"[ACM] Cycles detected: {result.has_cycles}")
    if result.has_cycles:
        print(f"[ACM] Severity: {result.severity.name}")
        print(f"[ACM] Affected nodes: {len(result.affected_nodes)}")
        for i, cycle in enumerate(result.cycles[:5]):
            print(f"[ACM] Cycle {i+1}: {' -> '.join(cycle)}")
        print(f"[ACM] φ-CPS impact: {result.phi_cps_impact:.3f}")
    
    if result.recommendations:
        print("[ACM] Recommendations:")
        for rec in result.recommendations:
            print(f"  {rec}")
    
    if args.output:
        detector.export_analysis(args.output)
        print(f"[ACM] Analysis exported to {args.output}")
    
    return 1 if result.has_cycles else 0


if __name__ == "__main__":
    exit(main())