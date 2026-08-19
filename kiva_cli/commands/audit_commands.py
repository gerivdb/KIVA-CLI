#!/usr/bin/env python3
"""
audit_orphan_branches.py - BRGS L5: Orphan branch audit module for KIVA-CLI

Scans all repositories in the governance manifest for orphan branches:
  - Branches containing files in forbidden paths (wrong repo)
  - Branches with non-compliant naming conventions
  - Merged branches not yet deleted

Usage:
    kiva audit orphan-branches --config <manifest_path> --output <report.md>

IntentHash: 0xBRG_KIVA_AUDIT_20260526
Version: 1.0.0
"""

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# --- Data classes ---

class OrphanReason(str, Enum):
    """Reason a branch is considered orphaned."""
    FORBIDDEN_PATH = "FORBIDDEN_PATH"
    WRONG_PREFIX = "WRONG_PREFIX"
    MERGED_NOT_DELETED = "MERGED_NOT_DELETED"
    STALE = "STALE"


@dataclass
class OrphanBranch:
    """Represents an orphan branch finding."""
    repo_name: str
    repo_path: str
    branch_name: str
    reason: str
    details: str
    last_commit_date: str = ""
    last_commit_author: str = ""
    files_violated: List[str] = field(default_factory=list)
    suggested_action: str = ""
    prune_command: str = ""


@dataclass
class AuditSummary:
    """Summary of the orphan branch audit."""
    scan_date: str
    repos_scanned: int = 0
    branches_scanned: int = 0
    orphans_found: int = 0
    forbidden_path_count: int = 0
    wrong_prefix_count: int = 0
    merged_not_deleted_count: int = 0
    stale_count: int = 0
    orphans: List[OrphanBranch] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# --- Manifest loading ---

def load_manifest(manifest_path: str) -> Dict[str, Any]:
    """Load and parse the governance manifest."""
    if not HAS_YAML:
        click.echo("Error: PyYAML required - pip install pyyaml", err=True)
        sys.exit(1)

    path = Path(manifest_path)
    if not path.exists():
        click.echo(f"Error: Manifest not found at {manifest_path}", err=True)
        sys.exit(1)

    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML in manifest: {e}", err=True)
        sys.exit(1)


def get_repo_config(manifest: Dict, repo_name: str) -> Optional[Dict]:
    """Get branch_routing config for a specific repository."""
    routing = manifest.get("branch_routing", {})
    repos = routing.get("repositories", {})
    return repos.get(repo_name)


# --- Git operations ---

def run_git(repo_path: str, args: List[str], timeout: int = 30) -> Tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", "git not found"
    except Exception as e:
        return -1, "", str(e)


def get_remote_branches(repo_path: str) -> List[str]:
    """Get list of remote branches (without 'origin/' prefix)."""
    rc, stdout, _ = run_git(repo_path, ["branch", "-r", "--no-merged", "origin/main"])
    if rc != 0:
        rc, stdout, _ = run_git(repo_path, ["branch", "-r"])

    branches = []
    for line in stdout.split("\n"):
        line = line.strip()
        if line.startswith("origin/") and "HEAD" not in line:
            name = line.replace("origin/", "", 1)
            if name != "main":
                branches.append(name)
    return branches


def get_branch_files(repo_path: str, branch_name: str) -> List[str]:
    """Get files changed in a branch compared to origin/main."""
    rc, stdout, _ = run_git(
        repo_path,
        ["diff", "--name-only", f"origin/main...origin/{branch_name}"],
    )
    if rc != 0 or not stdout:
        rc, stdout, _ = run_git(
            repo_path,
            ["diff", "--name-only", f"origin/main..origin/{branch_name}"],
        )
    if not stdout:
        return []
    return [f for f in stdout.split("\n") if f]


def get_branch_last_commit(repo_path: str, branch_name: str) -> Tuple[str, str]:
    """Get last commit date and author for a branch."""
    rc, stdout, _ = run_git(
        repo_path,
        ["log", "-1", "--format=%ai|%an", f"origin/{branch_name}"],
    )
    if rc == 0 and "|" in stdout:
        parts = stdout.split("|", 1)
        return parts[0].strip(), parts[1].strip()
    return "", ""


def is_branch_merged(repo_path: str, branch_name: str) -> bool:
    """Check if a branch has been merged into origin/main."""
    rc, _, _ = run_git(
        repo_path,
        ["branch", "-r", "--merged", "origin/main", f"--list", f"origin/{branch_name}"],
    )
    return rc == 0


# --- Audit logic ---

def audit_repo(
    repo_name: str,
    repo_path: str,
    repo_config: Dict[str, Any],
    check_merged: bool = True,
    stale_days: int = 90,
) -> List[OrphanBranch]:
    """Audit a single repository for orphan branches."""
    orphans = []
    forbidden_paths = repo_config.get("forbidden_paths", [])
    allowed_prefixes = repo_config.get("allowed_branch_prefixes", [])
    redirect_map = repo_config.get("redirect_map", {})

    if not Path(repo_path).exists():
        return orphans

    rc, _, _ = run_git(repo_path, ["fetch", "origin", "--prune"], timeout=60)
    if rc != 0:
        click.echo(f"  [WARN] Could not fetch {repo_name}, using local refs")

    branches = get_remote_branches(repo_path)

    for branch_name in branches:
        files = get_branch_files(repo_path, branch_name)
        last_date, last_author = get_branch_last_commit(repo_path, branch_name)

        # Check 1: Forbidden paths
        if forbidden_paths:
            violated = []
            for fp in forbidden_paths:
                prefix = fp.rstrip("/")
                for f in files:
                    if f.startswith(prefix + "/") or f == prefix:
                        violated.append(f)

            if violated:
                redirect_target = ""
                for fp, target in redirect_map.items():
                    fp_prefix = fp.rstrip("/")
                    for v in violated:
                        if v.startswith(fp_prefix + "/"):
                            redirect_target = target
                            break
                    if redirect_target:
                        break

                detail = f"Branch '{branch_name}' contains {len(violated)} file(s) in forbidden paths"
                if redirect_target:
                    detail += f" - belongs to {redirect_target}"

                orphans.append(OrphanBranch(
                    repo_name=repo_name,
                    repo_path=repo_path,
                    branch_name=branch_name,
                    reason=OrphanReason.FORBIDDEN_PATH,
                    details=detail,
                    last_commit_date=last_date,
                    last_commit_author=last_author,
                    files_violated=violated[:10],
                    suggested_action=f"Move to {redirect_target}" if redirect_target else "Review and prune",
                    prune_command=f"git push origin --delete {branch_name}",
                ))
                continue

        # Check 2: Wrong prefix
        if allowed_prefixes and branch_name not in ("main", "dev"):
            prefix_ok = False
            for p in allowed_prefixes:
                clean_p = p.rstrip("/")
                if branch_name.startswith(clean_p):
                    prefix_ok = True
                    break

            if not prefix_ok:
                orphans.append(OrphanBranch(
                    repo_name=repo_name,
                    repo_path=repo_path,
                    branch_name=branch_name,
                    reason=OrphanReason.WRONG_PREFIX,
                    details=f"Branch '{branch_name}' does not match allowed prefixes: {', '.join(allowed_prefixes)}",
                    last_commit_date=last_date,
                    last_commit_author=last_author,
                    suggested_action="Rename branch to match convention",
                    prune_command=f"git branch -m {branch_name} <prefix>/<description>",
                ))
                continue

        # Check 3: Merged but not deleted
        if check_merged and is_branch_merged(repo_path, branch_name):
            orphans.append(OrphanBranch(
                repo_name=repo_name,
                repo_path=repo_path,
                branch_name=branch_name,
                reason=OrphanReason.MERGED_NOT_DELETED,
                details=f"Branch '{branch_name}' is merged into main but not deleted",
                last_commit_date=last_date,
                last_commit_author=last_author,
                suggested_action="Delete merged branch",
                prune_command=f"git push origin --delete {branch_name}",
            ))
            continue

        # Check 4: Stale
        if last_date:
            try:
                commit_date = datetime.strptime(last_date, "%Y-%m-%d %H:%M:%S %z")
                age_days = (datetime.now(commit_date.tzinfo) - commit_date).days
                if age_days > stale_days:
                    orphans.append(OrphanBranch(
                        repo_name=repo_name,
                        repo_path=repo_path,
                        branch_name=branch_name,
                        reason=OrphanReason.STALE,
                        details=f"Branch '{branch_name}' is {age_days} days old (last commit: {last_date})",
                        last_commit_date=last_date,
                        last_commit_author=last_author,
                        suggested_action="Review and prune if no longer needed",
                        prune_command=f"git push origin --delete {branch_name}",
                    ))
            except (ValueError, TypeError):
                pass

    return orphans


# --- Report generation ---

def generate_report(summary: AuditSummary, output_path: str) -> str:
    """Generate a Markdown audit report."""
    lines = []
    lines.append("# BRGS Audit - Orphan Branches Report")
    lines.append("")
    lines.append(f"**Scan Date**: {summary.scan_date}")
    lines.append(f"**Repos Scanned**: {summary.repos_scanned}")
    lines.append(f"**Branches Scanned**: {summary.branches_scanned}")
    lines.append(f"**Orphans Found**: {summary.orphans_found}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Reason | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Forbidden Paths | {summary.forbidden_path_count} |")
    lines.append(f"| Wrong Prefix | {summary.wrong_prefix_count} |")
    lines.append(f"| Merged Not Deleted | {summary.merged_not_deleted_count} |")
    lines.append(f"| Stale (>90 days) | {summary.stale_count} |")
    lines.append("")

    if summary.errors:
        lines.append("## Errors")
        lines.append("")
        for err in summary.errors:
            lines.append(f"- [WARN] {err}")
        lines.append("")

    by_repo: Dict[str, List[OrphanBranch]] = {}
    for o in summary.orphans:
        by_repo.setdefault(o.repo_name, []).append(o)

    for repo_name, repo_orphans in sorted(by_repo.items()):
        lines.append(f"## {repo_name} ({len(repo_orphans)} orphan(s))")
        lines.append("")

        for o in repo_orphans:
            lines.append(f"### `{o.branch_name}` - {o.reason}")
            lines.append("")
            lines.append(f"- **Details**: {o.details}")
            if o.last_commit_date:
                lines.append(f"- **Last Commit**: {o.last_commit_date} by {o.last_commit_author}")
            if o.files_violated:
                lines.append("- **Violated Files**:")
                for f in o.files_violated:
                    lines.append(f"  - `{f}`")
            lines.append(f"- **Suggested Action**: {o.suggested_action}")
            lines.append(f"- **Command**: `{o.prune_command}`")
            lines.append("")

    lines.append("## Bulk Prune Commands")
    lines.append("")
    lines.append("```bash")
    for o in summary.orphans:
        if o.reason in (OrphanReason.FORBIDDEN_PATH, OrphanReason.MERGED_NOT_DELETED, OrphanReason.STALE):
            lines.append(f"cd {o.repo_path} && {o.prune_command}")
    lines.append("```")
    lines.append("")

    report = "\n".join(lines)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return report


# --- Click command ---

@click.group()
def audit():
    """Audit commands for BRGS (Branch Routing & Governance System)."""
    pass


@audit.command("orphan-branches")
@click.option(
    "--config", "manifest_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to multi-repo-governance.yaml",
)
@click.option(
    "--output", "output_path",
    default=None,
    type=click.Path(),
    help="Output path for the audit report (default: GOVERNANCE-HUB/RIS/audit-orphan-branches-YYYY-WW.md)",
)
@click.option(
    "--repos", "repo_filter",
    default=None,
    help="Comma-separated list of repo names to audit (default: all in manifest)",
)
@click.option(
    "--no-merged-check",
    is_flag=True,
    help="Skip merged-branch detection",
)
@click.option(
    "--stale-days",
    default=90,
    type=int,
    help="Number of days after which a branch is considered stale (default: 90)",
)
@click.option(
    "--json-output",
    "json_output_path",
    default=None,
    type=click.Path(),
    help="Optional JSON output path for machine-readable results",
)
def audit_orphan_branches(
    manifest_path: str,
    output_path: Optional[str],
    repo_filter: Optional[str],
    no_merged_check: bool,
    stale_days: int,
    json_output_path: Optional[str],
):
    """Scan all repositories for orphan branches.

    Finds branches that:

    - Contain files in forbidden paths (wrong repo)
    - Don't follow the naming convention
    - Are merged but not deleted
    - Are stale (>90 days old)

    Example:

        kiva audit orphan-branches --config D:\\\\DO\\\\WEB\\\\TOOLS\\\\L0-CANON\\\\GOVERNANCE-HUB\\\\multi-repo-governance.yaml

        kiva audit orphan-branches --config manifest.yaml --repos DevTools,ECOS-CLI

        kiva audit orphan-branches --config manifest.yaml --stale-days 30 --json-output results.json
    """
    click.echo("=" * 60)
    click.echo("  BRGS L5 - Orphan Branch Audit")
    click.echo("=" * 60)
    click.echo("")

    manifest = load_manifest(manifest_path)
    routing = manifest.get("branch_routing", {})
    repos_config = routing.get("repositories", {})

    if not repos_config:
        click.echo("Error: No branch_routing.repositories found in manifest", err=True)
        sys.exit(1)

    if repo_filter:
        filter_names = [n.strip() for n in repo_filter.split(",")]
        repos_config = {k: v for k, v in repos_config.items() if k in filter_names}

    if not output_path:
        now = datetime.now()
        week = now.isocalendar()[1]
        year = now.year
        hub_path = Path(manifest_path).parent
        output_path = str(hub_path / "RIS" / f"audit-orphan-branches-{year}-W{week:02d}.md")

    summary = AuditSummary(
        scan_date=datetime.now().isoformat(),
        repos_scanned=len(repos_config),
    )

    for repo_name, repo_config in repos_config.items():
        local_path = repo_config.get("local_path", "")
        click.echo(f"-- {repo_name} ({local_path}) --")

        if not local_path or not Path(local_path).exists():
            msg = f"Skipped {repo_name}: path not found ({local_path})"
            click.echo(f"  [WARN] {msg}")
            summary.errors.append(msg)
            continue

        orphans = audit_repo(
            repo_name=repo_name,
            repo_path=local_path,
            repo_config=repo_config,
            check_merged=not no_merged_check,
            stale_days=stale_days,
        )

        summary.orphans.extend(orphans)
        click.echo("  Found {} orphan branch(es)".format(len(orphans)))
        click.echo("")

    summary.orphans_found = len(summary.orphans)
    summary.forbidden_path_count = sum(1 for o in summary.orphans if o.reason == OrphanReason.FORBIDDEN_PATH)
    summary.wrong_prefix_count = sum(1 for o in summary.orphans if o.reason == OrphanReason.WRONG_PREFIX)
    summary.merged_not_deleted_count = sum(1 for o in summary.orphans if o.reason == OrphanReason.MERGED_NOT_DELETED)
    summary.stale_count = sum(1 for o in summary.orphans if o.reason == OrphanReason.STALE)

    report = generate_report(summary, output_path)

    click.echo("=" * 60)
    click.echo("  RESULTS")
    click.echo("=" * 60)
    click.echo(f"  Repos Scanned    : {summary.repos_scanned}")
    click.echo(f"  Orphans Found    : {summary.orphans_found}")
    click.echo(f"    Forbidden Paths: {summary.forbidden_path_count}")
    click.echo(f"    Wrong Prefix   : {summary.wrong_prefix_count}")
    click.echo(f"    Merged/Deleted : {summary.merged_not_deleted_count}")
    click.echo(f"    Stale          : {summary.stale_count}")
    if summary.errors:
        click.echo(f"  Errors           : {len(summary.errors)}")
    click.echo("")
    click.echo(f"  Report: {output_path}")
    click.echo("=" * 60)

    if json_output_path:
        json_data = {
            "scan_date": summary.scan_date,
            "repos_scanned": summary.repos_scanned,
            "orphans_found": summary.orphans_found,
            "forbidden_path_count": summary.forbidden_path_count,
            "wrong_prefix_count": summary.wrong_prefix_count,
            "merged_not_deleted_count": summary.merged_not_deleted_count,
            "stale_count": summary.stale_count,
            "orphans": [
                {
                    "repo": o.repo_name,
                    "branch": o.branch_name,
                    "reason": o.reason,
                    "details": o.details,
                    "last_commit_date": o.last_commit_date,
                    "suggested_action": o.suggested_action,
                    "prune_command": o.prune_command,
                }
                for o in summary.orphans
            ],
            "errors": summary.errors,
        }
        Path(json_output_path).write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        click.echo(f"  JSON: {json_output_path}")
