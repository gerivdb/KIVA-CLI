"""KIVA-012 S2 — kiva workflow commands (cross-format workflow catalog).

Group: kiva workflow
Commands:
  list                  List all discovered workflows across formats
  validate <name>       Validate a workflow file + registry presence
  register <path>       Register a workflow in both GOVERNANCE-HUB and local KIVA-CLI
  drift                 Detect unregistered/phantom workflows
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click

from kiva_cli.core.pipeline_loader import load_pipeline
from kiva_cli.core.pipeline_registry import PipelineRegistryStore, PipelineRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

KIVA_ROOT = Path(__file__).resolve().parent.parent.parent

# Canonical registry in GOVERNANCE-HUB
GOV_REGISTRY = KIVA_ROOT.parent / "GOVERNANCE-HUB" / "REGISTRY" / "workflows.yaml"
# Local KIVA-CLI registry
LOCAL_REGISTRY = Path.home() / ".kiva" / "pipeline_registry.json"


def _pipelines_dir() -> Path:
    return Path.cwd() / ".kiva" / "pipelines"


def _workflows_dir() -> Path:
    return Path.cwd() / ".kiva" / "workflows"


def _gov_workflows_dir() -> Path:
    return Path.cwd() / "workflows"


def _discover_pipeline_files() -> list[Path]:
    d = _pipelines_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.yaml"))


def _discover_kiva_workflow_files() -> list[Path]:
    d = _workflows_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.kiva.yml"))


def _discover_governance_workflow_files() -> list[Path]:
    d = _gov_workflows_dir()
    if not d.exists():
        return []
    return sorted(d.glob("*.yaml"))


def _load_local_registry() -> dict:
    if not LOCAL_REGISTRY.exists():
        return {}
    try:
        return json.loads(LOCAL_REGISTRY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _load_gov_registry() -> dict:
    if not GOV_REGISTRY.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(GOV_REGISTRY.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

@click.group("workflow")
def workflow_cli():
    """Cross-format workflow catalog and registration (KIVA-012 S2)."""


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@workflow_cli.command("list")
@click.option("--json", "as_json", is_flag=True, default=False, help="JSON output")
def workflow_list(as_json: bool):
    """List all discovered workflows across formats."""
    rows = []

    # .kiva/pipelines/*.yaml
    for p in _discover_pipeline_files():
        rows.append({
            "name": p.stem,
            "path": str(p),
            "format": "kiva-pipeline",
            "executor": "KIVA-CLI",
            "status": "unknown",
        })

    # .kiva/workflows/*.kiva.yml
    for p in _discover_kiva_workflow_files():
        rows.append({
            "name": p.stem,
            "path": str(p),
            "format": "kiva-workflow",
            "executor": "GitHub Actions",
            "status": "unknown",
        })

    # workflows/*.yaml
    for p in _discover_governance_workflow_files():
        rows.append({
            "name": p.stem,
            "path": str(p),
            "format": "governance",
            "executor": "none",
            "status": "unknown",
        })

    if as_json:
        click.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    if not rows:
        click.echo("No workflows found.")
        return

    click.echo(f"Workflows ({len(rows)}):")
    for r in rows:
        click.echo(f"  {r['name']:<32} {r['format']:<16} {r['executor']:<16} {r['path']}")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@workflow_cli.command("validate")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, default=False)
def workflow_validate(name: str, as_json: bool):
    """Validate a workflow file + registry presence."""
    # Search in all locations
    candidates = (
        _discover_pipeline_files()
        + _discover_kiva_workflow_files()
        + _discover_governance_workflow_files()
    )

    target = None
    for c in candidates:
        if c.stem == name:
            target = c
            break

    if target is None:
        click.echo(f"[ERROR] Workflow not found: '{name}'", err=True)
        raise SystemExit(1)

    errors = []
    warnings = []

    # 1) Check IntentHash
    try:
        content = target.read_text(encoding="utf-8")
        if "intent_hash:" not in content and "IntentHash:" not in content:
            warnings.append("Missing intent_hash")
    except OSError as e:
        errors.append(f"Cannot read file: {e}")

    # 2) Check registry presence
    local = _load_local_registry()
    gov = _load_gov_registry()
    in_local = name in local
    in_gov = any(w.get("name") == name for w in gov.get("workflows", []))

    if not in_local and not in_gov:
        warnings.append("Not registered in any registry (local or GOVERNANCE-HUB)")

    # 3) If kiva-pipeline, try to load
    if target.suffix == ".yaml" and ".kiva/pipelines" in str(target):
        try:
            load_pipeline(target)
        except Exception as e:
            errors.append(f"Pipeline load error: {e}")

    ok = len(errors) == 0

    if as_json:
        click.echo(json.dumps({
            "name": name,
            "path": str(target),
            "valid": ok,
            "errors": errors,
            "warnings": warnings,
            "in_local_registry": in_local,
            "in_gov_registry": in_gov,
        }, indent=2, ensure_ascii=False))
        if not ok:
            raise SystemExit(1)
        return

    if ok:
        click.echo(f"[OK] Workflow '{name}' is valid.")
        for w in warnings:
            click.echo(f"  [WARN] {w}")
    else:
        click.echo(f"[FAIL] Workflow '{name}' has errors:", err=True)
        for e in errors:
            click.echo(f"  - {e}", err=True)
        for w in warnings:
            click.echo(f"  [WARN] {w}", err=True)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

@workflow_cli.command("register")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--name", default=None, help="Override workflow name")
@click.option("--description", default=None, help="Workflow description")
@click.option("--format", "fmt", default=None, help="Format override")
@click.option("--executor", default=None, help="Executor override")
def workflow_register(
    path: Path,
    name: Optional[str],
    description: Optional[str],
    fmt: Optional[str],
    executor: Optional[str],
):
    """Register a workflow in both GOVERNANCE-HUB and local KIVA-CLI."""
    # Determine format
    if path.suffix == ".yaml" and ".kiva/pipelines" in str(path):
        detected_format = "kiva-pipeline"
        detected_executor = "KIVA-CLI"
    elif path.suffix == ".kiva.yml":
        detected_format = "kiva-workflow"
        detected_executor = "GitHub Actions"
    elif path.suffix == ".yaml":
        detected_format = "governance"
        detected_executor = "none"
    else:
        detected_format = "unknown"
        detected_executor = "unknown"

    workflow_format = fmt or detected_format
    workflow_executor = executor or detected_executor
    workflow_name = name or path.stem

    # 1) Update GOVERNANCE-HUB registry
    gov_reg = _load_gov_registry()
    if "workflows" not in gov_reg:
        gov_reg["workflows"] = []

    # Check if already exists
    existing = [w for w in gov_reg["workflows"] if w.get("name") == workflow_name]
    entry = {
        "name": workflow_name,
        "repo": "GeriCode",
        "path": str(path),
        "format": workflow_format,
        "executor": workflow_executor,
        "status": "active",
        "description": description or "",
        "registered_at": "2026-09-21",
    }

    if existing:
        gov_reg["workflows"].remove(existing[0])
    gov_reg["workflows"].append(entry)

    GOV_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    GOV_REGISTRY.write_text(
        __import__("yaml").safe_dump(gov_reg, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    # 2) Update local KIVA-CLI registry
    try:
        store = PipelineRegistryStore(store_path=LOCAL_REGISTRY)
        schema_hash = ""
        try:
            content = path.read_text(encoding="utf-8")
            import hashlib
            schema_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
        except OSError:
            pass

        record = PipelineRecord(
            name=workflow_name,
            version="1",
            nexus_status="DRAFT",
            schema_hash=schema_hash,
            step_count=0,
            operational_owner="gerivdb",
            registered_at="2026-09-21",
        )
        store.upsert_record(record)
    except Exception as e:
        click.echo(f"[WARN] Local registry update failed: {e}", err=True)

    click.echo(f"REGISTERED: {workflow_name}")
    click.echo(f"  GOVERNANCE-HUB: {GOV_REGISTRY}")
    click.echo(f"  Local KIVA-CLI: {LOCAL_REGISTRY}")


# ---------------------------------------------------------------------------
# drift
# ---------------------------------------------------------------------------

@workflow_cli.command("drift")
@click.option("--json", "as_json", is_flag=True, default=False)
def workflow_drift(as_json: bool):
    """Detect unregistered/phantom workflows."""
    discovered = {}

    for p in _discover_pipeline_files():
        discovered[p.stem] = {"path": str(p), "format": "kiva-pipeline"}
    for p in _discover_kiva_workflow_files():
        discovered[p.stem] = {"path": str(p), "format": "kiva-workflow"}
    for p in _discover_governance_workflow_files():
        discovered[p.stem] = {"path": str(p), "format": "governance"}

    local = _load_local_registry()
    gov = _load_gov_registry()
    gov_names = {w.get("name") for w in gov.get("workflows", [])}

    unregistered = []
    for name, info in discovered.items():
        in_local = name in local
        in_gov = name in gov_names
        if not in_local and not in_gov:
            unregistered.append({
                "name": name,
                "path": info["path"],
                "format": info["format"],
                "issue": "not_registered",
            })

    phantom = []
    for name in set(list(local.keys()) + list(gov_names)):
        if name not in discovered:
            phantom.append({
                "name": name,
                "issue": "phantom",
            })

    result = {
        "discovered": len(discovered),
        "unregistered": len(unregistered),
        "phantom": len(phantom),
        "unregistered_list": unregistered,
        "phantom_list": phantom,
    }

    if as_json:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        if unregistered or phantom:
            raise SystemExit(1)
        return

    click.echo(f"Discovered: {len(discovered)}")
    click.echo(f"Unregistered: {len(unregistered)}")
    click.echo(f"Phantom: {len(phantom)}")

    if unregistered:
        click.echo("\nUnregistered workflows:")
        for u in unregistered:
            click.echo(f"  {u['name']} ({u['path']})")

    if phantom:
        click.echo("\nPhantom registry entries:")
        for p in phantom:
            click.echo(f"  {p['name']}")

    if unregistered or phantom:
        raise SystemExit(1)
