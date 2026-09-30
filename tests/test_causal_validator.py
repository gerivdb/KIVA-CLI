"""Tests pour KIVA-CLI causal_validator."""

from src.causal_validator import (
    CausalValidationResult,
    CausalValidator,
    build_causal_validator,
)


def test_build_causal_validator() -> None:
    validator = build_causal_validator()
    assert isinstance(validator, CausalValidator)


def test_causal_validator_valid() -> None:
    validator = build_causal_validator()
    result = validator.validate("rel-1", {"confidence": 0.9})
    assert result.relation_id == "rel-1"
    assert result.valid is True
    assert result.confidence == 0.9
    assert result.issues == []


def test_causal_validator_invalid() -> None:
    validator = build_causal_validator()
    result = validator.validate("rel-1", {"confidence": 0.3})
    assert result.valid is False
    assert result.confidence == 0.3
    assert "low_confidence" in result.issues
