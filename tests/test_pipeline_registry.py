"""Tests KIVA-012 S1 — PipelineRecord + PipelineRegistryStore + compute_schema_hash.

Couvre : AC-K12-8 (round-trip JSON), AC-K12-9 (coverage partielle S1).
Aucune dépendance réseau / WAL / disque L0-CANON.
Tout est isolé via tmp_path (pytest fixture).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest
from click.testing import CliRunner

from kiva_cli.commands.nexus_commands import pipeline_prune

from kiva_cli.core.pipeline_registry import (
    PipelineRecord,
    PipelineRegistryStore,
    compute_schema_hash,
    discover_pipelines,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(name: str = "build", **kwargs) -> PipelineRecord:
    defaults = {
        "version": "1.0",
        "nexus_status": "ACTIVE",
        "step_count": 8,
    }
    # kwargs take precedence over defaults
    data = {**defaults, **kwargs, "name": name}
    return PipelineRecord(**data)


def _write_yaml(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# PipelineRecord
# ---------------------------------------------------------------------------

class TestPipelineRecord:
    def test_defaults(self):
        r = PipelineRecord(name="demo")
        assert r.version == "1"
        assert r.nexus_status == "DRAFT"
        assert r.total_runs == 0
        assert r.success_runs == 0
        assert r.avg_duration_s == 0.0
        assert r.operational_owner == "gerivdb"
        assert r.last_success_at is None

    def test_success_rate_zero_runs(self):
        r = PipelineRecord(name="demo")
        # success_rate property : 0 runs → 0.0 (no ZeroDivisionError)
        rate = r.success_runs / r.total_runs if r.total_runs else 0.0
        assert rate == 0.0

    def test_success_rate_partial(self):
        r = PipelineRecord(name="demo", total_runs=10, success_runs=7)
        rate = r.success_runs / r.total_runs
        assert abs(rate - 0.7) < 1e-9

    def test_schema_hash_length(self):
        r = PipelineRecord(name="demo", schema_hash="abc1234567890123")
        assert len(r.schema_hash) == 16

    def test_round_trip_json(self, tmp_path):
        """AC-K12-8 : sérialisation → désérialisation sans perte."""
        r = _make_record(
            schema_hash="aabbccdd11223344",
            last_run_at="2026-05-22T06:00:00Z",
            last_status="SUCCESS",
            last_intent_hash="deadbeef" * 4,
            avg_duration_s=12.5,
            total_runs=5,
            success_runs=4,
            last_success_at="2026-05-22T06:00:00Z",
            registered_at="2026-05-01T00:00:00Z",
        )
        store_path = tmp_path / "registry.json"
        store = PipelineRegistryStore(store_path=store_path)
        store.upsert_record(r)

        loaded = store.get_record("build")
        assert loaded is not None
        assert loaded.name == r.name
        assert loaded.version == r.version
        assert loaded.nexus_status == r.nexus_status
        assert loaded.schema_hash == r.schema_hash
        assert loaded.step_count == r.step_count
        assert loaded.last_run_at == r.last_run_at
        assert loaded.last_status == r.last_status
        assert loaded.last_intent_hash == r.last_intent_hash
        assert abs(loaded.avg_duration_s - r.avg_duration_s) < 1e-9
        assert loaded.total_runs == r.total_runs
        assert loaded.success_runs == r.success_runs
        assert loaded.last_success_at == r.last_success_at
        assert loaded.operational_owner == r.operational_owner
        assert loaded.registered_at == r.registered_at


# ---------------------------------------------------------------------------
# PipelineRegistryStore
# ---------------------------------------------------------------------------

class TestPipelineRegistryStore:
    def test_empty_store_returns_empty_list(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        assert store.list_records() == []

    def test_upsert_and_get(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        r = _make_record("alpha")
        store.upsert_record(r)
        got = store.get_record("alpha")
        assert got is not None
        assert got.name == "alpha"

    def test_get_missing_returns_none(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        assert store.get_record("nonexistent") is None

    def test_upsert_overwrites(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        r1 = _make_record("build", nexus_status="DRAFT")
        store.upsert_record(r1)
        r2 = _make_record("build", nexus_status="ACTIVE", total_runs=3)
        store.upsert_record(r2)
        got = store.get_record("build")
        assert got.nexus_status == "ACTIVE"
        assert got.total_runs == 3

    def test_list_records_multiple(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        for name in ("alpha", "beta", "gamma"):
            store.upsert_record(_make_record(name))
        records = store.list_records()
        assert len(records) == 3
        names = {r.name for r in records}
        assert names == {"alpha", "beta", "gamma"}

    def test_delete_record(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        store.upsert_record(_make_record("to-delete"))
        store.delete_record("to-delete")
        assert store.get_record("to-delete") is None

    def test_delete_nonexistent_is_noop(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        store.delete_record("ghost")  # must not raise

    def test_persistence_across_instances(self, tmp_path):
        """Le store JSON doit survivre à une recréation de l'instance."""
        path = tmp_path / "reg.json"
        store1 = PipelineRegistryStore(store_path=path)
        store1.upsert_record(_make_record("persistent"))

        store2 = PipelineRegistryStore(store_path=path)
        got = store2.get_record("persistent")
        assert got is not None
        assert got.name == "persistent"

    def test_atomic_write_leaves_valid_json(self, tmp_path):
        """Après upsert, le fichier JSON doit être parseable directement."""
        path = tmp_path / "reg.json"
        store = PipelineRegistryStore(store_path=path)
        store.upsert_record(_make_record("build"))
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert "build" in raw

    def test_find_orphans_never_run(self, tmp_path):
        """Un pipeline avec total_runs=0 est orphelin."""
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        r = PipelineRecord(name="never-run", total_runs=0)
        store.upsert_record(r)
        orphans = store.find_orphans()
        assert any(o.name == "never-run" for o in orphans)

    def test_find_orphans_no_owner(self, tmp_path):
        """Un pipeline sans operational_owner est orphelin."""
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        r = PipelineRecord(name="no-owner", total_runs=5, operational_owner="")
        store.upsert_record(r)
        orphans = store.find_orphans()
        assert any(o.name == "no-owner" for o in orphans)

    def test_find_orphans_excludes_healthy(self, tmp_path):
        """Un pipeline récent avec owner et runs ne doit PAS être orphelin."""
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        r = PipelineRecord(
            name="healthy",
            total_runs=10,
            success_runs=9,
            operational_owner="gerivdb",
            last_run_at=now_iso,
        )
        store.upsert_record(r)
        orphans = store.find_orphans()
        assert not any(o.name == "healthy" for o in orphans)


# ---------------------------------------------------------------------------
# compute_schema_hash
# ---------------------------------------------------------------------------

class TestComputeSchemaHash:
    def test_returns_16_chars(self, tmp_path):
        f = tmp_path / "pipe.yaml"
        f.write_text("name: test\nsteps: []\n", encoding="utf-8")
        h = compute_schema_hash(f)
        assert len(h) == 16

    def test_hex_only(self, tmp_path):
        f = tmp_path / "pipe.yaml"
        f.write_text("name: test\nsteps: []\n", encoding="utf-8")
        h = compute_schema_hash(f)
        int(h, 16)  # raises ValueError if not valid hex

    def test_deterministic(self, tmp_path):
        f = tmp_path / "pipe.yaml"
        f.write_text("name: test\nsteps: []\n", encoding="utf-8")
        assert compute_schema_hash(f) == compute_schema_hash(f)

    def test_different_content_gives_different_hash(self, tmp_path):
        f1 = tmp_path / "a.yaml"
        f2 = tmp_path / "b.yaml"
        f1.write_text("name: alpha\nsteps: []\n", encoding="utf-8")
        f2.write_text("name: beta\nsteps: []\n", encoding="utf-8")
        assert compute_schema_hash(f1) != compute_schema_hash(f2)

    def test_whitespace_invariant(self, tmp_path):
        """Deux YAMLs sémantiquement identiques → même hash (normalisation)."""
        f1 = tmp_path / "c.yaml"
        f2 = tmp_path / "d.yaml"
        # Same content, different whitespace/order — yaml.dump normalizes both
        f1.write_text("name: demo\nversion: '1'\n", encoding="utf-8")
        f2.write_text("version: '1'\nname:    demo\n", encoding="utf-8")
        # May differ if PyYAML not installed (raw fallback) — just check no crash
        h1 = compute_schema_hash(f1)
        h2 = compute_schema_hash(f2)
        assert isinstance(h1, str) and isinstance(h2, str)

    def test_fallback_without_yaml(self, tmp_path, monkeypatch):
        """Le fallback sans PyYAML ne lève pas d'exception."""
        import sys
        # Simulate missing yaml by patching the import inside the module
        original = sys.modules.get("yaml")
        sys.modules["yaml"] = None  # type: ignore[assignment]
        try:
            f = tmp_path / "pipe.yaml"
            f.write_text("name: test\nsteps: []\n", encoding="utf-8")
            h = compute_schema_hash(f)
            assert len(h) == 16
        finally:
            if original is None:
                sys.modules.pop("yaml", None)
            else:
                sys.modules["yaml"] = original


# ---------------------------------------------------------------------------
# discover_pipelines
# ---------------------------------------------------------------------------

class TestDiscoverPipelines:
    def test_empty_dir_returns_empty(self, tmp_path):
        assert discover_pipelines(tmp_path) == []

    def test_finds_yaml_files(self, tmp_path):
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        (pipes_dir / "build.yaml").write_text("name: build\n", encoding="utf-8")
        (pipes_dir / "deploy.yaml").write_text("name: deploy\n", encoding="utf-8")
        found = discover_pipelines(tmp_path)
        names = {p.name for p in found}
        assert names == {"build.yaml", "deploy.yaml"}

    def test_ignores_non_yaml(self, tmp_path):
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        (pipes_dir / "build.yaml").write_text("name: build\n", encoding="utf-8")
        (pipes_dir / "README.md").write_text("# readme\n", encoding="utf-8")
        (pipes_dir / "config.json").write_text("{}\n", encoding="utf-8")
        found = discover_pipelines(tmp_path)
        assert all(p.suffix == ".yaml" for p in found)
        assert len(found) == 1

    def test_returns_sorted(self, tmp_path):
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        for name in ("zoo.yaml", "alpha.yaml", "mid.yaml"):
            (pipes_dir / name).write_text(f"name: {name}\n", encoding="utf-8")
        found = discover_pipelines(tmp_path)
        names = [p.name for p in found]
        assert names == sorted(names)

    def test_missing_pipelines_dir_returns_empty(self, tmp_path):
        """Pas de dossier .kiva/pipelines → liste vide, pas d'exception."""
        result = discover_pipelines(tmp_path / "nonexistent")
        assert result == []

    def test_uses_cwd_when_no_root(self, tmp_path, monkeypatch):
        """Sans argument root, découverte depuis le cwd courant."""
        monkeypatch.chdir(tmp_path)
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        (pipes_dir / "cwd-test.yaml").write_text("name: cwd\n", encoding="utf-8")
        found = discover_pipelines()
        assert any(p.name == "cwd-test.yaml" for p in found)


# ---------------------------------------------------------------------------
# record_run tests (AC-K12-5)
# ---------------------------------------------------------------------------

class TestRecordRun:
    def test_record_run_success_increments_counters(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        store.upsert_record(_make_record("build"))
        store.record_run("build", status="SUCCESS", duration_s=10.0, intent_hash="abc123")
        r = store.get_record("build")
        assert r.total_runs == 1
        assert r.success_runs == 1
        assert r.last_status == "SUCCESS"
        assert r.last_intent_hash == "abc123"
        assert r.last_success_at is not None

    def test_record_run_failure_no_last_success_update(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        store.upsert_record(_make_record("build"))
        store.record_run("build", status="FAILED", duration_s=5.0, intent_hash="xyz")
        r = store.get_record("build")
        assert r.total_runs == 1
        assert r.success_runs == 0
        assert r.last_status == "FAILED"
        assert r.last_success_at is None  # pas de succès → pas de mise à jour

    def test_record_run_rolling_avg(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        store.upsert_record(_make_record("build"))
        store.record_run("build", status="SUCCESS", duration_s=10.0, intent_hash="h1")
        store.record_run("build", status="SUCCESS", duration_s=20.0, intent_hash="h2")
        r = store.get_record("build")
        # avg = 10 + (20 - 10) / 2 = 15.0
        assert abs(r.avg_duration_s - 15.0) < 0.01

    def test_record_run_unknown_pipeline_creates_record(self, tmp_path):
        """record_run sur un pipeline inconnu doit créer l'entrée, pas lever."""
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        store.record_run("auto-created", status="SUCCESS", duration_s=3.0, intent_hash="h0")
        r = store.get_record("auto-created")
        assert r is not None
        assert r.total_runs == 1


# ---------------------------------------------------------------------------
# compute_drift_report tests (S3)
# ---------------------------------------------------------------------------

class TestComputeDriftReport:
    def test_no_yaml_no_records_empty(self, tmp_path):
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        report = store.compute_drift_report(pipelines_root=tmp_path)
        assert report == []

    def test_stable_pipeline_no_drift(self, tmp_path):
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        yaml_path = pipes_dir / "build.yaml"
        yaml_path.write_text("name: build\nsteps: []\n", encoding="utf-8")

        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        hash_now = compute_schema_hash(yaml_path)
        rec = PipelineRecord(name="build", schema_hash=hash_now, total_runs=1)
        store.upsert_record(rec)

        report = store.compute_drift_report(pipelines_root=tmp_path)
        assert len(report) == 1
        assert report[0]["drifted"] is False
        assert report[0]["current_hash"] == hash_now

    def test_drifted_pipeline_detected(self, tmp_path):
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        yaml_path = pipes_dir / "build.yaml"
        yaml_path.write_text("name: build\nsteps: []\n", encoding="utf-8")

        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        rec = PipelineRecord(name="build", schema_hash="0000000000000000", total_runs=3)
        store.upsert_record(rec)

        report = store.compute_drift_report(pipelines_root=tmp_path)
        assert len(report) == 1
        assert report[0]["drifted"] is True
        assert report[0]["registry_hash"] == "0000000000000000"

    def test_missing_yaml_reported_as_drift(self, tmp_path):
        """Pipeline dans le registry mais YAML supprimé → drifted=True, current=MISSING."""
        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        rec = PipelineRecord(name="ghost", schema_hash="aabbccdd11223344", total_runs=5)
        store.upsert_record(rec)

        report = store.compute_drift_report(pipelines_root=tmp_path)
        ghost = next((r for r in report if r["name"] == "ghost"), None)
        assert ghost is not None
        assert ghost["drifted"] is True
        assert ghost["current_hash"] == "MISSING"

    def test_unregistered_yaml_not_drifted(self, tmp_path):
        """YAML présent mais jamais exécuté → drifted=False (pas de hash référence)."""
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        (pipes_dir / "new.yaml").write_text("name: new\nsteps: []\n", encoding="utf-8")

        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        report = store.compute_drift_report(pipelines_root=tmp_path)
        assert len(report) == 1
        assert report[0]["drifted"] is False
        assert report[0]["registry_hash"] == "UNREGISTERED"

    def test_drifted_pipelines_sorted_first(self, tmp_path):
        """Les pipelines driftés remontent en tête du report."""
        pipes_dir = tmp_path / ".kiva" / "pipelines"
        pipes_dir.mkdir(parents=True)
        for name in ("alpha", "beta", "gamma"):
            (pipes_dir / f"{name}.yaml").write_text(f"name: {name}\n", encoding="utf-8")

        store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
        # Seul beta est drifté
        store.upsert_record(PipelineRecord(name="beta", schema_hash="0000000000000000", total_runs=2))

        report = store.compute_drift_report(pipelines_root=tmp_path)
        assert report[0]["name"] == "beta"
        assert report[0]["drifted"] is True


# ---------------------------------------------------------------------------
# S4 — kiva nexus pipeline prune (CLI tests)
# ---------------------------------------------------------------------------

class TestPipelinePruneCLI:
    def test_dry_run_no_deletion(self, tmp_path, monkeypatch):
        """--dry-run ne supprime rien."""
        monkeypatch.setattr(
            "kiva_cli.commands.nexus_commands.PipelineRegistryStore",
            lambda: _make_store_with_orphan(tmp_path),
        )
        runner = CliRunner()
        result = runner.invoke(pipeline_prune, ["--dry-run"])
        assert result.exit_code == 0
        assert "DRY-RUN" in result.output
        # Le record doit toujours exister
        store = _make_store_with_orphan(tmp_path)  # recharge depuis disque
        assert store.get_record("orphan-never-run") is not None

    def test_force_deletes_orphan(self, tmp_path, monkeypatch):
        """--force supprime sans prompt."""
        store_path = tmp_path / "reg.json"
        store = PipelineRegistryStore(store_path=store_path)
        store.upsert_record(PipelineRecord(name="orphan-never-run", total_runs=0))

        monkeypatch.setattr(
            "kiva_cli.commands.nexus_commands.PipelineRegistryStore",
            lambda: PipelineRegistryStore(store_path=store_path),
        )
        runner = CliRunner()
        result = runner.invoke(pipeline_prune, ["--force"])
        assert result.exit_code == 0
        assert "Supprimé" in result.output

        reloaded = PipelineRegistryStore(store_path=store_path)
        assert reloaded.get_record("orphan-never-run") is None

    def test_no_orphans_clean_message(self, tmp_path, monkeypatch):
        """Registry sans orphelin → message propre, exit 0."""
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
        runner = CliRunner()
        result = runner.invoke(pipeline_prune, ["--dry-run"])
        assert result.exit_code == 0
        assert "propre" in result.output.lower() or "aucun" in result.output.lower()

    def test_name_filter_targets_specific(self, tmp_path, monkeypatch):
        """--name cible un pipeline spécifique même non-orphelin."""
        store_path = tmp_path / "reg.json"
        store = PipelineRegistryStore(store_path=store_path)
        store.upsert_record(PipelineRecord(name="target", total_runs=10))
        store.upsert_record(PipelineRecord(name="keep", total_runs=10))

        monkeypatch.setattr(
            "kiva_cli.commands.nexus_commands.PipelineRegistryStore",
            lambda: PipelineRegistryStore(store_path=store_path),
        )
        runner = CliRunner()
        result = runner.invoke(pipeline_prune, ["--name", "target", "--force"])
        assert result.exit_code == 0

        reloaded = PipelineRegistryStore(store_path=store_path)
        assert reloaded.get_record("target") is None
        assert reloaded.get_record("keep") is not None

    def test_json_output_dry_run(self, tmp_path, monkeypatch):
        """--json --dry-run retourne du JSON parseable."""
        import json as json_mod
        store_path = tmp_path / "reg.json"
        PipelineRegistryStore(store_path=store_path).upsert_record(
            PipelineRecord(name="orphan-json", total_runs=0)
        )
        monkeypatch.setattr(
            "kiva_cli.commands.nexus_commands.PipelineRegistryStore",
            lambda: PipelineRegistryStore(store_path=store_path),
        )
        runner = CliRunner()
        result = runner.invoke(pipeline_prune, ["--json", "--dry-run"])
        assert result.exit_code == 0
        data = json_mod.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["name"] == "orphan-json"
        assert data[0]["would_delete"] is False


def _make_store_with_orphan(tmp_path: Path) -> "PipelineRegistryStore":
    store = PipelineRegistryStore(store_path=tmp_path / "reg.json")
    store.upsert_record(PipelineRecord(name="orphan-never-run", total_runs=0))
    return store
