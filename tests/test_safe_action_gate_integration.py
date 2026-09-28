#!/usr/bin/env python3
"""
Integration tests for safe-action-gate in KIVA-CLI.
"""

import pytest
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "PRD"))
sys.path.insert(0, str(Path(__file__).parent.parent / "kiva_cli"))

from safe_action_gate_integration import get_safe_action_gate


def test_safe_action_gate_allow():
    """Test that valid action is allowed."""
    gate = get_safe_action_gate()
    context = {
        "intent_hash": "0xTEST_20260928",
        "consumer": "KIVA-CLI",
    }
    result = gate.verify_before_command("run", context)
    assert result["state"] == "ALLOW"


def test_safe_action_gate_deny_missing_hash():
    """Test that action without intent_hash is denied."""
    gate = get_safe_action_gate()
    context = {"consumer": "KIVA-CLI"}
    result = gate.verify_before_command("run", context)
    assert result["state"] == "DENY"
    assert "intent_hash" in result["reason"]


def test_safe_action_gate_deny_missing_consumer():
    """Test that action without consumer is denied."""
    gate = get_safe_action_gate()
    context = {"intent_hash": "0xTEST_20260928"}
    result = gate.verify_before_command("run", context)
    assert result["state"] == "DENY"
    assert "consumer" in result["reason"]


def test_check_and_execute_allows():
    """Test check_and_execute with valid context."""
    gate = get_safe_action_gate()
    context = {
        "intent_hash": "0xTEST_20260928",
        "consumer": "KIVA-CLI",
    }
    executed = []

    def action(ctx):
        executed.append(True)
        return {"status": "ok"}

    result = gate.check_and_execute("run", context, action)
    assert result["validation"]["state"] == "ALLOW"
    assert result["execution"] is not None
    assert len(executed) == 1


def test_check_and_execute_blocks():
    """Test check_and_execute with invalid context."""
    gate = get_safe_action_gate()
    context = {"consumer": "KIVA-CLI"}  # missing intent_hash
    executed = []

    def action(ctx):
        executed.append(True)
        return {"status": "ok"}

    result = gate.check_and_execute("run", context, action)
    assert result["validation"]["state"] == "DENY"
    assert result["execution"] is None
    assert len(executed) == 0
