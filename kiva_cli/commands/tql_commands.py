"""KIVA-TQL integration -- kiva tql commands (EPIC-203 S4).

Group: kiva tql
Commands:
  query <tql>           Execute une requete TQL
  index                 Construit l'index VDB a partir des chunks TRIX
  stats                 Statistiques sur l'index VDB
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import click


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_VDB_SRC = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\VDB\src")
DEFAULT_CHUNKS_DIR = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\TRIX\output\chunks")
DEFAULT_TOPOLOGY = Path(r"D:\DO\WEB\TOOLS\L1-INFRA\TOPOS\topology.yaml")
DEFAULT_INDEX_PATH = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\VDB\output\vdb_index.json")


def _run_tql(query_str, topology=None, chunks_dir=None, index_path=None):
    """Run TQL query via the VDB query engine."""
    cmd = [sys.executable, str(DEFAULT_VDB_SRC / "tql_query_engine.py"), query_str, "--quiet"]

    if topology:
        cmd.extend(["--topology", str(topology)])
    if chunks_dir:
        cmd.extend(["--chunks-dir", str(chunks_dir)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr or result.stdout}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"output": result.stdout}


# ---------------------------------------------------------------------------
# kiva tql group
# ---------------------------------------------------------------------------

@click.group("tql")
def tql_cli():
    """TQL query engine (DEPS, CONSUMERS, INTERFACES, STATUS, PATH)."""
    pass


@tql_cli.command("query")
@click.argument("query_str")
@click.option("--topology", default=str(DEFAULT_TOPOLOGY),
              help="Chemin vers topology.yaml")
@click.option("--chunks-dir", default=str(DEFAULT_CHUNKS_DIR),
              help="Repertoire des chunks TRIX")
@click.option("--index", default=str(DEFAULT_INDEX_PATH),
              help="Chemin vers l'index VDB JSON")
def tql_query(query_str, topology, chunks_dir, index):
    """
    Execute une requete TQL.

    Requetes supportees:
      DEPS <repo>                 -- dependances directes
      CONSUMERS <repo>            -- repos qui dependent du repo
      INTERFACES <repo>           -- APIs/schemas exposes
      STATUS <repo>               -- strate, statut, local_path
      PATH <repo_A> <repo_B>      -- chemin de dependances

    Exemples:
      kiva tql query "DEPS KIVA-CLI"
      kiva tql query "CONSUMERS NEXUS"
      kiva tql query "STATUS GOVERNANCE-HUB"
      kiva tql query "PATH KIVA-CLI BRAIN-DOCS"
    """
    result = _run_tql(query_str, topology=topology, chunks_dir=chunks_dir)
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@tql_cli.command("index")
@click.option("--chunks-dir", default=str(DEFAULT_CHUNKS_DIR),
              help="Repertoire des chunks TRIX")
@click.option("--topology", default=str(DEFAULT_TOPOLOGY),
              help="Chemin vers topology.yaml")
@click.option("--scan-root", default=None,
              help="Racine pour scan ECOS_ROOT.json")
@click.option("--output", default=str(DEFAULT_INDEX_PATH),
              help="Chemin de sauvegarde de l'index")
def tql_index(chunks_dir, topology, scan_root, output):
    """
    Construit l'index VDB a partir des chunks TRIX et de la topologie.
    """
    cmd = [
        sys.executable, str(DEFAULT_VDB_SRC / "vdb_indexer.py"),
        "--chunks-dir", chunks_dir,
        "--topology", topology,
        "--output", output,
    ]
    if scan_root:
        cmd.extend(["--scan-root", scan_root])

    result = subprocess.run(cmd, capture_output=True, text=True)
    click.echo(result.stdout)
    if result.stderr:
        click.echo(result.stderr, err=True)


@tql_cli.command("stats")
@click.option("--index", default=str(DEFAULT_INDEX_PATH),
              help="Chemin vers l'index VDB JSON")
def tql_stats(index):
    """Statistiques sur l'index VDB."""
    index_path = Path(index)
    if not index_path.exists():
        click.echo(f"[ERROR] Index introuvable: {index}", err=True)
        sys.exit(1)

    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = data.get("stats", {})
    repos = data.get("repos", {})
    deps = data.get("deps", {})
    interfaces = data.get("interfaces", {})

    click.echo(f"=== VDB Index Stats ===")
    click.echo(f"Repos: {len(repos)}")
    click.echo(f"Chunks: {stats.get('total_chunks', '?')}")
    click.echo(f"Indexed at: {stats.get('indexed_at', '?')}")
    click.echo(f"Build duration: {stats.get('duration_ms', '?')}ms")

    # Layer distribution
    layers = {}
    for repo, info in repos.items():
        layer = info.get("layer", "unknown")
        layers[layer] = layers.get(layer, 0) + 1

    click.echo(f"\nLayer distribution:")
    for layer, count in sorted(layers.items()):
        click.echo(f"  {layer}: {count}")

    # Repos with most deps
    click.echo(f"\nRepos with most deps:")
    for repo, dep_list in sorted(deps.items(), key=lambda x: -len(x[1]))[:10]:
        if dep_list:
            click.echo(f"  {repo}: {len(dep_list)} deps")

    # Repos with most interfaces
    click.echo(f"\nRepos with most interfaces:")
    for repo, iface_list in sorted(interfaces.items(), key=lambda x: -len(x[1]))[:10]:
        if iface_list:
            click.echo(f"  {repo}: {len(iface_list)} interfaces")
