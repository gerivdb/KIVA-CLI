#!/usr/bin/env python3
"""
Repository Discovery - KIVA CLI

Automatically scans directories for git repositories and adds them to the PathResolver registry.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
import json
import re
import time
from datetime import datetime


class RepoDiscovery:
    """Discovers git repositories in a directory tree."""

    def __init__(self, scan_dirs: Optional[List[str]] = None):
        if scan_dirs is None:
            scan_dirs = [
                "D:\\DO\\WEB",
                "D:\\DO\\WEB\\TOOLS",
                "C:\\DevTools"
            ]
        self.scan_dirs = [Path(d) for d in scan_dirs]

    def discover_repos(self) -> List[Dict[str, str]]:
        """
        Scan directories for git repositories.
        
        Returns:
            List of dicts with keys: name, path, remote
        """
        repos = []
        for scan_dir in self.scan_dirs:
            if not scan_dir.exists():
                continue
            repos.extend(self._scan_directory(scan_dir))
        return repos

    def _scan_directory(self, base_dir: Path) -> List[Dict[str, str]]:
        """Recursively scan a directory for git repos."""
        repos = []
        
        try:
            for item in base_dir.iterdir():
                if item.is_dir() and item.name.startswith('.'):
                    continue
                
                if item.is_dir() and (item / ".git").exists():
                    # Found a git repo
                    repo_info = self._get_repo_info(item)
                    if repo_info:
                        repos.append(repo_info)
                elif item.is_dir():
                    # Recurse into subdirectory
                    repos.extend(self._scan_directory(item))
        except (PermissionError, OSError) as e:
            print(f"Warning: Could not scan {base_dir}: {e}")
        
        return repos

    def _get_repo_info(self, repo_path: Path) -> Optional[Dict[str, str]]:
        """Get repository information."""
        try:
            # Get repo name
            name = repo_path.name
            
            # Get remote URL
            remote_url = ""
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    cwd=str(repo_path),
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    remote_url = result.stdout.strip()
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass
            
            return {
                "name": name,
                "path": str(repo_path),
                "remote": remote_url
            }
        except Exception:
            return None

    def compare_with_registry(self, discovered: List[Dict[str, str]], registered: Dict[str, Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        Compare discovered repos with registered repos.
        
        Returns:
            (new_repos, existing_repos) tuples
        """
        new_repos = []
        existing_repos = []
        
        registered_paths = {r["local_path"]: name for name, r in registered.items()}
        registered_remotes = {r["remote_url"]: name for name, r in registered.items()}
        
        for repo in discovered:
            if repo["path"] in registered_paths or repo["remote"] in registered_remotes:
                existing_repos.append(repo)
            else:
                new_repos.append(repo)
        
        return new_repos, existing_repos


@click.group(name='repo')
def repo_cli():
    """
    Repository discovery and management.

    Provides:
    - Automatic repository discovery
    - Registry management
    """
    pass

# Registry sync configuration
SCAN_ROOTS = [
    Path(r"D:\DO\WEB\TOOLS\L0-CANON"),
    Path(r"D:\DO\WEB\TOOLS\L1-INFRA"),
    Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM"),
    Path(r"D:\DO\WEB\TOOLS\L2-TOOLS"),
    Path(r"D:\DO\WEB\TOOLS\L3-APPS"),
    Path(r"D:\DO\WEB\TOOLS\L3-CITIZENS"),
    Path(r"D:\DO\WEB\TOOLS\L4-TOOLS"),
    Path(r"D:\DO\WEB\TOOLS\L5-ARCHIVE"),
]
FLAT_ROOTS = [Path(r"D:\DO\WEB\TOOLS"), Path(r"D:\DO\WEB")]
EXCEPTIONS = {"DevTools": Path(r"C:\DevTools"), "ECOYSTEM": Path(r"D:\DO\WEB\ECOYSTEM")}
EXCLUDE_PATTERNS = ["lovable-*", "*.lovable", "test-*-tmp"]
NEXUS_ECOS_ROOT = Path(r"D:\DO\WEB\TOOLS\L0-CANON\NEXUS\ecosystem\registry\ECOS_ROOT.json")

def _run_git(repo_path, args, timeout=10):
    try:
        r = subprocess.run(["git"] + args, cwd=str(repo_path),
                          capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception:
        return -1, ""

def _scan_local():
    local_map = {}
    for root in SCAN_ROOTS + FLAT_ROOTS:
        if not root.exists():
            continue
        for sd in sorted(root.iterdir()):
            if not sd.is_dir() or not (sd / ".git").exists():
                continue
            rc, url = _run_git(sd, ["remote", "get-url", "origin"])
            if rc != 0 or not url:
                continue
            norm = re.sub(r'\.git$', '', url)
            local_map.setdefault(norm, []).append(str(sd))
    return local_map

def _load_nexus():
    if not NEXUS_ECOS_ROOT.exists():
        return {}
    try:
        with open(NEXUS_ECOS_ROOT, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {n: r for n, r in data.get("repos", {}).items()}
    except Exception:
        return {}

def _repo_name_from_url(url):
    m = re.search(r'[:/]([^/]+)/([^/]+?)(?:\.git)?$', url)
    return m.group(2) if m else ""

def _git_info(p):
    info = {}
    rc, out = _run_git(Path(p), ["log", "-1", "--format=%ai"])
    info["last_commit"] = out[:10] if rc == 0 else ""
    rc, out = _run_git(Path(p), ["symbolic-ref", "--short", "HEAD"])
    info["branch"] = out if rc == 0 else ""
    rc, out = _run_git(Path(p), ["status", "--porcelain"])
    info["dirty"] = bool(out.strip()) if rc == 0 else False
    rc, out = _run_git(Path(p), ["log", "--branches", "--not", "--remotes", "--oneline"])
    info["unpushed"] = len([l for l in out.splitlines() if l.strip()]) if rc == 0 else 0
    return info

def _excluded(name):
    import fnmatch
    return any(fnmatch.fnmatch(name, p) for p in EXCLUDE_PATTERNS)



@repo_cli.command(name='discover')
@click.option('--scan-dir', '-s', multiple=True, help='Directory to scan')
@click.option('--add-all', '-a', is_flag=True, help='Add all discovered repos without prompting')
def discover_repos(scan_dir: tuple, add_all: bool):
    """
    Discover git repositories in scan directories.

    Example:
        kiva repo discover
        kiva repo discover --scan-dir D:\\MyRepos
    """
    from kiva_cli.core.path_resolver import PathResolver
    
    scan_dirs = list(scan_dir) if scan_dir else None
    discovery = RepoDiscovery(scan_dirs)
    resolver = PathResolver()
    
    click.echo("Scanning for repositories...")
    discovered = discovery.discover_repos()
    
    if not discovered:
        click.echo(click.style("No repositories found.", fg="yellow"))
        return
    
    new_repos, existing_repos = discovery.compare_with_registry(discovered, resolver.list_repos())
    
    click.echo(f"\nFound {len(discovered)} repositories:")
    click.echo(click.style(f"  {len(existing_repos)} already registered", fg="green"))
    click.echo(click.style(f"  {len(new_repos)} new", fg="yellow"))
    
    if existing_repos:
        click.echo("\nAlready registered:")
        for repo in existing_repos:
            click.echo(f"  {click.style(repo['name'], fg='green')} ({repo['path']})")
    
    if new_repos:
        click.echo("\nNew repositories:")
        for repo in new_repos:
            click.echo(f"  {click.style(repo['name'], fg='yellow')}")
            click.echo(f"    Path:   {repo['path']}")
            click.echo(f"    Remote: {repo['remote']}")
            
            if add_all:
                resolver.add_repo(repo['name'], repo['path'], repo['remote'])
                click.echo(click.style(f"    Added!", fg="green"))
            else:
                response = input("    Add to registry? [y/N]: ")
                if response.lower() == 'y':
                    resolver.add_repo(repo['name'], repo['path'], repo['remote'])
                    click.echo(click.style(f"    Added!", fg="green"))
    
    click.echo("")

@repo_cli.command(name="sync")
@click.option("--dry-run", is_flag=True, help="Simule sans ecrire")
@click.option("--output-dir", "-o", default="", help="Repertoire de sortie")
def registry_sync(dry_run, output_dir):
    """
    Synchronise la matrice remote <-> local <-> registres.

    Construit repo-matrix.json classant tous les repos:
    - OK: local + registre
    - Doublons: plusieurs clones (ancien/nouveau)
    - Orphelin local: clone sans entree registre
    - Orphelin remote: registre sans clone

    Example:
        kiva repo sync --dry-run
    """
    if not output_dir:
        output_dir = Path(r"D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB\scripts")
    else:
        output_dir = Path(output_dir)

    click.echo("\n" + "=" * 48)
    click.echo("  KIVA Registry Sync")
    click.echo("=" * 48)

    click.echo("\n[1/3] Scanning local repos...")
    local = _scan_local()
    click.echo(f"  Found: {len(local)} unique remotes")

    click.echo("[2/3] Loading registries...")
    nexus = _load_nexus()
    click.echo(f"  ECOS_ROOT.json: {len(nexus)} repos")

    click.echo("[3/3] Building matrix...")
    all_names = set(nexus.keys())
    for url, paths in local.items():
        rn = _repo_name_from_url(url)
        if rn:
            all_names.add(rn)

    # Load gov yaml
    gov_yaml = Path(r"D:\DO\WEB\TOOLS\L0-CANON\GOVERNANCE-HUB\known_repositories.yaml")
    gov = {}
    if gov_yaml.exists():
        try:
            with open(gov_yaml, "r", encoding="utf-8") as fh:
                gd = __import__("yaml", fromlist=["safe_load"]).safe_load(fh) or {}
            for sec in ["P0_CONSTITUTIONAL", "P1_STRATEGIC", "P2_SUPPORT", "P3_DORMANT"]:
                for r in gd.get(sec, []):
                    n = r.get("name", "")
                    if n:
                        all_names.add(n)
                        gov[n] = r
        except Exception:
            pass

    matrix = {}
    for name in sorted(all_names):
        if _excluded(name):
            continue
        e = {
            "name": name, "local_path": None, "local_exists": False,
            "local_dirty": False, "local_unpushed": 0, "local_last_commit": "",
            "local_branch": "", "reg_nexus": name in nexus, "reg_gov": name in gov,
            "layer": None, "criticality": None, "lifecycle": "UNKNOWN",
            "duplicates": [], "notes": []
        }
        if name in nexus:
            nd = nexus[name]
            e["local_path"] = nd.get("local_path")
            e["layer"] = nd.get("layer")
            e["criticality"] = nd.get("criticality")
            e["lifecycle"] = nd.get("lifecycle") or "UNKNOWN"
        if name in gov:
            gr = gov[name]
            if not e["local_path"]:
                e["local_path"] = gr.get("local_path")
            if not e["layer"]:
                e["layer"] = gr.get("layer")
        if name in EXCEPTIONS:
            e["local_path"] = str(EXCEPTIONS[name])
        for url, paths in local.items():
            rn2 = _repo_name_from_url(url)
            if rn2 == name:
                if len(paths) > 1:
                    e["duplicates"] = paths
                    best = paths[0]
                    for p in paths:
                        if p == e.get("local_path"):
                            best = p
                            break
                        if re.search(r'\\L[0-5]-', p) and not re.search(r'\\L[0-5]-', best):
                            best = p
                    e["local_path"] = best
                e["local_exists"] = True
                break
        matrix[name] = e

    # Git info
    click.echo("  Getting git info...")
    gc = 0
    for n, e in matrix.items():
        if not e.get("local_path"):
            continue
        if not Path(e["local_path"]).joinpath(".git").exists():
            continue
        gi = _git_info(e["local_path"])
        e["local_last_commit"] = gi.get("last_commit", "")
        e["local_branch"] = gi.get("branch", "")
        e["local_dirty"] = gi.get("dirty", False)
        e["local_unpushed"] = gi.get("unpushed", 0)
        gc += 1
    click.echo(f"  Git info: {gc} repos")

    # Categorize
    c_ok, c_dup, c_ol, c_or, c_miss = [], [], [], [], []
    for n, e in sorted(matrix.items()):
        if e.get("lifecycle") == "DEPRECATED":
            continue
        if e["local_exists"]:
            if e.get("duplicates"):
                c_dup.append(n)
            elif e["reg_nexus"] or e["reg_gov"]:
                c_ok.append(n)
            else:
                c_ol.append(n)
        else:
            if e["reg_nexus"] or e["reg_gov"]:
                c_or.append(n)
            else:
                c_miss.append(n)

    # Write
    date_s = datetime.now().strftime("%Y-%m-%d")
    mp = output_dir / "repo-matrix.json"
    rp = output_dir / f"REPORT-registry-sync-{date_s}.md"

    if not dry_run:
        with open(mp, "w", encoding="utf-8") as fh:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "schema_version": "2.0",
                "kiva_cli": True,
                "repos": matrix
            }, fh, indent=2, ensure_ascii=False, default=str)
        click.echo(f"  Written: {mp}")

    lines = [f"# Registry Sync Report - {date_s}", "", "| Categorie | Count |", "|-----------|-------|"]
    for lbl, items in [("OK", c_ok), ("Doublons", c_dup), ("Orphelin_local", c_ol), ("Orphelin_remote", c_or), ("Manquant", c_miss)]:
        lines.append(f"| {lbl} | {len(items)} |")
    lines.append(f"| **TOTAL** | **{len(c_ok)+len(c_dup)+len(c_ol)+len(c_or)+len(c_miss)}** |")
    lines.append("")
    for lbl, items in [("OK", c_ok), ("DOUBLONS", c_dup), ("ORPHELIN_LOCAL", c_ol), ("ORPHELIN_REMOTE", c_or)]:
        if not items:
            continue
        lines.append(f"## {lbl} ({len(items)})")
        lines.append("")
        for n in items:
            e = matrix[n]
            lines.append(f"### {n}")
            lines.append(f"- Path: {e.get('local_path','N/A')} | Branch: {e.get('local_branch','')} | Commit: {e.get('local_last_commit','')}")
            if e.get("duplicates"):
                lines.append(f"- DUPLICATES: {' | '.join(e['duplicates'])}")
            if e.get("layer"):
                lines.append(f"- Layer: {e['layer']} | Crit: {e.get('criticality')} | Life: {e.get('lifecycle')}")
            lines.append("")

    if not dry_run:
        with open(rp, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        click.echo(f"  Written: {rp}")

    click.echo(f"\n  OK={len(c_ok)} DUP={len(c_dup)} ORPH_L={len(c_ol)} ORPH_R={len(c_or)}")



@repo_cli.command(name='list')
def list_discovered():
    """
    List all discovered repositories (alias for kiva path list).
    """
    from kiva_cli.commands.path_commands import list_repos
    list_repos()