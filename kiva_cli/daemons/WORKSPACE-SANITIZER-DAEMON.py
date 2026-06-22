"""WORKSPACE-SANITIZER-DAEMON — Daemon KIVA-CLI de protection des workspaces.

Bloque les git push quand le working tree est pollué ou quand des changements
non liés risquent de contaminer le commit.

Déclenchement : pre-push hook global (KIVA-CLI).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def git_status(repo: str) -> dict[str, Any]:
    try:
        out = subprocess.check_output(
            ["git", "-C", repo, "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return {"error": str(exc)}

    lines = [line for line in out.splitlines() if line.strip()]
    staged = [l for l in lines if l.startswith("M ") or l.startswith("A ")]
    modified = [l for l in lines if l.startswith(" M")]
    untracked = [l for l in lines if l.startswith("??")]
    return {
        "repo": repo,
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "total_changes": len(lines),
    }


def run(repo: str) -> dict[str, Any]:
    status = git_status(repo)
    if "error" in status:
        return {"ok": False, "error": status["error"]}

    blocked = False
    reasons: list[str] = []

    if status["total_changes"] == 0:
        return {"ok": True, "repo": repo, "status": "CLEAN"}

    if len(status["modified"]) > 10:
        blocked = True
        reasons.append(
            f"Trop de fichiers modifies non stages: {len(status['modified'])} > 10"
        )

    if len(status["untracked"]) > 20:
        blocked = True
        reasons.append(
            f"Trop de fichiers non trackes: {len(status['untracked'])} > 20"
        )

    return {
        "ok": not blocked,
        "repo": repo,
        "blocked": blocked,
        "reasons": reasons,
        "status": status,
    }


if __name__ == "__main__":
    import sys

    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    result = run(repo)
    if not result["ok"]:
        print("WORKSPACE_POLLUTION detectee:")
        for reason in result["reasons"]:
            print(f"- {reason}")
        raise SystemExit(1)
    print("Workspace propre.")
