"""Tests for nexus_commands.py — CLI coverage for NEXUS governance.

Covers:
- nexus_query (path resolution, section=status/tracking/wal/all, format=json/yaml/table)
- nexus_status (existing and missing STATUS.yaml)
- nexus_mutate (create_tracking, update_status, set_field, set_conflict)
- pipeline_list / pipeline_validate / pipeline_show / pipeline_drift / pipeline_prune
- tracking_init (dry-run and real)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from kiva_cli.commands.nexus_commands import (
    nexus_cli,
    nexus_query,
    nexus_status,
    nexus_mutate,
    tracking_init,
    pipeline_list,
    pipeline_validate,
    pipeline_show,
    pipeline_drift,
    pipeline_prune,
    _now_iso,
    _intent_hash,
    _default_path,
    _severity_icon,
    _read_yaml_file,
    _tracking_md,
    _status_yaml,
    _orphan_reason,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


def _make_nexus_dir(tmp_path: Path, repo: str = "TESTREPO") -> Path:
    """Create a fake repo root with .nexus/STATUS.yaml and TRACKING.md."""
    root = tmp_path / repo
    nexus_dir = root / ".nexus"
    nexus_dir.mkdir(parents=True)
    (nexus_dir / "TRACKING.md").write_text("# Tracking", encoding="utf-8")
    ts = _now_iso()
    ih = _intent_hash(repo, ts)
    (nexus_dir / "STATUS.yaml").write_text(
        "\n".join([
            f"repo: {repo}",
            f"nexus_status: ACTIVE",
            f'last_synced_at: "{ts}"',
            "conflict_flag: false",
            f'intent_hash: "{ih}"',
        ]),
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    def test_now_iso_format(self):
        ts = _now_iso()
        assert ts.endswith("Z")
        assert len(ts) == 20  # "YYYY-MM-DDTHH:MM:SSZ"

    def test_intent_hash_deterministic(self):
        h1 = _intent_hash("REPO", "2026-01-01T00:00:00Z")
        h2 = _intent_hash("REPO", "2026-01-01T00:00:00Z")
        assert h1 == h2
        assert h1.startswith("0x")
        assert len(h1) == 34  # 0x + 32 hex chars

    def test_intent_hash_differs_by_repo(self):
        h1 = _intent_hash("REPO_A", "2026-01-01T00:00:00Z")
        h2 = _intent_hash("REPO_B", "2026-01-01T00:00:00Z")
        assert h1 != h2

    def test_default_path_known_repo(self):
        p = _default_path("NEXUS")
        assert "L0-CANON" in str(p) or "L1-ACTIVE" in str(p)

    def test_default_path_unknown_repo(self):
        p = _default_path("UNKNOWN_REPO_XYZ")
        assert "L1-ACTIVE" in str(p)

    def test_severity_icon_phi_alert(self):
        assert _severity_icon(phi_cps_alert=True, validation_state="VALID") == "[!]"

    def test_severity_icon_failed(self):
        assert _severity_icon(phi_cps_alert=False, validation_state="FAILED") == "[x]"

    def test_severity_icon_pending(self):
        assert _severity_icon(phi_cps_alert=False, validation_state="PENDING") == "[?]"

    def test_severity_icon_ok(self):
        assert _severity_icon(phi_cps_alert=False, validation_state="VALID") == "[ok]"

    def test_read_yaml_file_valid(self, tmp_path):
        p = tmp_path / "data.yaml"
        p.write_text("key: value\n", encoding="utf-8")
        data = _read_yaml_file(p)
        assert data["key"] == "value"

    def test_read_yaml_file_missing(self, tmp_path):
        p = tmp_path / "missing.yaml"
        data = _read_yaml_file(p)
        assert data == {}

    def test_tracking_md_contains_repo(self):
        md = _tracking_md("MYREPO", "2026-01-01T00:00:00Z")
        assert "MYREPO" in md
        assert "TRACKING.md" in md

    def test_status_yaml_contains_fields(self):
        yaml_text = _status_yaml("MYREPO", "2026-01-01T00:00:00Z", "0xABCD")
        assert "repo: MYREPO" in yaml_text
        assert "nexus_status: UNTRACKED" in yaml_text
        assert "0xABCD" in yaml_text

    def test_orphan_reason_never_run(self):
        from kiva_cli.core.pipeline_registry import PipelineRecord
        rec = PipelineRecord(name="x", total_runs=0)
        assert "jamais" in _orphan_reason(rec)

    def test_orphan_reason_no_owner(self):
        from kiva_cli.core.pipeline_registry import PipelineRecord
        rec = PipelineRecord(name="x", total_runs=5, operational_owner="")
        assert "owner" in _orphan_reason(rec)


# ---------------------------------------------------------------------------
# nexus_query
# ---------------------------------------------------------------------------

class TestNexusQuery:
    def test_query_repo_root_status_section(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        result = runner.invoke(nexus_query, [str(root), "--section", "status"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"]["repo"] == "TESTREPO"

    def test_query_repo_root_tracking_section(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        result = runner.invoke(nexus_query, [str(root), "--section", "tracking"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["tracking"] is not None

    def test_query_file_status_yaml(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        status_file = root / ".nexus" / "STATUS.yaml"
        result = runner.invoke(nexus_query, [str(status_file), "--section", "status"])
        assert result.exit_code == 0

    def test_query_file_tracking_md(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        tracking_file = root / ".nexus" / "TRACKING.md"
        result = runner.invoke(nexus_query, [str(tracking_file), "--section", "tracking"])
        assert result.exit_code == 0

    def test_query_missing_path_errors(self, runner):
        result = runner.invoke(nexus_query, ["/nonexistent/path/12345"])
        assert result.exit_code != 0

    def test_query_format_yaml(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        result = runner.invoke(nexus_query, [str(root), "--format", "yaml"])
        assert result.exit_code == 0

    def test_query_format_table(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        result = runner.invoke(nexus_query, [str(root), "--format", "table"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# nexus_status
# ---------------------------------------------------------------------------

class TestNexusStatus:
    def test_status_existing_repo(self, runner, tmp_path, monkeypatch):
        root = _make_nexus_dir(tmp_path)
        monkeypatch.setattr(
            "kiva_cli.commands.nexus_commands._default_path",
            lambda repo: root,
        )
        result = runner.invoke(nexus_status, ["TESTREPO"])
        assert result.exit_code == 0
        assert "ACTIVE" in result.output

    def test_status_missing_status_yaml(self, runner, tmp_path, monkeypatch):
        root = tmp_path / "NOTRACKED"
        root.mkdir()
        monkeypatch.setattr(
            "kiva_cli.commands.nexus_commands._default_path",
            lambda repo: root,
        )
        result = runner.invoke(nexus_status, ["NOTRACKED"])
        assert result.exit_code == 0
        assert "UNTRACKED" in result.output or "Aucun" in result.output


# ---------------------------------------------------------------------------
# nexus_mutate
# ---------------------------------------------------------------------------

class TestNexusMutate:
    def test_create_tracking_dry_run(self, runner, tmp_path):
        root = tmp_path / "NEWREPO"
        root.mkdir()
        result = runner.invoke(nexus_mutate, [
            "--op", "create_tracking",
            "--path", str(root),
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert "DRY-RUN" in result.output

    def test_create_tracking_real(self, runner, tmp_path):
        root = tmp_path / "NEWREPO"
        root.mkdir()
        result = runner.invoke(nexus_mutate, [
            "--op", "create_tracking",
            "--path", str(root),
        ])
        assert result.exit_code == 0
        assert (root / ".nexus" / "TRACKING.md").exists()
        assert (root / ".nexus" / "STATUS.yaml").exists()

    def test_update_status(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        result = runner.invoke(nexus_mutate, [
            "--op", "update_status",
            "--path", str(root),
            "--data", '{"nexus_status": "ACTIVE"}',
        ])
        assert result.exit_code == 0

    def test_set_field(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        result = runner.invoke(nexus_mutate, [
            "--op", "set_field",
            "--path", str(root),
            "--field", "nexus_status",
            "--value", "CONFLICT",
        ])
        assert result.exit_code == 0

    def test_set_conflict(self, runner, tmp_path):
        root = _make_nexus_dir(tmp_path)
        result = runner.invoke(nexus_mutate, [
            "--op", "set_conflict",
            "--path", str(root),
            "--value", "true",
        ])
        assert result.exit_code == 0

    def test_mutate_missing_status_yaml(self, runner, tmp_path):
        root = tmp_path / "NOSTATUS"
        root.mkdir()
        result = runner.invoke(nexus_mutate, [
            "--op", "update_status",
            "--path", str(root),
            "--data", '{"nexus_status": "ACTIVE"}',
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# tracking_init
# ---------------------------------------------------------------------------

class TestTrackingInit:
    def test_init_dry_run(self, runner):
        result = runner.invoke(tracking_init, ["NEXUS", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY-RUN" in result.output

    def test_init_nonexistent_path_warns(self, runner):
        result = runner.invoke(tracking_init, ["UNKNOWN_REPO", "--dry-run"])
        # Should not crash
        assert result.exit_code in (0, 1)


# ---------------------------------------------------------------------------
# pipeline commands
# ---------------------------------------------------------------------------

class TestPipelineList:
    def test_list_empty(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(pipeline_list, [])
        assert result.exit_code == 0

    def test_list_json_output(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(pipeline_list, ["--json"])
        assert result.exit_code == 0


class TestPipelineValidate:
    def test_validate_missing_pipeline(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(pipeline_validate, ["nonexistent"])
        assert result.exit_code != 0


class TestPipelineShow:
    def test_show_missing_pipeline(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(pipeline_show, ["nonexistent"])
        assert result.exit_code == 0


class TestPipelineDrift:
    def test_drift_json_output(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(pipeline_drift, ["--json"])
        assert result.exit_code == 0


class TestPipelinePrune:
    def test_prune_dry_run_clean(self, runner, tmp_path, monkeypatch):
        from kiva_cli.core.pipeline_registry import PipelineRegistryStore, PipelineRecord

        store_path = tmp_path / "reg.json"
        store = PipelineRegistryStore(store_path=store_path)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        store.upsert_record(PipelineRecord(
            name="healthy", total_runs=5, operational_owner="gerivdb", last_run_at=now_iso
        ))

        monkeypatch.setattr(
            "kiva_cli.commands.nexus_commands.PipelineRegistryStore",
            lambda: PipelineRegistryStore(store_path=store_path),
        )
        result = runner.invoke(pipeline_prune, ["--dry-run"])
        assert result.exit_code == 0
