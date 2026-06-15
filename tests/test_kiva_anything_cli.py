#!/usr/bin/env python3
"""Tests unitaires — KIVA-CLI Anything-CLI Suite v1.0 | IntentHash: 0xTEST_KIVA_ANYTHING_20260615"""
import json, sys, time
from pathlib import Path

KIVA_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(KIVA_ROOT))


def _validate(result, name):
    assert isinstance(result, dict), f"{name}: not a dict"
    for k in ("tool", "status", "intent_hash", "result", "timestamp", "phi_cps"):
        assert k in result, f"{name}: missing '{k}'"
    assert result["tool"] == name
    assert result["status"] in ("success", "error")
    assert result["phi_cps"] == 4.092


def test_schedule_success():
    from cli_tools.anything.schedule_anything import schedule_anything
    r = schedule_anything(name="test_pipeline", pipeline_type="sequential", steps=[{"id": "s1"}])
    _validate(r, "schedule-anything")
    assert r["status"] == "success"

def test_schedule_missing():
    from cli_tools.anything.schedule_anything import schedule_anything
    r = schedule_anything(name="")
    _validate(r, "schedule-anything")
    assert r["status"] == "error"

def test_run_success():
    from cli_tools.anything.run_anything import run_anything
    r = run_anything(commands=[{"command": "test"}], mode="sequential")
    _validate(r, "run-anything")
    assert r["status"] == "success"

def test_run_missing():
    from cli_tools.anything.run_anything import run_anything
    r = run_anything(commands=[])
    _validate(r, "run-anything")
    assert r["status"] == "error"

def test_run_parallel():
    from cli_tools.anything.run_anything import run_anything
    r = run_anything(commands=[{"command": "a"}, {"command": "b"}], mode="parallel", max_workers=2)
    _validate(r, "run-anything")

def test_run_chain():
    from cli_tools.anything.run_anything import run_anything
    r = run_anything(commands=[{"id": "c1"}, {"id": "c2"}], mode="chain")
    _validate(r, "run-anything")

def test_wal_status():
    from cli_tools.anything.wal_anything import wal_anything
    r = wal_anything(action="status")
    _validate(r, "wal-anything")

def test_wal_append():
    from cli_tools.anything.wal_anything import wal_anything
    r = wal_anything(action="append", message="test message", intent_hash="0xTEST")
    _validate(r, "wal-anything")

def test_citizen_status():
    from cli_tools.anything.citizen_anything import citizen_anything
    r = citizen_anything(action="status")
    _validate(r, "citizen-anything")

def test_citizen_register():
    from cli_tools.anything.citizen_anything import citizen_anything
    r = citizen_anything(action="register", name="test_citizen", repo="WAZAA")
    _validate(r, "citizen-anything")

def test_skill_list():
    from cli_tools.anything.skill_anything import skill_anything
    r = skill_anything(action="list")
    _validate(r, "skill-anything")

def test_deploy_strategies():
    from cli_tools.anything.deploy_anything import deploy_anything
    r = deploy_anything(action="strategies")
    _validate(r, "deploy-anything")
    assert r["status"] == "success"

def test_phi_status():
    from cli_tools.anything.phi_anything import phi_anything
    r = phi_anything(action="status")
    _validate(r, "phi-anything")

def test_rollback_status():
    from cli_tools.anything.rollback_anything import rollback_anything
    r = rollback_anything(action="status")
    _validate(r, "rollback-anything")

def test_tool_map():
    from cli_tools import anything as pkg
    expected = ["schedule-anything","run-anything","wal-anything","citizen-anything",
                "skill-anything","deploy-anything","phi-anything","rollback-anything"]
    for t in expected:
        assert t in pkg.TOOL_MAP, f"Missing: {t}"
    assert len(pkg.TOOL_MAP) == 8


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = f = 0
    for t in tests:
        try:
            t(); p += 1; print(f"  [OK] {t.__name__}")
        except Exception as e:
            f += 1; print(f"  [FAIL] {t.__name__}: {e}")
    print(f"\n{p} passed, {f} failed, {p+f} total")
    sys.exit(0 if f == 0 else 1)
