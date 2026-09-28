#!/usr/bin/env python3
"""
Integration tests for safe-action-pattern in KIVA-CLI.
"""

import pytest
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "PRD"))
sys.path.insert(0, str(Path(__file__).parent.parent / "kiva_cli"))

from safe_action_integration import get_safe_action


def test_safe_action_integration_allow():
    """Test that valid action is allowed."""
    sa = get_safe_action()
    context = {
        "intent_hash": "0xTEST_20260928",
        "consumer": "KIVA-CLI",
        "action": "test",
    }
    result = sa.validate_action(context)
    assert result["state"] == "ALLOW"


def test_safe_action_integration_deny_missing_hash():
    """Test that action without intent_hash is denied."""
    sa = get_safe_action()
    context = {"consumer": "KIVA-CLI"}
    result = sa.validate_action(context)
    assert result["state"] == "DENY"
    assert "intent_hash" in result["reason"]
