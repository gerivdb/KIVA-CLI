#!/usr/bin/env python3
"""
KIVA-012 S3 — Smoke test for anything-CLI style helpers.

Satisfies post-implement check F10 for KIVA-CLI by validating
the new cross-platform helpers introduced in this slice.
"""
from __future__ import annotations

import pytest

from kiva_cli.core.shell_helpers import normalize_shell_command
from kiva_cli.core.file_helpers import insert_line_after, insert_line_before, replace_line
from kiva_cli.core.pipeline_loader import ALLOWED_ON_FAILURE, validate_pipeline_schema, validate_step_schema
from tests.utils.abc_contract_validator import ABCContractValidator


class TestAnythingCLISmoke:
    """Smoke tests for KIVA-012 cross-platform helpers."""

    def test_shell_normalization_noop_on_non_windows(self, monkeypatch):
        monkeypatch.setattr("kiva_cli.core.shell_helpers.is_windows", lambda: False)
        assert normalize_shell_command("echo hello | head -5") == "echo hello | head -5"

    def test_file_helpers_insert_before(self, tmp_path):
        target = tmp_path / "sample.txt"
        target.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        insert_line_before(target, "beta", "INSERTED")
        assert target.read_text(encoding="utf-8").splitlines() == ["alpha", "INSERTED", "beta", "gamma"]

    def test_pipeline_schema_rejects_invalid_on_failure(self, tmp_path):
        p = tmp_path / "pipeline.yaml"
        p.write_text("steps:\n  - name: bad\n    on_failure: stop\n", encoding="utf-8")
        errors = validate_pipeline_schema(p)
        assert any("on_failure" in e for e in errors)

    def test_allowed_on_failure_values(self):
        expected = {"abort", "warn", "continue", "notify"}
        assert ALLOWED_ON_FAILURE == expected

    def test_abc_contract_validator_instantiable(self):
        class Dummy:
            pass

        ABCContractValidator.assert_instantiable(Dummy)
