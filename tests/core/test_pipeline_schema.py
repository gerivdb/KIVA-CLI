"""KIVA-012 S3 — Unit tests for pipeline schema validation."""
from __future__ import annotations

from pathlib import Path

import pytest

from kiva_cli.core.pipeline_loader import (
    ALLOWED_ON_FAILURE,
    validate_pipeline_schema,
    validate_step_schema,
)


def test_validate_step_schema_accepts_valid_step():
    errors = validate_step_schema({"name": "ok", "on_failure": "abort"}, 0)
    assert errors == []


def test_validate_step_schema_rejects_invalid_on_failure():
    errors = validate_step_schema({"name": "bad", "on_failure": "stop"}, 0)
    assert any("on_failure" in e for e in errors)


def test_validate_step_schema_allows_all_valid_values():
    for value in ALLOWED_ON_FAILURE:
        errors = validate_step_schema({"name": "ok", "on_failure": value}, 0)
        assert errors == []


def test_validate_pipeline_schema_detects_invalid_step(tmp_path: Path):
    p = tmp_path / "pipeline.yaml"
    p.write_text("steps:\n  - name: bad\n    on_failure: stop\n", encoding="utf-8")
    errors = validate_pipeline_schema(p)
    assert any("on_failure" in e for e in errors)


def test_validate_pipeline_schema_missing_file():
    errors = validate_pipeline_schema(Path("nonexistent.yaml"))
    assert any("not found" in e for e in errors)
