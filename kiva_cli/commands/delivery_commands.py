#!/usr/bin/env python3
"""
delivery_commands.py — KIVA-CLI delivery commands.

Provides:
- kiva deliver <repo-l6> : exécute le workflow de delivery mutualisé
  (build -> test -> package -> audit) via CTULU familles/delivery-engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

_CTULU_ROOT = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\CTULU")


def _load_ctulu_delivery():
    import importlib.util

    module_path = _CTULU_ROOT / "familles" / "delivery-engine" / "delivery_engine.py"
    spec = importlib.util.spec_from_file_location("ctulu_delivery_engine", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@click.group(name="deliver")
def deliver_cli():
    """Delivery engine mutualisé pour repos L6-WORK."""


@deliver_cli.command(name="run")
@click.argument("repo_path", type=click.Path(exists=True, path_type=Path))
@click.option("--workflow", multiple=True, default=["build", "test", "package", "audit"])
def deliver_run(repo_path: Path, workflow: tuple[str, ...]):
    """Exécute le workflow de delivery sur REPO_PATH."""
    try:
        engine_mod = _load_ctulu_delivery()
    except Exception as exc:
        click.echo(f"Erreur chargement delivery-engine CTULU: {exc}")
        raise click.ClickException(str(exc))

    engine = engine_mod.DeliveryEngine(repo_root=repo_path, workflow=list(workflow))
    results = engine.run()
    overall = all(r.success for r in results)
    for r in results:
        status = "OK" if r.success else "FAIL"
        click.echo(f"[{status}] {r.step} ({r.duration_s:.2f}s)")
        if not r.success and r.stderr:
            click.echo(r.stderr)
    click.echo(engine_mod.DeliveryResult(
        step="workflow",
        success=overall,
        returncode=0 if overall else 1,
        stdout=engine.to_json(),
    ).stdout)
    if not overall:
        raise click.ClickException("Workflow delivery échoué")


__all__ = ["deliver_cli"]
