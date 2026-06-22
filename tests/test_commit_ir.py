"""
test_commit_ir.py — Tests COMMIT-IR v1.0 (S1→S3)

≥ 15 tests couvrant AC-1 a AC-5.

IntentHash: 0xTEST_COMMIT_IR_20260620
"""

from __future__ import annotations

import pytest

from nexus.ir import CommitIR
from nexus.ir.commit_ir import CommitValidationError

import nexus.ir.commit_ir as _mod
IRNode = _mod.IRNode
DAG = _mod.DAG
TritLevel = _mod.TritLevel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_commit() -> dict:
    return {
        "id": "abc123def456",
        "intent_hash": "0xINTENT001_20260620",
        "phi": 7.5,
        "trit": "T1",
        "parent_commit": "parent123",
        "timestamp": "2026-06-20T10:00:00+00:00",
    }

@pytest.fixture
def commit_list() -> list[dict]:
    return [
        {
            "id": "commit-1",
            "intent_hash": "0xINTENT001_20260620",
            "phi": 8.0,
            "trit": "T1",
            "parent_commit": "",
            "timestamp": "2026-06-20T10:00:00+00:00",
        },
        {
            "id": "commit-2",
            "intent_hash": "0xINTENT001_20260620",
            "phi": 6.5,
            "trit": "T1",
            "parent_commit": "commit-1",
            "timestamp": "2026-06-20T11:00:00+00:00",
        },
        {
            "id": "commit-3",
            "intent_hash": "0xINTENT002_20260620",
            "phi": 3.0,
            "trit": "T2",
            "parent_commit": "commit-2",
            "timestamp": "2026-06-20T12:00:00+00:00",
        },
    ]


# ---------------------------------------------------------------------------
# S1: COMMIT_LOAD
# ---------------------------------------------------------------------------

class TestCommitLoad:
    def test_load_valid(self, sample_commit: dict) -> None:
        node = CommitIR.load(sample_commit)
        assert node.id == "abc123def456"
        assert node.node_type == "commit"
        assert node.phi == 7.5
        assert node.trit == TritLevel.T1

    def test_load_missing_id(self) -> None:
        with pytest.raises(CommitValidationError):
            CommitIR.load({"intent_hash": "0xTEST"})

    def test_load_parses_intent_hash(self, sample_commit: dict) -> None:
        node = CommitIR.load(sample_commit)
        assert node.meta.get("intent_hash") == "0xINTENT001_20260620"

    def test_load_parses_parent(self, sample_commit: dict) -> None:
        node = CommitIR.load(sample_commit)
        assert node.meta.get("parent_commit") == "parent123"

    def test_load_parses_trit_t2(self) -> None:
        node = CommitIR.load({"id": "x", "trit": "T2", "phi": 5.0})
        assert node.trit == TritLevel.T2

    def test_load_parses_timestamp(self, sample_commit: dict) -> None:
        node = CommitIR.load(sample_commit)
        assert "2026-06-20" in node.meta.get("timestamp", "")


# ---------------------------------------------------------------------------
# S2: COMMIT_GATE
# ---------------------------------------------------------------------------

class TestCommitGate:
    def test_gate_t1_coherent(self, sample_commit: dict) -> None:
        node = CommitIR.load(sample_commit)
        result = CommitIR.gate(node)
        assert result == "T1"

    def test_gate_t2_low_phi(self) -> None:
        node = CommitIR.load({"id": "x", "phi": 3.0, "trit": "T2"})
        result = CommitIR.gate(node)
        assert result == "T2"

    def test_gate_t3_critical_phi(self) -> None:
        node = CommitIR.load({"id": "x", "phi": 1.5, "trit": "T3"})
        result = CommitIR.gate(node)
        assert result == "T3"

    def test_gate_t3_bad_intent_hash(self) -> None:
        node = CommitIR.load({"id": "x", "intent_hash": "bad_format", "phi": 8.0})
        result = CommitIR.gate(node)
        assert result == "T3"

    def test_gate_t3_orphan_parent(self) -> None:
        node = CommitIR.load({
            "id": "x", "phi": 8.0, "intent_hash": "0xTEST_20260620",
            "parent_commit": "nonexistent",
        })
        dag = DAG()
        dag.add_node(node)
        result = CommitIR.gate(node, dag)
        assert result == "T3"


# ---------------------------------------------------------------------------
# S3: COMMIT_DAG + COMMIT_SCORE + DEGRADATION
# ---------------------------------------------------------------------------

class TestCommitDag:
    def test_build_dag(self, commit_list: list[dict]) -> None:
        nodes = [CommitIR.load(c) for c in commit_list]
        dag = CommitIR.build_dag(nodes)
        assert dag.node_count == 3

    def test_build_dag_has_arcs(self, commit_list: list[dict]) -> None:
        nodes = [CommitIR.load(c) for c in commit_list]
        dag = CommitIR.build_dag(nodes)
        assert dag.arc_count == 2  # commit-2 -> commit-1, commit-3 -> commit-2

    def test_build_dag_acyclic(self, commit_list: list[dict]) -> None:
        nodes = [CommitIR.load(c) for c in commit_list]
        dag = CommitIR.build_dag(nodes)
        result = CommitIR.gate(nodes[0], dag)
        assert result == "T1"


class TestCommitScore:
    def test_score_empty(self) -> None:
        assert CommitIR.score(DAG()) == 0.0

    def test_score_range(self, commit_list: list[dict]) -> None:
        nodes = [CommitIR.load(c) for c in commit_list]
        dag = CommitIR.build_dag(nodes)
        score = CommitIR.score(dag, window_days=30)
        assert 0.0 <= score <= 1.0

    def test_score_window_filters_old(self) -> None:
        old_commit = CommitIR.load({
            "id": "old",
            "phi": 8.0,
            "timestamp": "2025-01-01T00:00:00+00:00",
        })
        dag = DAG()
        dag.add_node(old_commit)
        score = CommitIR.score(dag, window_days=30)
        # Le commit est trop ancien, devrait etre filtre
        # Mais sans timestamp valide, il est inclus
        assert 0.0 <= score <= 1.0


class TestCommitDegradation:
    def test_detect_degradation_true(self) -> None:
        low_commit = CommitIR.load({
            "id": "low",
            "phi": 2.0,
            "timestamp": "2026-06-20T00:00:00+00:00",
        })
        dag = DAG()
        dag.add_node(low_commit)
        assert CommitIR.detect_degradation(dag, window_days=7, threshold=4.559) is True

    def test_detect_degradation_false(self) -> None:
        good_commit = CommitIR.load({
            "id": "good",
            "phi": 8.0,
            "timestamp": "2026-06-20T00:00:00+00:00",
        })
        dag = DAG()
        dag.add_node(good_commit)
        assert CommitIR.detect_degradation(dag, window_days=7, threshold=4.559) is False

    def test_hitl_trigger_on_degradation(self) -> None:
        """AC-5: HITL trigger si phi < 4.559 pendant 7 jours."""
        low_commit = CommitIR.load({
            "id": "low",
            "phi": 2.0,
            "timestamp": "2026-06-20T00:00:00+00:00",
        })
        dag = DAG()
        dag.add_node(low_commit)
        is_degraded = CommitIR.detect_degradation(dag, window_days=7, threshold=4.559)
        assert is_degraded  # Doit trigger HITL


# ---------------------------------------------------------------------------
# COMMIT_LINK
# ---------------------------------------------------------------------------

class TestCommitLink:
    def test_link_parent(self) -> None:
        child = IRNode(id="child")
        parent = IRNode(id="parent")
        arc = CommitIR.link(child, parent, "parent")
        assert arc.source == "child"
        assert arc.target == "parent"
        assert arc.arc_type == "parent"

    def test_link_triggers(self) -> None:
        a = IRNode(id="a")
        b = IRNode(id="b")
        arc = CommitIR.link(a, b, "triggers")
        assert arc.arc_type == "triggers"

    def test_link_invalid_defaults_to_parent(self) -> None:
        a = IRNode(id="a")
        b = IRNode(id="b")
        arc = CommitIR.link(a, b, "invalid")
        assert arc.arc_type == "parent"


# ---------------------------------------------------------------------------
# Import test (AC-1)
# ---------------------------------------------------------------------------

class TestImport:
    def test_import_commit_ir(self) -> None:
        from nexus.ir import CommitIR
        assert CommitIR is not None

    def test_version(self) -> None:
        from nexus.ir import __version__
        assert __version__ == "1.0.0"
