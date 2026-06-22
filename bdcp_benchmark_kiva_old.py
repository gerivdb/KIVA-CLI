#!/usr/bin/env python3
"""BDCP Content Search Performance Benchmark."""

import time
import sys
from pathlib import Path

# Add kiva_cli to path
sys.path.insert(0, str(Path(__file__).parent / "kiva_cli"))

from kiva_cli.commands.epic_commands import ResourceDiscovery


def benchmark_content_search():
    """Benchmark BDCP-optimized vs traditional content search."""

    # Setup
    ontology_client = None  # Mock for this test
    discovery = ResourceDiscovery(ontology_client)

    # Test parameters
    test_epic_id = "EPIC_TEMPLATE_ENGINE_V1"
    base_path = Path("D:/DO/WEB/TOOLS/L0-CANON/NEXUS")

    if not base_path.exists():
        print("ERROR: Test directory does not exist")
        return

    print("🔬 BDCP Content Search Benchmark")
    print("=" * 50)
    print(f"EPIC ID: {test_epic_id}")
    print(f"Base path: {base_path}")
    print()

    # Benchmark BDCP version
    print("Testing BDCP-optimized search...")
    start_time = time.time()

    discovered_bdcp = {
        "epic_files": [],
        "prds": [],
        "tests": [],
        "modules": [],
        "docs": [],
    }

    discovery._find_by_content(base_path, test_epic_id, discovered_bdcp)

    bdcp_time = time.time() - start_time
    bdcp_total_files = sum(len(files) for files in discovered_bdcp.values())

    print(f"BDCP search completed in {bdcp_time:.3f}s")
    print(f"  Files found: {bdcp_total_files}")
    print(f"  Tests: {len(discovered_bdcp['tests'])}")
    print(f"  Modules: {len(discovered_bdcp['modules'])}")
    print()

    # Traditional approach simulation (simplified)
    print("Simulating traditional search...")
    start_time = time.time()

    discovered_traditional = {
        "epic_files": [],
        "prds": [],
        "tests": [],
        "modules": [],
        "docs": [],
    }

    # Simulate traditional approach with file reading
    import subprocess

    try:
        result = subprocess.run(
            [
                "rg",
                "--files-with-matches",
                "--glob",
                "*.py",
                "--regexp",
                test_epic_id,
                str(base_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    try:
                        file_path = Path(line.strip())
                        if file_path.exists():
                            rel_path = str(file_path.relative_to(base_path))
                            if "test" in rel_path.lower():
                                discovered_traditional["tests"].append(rel_path)
                            else:
                                discovered_traditional["modules"].append(rel_path)
                    except:
                        pass
    except:
        pass

    traditional_time = time.time() - start_time
    traditional_total_files = sum(
        len(files) for files in discovered_traditional.values()
    )

    print(f"Traditional search completed in {traditional_time:.3f}s")
    print(f"  Files found: {traditional_total_files}")
    print()

    # Results comparison
    print("📊 PERFORMANCE COMPARISON")
    print("=" * 30)

    if bdcp_time > 0 and traditional_time > 0:
        speedup = (
            traditional_time / bdcp_time
            if bdcp_time < traditional_time
            else bdcp_time / traditional_time
        )
        winner = "BDCP" if bdcp_time < traditional_time else "Traditional"

        print(f"BDCP time: {bdcp_time:.3f}s")
        print(f"Traditional time: {traditional_time:.3f}s")
        print(f"Speedup: {speedup:.1f}x")
        print(f"Winner: {winner}")
    else:
        print("Insufficient data for comparison")

    print()
    print("✅ BDCP Sprint 1 implementation complete")
    print("Next: API calls optimization (Sprint 2)")


if __name__ == "__main__":
    benchmark_content_search()
