#!/usr/bin/env python3
"""
KIVA-CLI Wrapper — Point d'entrée standard pour l'écosystème NEXUS.

Usage:
    python kiva_wrapper.py <command> [args...]

Commands:
    ci-status <repo_path>     Check CI status for a repository
    gate-check <repo>         Run phi-CPS gate check before merge
    gate-status <repo>        Quick gate status (non-blocking)
    wal-query [options]       Query WAL events
    phi-status                Show phi-CPS status
    discover                  Discover repositories
    version                   Show KIVA-CLI version
"""

import sys
import os
import subprocess

KIVA_CLI_PATH = r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI"
KIVA_BIN = os.path.join(KIVA_CLI_PATH, "bin", "kiva")


def run_kiva(args: list[str]) -> int:
    """Run kiva CLI with the given arguments."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["KIVA_CLI_HOME"] = KIVA_CLI_PATH

    result = subprocess.run(
        [sys.executable, KIVA_BIN] + args,
        cwd=KIVA_CLI_PATH,
        env=env,
    )
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    match command:
        case "ci-status":
            if not args:
                print("Usage: kiva_wrapper.py ci-status <repo_path>")
                sys.exit(1)
            sys.exit(run_kiva(["cicd", "status", args[0]]))

        case "gate-check":
            if not args:
                print("Usage: kiva_wrapper.py gate-check <repo_name>")
                sys.exit(1)
            sys.exit(run_kiva(["gate", "check", "--repo", args[0]]))

        case "gate-status":
            if not args:
                print("Usage: kiva_wrapper.py gate-status <repo_name>")
                sys.exit(1)
            sys.exit(run_kiva(["gate", "status", "--repo", args[0]]))

        case "wal-query":
            sys.exit(run_kiva(["wal", "query"] + args))

        case "phi-status":
            sys.exit(run_kiva(["phi-cps", "status"]))

        case "discover":
            sys.exit(run_kiva(["repo", "discover"] + args))

        case "version":
            sys.exit(run_kiva(["--version"]))

        case _:
            # Pass through to kiva directly
            sys.exit(run_kiva([command] + args))


if __name__ == "__main__":
    main()
