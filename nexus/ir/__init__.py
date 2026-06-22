"""
nexus/ir/__init__.py — COMMIT-IR v1.0

CommitIR(AnywhereIR) — coherence moteur pour Thought-Commits NEXUS.
5 opcodes : COMMIT_LOAD, COMMIT_LINK, COMMIT_GATE, COMMIT_DAG, COMMIT_SCORE.

v1.0: IntentHash: 0xCOMMIT_IR_INIT_20260620
"""

from .commit_ir import CommitIR

__all__ = ["CommitIR"]
__version__ = "1.0.0"
