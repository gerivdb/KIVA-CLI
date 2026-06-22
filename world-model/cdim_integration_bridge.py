#!/usr/bin/env python3
"""CDIM Integration Bridge — PRD-049.

Bridge entre le module CDIM (world-model/) et KIVA-CLI.
Expose les opérations CDIM via `kiva nexus` et le MCP tool nexus_query.

Usage:
    python -m world-model.cdim_integration_bridge --query --repo NEXUS
    python -m world-model.cdim_integration_bridge --causal --events events.json
    python -m world-model.cdim_integration_bridge --counterfactual --hypothesis "What if O3 delayed?"
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

NEXUS_ROOT = Path(__file__).resolve().parent.parent
WORLD_MODEL_DIR = Path(__file__).resolve().parent


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def query_kiva_nexus(path: str, section: str = "all") -> dict:
    """Interroge KIVA-CLI pour l'état NEXUS."""
    try:
        result = subprocess.run(
            ["python", "-m", "kiva_cli", "nexus", "query", path,
             "--section", section, "--format", "json"],
            capture_output=True, text=True, timeout=30,
            cwd=str(NEXUS_ROOT),
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr.strip(), "exit_code": result.returncode}
    except Exception as exc:
        return {"error": str(exc)}


def run_world_model(repo: str = "NEXUS") -> dict:
    """Lance le World Model Verse."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "world-model.world_model_verse",
             "--predict", "--repo", repo],
            capture_output=True, text=True, timeout=30,
            cwd=str(NEXUS_ROOT),
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr.strip()}
    except Exception as exc:
        return {"error": str(exc)}


def run_causal_consolidation(phi: int, **kwargs) -> dict:
    """Lance la Causal Consolidation (φ1, φ4, φ6)."""
    cmd = [sys.executable, "-m", "world-model.causal_consolidation", "--phi", str(phi)]
    for k, v in kwargs.items():
        cmd.extend([f"--{k}", str(v)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(NEXUS_ROOT))
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr.strip()}
    except Exception as exc:
        return {"error": str(exc)}


def run_counterfactual(hypothesis: str) -> dict:
    """Lance le Counterfactual Keel."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "world-model.counterfactual_keel",
             "--evaluate", "--scenario", hypothesis],
            capture_output=True, text=True, timeout=30,
            cwd=str(NEXUS_ROOT),
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr.strip()}
    except Exception as exc:
        return {"error": str(exc)}


def full_cdim_pipeline(repo: str = "NEXUS") -> dict:
    """Exécute le pipeline CDIM complet."""
    return {
        "timestamp": _now_iso(),
        "repo": repo,
        "kiva_state": query_kiva_nexus(str(NEXUS_ROOT)),
        "world_model": run_world_model(repo),
        "causal_phi1": run_causal_consolidation(1, events="[]"),
        "counterfactual": run_counterfactual(f"What if {repo} O3 was delayed?"),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CDIM Integration Bridge")
    parser.add_argument("--query", action="store_true", help="Query KIVA-CLI")
    parser.add_argument("--causal", action="store_true", help="Run causal consolidation")
    parser.add_argument("--phi", type=int, default=1, help="φ operation (1, 4, 6)")
    parser.add_argument("--events", type=str, help="Events JSON file")
    parser.add_argument("--counterfactual", action="store_true", help="Run counterfactual keel")
    parser.add_argument("--hypothesis", type=str, help="Counterfactual hypothesis")
    parser.add_argument("--full", action="store_true", help="Full CDIM pipeline")
    parser.add_argument("--repo", default="NEXUS", help="Target repo")
    args = parser.parse_args()

    if args.full:
        result = full_cdim_pipeline(args.repo)
    elif args.query:
        result = query_kiva_nexus(str(NEXUS_ROOT))
    elif args.causal:
        result = run_causal_consolidation(args.phi, events=args.events or "[]")
    elif args.counterfactual:
        result = run_counterfactual(args.hypothesis or "What if O3 delayed?")
    else:
        result = full_cdim_pipeline(args.repo)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
