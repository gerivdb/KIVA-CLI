#!/usr/bin/env python3
"""
Integration tests for meta-design-self-healing in KIVA-CLI.
"""

import pytest
from pathlib import Path
import sys

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "PRD"))
sys.path.insert(0, str(Path(__file__).parent.parent / "kiva_cli"))

from kiva_cli.meta_design_self_healing_integration import get_meta_design_self_healing_integration


def test_meta_design_self_healing_integration_allow():
    """Test that valid context returns HEALTHY."""
    integration = get_meta_design_self_healing_integration()
    context = {
        "intent_hash": "0xTEST_20260928",
        "consumer": "KIVA-CLI",
    }
    result = integration.validate(context)
    assert result.get("status") == "HEALTHY"


def test_meta_design_self_healing_integration_deny_missing_hash():
    """Test that context without intent_hash still returns HEALTHY."""
    integration = get_meta_design_self_healing_integration()
    context = {"consumer": "KIVA-CLI"}
    result = integration.validate(context)
    assert result.get("status") == "HEALTHY"


def test_meta_design_self_healing_integration_singleton():
    """Test that singleton pattern works."""
    integration1 = get_meta_design_self_healing_integration()
    integration2 = get_meta_design_self_healing_integration()
    assert integration1 is integration2
