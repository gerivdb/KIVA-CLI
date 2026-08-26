#!/usr/bin/env python3
"""Tests for ScriptMaturationManager.

Focus: queue management, level detection, promotion logic with temp dirs.
"""
from pathlib import Path

import pytest

from kiva_cli.core.script_maturation_manager import ScriptMaturationManager


@pytest.fixture
def mgr(tmp_path):
    return ScriptMaturationManager(queue_dir=str(tmp_path / "queue"))


@pytest.fixture
def scripts_dir(tmp_path):
    d = tmp_path / "bin"
    d.mkdir()
    return d


def test_init_creates_queue_file(tmp_path):
    q = tmp_path / "queue"
    m = ScriptMaturationManager(queue_dir=str(q))
    assert (q / "queue.json").exists()
    data = m._load_queue_data()
    assert data["queue"] == []


def test_get_script_level_missing_returns_zero(scripts_dir):
    m = ScriptMaturationManager(queue_dir=str(scripts_dir.parent / "q"))
    assert m.get_script_level("nope.ps1", str(scripts_dir)) == 0


def test_get_script_level_skeleton(scripts_dir):
    m = ScriptMaturationManager(queue_dir=str(scripts_dir.parent / "q"))
    (scripts_dir / "s.ps1").write_text("short")
    assert m.get_script_level("s.ps1", str(scripts_dir)) == 0


def test_get_script_level_stub(scripts_dir):
    m = ScriptMaturationManager(queue_dir=str(scripts_dir.parent / "q"))
    (scripts_dir / "s.ps1").write_text("x" * 60)
    assert m.get_script_level("s.ps1", str(scripts_dir)) == 1


def test_get_script_level_prototype(scripts_dir):
    m = ScriptMaturationManager(queue_dir=str(scripts_dir.parent / "q"))
    (scripts_dir / "s.ps1").write_text('param(\n)\nWrite-Host "hi"\n' + "y" * 40)
    assert m.get_script_level("s.ps1", str(scripts_dir)) == 2


def test_get_script_level_functional(scripts_dir):
    m = ScriptMaturationManager(queue_dir=str(scripts_dir.parent / "q"))
    content = 'param(\n)\nWrite-Host "hi"\ntry {\n' + "z" * 520 + '\n} catch {\n}\n'
    (scripts_dir / "s.ps1").write_text(content)
    assert m.get_script_level("s.ps1", str(scripts_dir)) == 3


def test_get_script_level_production(scripts_dir):
    m = ScriptMaturationManager(queue_dir=str(scripts_dir.parent / "q"))
    content = 'param(\n)\nWrite-Host "hi"\ntry {\n' + "z" * 520 + '\n} catch {\n}\nExport-ModuleMember -Function *'
    (scripts_dir / "s.ps1").write_text(content)
    assert m.get_script_level("s.ps1", str(scripts_dir)) == 4


def test_add_to_queue(mgr):
    assert mgr.add_to_queue("a.ps1", 4) is True
    data = mgr._load_queue_data()
    assert len(data["queue"]) == 1
    assert data["queue"][0]["script"] == "a.ps1"


def test_add_to_queue_duplicate(mgr):
    mgr.add_to_queue("a.ps1", 4)
    assert mgr.add_to_queue("a.ps1", 4) is False
    assert len(mgr._load_queue_data()["queue"]) == 1


def test_remove_from_queue(mgr):
    mgr.add_to_queue("a.ps1", 4)
    assert mgr.remove_from_queue("a.ps1") is True
    assert mgr.remove_from_queue("a.ps1") is False
    assert len(mgr._load_queue_data()["queue"]) == 0


def test_promote_script_not_found(mgr, scripts_dir):
    assert mgr.promote_script("missing.ps1", 4, str(scripts_dir)) is False


def test_promote_script_to_level_4(mgr, scripts_dir):
    (scripts_dir / "s.ps1").write_text('Write-Host "hello"')
    assert mgr.promote_script("s.ps1", 4, str(scripts_dir)) is True
    content = (scripts_dir / "s.ps1").read_text()
    assert "param(" in content
    assert "try {" in content
    assert "Export-ModuleMember" in content


def test_promote_script_already_at_level(mgr, scripts_dir):
    (scripts_dir / "s.ps1").write_text('Export-ModuleMember -Function *')
    assert mgr.promote_script("s.ps1", 4, str(scripts_dir)) is True


def test_process_queue_promotes_and_completes(mgr, scripts_dir):
    (scripts_dir / "s.ps1").write_text('Write-Host "hello"')
    mgr.add_to_queue("s.ps1", 4)
    assert mgr.process_queue(str(scripts_dir)) is True
    data = mgr._load_queue_data()
    assert data["queue"] == []
    assert len(data["completed"]) == 1
    assert data["processing"] is None


def test_process_queue_empty(mgr):
    assert mgr.process_queue("x") is False


def test_get_queue_status(mgr):
    mgr.add_to_queue("a.ps1", 4)
    status = mgr.get_queue_status()
    assert status["queue_count"] == 1
    assert status["completed_count"] == 0
    assert status["worker"]["running"] is False


def test_get_worker_status_no_pid_file(mgr):
    assert mgr.get_worker_status() == {"running": False, "pid": None}


def test_get_worker_status_running(mgr, tmp_path):
    pid_file = mgr.worker_pid_file
    pid_file.write_text("999999\n")
    # monkeypatch tasklist to report the pid as running
    import subprocess
    from unittest import mock
    with mock.patch("subprocess.run") as mrun:
        mrun.return_value = subprocess.CompletedProcess(
            ["tasklist"], 0, stdout="999999 Console\n", stderr=""
        )
        assert mgr.get_worker_status()["running"] is True
