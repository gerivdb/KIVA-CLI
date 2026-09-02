#!/usr/bin/env python3
"""
KIVA-CLI Local CI Runner
ZERO GitHub Actions — Exécute les 150 enforcers localement
"""

import sys
import subprocess
import yaml
import json
import time
from pathlib import Path
from typing import Dict, List, Any

class KivaCILocalCI:
    def __init__(self, config_path: str = "ci.yaml", enforcers_path: str = "enforcers.yaml"):
        self.repo_root = Path(__file__).parent
        self.config = yaml.safe_load((self.repo_root / ".kiva" / config_path).read_text(encoding="utf-8"))
        self.enforcers = yaml.safe_load((self.repo_root / ".kiva" / enforcers_path).read_text(encoding="utf-8"))
        self.results = []
        self.start_time = time.time()

    def run_command(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        """Exécute une commande et retourne le résultat."""
        start = time.time()
        try:
            result = subprocess.run(
                command, shell=True, cwd=self.repo_root,
                capture_output=True, text=True, timeout=timeout
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "duration": time.time() - start
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Timeout ({timeout}s)",
                "returncode": -1,
                "duration": time.time() - start
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "duration": time.time() - start
            }

    def run_pre_commit(self) -> bool:
        """Exécute les checks pre-commit."""
        print("\n" + "=" * 60)
        print("🔒 KIVA-CLI PRE-COMMIT CHECKS")
        print("=" * 60)

        checks = self.config.get("pre_commit", [])
        all_passed = True

        for check in checks:
            name = check.get("name", "Unknown")
            command = check.get("command", "")
            timeout = check.get("timeout", 60)
            critical = check.get("critical", True)

            print(f"\n🔍 {name}...")
            result = self.run_command(command, timeout)

            if result["success"]:
                print(f"   ✅ {name} — OK ({result['duration']:.1f}s)")
            else:
                print(f"   ❌ {name} — ÉCHEC ({result['duration']:.1f}s)")
                print(f"   stderr: {result['stderr'][:200]}")
                if critical:
                    all_passed = False

        return all_passed

    def run_pre_push(self) -> bool:
        """Exécute les checks pre-push."""
        print("\n" + "=" * 60)
        print("🚀 KIVA-CLI PRE-PUSH CHECKS")
        print("=" * 60)

        checks = self.config.get("pre_push", [])
        all_passed = True

        for check in checks:
            name = check.get("name", "Unknown")
            command = check.get("command", "")
            timeout = check.get("timeout", 120)
            critical = check.get("critical", True)

            print(f"\n🔍 {name}...")
            result = self.run_command(command, timeout)

            if result["success"]:
                print(f"   ✅ {name} — OK ({result['duration']:.1f}s)")
            else:
                print(f"   ❌ {name} — ÉCHEC ({result['duration']:.1f}s)")
                print(f"   stderr: {result['stderr'][:200]}")
                if critical:
                    all_passed = False

        return all_passed

    def run_enforcers(self, phases: List[str] = None) -> Dict[str, Any]:
        """Exécute les enforcers par phases."""
        if phases is None:
            phases = self.enforcers.get("execution_order", [])

        print("\n" + "=" * 60)
        print("🛡️  KIVA-CLI ENFORCERS EXECUTION")
        print("=" * 60)

        enforcer_results = {}
        total_phases = len(phases)
        all_passed = True

        for i, phase in enumerate(phases, 1):
            enforcer_list = self.enforcers.get(phase, [])
            print(f"\n📦 Phase {i}/{total_phases}: {phase} ({len(enforcer_list)} enforcers)")

            phase_results = []
            for enforcer_id in enforcer_list:
                enforcer_file = self.repo_root / "kilocode" / "guards" / "design_enforcement" / f"{enforcer_id}.py"
                if not enforcer_file.exists():
                    print(f"   ⚠️  {enforcer_id} — FICHIER MANQUANT")
                    phase_results.append({"enforcer": enforcer_id, "success": False, "error": "File not found"})
                    continue

                # Import et exécution de l'enforcer
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location(enforcer_id, enforcer_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    enforcer_class = getattr(module, f"{''.join(w.capitalize() for w in enforcer_id.replace('.', '_').split('_'))}Enforcer")
                    enforcer = enforcer_class()

                    from kilocode.guards.base import GuardContext
                    ctx = GuardContext()
                    result = enforcer.check(ctx)

                    phase_results.append({
                        "enforcer": enforcer_id,
                        "success": result.passed,
                        "message": result.message,
                        "severity": result.severity
                    })

                    status = "✅" if result.passed else "❌"
                    print(f"   {status} {enforcer_id}: {result.message[:80]}")

                    if not result.passed:
                        all_passed = False

                except Exception as e:
                    print(f"   ❌ {enforcer_id} — ERREUR: {e}")
                    phase_results.append({"enforcer": enforcer_id, "success": False, "error": str(e)})
                    all_passed = False

            enforcer_results[phase] = phase_results

        return {"success": all_passed, "phases": enforcer_results}

    def run_full_ci(self) -> Dict[str, Any]:
        """Exécute le pipeline CI complet."""
        print("=" * 60)
        print("🚀 KIVA-CLI LOCAL CI PIPELINE")
        print("   ZERO GitHub Actions — Local CI Only")
        print("=" * 60)

        results = {
            "pre_commit": False,
            "pre_push": False,
            "enforcers": {},
            "total_duration": 0,
            "overall_success": False
        }

        # Pre-commit
        results["pre_commit"] = self.run_pre_commit()

        # Pre-push
        results["pre_push"] = self.run_pre_push()

        # Enforcers
        phases = self.enforcers.get("execution_order", [])
        enforcer_results = self.run_enforcers(phases)
        results["enforcers"] = enforcer_results

        # Résumé final
        results["total_duration"] = time.time() - self.start_time
        results["overall_success"] = (
            results["pre_commit"] and
            results["pre_push"] and
            results["enforcers"].get("success", False)
        )

        self.print_summary(results)
        return results

    def print_summary(self, results: Dict[str, Any]):
        print("\n" + "=" * 60)
        print("📊 KIVA-CLI CI SUMMARY")
        print("=" * 60)
        print(f"   Pre-commit:     {'✅ PASS' if results['pre_commit'] else '❌ FAIL'}")
        print(f"   Pre-push:       {'✅ PASS' if results['pre_push'] else '❌ FAIL'}")
        print(f"   Enforcers:      {'✅ PASS' if results['enforcers'].get('success') else '❌ FAIL'}")
        print(f"   Durée totale:   {results['total_duration']:.1f}s")
        print(f"   GLOBAL:         {'✅ SUCCESS' if results['overall_success'] else '❌ FAILURE'}")
        print("=" * 60)

        # Sauvegarder rapport JSON
        report_dir = self.repo_root / ".kiva" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"ci-report-{time.strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"📄 Rapport sauvegardé: {report_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="KIVA-CLI Local CI Runner")
    parser.add_argument("--pre-commit", action="store_true", help="Run pre-commit checks only")
    parser.add_argument("--pre-push", action="store_true", help="Run pre-push checks only")
    parser.add_argument("--enforcers", action="store_true", help="Run enforcers only")
    parser.add_argument("--full", action="store_true", help="Run full CI pipeline (default)")
    args = parser.parse_args()

    ci = KivaCILocalCI()

    if args.pre_commit:
        success = ci.run_pre_commit()
        sys.exit(0 if success else 1)
    elif args.pre_push:
        success = ci.run_pre_push()
        sys.exit(0 if success else 1)
    elif args.enforcers:
        results = ci.run_enforcers()
        sys.exit(0 if results.get("success") else 1)
    else:
        results = ci.run_full_ci()
        sys.exit(0 if results["overall_success"] else 1)


if __name__ == "__main__":
    main()