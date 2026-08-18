#!/usr/bin/env python3
"""Doctor commands - KIVA CLI

Provides path hygiene and repository health diagnostics.
"""

import click
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple


@click.group(name='doctor')
def doctor_cli():
    """KIVA-CLI doctor — hygiene and diagnostics."""
    pass


@doctor_cli.command(name='paths')
@click.option('--auto', is_flag=True, help='Auto-fix relative paths to @ALIAS')
@click.option('--registry', default=None, help='Path to path-registry.yaml')
@click.option('--scan', default='.', help='Directory to scan')
def check_paths(auto: bool, registry: str, scan: str):
    """Scan files for relative path aberrations and enforce @ALIAS usage.

    Examples:
        kiva doctor paths
        kiva doctor paths --scan D:\\DO\\WEB\\TOOLS\\L4-TOOLS\\KORX
        kiva doctor paths --auto
    """
    scan_path = Path(scan)
    if not scan_path.exists():
        click.echo(click.style(f"ERROR: {scan} does not exist", fg='red'))
        raise click.ClickException(1)

    # Load path-registry.yaml if available
    registry_path = None
    if registry:
        registry_path = Path(registry)
    else:
        candidates = [
            Path('D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/config/path-registry.yaml'),
            Path.home() / '.kiva' / 'path-registry.yaml',
        ]
        for c in candidates:
            if c.exists():
                registry_path = c
                break

    aliases = {}
    if registry_path and registry_path.exists():
        aliases = _load_registry(registry_path)

    violations = []
    fixed = []

    for file_path in scan_path.rglob('*'):
        if not file_path.is_file():
            continue
        if any(part.startswith('.git') for part in file_path.parts):
            continue
        if file_path.suffix.lower() not in ('.py', '.zig', '.ps1', '.md', '.yaml', '.yml', '.json', '.toml'):
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        rel_paths = _find_relative_paths(content)
        if not rel_paths:
            continue

        for rel_path in rel_paths:
            alias = _match_alias(rel_path, aliases)
            violations.append((str(file_path), rel_path, alias))

            if auto and alias:
                new_content = content.replace(rel_path, f'@{alias}')
                file_path.write_text(new_content, encoding='utf-8')
                fixed.append((str(file_path), rel_path, f'@{alias}'))
                content = new_content

    # Report
    click.echo(click.style(f"\nDoctor Path Report — {scan}", fg='cyan'))
    click.echo(click.style('=' * 50, fg='cyan'))
    click.echo(f"Registry : {registry_path or 'NOT FOUND'}")
    click.echo(f"Violations: {len(violations)}")

    if violations:
        click.echo(click.style("\nViolations:", fg='yellow'))
        for f, p, a in violations[:20]:
            alias_info = f" → @{a}" if a else " (no alias)"
            click.echo(f"  {f}: {p}{alias_info}")

    if fixed:
        click.echo(click.style(f"\nFixed ({len(fixed)}):", fg='green'))
        for f, old, new in fixed[:20]:
            click.echo(f"  {f}: {old} -> {new}")

    if not violations:
        click.echo(click.style("\nNo relative path violations found.", fg='green'))
    elif not auto:
        click.echo(click.style("\nRun with --auto to fix automatically.", fg='yellow'))


def _load_registry(registry_path: Path) -> Dict[str, str]:
    """Load path-registry.yaml and return alias -> path mapping."""
    aliases = {}
    try:
        content = registry_path.read_text(encoding='utf-8')
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Match alias lines like: "@ALIAS":
            if '@' in line and line.endswith(':'):
                alias = line[:-1].strip().strip('"').strip("'")
                # Look ahead for local_path on next lines
                j = i + 1
                while j < len(lines):
                    sub = lines[j].strip()
                    if sub.startswith('local_path:'):
                        # Extract path from quotes
                        path_value = sub.split(':', 1)[1].strip()
                        if path_value.startswith('"') and '"' in path_value[1:]:
                            path = path_value[1:].split('"')[0]
                            aliases[alias] = path
                        break
                    if sub and not sub.startswith('#') and not sub.startswith('canonical_name') and not sub.startswith('stratum') and not sub.startswith('role') and not sub.startswith('status'):
                        break
                    j += 1
            i += 1
    except Exception as e:
        click.echo(click.style(f"Warning: Could not load registry: {e}", fg='yellow'))
    return aliases


def _find_relative_paths(content: str) -> List[str]:
    """Find relative paths (./ or ../) in content."""
    patterns = re.findall(r'(?:\.{1,2}/[^\s"\'\)]+)', content)
    return list(set(patterns))


def _match_alias(rel_path: str, aliases: Dict[str, str]) -> str:
    """Match a relative path to an alias if it resolves to the same physical path."""
    rel_normalized = rel_path.replace('\\', '/')
    for alias, physical in aliases.items():
        phys_normalized = physical.replace('\\', '/')
        alias_name = alias.lstrip('@')
        if rel_normalized.startswith('../' + alias_name + '/') or rel_normalized.startswith('./' + alias_name + '/'):
            return alias_name
        if rel_normalized.endswith(phys_normalized.split('/')[-1]):
            return alias_name
    return ''



if __name__ == '__main__':
    doctor_cli()
