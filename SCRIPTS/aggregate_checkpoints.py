#!/usr/bin/env python3
"""
aggregate_checkpoints.py — Agrège tous les checkpoints .mdu de l'écosystème gerivdb
Usage: python aggregate_checkpoints.py [--output json|md] [--repos-root PATH]
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Repos connus (depuis ECOS-CLI registry)
REPO_ROOTS = [
    Path(r"D:\DO\WEB\TOOLS\L0-CANON"),
    Path(r"D:\DO\WEB\TOOLS\L1-INFRA"),
    Path(r"D:\DO\WEB\TOOLS\L2-PLATFORM"),
    Path(r"D:\DO\WEB\TOOLS\L3-CITIZENS"),
    Path(r"D:\DO\WEB\TOOLS\L4-TOOLS"),
    Path(r"D:\DO\WEB\TOOLS\L5-ARCHIVE"),
]

CHECKPOINT_FILES = ["checkpoint.json", "checkpoint_sync.json"]


def find_repos(root: Path) -> List[Path]:
    """Trouve tous les dossiers qui sont des repos git avec .mdu"""
    repos = []
    if not root.exists():
        return repos
    for item in root.iterdir():
        if item.is_dir() and (item / ".git").exists():
            repos.append(item)
    return repos


def read_checkpoint(repo_path: Path, filename: str) -> Optional[Dict]:
    """Lit un fichier checkpoint s'il existe"""
    cp_path = repo_path / ".mdu" / filename
    if cp_path.exists():
        try:
            with open(cp_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"error": "invalid_json", "path": str(cp_path)}
    return None


def aggregate_checkpoints(repo_roots: List[Path]) -> Dict[str, Any]:
    """Agrège tous les checkpoints trouvés"""
    result = {
        "generated_at": datetime.now().isoformat(),
        "total_repos_scanned": 0,
        "repos_with_checkpoints": 0,
        "checkpoints": {},
        "summary": {
            "last_actions": [],
            "latest_timestamp": None,
            "sync_sources": set(),
        }
    }

    for root in repo_roots:
        repos = find_repos(root)
        result["total_repos_scanned"] += len(repos)

        for repo in repos:
            repo_name = repo.name
            repo_data = {"path": str(repo), "checkpoints": {}}
            has_any = False

            for cp_file in CHECKPOINT_FILES:
                data = read_checkpoint(repo, cp_file)
                if data:
                    repo_data["checkpoints"][cp_file] = data
                    has_any = True

                    # Collecter infos pour summary
                    if "last_action" in data:
                        result["summary"]["last_actions"].append({
                            "repo": repo_name,
                            "action": data["last_action"],
                            "timestamp": data.get("timestamp", "unknown")
                        })
                    if "last_sync" in data:
                        result["summary"]["sync_sources"].add(data.get("source", "unknown"))
                        if not result["summary"]["latest_timestamp"] or data["last_sync"] > result["summary"]["latest_timestamp"]:
                            result["summary"]["latest_timestamp"] = data["last_sync"]

            if has_any:
                result["repos_with_checkpoints"] += 1
                result["checkpoints"][repo_name] = repo_data

    # Convert set to list for JSON serialization
    result["summary"]["sync_sources"] = list(result["summary"]["sync_sources"])
    return result


def output_json(data: Dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def output_markdown(data: Dict) -> str:
    lines = [
        f"# Checkpoint Aggregation Report",
        f"",
        f"**Generated**: {data['generated_at']}",
        f"**Repos scanned**: {data['total_repos_scanned']}",
        f"**Repos with checkpoints**: {data['repos_with_checkpoints']}",
        f"**Latest sync**: {data['summary']['latest_timestamp'] or 'N/A'}",
        f"**Sync sources**: {', '.join(data['summary']['sync_sources']) or 'N/A'}",
        f"",
        f"---",
        f"",
    ]

    # Last actions table
    if data["summary"]["last_actions"]:
        lines.append("## Recent Actions")
        lines.append("")
        lines.append("| Repo | Action | Timestamp |")
        lines.append("|------|--------|-----------|")
        for action in data["summary"]["last_actions"]:
            lines.append(f"| {action['repo']} | {action['action']} | {action['timestamp']} |")
        lines.append("")

    # Per-repo details
    lines.append("## Per-Repository Checkpoints")
    lines.append("")

    for repo_name, repo_data in sorted(data["checkpoints"].items()):
        lines.append(f"### {repo_name}")
        lines.append(f"**Path**: `{repo_data['path']}`")
        lines.append("")

        for cp_file, cp_data in repo_data["checkpoints"].items():
            lines.append(f"#### `{cp_file}`")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(cp_data, indent=2, ensure_ascii=False))
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aggregate .mdu checkpoints across gerivdb ecosystem")
    parser.add_argument("--output", choices=["json", "md"], default="json", help="Output format")
    parser.add_argument("--repos-root", type=str, help="Override repo roots (colon-separated)")
    parser.add_argument("--output-file", type=str, help="Write to file instead of stdout")
    args = parser.parse_args()

    roots = REPO_ROOTS
    if args.repos_root:
        roots = [Path(p) for p in args.repos_root.split(";")]

    data = aggregate_checkpoints(roots)

    if args.output == "json":
        out = output_json(data)
    else:
        out = output_markdown(data)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Written to {args.output_file}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()