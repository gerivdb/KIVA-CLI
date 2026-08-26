#!/usr/bin/env python3
"""
Digestion Engine Orchestrator
Pipeline orchestration pour la triade cognitive IRIS/KRONOS/STYX.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Import des services
sys.path.insert(0, str(Path(__file__).parent))
from iris_service import IrisService, MudSignal
from kronos_engine import KronosEngine, KronosRules
from styx_pipeline import StyxPipeline


class DigestionOrchestrator:
    """Orchestrateur du pipeline Digestion Engine"""
    
    def __init__(self):
        self.iris = IrisService()
        self.kronos = KronosEngine()
        self.styx = StyxPipeline()
        self.wal_path = Path("/wal/digestion")
        self.wal_path.mkdir(parents=True, exist_ok=True)
    
    async def run_single_cycle(self):
        """Exécuter un cycle complet du pipeline"""
        results = []
        
        for repo in self.iris.config["targets"]:
            print(f"[ORCHESTRATOR] Processing {repo}")
            
            # Étape 1: IRIS - Collecte des signaux
            mud_signal = await self.iris.collect_signals(repo)
            signal_dict = mud_signal.to_dict()
            
            # Étape 2: KRONOS - Qualification
            verdict = self.kronos.qualify(signal_dict)
            
            # Étape 3: STYX - Traitement des verdicts
            styx_result = self.styx.process_verdict(verdict)
            
            # Log des résultats
            result = {
                "repo": repo,
                "signal": signal_dict,
                "verdict": verdict,
                "styx_result": styx_result,
                "timestamp": mud_signal.timestamp
            }
            results.append(result)
            
            # Écriture dans le WAL
            self._write_to_wal(result)
        
        return results
    
    def _write_to_wal(self, result: Dict):
        """Écrire le résultat dans le WAL"""
        timestamp = result.get("timestamp", "").replace(":", "-").replace(".", "-")
        wal_file = self.wal_path / f"{timestamp}.jsonl"
        
        with open(wal_file, "a") as f:
            f.write(json.dumps(result) + "\n")
    
    async def run(self):
        """Exécuter le pipeline en continu"""
        print("[ORCHESTRATOR] Démarrage du pipeline Digestion Engine")
        print(f"[ORCHESTRATOR] Cibles: {self.iris.config['targets']}")
        print(f"[ORCHESTRATOR] Intervalle: {self.iris.config['poll_interval']}s")
        
        while True:
            try:
                results = await self.run_single_cycle()
                print(f"[ORCHESTRATOR] Cycle terminé: {len(results)} repos traités")
                
                # Statistiques
                citizens = sum(1 for r in results if r["verdict"]["verdict"] == "CITIZEN")
                monitors = sum(1 for r in results if r["verdict"]["verdict"] == "MONITOR")
                expulsions = sum(1 for r in results if r["verdict"]["verdict"] == "EXPULSION")
                
                print(f"[ORCHESTRATOR] Stats: CITIZEN={citizens}, MONITOR={monitors}, EXPULSION={expulsions}")
                
            except Exception as e:
                print(f"[ORCHESTRATOR] Erreur: {e}", file=sys.stderr)
            
            await asyncio.sleep(self.iris.config["poll_interval"])


def main():
    """Main entry point"""
    orchestrator = DigestionOrchestrator()
    asyncio.run(orchestrator.run())


if __name__ == "__main__":
    main()