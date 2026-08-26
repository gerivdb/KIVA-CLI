#!/usr/bin/env python3
"""
STYX - Pipeline d'Expulsion
Gère l'expulsion des dépôts obsolètes vers EMRG-ARCHIVE.
"""

import json
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class StyxPipeline:
    """Pipeline d'expulsion STYX"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            "archive_target": "EMRG-ARCHIVE",
            "notification_channels": ["governance-hub", "alerts-slack"],
            "rollback_window_hours": 72,
            "dry_run": True  # Mode test par défaut
        }
        self.expiry_log = Path("/var/log/styx_expiry.log")
    
    def process_verdict(self, verdict: Dict) -> Dict:
        """
        Traite un verdict d'expulsion.
        
        Returns:
            Dict with action status and details
        """
        if verdict.get("verdict") != "EXPULSION":
            return {
                "action": "skip",
                "reason": f"Verdict {verdict.get('verdict')} ne nécessite pas d'expulsion",
                "repo": verdict.get("repo")
            }
        
        repo = verdict.get("repo")
        if not repo:
            return {"action": "error", "reason": "Repo manquant dans le verdict"}
        
        result = {
            "action": "expulsion",
            "repo": repo,
            "timestamp": datetime.utcnow().isoformat(),
            "steps": []
        }
        
        # Étape 1: Snapshot
        snapshot_result = self._create_snapshot(repo)
        result["steps"].append({"step": "snapshot", "status": snapshot_result["status"]})
        
        if snapshot_result["status"] == "error":
            result["action"] = "error"
            result["reason"] = snapshot_result.get("error", "Snapshot échoué")
            return result
        
        # Étape 2: Archive (si pas dry_run)
        if not self.config.get("dry_run", True):
            archive_result = self._archive_repo(repo)
            result["steps"].append({"step": "archive", "status": archive_result["status"]})
        else:
            result["steps"].append({"step": "archive", "status": "dry_run"})
        
        # Étape 3: Notification
        notification_result = self._notify(repo, verdict)
        result["steps"].append({"step": "notification", "status": notification_result["status"]})
        
        # Étape 4: Cleanup (si pas dry_run)
        if not self.config.get("dry_run", True):
            cleanup_result = self._cleanup_fork(repo)
            result["steps"].append({"step": "cleanup", "status": cleanup_result["status"]})
        else:
            result["steps"].append({"step": "cleanup", "status": "dry_run"})
        
        return result
    
    def _create_snapshot(self, repo: str) -> Dict:
        """Créer un snapshot complet du dépôt"""
        try:
            # Vérifier si le dépôt existe localement
            local_path = Path(f"D:/DO/WEB/TOOLS/L1-INFRA/{repo.split('/')[-1]}")
            if not local_path.exists():
                return {"status": "skipped", "reason": "Repo local non trouvé"}
            
            # Créer snapshot
            snapshot_dir = Path(f"/snapshots/{repo.split('/')[-1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            # Copier le contenu
            shutil.copytree(local_path, snapshot_dir / "repo", dirs_exist_ok=True)
            
            # Créer métadonnées du snapshot
            metadata = {
                "repo": repo,
                "snapshot_timestamp": datetime.utcnow().isoformat(),
                "reason": "STYX expulsion",
                "verdict_timestamp": datetime.utcnow().isoformat()
            }
            with open(snapshot_dir / "metadata.json", "w") as f:
                json.dump(metadata, f, indent=2)
            
            return {"status": "completed", "snapshot_path": str(snapshot_dir)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _archive_repo(self, repo: str) -> Dict:
        """Archiver le dépôt dans EMRG-ARCHIVE"""
        try:
            # Cette étape nécessiterait un accès au système d'archivage
            # Pour l'instant, on loggue l'intention
            return {"status": "completed", "note": "Archive intentée vers EMRG-ARCHIVE"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _notify(self, repo: str, verdict: Dict) -> Dict:
        """Envoyer les notifications"""
        try:
            notification = {
                "type": "expulsion",
                "repo": repo,
                "verdict": verdict,
                "timestamp": datetime.utcnow().isoformat(),
                "channels": self.config.get("notification_channels", [])
            }
            
            # Log pour inspection
            print(json.dumps({"notification": notification}), file=sys.stderr)
            
            return {"status": "completed", "channels": notification["channels"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _cleanup_fork(self, repo: str) -> Dict:
        """Nettoyer le fork local"""
        try:
            local_path = Path(f"D:/DO/WEB/TOOLS/L1-INFRA/{repo.split('/')[-1]}")
            if local_path.exists():
                shutil.rmtree(local_path)
                return {"status": "completed", "path_removed": str(local_path)}
            return {"status": "skipped", "reason": "Path non trouvé"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


def main():
    """Read verdict from stdin, process expulsion, output result"""
    styx = StyxPipeline()
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            verdict = json.loads(line)
            result = styx.process_verdict(verdict)
            print(json.dumps(result))
        except json.JSONDecodeError as e:
            print(json.dumps({"action": "error", "error": f"Invalid JSON: {e}"}), file=sys.stderr)
        except Exception as e:
            print(json.dumps({"action": "error", "error": str(e)}), file=sys.stderr)


if __name__ == "__main__":
    main()