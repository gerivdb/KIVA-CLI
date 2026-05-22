"""KIVA-012 S1 — Pipeline Registry (Foundation).

Provides:
- PipelineRecord dataclass
- PipelineRegistryStore (lightweight JSON store with atomic writes)
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PipelineRecord:
    """Persisted metadata for one pipeline definition."""

    name: str
    version: str = "1"
    nexus_status: str = "DRAFT"
    schema_hash: str = ""           # sha256(normalized_yaml)[:16]
    step_count: int = 0
    last_run_at: Optional[str] = None
    last_status: Optional[str] = None
    last_intent_hash: Optional[str] = None
    avg_duration_s: float = 0.0
    total_runs: int = 0
    success_runs: int = 0
    last_success_at: Optional[str] = None  # ISO du dernier SUCCESS (pour S3 drift schema_hash)
    operational_owner: str = "gerivdb"
    registered_at: str = ""


class PipelineRegistryStore:
    """Lightweight persistent store for PipelineRecord objects.

    Uses atomic write-then-rename to `~/.kiva/pipeline_registry.json`.
    """

    def __init__(self, path: Optional[Path] = None, store_path: Optional[Path] = None):
        # Support both "path" and "store_path" for flexibility
        target = store_path or path
        if target is None:
            target = Path.home() / ".kiva" / "pipeline_registry.json"
        self.path = target
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        """Atomic write using write-then-rename."""
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert_record(self, record: PipelineRecord) -> None:
        """Insert or update a record."""
        if not record.registered_at:
            record.registered_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self._data[record.name] = asdict(record)
        self._save()

    def get_record(self, name: str) -> Optional[PipelineRecord]:
        """Return a PipelineRecord or None."""
        raw = self._data.get(name)
        if not raw:
            return None
        return PipelineRecord(**raw)

    def list_records(self) -> list[PipelineRecord]:
        """Return all records sorted by name."""
        records = [PipelineRecord(**v) for v in self._data.values()]
        return sorted(records, key=lambda r: r.name)

    def find_orphans(self) -> list[PipelineRecord]:
        """Return records that look orphaned (never run, no owner, or very old)."""
        now = time.time()
        orphans: list[PipelineRecord] = []

        for raw in self._data.values():
            rec = PipelineRecord(**raw)

            is_orphan = False

            if rec.total_runs == 0:
                is_orphan = True
            elif not rec.operational_owner or rec.operational_owner.strip() == "":
                is_orphan = True
            elif rec.last_run_at:
                try:
                    last = time.mktime(time.strptime(rec.last_run_at, "%Y-%m-%dT%H:%M:%SZ"))
                    if (now - last) > (30 * 24 * 3600):  # 30 days
                        is_orphan = True
                except ValueError:
                    is_orphan = True

            if is_orphan:
                orphans.append(rec)

        return orphans

    def delete_record(self, name: str) -> bool:
        """Delete a record if it exists. Returns True if deleted."""
        if name in self._data:
            del self._data[name]
            self._save()
            return True
        return False

    def record_run(
        self,
        name: str,
        status: str,
        duration_s: float,
        intent_hash: str | None = None,
    ) -> None:
        """Update registry after a pipeline execution (non-blocking safe)."""
        rec = self.get_record(name) or PipelineRecord(name=name)

        rec.last_run_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rec.last_status = status
        if intent_hash:
            rec.last_intent_hash = intent_hash

        rec.total_runs += 1
        if status == "SUCCESS":
            rec.success_runs += 1
            rec.last_success_at = rec.last_run_at

        # Incremental average
        if rec.total_runs == 1:
            rec.avg_duration_s = duration_s
        else:
            rec.avg_duration_s = (
                (rec.avg_duration_s * (rec.total_runs - 1) + duration_s) / rec.total_runs
            )

        self.upsert_record(rec)


# ---------------------------------------------------------------------------
# Discovery & schema hash helpers (KIVA-012 S1)
# ---------------------------------------------------------------------------

import hashlib

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def compute_schema_hash(yaml_path: Path) -> str:
    """sha256 du YAML normalisé (strip + sorted keys) → 16 premiers caractères."""
    try:
        raw = yaml_path.read_text(encoding="utf-8")
        if _HAS_YAML:
            data = yaml.safe_load(raw)
            normalized = yaml.dump(data, default_flow_style=False, sort_keys=True)
        else:
            normalized = raw.strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    except Exception:
        # Fallback très conservateur
        try:
            return hashlib.sha256(yaml_path.read_bytes()).hexdigest()[:16]
        except Exception:
            return ""


_PIPELINES_DIR_NAME = ".kiva/pipelines"


def discover_pipelines(root: Path | None = None) -> list[Path]:
    """Retourne tous les *.yaml dans <root>/.kiva/pipelines/."""
    base = (root or Path.cwd()) / _PIPELINES_DIR_NAME
    if not base.exists():
        return []
    return sorted(base.glob("*.yaml"))
