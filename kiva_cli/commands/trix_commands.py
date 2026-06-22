"""KIVA-TRIX integration -- kiva trix commands (EPIC-202 S4).

Group: kiva trix
Commands:
  run                   Execute le pipeline snapshot -> chunks
  chunk-list            Liste les chunks generes
  chunk-stats           Statistiques sur les chunks
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import click


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_SNAPSHOT_PATH = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\LYCOS\lycos.snapshot")
DEFAULT_TRIX_TOOLS = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\TRIX\tools")
DEFAULT_OUTPUT_DIR = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\TRIX\output\chunks")
DEFAULT_HASH_STORE = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\TRIX\output\hash_store.json")
DEFAULT_TOPOS_PATH = Path(r"D:\DO\WEB\TOOLS\L1-INFRA\TOPOS\topology.yaml")


def _run_python(script_name, args, tools_dir=DEFAULT_TRIX_TOOLS):
    """Run a Python script from the TRIX tools directory."""
    script_path = tools_dir / script_name
    if not script_path.exists():
        click.echo(f"[ERROR] Script introuvable: {script_path}", err=True)
        sys.exit(1)
    cmd = [sys.executable, str(script_path)] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        click.echo(result.stdout)
    if result.stderr:
        click.echo(result.stderr, err=True)
    return result


# ---------------------------------------------------------------------------
# kiva trix group
# ---------------------------------------------------------------------------

@click.group("trix")
def trix_cli():
    """TRIX snapshot pipeline (snapshot -> semantic chunks -> VDB)."""
    pass


@trix_cli.command("run")
@click.option("--snapshot", default=str(DEFAULT_SNAPSHOT_PATH),
              help="Chemin vers lycos.snapshot")
@click.option("--output", default=str(DEFAULT_OUTPUT_DIR),
              help="Repertoire de sortie des chunks")
@click.option("--incremental/--full", default=True,
              help="Mode incremental (skip repos inchanges)")
@click.option("--hash-store", default=str(DEFAULT_HASH_STORE),
              help="Chemin vers le store de hashes")
@click.option("--topology", default=str(DEFAULT_TOPOS_PATH),
              help="Chemin vers topology.yaml")
@click.option("--wal-output", default=None,
              help="Chemin pour la WAL entry JSON")
def trix_run(snapshot, output, incremental, hash_store, topology, wal_output):
    """
    Execute le pipeline complet: snapshot -> chunks semantiques.

    Etapes:
    1. Parse lycos.snapshot (SnapshotParser)
    2. Normalise en chunks JSON (ChunkNormalizer)
    3. Hash incrementel (IncrementalHasher) si --incremental
    4. Ecrit WAL entry
    """
    start_time = time.time()

    snapshot_path = Path(snapshot)
    if not snapshot_path.exists():
        click.echo(f"[ERROR] Snapshot introuvable: {snapshot}", err=True)
        sys.exit(1)

    # Step 1+2: Normalize chunks
    click.echo(f"[INFO] Pipeline TRIX: {snapshot}")
    norm_result = _run_python("chunk_normalizer.py", [
        str(snapshot),
        "--output", output,
        "--topology", topology,
    ])

    if norm_result.returncode != 0:
        click.echo("[ERROR] Chunk normalization failed", err=True)
        sys.exit(1)

    # Step 3: Incremental hash (if incremental mode and hash store exists)
    if incremental and Path(hash_store).exists():
        click.echo("[INFO] Mode incremental: detection des changements...")
        hash_result = _run_python("incremental_hasher.py", [
            "--chunks-dir", output,
            "--hash-store", hash_store,
        ])
        if hash_result.returncode != 0:
            click.echo("[WARN] Incremental hash failed, continuing...")

    duration_ms = int((time.time() - start_time) * 1000)

    # Count chunks
    chunks_dir = Path(output)
    chunk_count = len(list(chunks_dir.glob("*.json"))) - 1  # Exclude index.json

    click.echo(f"[INFO] Pipeline termine en {duration_ms}ms")
    click.echo(f"[INFO] Chunks: {chunk_count}")

    # Step 4: WAL entry (if requested)
    if wal_output:
        intent_hash = f"0xTRIX_SNAPSHOT_{int(start_time)}"
        wal_entry = {
            "event_type": "SNAPSHOT_PIPELINE_RUN",
            "intent_hash": intent_hash,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "stats": {
                "total_chunks": chunk_count,
                "snapshot_path": str(snapshot),
                "output_dir": output,
                "incremental": incremental,
            },
            "duration_ms": duration_ms,
        }
        with open(wal_output, "w", encoding="utf-8") as f:
            json.dump(wal_entry, f, indent=2)
        click.echo(f"[INFO] WAL entry: {wal_output}")


@trix_cli.command("chunk-list")
@click.option("--output", default=str(DEFAULT_OUTPUT_DIR),
              help="Repertoire des chunks")
@click.option("--repo", default=None,
              help="Filtrer par repo")
def trix_chunk_list(output, repo):
    """Liste les chunks generes."""
    chunks_dir = Path(output)
    index_file = chunks_dir / "index.json"

    if not index_file.exists():
        click.echo(f"[ERROR] Index introuvable: {index_file}", err=True)
        sys.exit(1)

    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)

    chunks = index.get("chunks", [])
    repos = set()
    type_counts = {}

    for chunk in chunks:
        r = chunk.get("repo", "")
        repos.add(r)
        t = chunk.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    click.echo(f"Total chunks: {len(chunks)}")
    click.echo(f"Repos: {len(repos)}")
    click.echo(f"Types:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        click.echo(f"  {t}: {count}")

    if repo:
        repo_chunks = [c for c in chunks if c.get("repo") == repo]
        click.echo(f"\nChunks pour {repo}: {len(repo_chunks)}")
        for chunk in repo_chunks[:20]:
            click.echo(f"  {chunk['chunk_id']} ({chunk['type']})")
        if len(repo_chunks) > 20:
            click.echo(f"  ... et {len(repo_chunks) - 20} autres")


@trix_cli.command("chunk-stats")
@click.option("--output", default=str(DEFAULT_OUTPUT_DIR),
              help="Repertoire des chunks")
def trix_chunk_stats(output):
    """Statistiques sur les chunks generes."""
    chunks_dir = Path(output)
    index_file = chunks_dir / "index.json"

    if not index_file.exists():
        click.echo(f"[ERROR] Index introuvable: {index_file}", err=True)
        sys.exit(1)

    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)

    repos = index.get("repos", [])
    chunks = index.get("chunks", [])

    # Load a sample chunk for reference
    sample = {}
    for chunk_meta in chunks[:1]:
        chunk_file = chunks_dir / chunk_meta["file"]
        if chunk_file.exists():
            with open(chunk_file, "r", encoding="utf-8") as f:
                sample = json.load(f)
            break

    click.echo(f"Chunks totals: {len(chunks)}")
    click.echo(f"Repos couverts: {len(repos)}")
    click.echo(f"Date generation: {index.get('generated', '?')}")
    click.click(f"Version: {index.get('version', '?')}")

    if sample:
        click.echo(f"\nExemple de chunk:")
        click.echo(json.dumps(sample, indent=2, ensure_ascii=False))
