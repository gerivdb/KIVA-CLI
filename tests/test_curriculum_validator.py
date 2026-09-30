"""Tests pour KIVA-CLI curriculum_validator."""

from src.curriculum_validator import (
    CurriculumValidationResult,
    CurriculumValidator,
    build_curriculum_validator,
)


def test_build_curriculum_validator() -> None:
    validator = build_curriculum_validator()
    assert isinstance(validator, CurriculumValidator)


def test_curriculum_validator_valid() -> None:
    validator = build_curriculum_validator()
    result = validator.validate("cur-1", {"title": "Test", "steps": []})
    assert result.curriculum_id == "cur-1"
    assert result.valid is True
    assert result.issues == []


def test_curriculum_validator_invalid() -> None:
    validator = build_curriculum_validator()
    result = validator.validate("cur-1", {})
    assert result.valid is False
    assert "missing_title" in result.issues
    assert "missing_steps" in result.issues
