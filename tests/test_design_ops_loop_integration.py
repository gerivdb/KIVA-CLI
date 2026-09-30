#!/usr/bin/env python3
"""
Integration tests for design-ops-loop in KIVA-CLI.
"""

import pytest
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "PRD"))
sys.path.insert(0, str(Path(__file__).parent.parent / "kiva_cli"))

from design_ops_loop_integration import get_design_ops_loop


def test_think_returns_thought():
    """Test THINK phase returns expected structure."""
    loop = get_design_ops_loop()
    context = {"need_ecosystemic": True}
    result = loop.think(context)
    assert result["phase"] == "THINK"
    assert result["status"] == "OK"


def test_do_returns_action():
    """Test DO phase returns expected structure."""
    loop = get_design_ops_loop()
    context = {"action": "test_action"}
    result = loop.do(context)
    assert result["phase"] == "DO"
    assert result["status"] == "OK"
    assert result["action"] == "test_action"


def test_check_returns_coherence():
    """Test CHECK phase returns expected structure."""
    loop = get_design_ops_loop()
    context = {"coherence": True}
    result = loop.check(context)
    assert result["phase"] == "CHECK"
    assert result["status"] == "OK"


def test_run_completes_loop():
    """Test full THINK/DO/CHECK loop."""
    loop = get_design_ops_loop()
    context = {
        "need_ecosystemic": True,
        "action": "test_action",
        "coherence": True,
    }
    result = loop.run(context)
    assert result["loop"] == "THINK/DO/CHECK"
    assert result["status"] == "COMPLETED"
    assert len(result["phases"]) == 3
    assert result["phases"][0]["phase"] == "THINK"
    assert result["phases"][1]["phase"] == "DO"
    assert result["phases"][2]["phase"] == "CHECK"


def test_run_with_empty_context():
    """Test loop with empty context defaults."""
    loop = get_design_ops_loop()
    result = loop.run({})
    assert result["status"] == "COMPLETED"
    assert len(result["phases"]) == 3
