#!/usr/bin/env python3
"""
KIVA-CLI — KEEL R10 Gate

Vérifie qu'un merge vers main/master contient bien un champ `hitl_approved: true`
dans le WAL event ou le commit message. Si absent → exit code 1.

R10 : counit (merge vers main) exige ⊷! FLUX — zéro auto-promotion.

ERR_009 mitigation.4 | IntentHash: 0xKEEL_R10_GATE_20260611
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone


class KeelR10Gate:
    """
    Gate R10 : merge vers main/master → requires hitl_approved.

    Vérifie :
    1. Le commit message contient [HITL-APPROVED] ou hitl_approved: true
    2. Le dernier WAL event contient hitl_approved: true
    3. La variable d'environnement HITL_APPROVED=true
    """

    HITL_PATTERNS = [
        r'\[HITL-APPROVED\]',
        r'hitl_approved:\s*true',
        r'⊷!\s*FLUX',
    ]

    def __init__(self, repo_path: str = ".", wal_path: str = ""):
        self.repo_path = Path(repo_path)
        self.wal_path = Path(wal_path) if wal_path else None

    def check_commit_message(self, message: str) -> bool:
        """Vérifie si le commit message contient une approbation HITL."""
        for pattern in self.HITL_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def check_wal_event(self) -> bool:
        """Vérifie si le dernier WAL event contient hitl_approved: true."""
        if self.wal_path is None or not self.wal_path.exists():
            return False
        try:
            lines = self.wal_path.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines):
                if line.strip():
                    event = json.loads(line)
                    if event.get("hitl_approved") is True:
                        return True
                    if "HITL-APPROVED" in str(event.get("detail", "")):
                        return True
        except (json.JSONDecodeError, KeyError):
            pass
        return False

    def check_env(self) -> bool:
        """Vérifie la variable d'environnement HITL_APPROVED."""
        return os.environ.get("HITL_APPROVED", "").lower() == "true"

    def validate(self, commit_message: str = "") -> tuple[bool, str]:
        """
        Valide le gate R10.
        Retourne (passed, message).
        """
        # Check 1: commit message
        if self.check_commit_message(commit_message):
            return True, "R10_PASS: HITL approval found in commit message"

        # Check 2: WAL event
        if self.check_wal_event():
            return True, "R10_PASS: HITL approval found in WAL event"

        # Check 3: env var
        if self.check_env():
            return True, "R10_PASS: HITL_APPROVED env var set"

        return False, (
            "R10_VIOLATION: counit (merge vers main) requires ⊷! FLUX. "
            "Add [HITL-APPROVED] to commit message, or set HITL_APPROVED=true, "
            "or add hitl_approved: true to WAL event."
        )


def main():
    """Point d'entrée CLI pour le gate R10."""
    import argparse

    parser = argparse.ArgumentParser(description="KEEL R10 Gate — merge requires HITL")
    parser.add_argument("--commit-message", "-m", default="", help="Commit message to check")
    parser.add_argument("--wal-path", "-w", default="", help="Path to WAL JSONL file")
    parser.add_argument("--repo-path", "-r", default=".", help="Repository path")
    args = parser.parse_args()

    gate = KeelR10Gate(
        repo_path=args.repo_path,
        wal_path=args.wal_path,
    )

    passed, message = gate.validate(args.commit_message)

    if passed:
        print(f"[R10_GATE] ✓ {message}")
        sys.exit(0)
    else:
        print(f"[R10_GATE] ✗ {message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
