#!/usr/bin/env python3
"""Extended tests for DaemonManager: get/start/stop/shutdown.

Uses temp db_path and monkeypatched _execute_daemon_script to avoid
spawning real processes.
"""
import os
import sqlite3
import threading
from pathlib import Path
from unittest import mock

import pytest

from kiva_cli.core.daemon_manager import DaemonManager


class FakeProcess:
    """Minimal subprocess.Popen stand-in."""
    def __init__(self, pid=12345):
        self.pid = pid
        self.returncode = None
        self._terminated = False

    def terminate(self):
        self._terminated = True
        self.returncode = 0

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode

    def poll(self):
        return self.returncode


@pytest.fixture
def mgr(tmp_path):
    # use a non-home db path; wal_manager left default (GlobalWALManager may touch disk)
    db = tmp_path / "daemons.db"
    return DaemonManager(db_path=str(db), wal_manager=None)


def test_get_daemon_none(mgr):
    assert mgr.get_daemon("nope") is None


def test_get_daemon_found(mgr):
    did = mgr.register_daemon("svc1", "PYTHON_SCRIPT", script_path="x.py")
    d = mgr.get_daemon(did)
    assert d is not None
    assert d["name"] == "svc1"
    assert d["daemon_id"] == did


def test_start_daemon_not_found(mgr):
    with pytest.raises(ValueError):
        mgr.start_daemon("missing")


def test_start_and_stop_daemon(mgr):
    did = mgr.register_daemon("svc2", "PYTHON_SCRIPT", script_path="x.py")
    with mock.patch.object(DaemonManager, "_execute_daemon_script", return_value=FakeProcess()):
        assert mgr.start_daemon(did) is True
    d = mgr.get_daemon(did)
    assert d["runtime_state"] == "RUNNING"
    assert d["pid"] == 12345
    assert mgr.stop_daemon(did) is True
    d = mgr.get_daemon(did)
    assert d["runtime_state"] == "STOPPED"
    assert d["pid"] is None


def test_start_daemon_already_running_returns_true(mgr):
    did = mgr.register_daemon("svc3", "PYTHON_SCRIPT", script_path="x.py")
    with mock.patch.object(DaemonManager, "_execute_daemon_script", return_value=FakeProcess()):
        assert mgr.start_daemon(did) is True
        # second start without force: already running -> True, no new process
        assert mgr.start_daemon(did) is True


def test_start_daemon_invalid_state_raises(mgr):
    did = mgr.register_daemon("svc4", "PYTHON_SCRIPT", script_path="x.py")
    conn = sqlite3.connect(mgr.db_path)
    conn.execute("UPDATE daemons SET validation_state='INVALID' WHERE daemon_id=?", (did,))
    conn.commit()
    conn.close()
    with pytest.raises(ValueError):
        mgr.start_daemon(did)


def test_shutdown_sets_event(mgr):
    assert isinstance(mgr.shutdown_event, threading.Event)
    mgr.shutdown()
    assert mgr.shutdown_event.is_set()


def test_stop_daemon_not_found(mgr):
    with pytest.raises(ValueError):
        mgr.stop_daemon("missing")
