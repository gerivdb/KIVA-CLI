"""Tests for condition_evaluator — KIVA-011 evaluate_when() API.

All tests target the primary string expression interface.
Legacy structured WhenCondition path is tested separately if needed.
"""
from __future__ import annotations

import pytest

from kiva_cli.core.condition_evaluator import evaluate_when


# ---------------------------------------------------------------------------
# Empty / trivial cases
# ---------------------------------------------------------------------------

def test_empty_string_always_runs():
    """Empty when → always execute (backward compat)."""
    assert evaluate_when("") is True


def test_whitespace_only_always_runs():
    assert evaluate_when("   ") is True


def test_none_context_safe():
    """None context must not crash."""
    assert evaluate_when("", None) is True


# ---------------------------------------------------------------------------
# Boolean literals
# ---------------------------------------------------------------------------

def test_true_literal():
    assert evaluate_when("True") is True


def test_false_literal():
    assert evaluate_when("False") is False


# ---------------------------------------------------------------------------
# Arithmetic / comparison
# ---------------------------------------------------------------------------

def test_trivial_arithmetic_true():
    assert evaluate_when("1 + 1 == 2") is True


def test_trivial_arithmetic_false():
    assert evaluate_when("1 + 1 == 3") is False


# ---------------------------------------------------------------------------
# Pipeline context variables
# ---------------------------------------------------------------------------

def test_last_status_success():
    ctx = {"last_status": "SUCCESS"}
    assert evaluate_when("last_status == 'SUCCESS'", ctx) is True


def test_last_status_failed():
    ctx = {"last_status": "FAILED"}
    assert evaluate_when("last_status == 'SUCCESS'", ctx) is False


def test_dry_run_true_skips():
    ctx = {"dry_run": True}
    assert evaluate_when("not dry_run", ctx) is False


def test_dry_run_false_runs():
    ctx = {"dry_run": False}
    assert evaluate_when("not dry_run", ctx) is True


def test_parallel_groups_executed():
    ctx = {"parallel_groups_executed": 2}
    assert evaluate_when("parallel_groups_executed > 0", ctx) is True


def test_parallel_groups_executed_zero():
    ctx = {"parallel_groups_executed": 0}
    assert evaluate_when("parallel_groups_executed > 0", ctx) is False


# ---------------------------------------------------------------------------
# env dict (e.g. passed as {"env": dict(os.environ)})
# ---------------------------------------------------------------------------

def test_env_get_match():
    ctx = {"env": {"CI": "1"}}
    assert evaluate_when("env.get('CI') == '1'", ctx) is True


def test_env_get_no_match():
    ctx = {"env": {"CI": "0"}}
    assert evaluate_when("env.get('CI') == '1'", ctx) is False


def test_env_get_missing_key_returns_none():
    ctx = {"env": {}}
    # env.get('CI') returns None, not '1'
    assert evaluate_when("env.get('CI') == '1'", ctx) is False


# ---------------------------------------------------------------------------
# Complex conditions (AND / OR)
# ---------------------------------------------------------------------------

def test_complex_and_both_true():
    ctx = {"last_status": "SUCCESS", "parallel_groups_executed": 1}
    assert evaluate_when("last_status == 'SUCCESS' and parallel_groups_executed > 0", ctx) is True


def test_complex_and_one_false():
    ctx = {"last_status": "FAILED", "parallel_groups_executed": 1}
    assert evaluate_when("last_status == 'SUCCESS' and parallel_groups_executed > 0", ctx) is False


def test_complex_or_one_true():
    ctx = {"last_status": "FAILED", "dry_run": True}
    assert evaluate_when("last_status == 'SUCCESS' or dry_run", ctx) is True


# ---------------------------------------------------------------------------
# Error handling — must return False, never crash
# ---------------------------------------------------------------------------

def test_invalid_syntax_returns_false():
    """Syntax error → safe skip (no exception propagated)."""
    assert evaluate_when("last_status ==== 'SUCCESS'") is False


def test_unknown_name_returns_false():
    """Undeclared name not in context → safe skip."""
    assert evaluate_when("unknown_variable == 42") is False


def test_disallowed_import_returns_false():
    """Attempt to use __import__ → disallowed AST node → safe skip."""
    assert evaluate_when("__import__('os').getcwd() != ''") is False


def test_disallowed_attribute_returns_false():
    """Disallowed attribute access → safe skip."""
    ctx = {"last_status": "SUCCESS"}
    assert evaluate_when("last_status.__class__.__name__ == 'str'", ctx) is False
