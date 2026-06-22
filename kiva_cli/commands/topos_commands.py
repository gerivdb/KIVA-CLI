"""KIVA-008 S2 -- kiva topos commands (TOPOS topology sync/diff/export).

Group: kiva topos
Commands:
  sync                  Reconcilie TOPOS/topology.yaml avec tous les ECOS_ROOT.json
  diff                  Detecte les divergences TOPOS vs ECOS_ROOT.json locaux
  export --format FMT   Exporte le graphe (json|mermaid|dot)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import click

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_TOPOS_PATH = Path(r"D:\DO\WEB\TOOLS\L1-INFRA\TOPOS\topology.yaml")
NEXUS_REPORTS_PATH = Path(r"D:\DO\WEB\TOOLS\L0-CANON\NEXUS\reports")


def _load_topology(topos_path: Path) -> dict:
    """Charge topology.yaml."""
    if yaml is None:
        click.echo("[ERROR] PyYAML requis: pip install pyyaml", err=True)
        sys.exit(1)
    if not topos_path.exists():
        click.echo(f"[ERROR] topology.yaml introuvable: {topos_path}", err=True)
        sys.exit(1)
    with open(topos_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _find_ecos_roots(scan_root: str) -> list:
    """Scan recursif pour trouver tous les ECOS_ROOT.json."""
    roots = []
    for root, dirs, files in os.walk(scan_root):
        dirs[:] = [
            d for d in dirs
            if d not in (".git", ".zig-cache", ".pytest-cache",
                         "__pycache__", "node_modules", ".swarm",
                         ".kilo", "zig-out", ".github")
        ]
        if "ECOS_ROOT.json" in files:
            roots.append(Path(root) / "ECOS_ROOT.json")
    return roots


def _parse_ecos_root(path: Path) -> dict:
    """Parse un ECOS_ROOT.json."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# kiva topos sync
# ---------------------------------------------------------------------------

@click.group("topos")
def topos_cli():
    """TOPOS topology management (sync, diff, export)."""
    pass


@topos_cli.command("sync")
@click.option("--topos-path", default=str(DEFAULT_TOPOS_PATH),
              help="Chemin vers topology.yaml")
@click.option("--scan-root", default=r"D:\DO\WEB\TOOLS",
              help="Racine pour le scan des ECOS_ROOT.json")
@click.option("--output", default=None,
              help="Chemin de sortie pour topology.yaml (default: ecrase l'existant)")
def topos_sync(topos_path, scan_root, output):
    """
    Reconcilie TOPOS/topology.yaml avec tous les ECOS_ROOT.json trouves.

    Lit tous les ECOS_ROOT.json du scan-root, extrait les dependances,
    et regenere topology.yaml.
    """
    import subprocess

    topos_path = Path(topos_path)
    output_path = Path(output) if output else topos_path

    # Use generate_topology.py if available
    gen_script = topos_path.parent / "scripts" / "generate_topology.py"
    if gen_script.exists():
        cmd = [
            sys.executable, str(gen_script),
            "--scan-root", scan_root,
            "--output", str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        click.echo(result.stdout)
        if result.returncode != 0:
            click.echo(result.stderr, err=True)
            sys.exit(result.returncode)
    else:
        # Inline generation
        click.echo(f"[INFO] Scan de {scan_root}...")
        ecos_roots = _find_ecos_roots(scan_root)
        click.echo(f"[INFO] {len(ecos_roots)} ECOS_ROOT.json trouves")

        nodes = {}
        edges = []
        for ecos_path in ecos_roots:
            data = _parse_ecos_root(ecos_path)
            if not data:
                continue
            name = data.get("name", ecos_path.parent.name)
            deps = data.get("dependencies", [])
            nodes[name] = {
                "layer": data.get("layer", ""),
                "status": "active",
                "local_path": str(ecos_path.parent),
                "deps": deps,
                "consumers": [],
                "ecos_root_file": str(ecos_path),
            }
            for dep in deps:
                edges.append({
                    "from": name, "to": dep,
                    "type": "runtime_dep",
                    "declared_in": "ECOS_ROOT.json",
                })

        # Resolve consumers
        for name, node in nodes.items():
            node["consumers"] = [
                n for n, n2 in nodes.items()
                if name in n2.get("deps", [])
            ]

        topology = {
            "version": "1.0",
            "generated": datetime.now(timezone.utc).isoformat(),
            "sot": "TOPOS",
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "repos_with_ecos_root": len(nodes),
            },
            "nodes": dict(sorted(nodes.items())),
            "edges": edges,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(topology, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        click.echo(f"[INFO] topology.yaml mis a jour: {output_path}")
        click.echo(f"[INFO]  Nodes: {len(nodes)}, Edges: {len(edges)}")


# ---------------------------------------------------------------------------
# kiva topos diff
# ---------------------------------------------------------------------------

@topos_cli.command("diff")
@click.option("--topos-path", default=str(DEFAULT_TOPOS_PATH),
              help="Chemin vers topology.yaml")
@click.option("--scan-root", default=r"D:\DO\WEB\TOOLS",
              help="Racine pour le scan des ECOS_ROOT.json")
@click.option("--output", default=None,
              help="Chemin du rapport de divergences (default: NEXUS/reports/)")
@click.option("--threshold", default=1, type=int,
              help="Seuil de divergences avant exit code 1")
def topos_diff(topos_path, scan_root, output, threshold):
    """
    Detecte les divergences entre TOPOS/topology.yaml et les ECOS_ROOT.json locaux.

    Compare les dependencies declarees dans topology.yaml avec celles
    trouvees dans chaque ECOS_ROOT.json.
    """
    topos_path = Path(topos_path)
    topology = _load_topology(topos_path)
    nodes = topology.get("nodes", {})

    # Scan ECOS_ROOT.json
    ecos_roots = _find_ecos_roots(scan_root)
    click.echo(f"[INFO] {len(ecos_roots)} ECOS_ROOT.json scannes")

    divergences = []
    matched = 0

    for ecos_path in ecos_roots:
        data = _parse_ecos_root(ecos_path)
        if not data:
            continue
        name = data.get("name", ecos_path.parent.name)
        local_deps = set(data.get("dependencies", []))

        if name in nodes:
            topo_deps = set(nodes[name].get("deps", []))
            added = local_deps - topo_deps
            removed = topo_deps - local_deps
            if added or removed:
                divergences.append({
                    "repo": name,
                    "ecos_root": str(ecos_path),
                    "added": sorted(added),
                    "removed": sorted(removed),
                })
            else:
                matched += 1
        else:
            divergences.append({
                "repo": name,
                "ecos_root": str(ecos_path),
                "added": sorted(local_deps),
                "removed": [],
                "note": "Absent de topology.yaml",
            })

    # Check for nodes in topology but missing ECOS_ROOT
    ecos_names = {data.get("name", p.parent.name) for p in ecos_roots
                  for data in [_parse_ecos_root(p)] if data}
    for topo_name in nodes:
        if topo_name not in ecos_names:
            divergences.append({
                "repo": topo_name,
                "ecos_root": nodes[topo_name].get("ecos_root_file", ""),
                "added": [],
                "removed": nodes[topo_name].get("deps", []),
                "note": "ECOS_ROOT.json absent",
            })

    # Output report
    now = datetime.now(timezone.utc)
    date_tag = now.strftime("%Y%m%d")
    if output is None:
        NEXUS_REPORTS_PATH.mkdir(parents=True, exist_ok=True)
        output = str(NEXUS_REPORTS_PATH / f"topos_diff_{date_tag}.md")
    else:
        output = str(output)

    lines = []
    lines.append(f"# topos_diff_report_{date_tag}.md")
    lines.append("")
    lines.append(f"## Metadonnees")
    lines.append(f"| Champ | Valeur |")
    lines.append(f"|-------|--------|")
    lines.append(f"| **Date** | {now.isoformat()} |")
    lines.append(f"| **Topology** | `{topos_path}` |")
    lines.append(f"| **Nodes dans TOPOS** | {len(nodes)} |")
    lines.append(f"| **ECOS_ROOT scannes** | {len(ecos_roots)} |")
    lines.append(f"| **Matches** | {matched} |")
    lines.append(f"| **Divergences** | {len(divergences)} |")
    lines.append("")

    if divergences:
        lines.append(f"## Divergences ({len(divergences)})")
        lines.append("")
        lines.append("| Repo | ECOS_ROOT | Ajoutes | Supprimes | Note |")
        lines.append("|------|-----------|---------|-----------|------|")
        for div in sorted(divergences, key=lambda d: d["repo"]):
            added = ", ".join(div.get("added", [])) or "-"
            removed = ", ".join(div.get("removed", [])) or "-"
            note = div.get("note", "")
            lines.append(f"| {div['repo']} | `{div.get('ecos_root', '')}` | {added} | {removed} | {note} |")
    else:
        lines.append("## Aucune divergence detectee")

    lines.append("")
    report = "\n".join(lines)
    with open(output, "w", encoding="utf-8") as f:
        f.write(report)

    click.echo(f"[INFO] Rapport ecrit: {output}")
    click.echo(f"[INFO] Divergences: {len(divergences)}, Matches: {matched}")

    if len(divergences) >= threshold:
        sys.exit(1)


# ---------------------------------------------------------------------------
# kiva topos export
# ---------------------------------------------------------------------------

@topos_cli.command("export")
@click.option("--topos-path", default=str(DEFAULT_TOPOS_PATH),
              help="Chemin vers topology.yaml")
@click.option("--format", "fmt", type=click.Choice(["json", "mermaid", "dot"]),
              default="json", help="Format d'export")
@click.option("--output", default=None, help="Fichier de sortie (default: stdout)")
def topos_export(topos_path, fmt, output):
    """
    Exporte le graphe TOPOS dans un format donne.

    Formats supportes:
      json    -- Graphe JSON (nodes + edges)
      mermaid -- Diagramme Mermaid (flowchart TD)
      dot     -- GraphViz DOT
    """
    topos_path = Path(topos_path)
    topology = _load_topology(topos_path)
    nodes = topology.get("nodes", {})
    edges = topology.get("edges", [])

    if fmt == "json":
        result = json.dumps(topology, indent=2, ensure_ascii=False)

    elif fmt == "mermaid":
        lines = ["flowchart TD"]
        for name in sorted(nodes.keys()):
            safe_name = name.replace("-", "_").replace(".", "_")
            lines.append(f"    {safe_name}[{name}]")
        for edge in edges:
            from_safe = edge["from"].replace("-", "_").replace(".", "_")
            to_safe = edge["to"].replace("-", "_").replace(".", "_")
            lines.append(f"    {from_safe} --> {to_safe}")
        result = "\n".join(lines)

    elif fmt == "dot":
        lines = ["digraph TOPOS {"]
        lines.append("    rankdir=TB;")
        lines.append('    node [shape=box];')
        for name in sorted(nodes.keys()):
            safe_name = name.replace("-", "_").replace(".", "_")
            layer = nodes[name].get("layer", "")
            lines.append(f'    {safe_name} [label="{name}\\n{layer}"];')
        for edge in edges:
            from_safe = edge["from"].replace("-", "_").replace(".", "_")
            to_safe = edge["to"].replace("-", "_").replace(".", "_")
            lines.append(f"    {from_safe} -> {to_safe};")
        lines.append("}")
        result = "\n".join(lines)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(result)
        click.echo(f"[INFO] Export ecrit: {output}")
    else:
        click.echo(result)
