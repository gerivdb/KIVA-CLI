"""
nexus/ir/commit_ir.py — CommitIR(AnywhereIR) (S1→S3)

Coherence moteur pour Thought-Commits NEXUS.
5 opcodes :
  COMMIT_LOAD        — parse Thought-Commit -> IRNode
  COMMIT_LINK        — arc parent / triggers / supersedes
  COMMIT_GATE        — PG1: intent_hash orphelin / PG2: phi < seuil / PG3: fork orphelin
  COMMIT_DAG        — arbre de causalite des commits
  COMMIT_SCORE       — phi-CPS sur fenetre glissante + detection degradation

v1.0: IntentHash: 0xCOMMIT_IR_COMMIT_IR_20260620
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

# --- Shim de compatibilite keel_core ---
try:
    from keel_core import DAG, IRArc, IRNode, TritLevel
except ImportError:
    from enum import auto as _auto

    class TritLevel:
        T1 = _auto()
        T2 = _auto()
        T3 = _auto()

    @dataclass
    class IRNode:
        id: str
        node_type: str = "commit"
        status: str = "active"
        phi: float = 0.0
        trit: Any = None
        meta: dict = field(default_factory=dict)

        @property
        def is_valid(self):
            return bool(self.id)

        @property
        def phi_contribution(self):
            return 1.0 if self.trit == TritLevel.T1 else 0.5 if self.trit == TritLevel.T2 else 0.0

    @dataclass
    class IRArc:
        source: str
        target: str
        arc_type: str = "parent"
        resolved: bool = True
        meta: dict = field(default_factory=dict)

    @dataclass
    class DAG:
        nodes: dict = field(default_factory=dict)
        arcs: list = field(default_factory=list)

        @property
        def node_count(self):
            return len(self.nodes)

        @property
        def arc_count(self):
            return len(self.arcs)

        def add_node(self, node):
            self.nodes[node.id] = node

        def add_arc(self, arc):
            self.arcs.append(arc)

        def get_node(self, nid):
            return self.nodes.get(nid)

        def get_dependencies(self, nid):
            return [a.target for a in self.arcs if a.source == nid]

        def get_dependents(self, nid):
            return [a.source for a in self.arcs if a.target == nid]

        def has_node(self, nid):
            return nid in self.nodes

        def has_arc(self, src, tgt):
            return any(a.source == src and a.target == tgt for a in self.arcs)


# --- Exceptions ---

class CommitValidationError(Exception):
    """Levee si un Thought-Commit est invalide."""
    pass


# --- CommitIR ---

class CommitIR:
    """
    Coherence moteur pour Thought-Commits NEXUS.

    Methodes :
      - load(commit_data) -> IRNode
      - link(source, target, arc_type) -> IRArc
      - gate(node, dag) -> str (T1/T2/T3)
      - build_dag(commits) -> DAG
      - score(dag, window_days) -> float
      - detect_degradation(dag, window_days, threshold) -> bool
    """

    VALID_STATUSES = {"active", "merged", "deprecated"}
    VALID_ARC_TYPES = {"parent", "triggers", "supersedes"}
    PHI_THRESHOLD = 4.559

    @staticmethod
    def load(commit_data: dict[str, Any]) -> IRNode:
        """
        COMMIT_LOAD — parse un Thought-Commit en IRNode.

        Args:
            commit_data: dict avec cles :
                - id (str, obligatoire) — hash du commit
                - intent_hash (str) — hash de l'INTENT parent
                - phi (float) — score phi-CPS
                - trit (str) — T1/T2/T3
                - parent_commit (str) — ID du commit parent
                - timestamp (str) — ISO date
                - meta (dict) — metadonnees supplementaires

        Returns:
            IRNode construit.

        Raises:
            CommitValidationError: si id absent.
        """
        commit_id = commit_data.get("id", "")
        if not commit_id:
            raise CommitValidationError("Commit sans champ 'id'")

        intent_hash = commit_data.get("intent_hash", "")
        phi = commit_data.get("phi", 0.0)
        trit_str = commit_data.get("trit", "T1")
        parent = commit_data.get("parent_commit", "")
        timestamp = commit_data.get("timestamp", "")

        # Parser le trit
        trit_map = {"T1": TritLevel.T1, "T2": TritLevel.T2, "T3": TritLevel.T3}
        trit = trit_map.get(trit_str, TritLevel.T1)

        meta = {
            "intent_hash": intent_hash,
            "parent_commit": parent,
            "timestamp": timestamp,
            "raw": commit_data,
        }
        meta.update(commit_data.get("meta", {}))

        return IRNode(
            id=commit_id,
            node_type="commit",
            status="active",
            phi=phi,
            trit=trit,
            meta=meta,
        )

    @staticmethod
    def link(
        source: IRNode,
        target: IRNode,
        arc_type: str = "parent",
    ) -> IRArc:
        """
        COMMIT_LINK — cree un arc entre deux commits.

        Args:
            source: IRNode source (commit enfant)
            target: IRNode cible (commit parent)
            arc_type: type d'arc (parent / triggers / supersedes)

        Returns:
            IRArc cree.
        """
        if arc_type not in CommitIR.VALID_ARC_TYPES:
            arc_type = "parent"

        return IRArc(
            source=source.id,
            target=target.id,
            arc_type=arc_type,
            resolved=True,
        )

    @staticmethod
    def gate(node: IRNode, dag: Optional[DAG] = None) -> str:
        """
        COMMIT_GATE — evalue la coherence d'un Thought-Commit.

        PG1 : intent_hash orphelin (non vide mais non resoluble)
        PG2 : phi < seuil 4.559
        PG3 : fork orphelin (parent inexistant dans le DAG)

        Returns:
            'T1' (coherent), 'T2' (warning), 'T3' (bloquant)
        """
        # PG1 : intent_hash
        intent_hash = node.meta.get("intent_hash", "")
        if intent_hash and not intent_hash.startswith("0x"):
            return "T3"  # format invalide

        # PG2 : phi
        if node.phi < CommitIR.PHI_THRESHOLD:
            if node.phi < 2.0:
                return "T3"
            return "T2"

        # PG3 : fork orphelin
        if dag:
            parent_id = node.meta.get("parent_commit", "")
            if parent_id and not dag.has_node(parent_id):
                return "T3"

        return "T1"

    @staticmethod
    def build_dag(commits: list[IRNode]) -> DAG:
        """
        COMMIT_DAG — construit l'arbre de causalite des commits.

        Args:
            commits: liste d'IRNode commits

        Returns:
            DAG construit.
        """
        dag = DAG()

        for commit in commits:
            dag.add_node(commit)

        # Creer les arcs parent
        id_set = {c.id for c in commits}
        for commit in commits:
            parent_id = commit.meta.get("parent_commit", "")
            if parent_id and parent_id in id_set:
                dag.add_arc(IRArc(
                    source=commit.id,
                    target=parent_id,
                    arc_type="parent",
                    resolved=True,
                ))

        return dag

    @staticmethod
    def score(dag: DAG, window_days: int = 30) -> float:
        """
        COMMIT_SCORE — calcule le phi-CPS sur fenetre glissante.

        Args:
            dag: DAG des commits
            window_days: fenetre en jours (defaut 30)

        Returns:
            float dans [0.0, 1.0]
        """
        if dag.node_count == 0:
            return 0.0

        # Filtrer par fenetre temporelle
        now = datetime.now(timezone.utc)
        recent_nodes = []
        for node in dag.nodes.values():
            ts = node.meta.get("timestamp", "")
            if ts:
                try:
                    commit_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    delta = (now - commit_time).days
                    if delta <= window_days:
                        recent_nodes.append(node)
                except (ValueError, TypeError):
                    recent_nodes.append(node)
            else:
                recent_nodes.append(node)

        if not recent_nodes:
            return 0.0

        phi_sum = sum(n.phi_contribution for n in recent_nodes)
        return round(phi_sum / len(recent_nodes), 4)

    @staticmethod
    def detect_degradation(
        dag: DAG,
        window_days: int = 7,
        threshold: float = 4.559,
    ) -> bool:
        """
        Detecte une degradation du phi-CPS sur fenetre glissante.

        Returns:
            True si phi < threshold sur tous les commits de la fenetre.
        """
        if dag.node_count == 0:
            return False

        now = datetime.now(timezone.utc)
        recent_scores = []
        for node in dag.nodes.values():
            ts = node.meta.get("timestamp", "")
            if ts:
                try:
                    commit_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    delta = (now - commit_time).days
                    if delta <= window_days:
                        recent_scores.append(node.phi)
                except (ValueError, TypeError):
                    recent_scores.append(node.phi)
            else:
                recent_scores.append(node.phi)

        if not recent_scores:
            return False

        return all(phi < threshold for phi in recent_scores)
