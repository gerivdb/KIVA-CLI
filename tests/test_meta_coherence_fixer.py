"""Tests pour KIVA-CLI meta_coherence_fixer."""

from src.meta_coherence_fixer import (
    MetaCoherenceFixer,
    MetaCoherenceResult,
    build_meta_coherence_fixer,
)


def test_build_meta_coherence_fixer() -> None:
    fixer = build_meta_coherence_fixer()
    assert isinstance(fixer, MetaCoherenceFixer)


def test_meta_coherence_fixer_inspect_clean() -> None:
    fixer = build_meta_coherence_fixer()
    issues = fixer.inspect("t1", {"narrative": {"cycle_id": "1"}, "curriculum": {"cycle_id": "1"}})
    assert issues == []


def test_meta_coherence_fixer_inspect_mismatch() -> None:
    fixer = build_meta_coherence_fixer()
    issues = fixer.inspect("t1", {"narrative": {"cycle_id": "1"}, "curriculum": {"cycle_id": "2"}})
    assert issues == ["cycle_id_mismatch"]


def test_meta_coherence_fixer_fix() -> None:
    fixer = build_meta_coherence_fixer()
    result = fixer.fix("t1", {"narrative": {"cycle_id": "1"}, "curriculum": {"cycle_id": "2"}})
    assert result.target_id == "t1"
    assert result.fixed is True
    assert "align_cycle_id" in result.applied_fixes
