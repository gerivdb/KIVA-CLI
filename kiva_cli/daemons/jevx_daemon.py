#!/usr/bin/env python3
"""
JEVX Daemon — Intégration KIX pour le décideur typé LLM-local.

Ce daemon permet de démarrer/arrêter JEVX via KIX.
JEVX est un service TypeScript/Bun qui expose /v1/systemone sur 127.0.0.1:8080.

Contrat : PRD-MOC-JEVX-CLM-INTEGRATION-CONTRACT-2026-09-19.md
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Ajouter KIX au path
KIX_PATH = Path(r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI")
sys.path.insert(0, str(KIX_PATH))

try:
    from kiva_cli.core.daemon_manager import DaemonManager
    from kiva_cli.core.service_discovery import ServiceDiscovery
    HAS_KIX = True
except ImportError:
    HAS_KIX = False


class JevxDaemon:
    """Daemon KIX pour JEVX."""
    
    def __init__(self):
        self.jevx_path = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\JEVX")
        self.port = 8080
        self.host = "127.0.0.1"
        self.process: Optional[subprocess.Popen] = None
        
        # Initialiser KIX si disponible
        if HAS_KIX:
            self.daemon_manager = DaemonManager()
            self.service_discovery = ServiceDiscovery()
        else:
            self.daemon_manager = None
            self.service_discovery = None
    
    def start(self) -> Dict[str, Any]:
        """Démarre JEVX via KIX."""
        if self.process and self.process.poll() is None:
            return {
                "status": "already_running",
                "pid": self.process.pid,
                "port": self.port
            }
        
        # Vérifier que le chemin JEVX existe
        if not self.jevx_path.exists():
            return {
                "status": "error",
                "message": f"JEVX path not found: {self.jevx_path}"
            }
        
        try:
            # Démarrer JEVX via bun
            env = os.environ.copy()
            env["PORT"] = str(self.port)
            env["HOST"] = self.host
            
            self.process = subprocess.Popen(
                ["bun", "run", "src/index.ts"],
                cwd=self.jevx_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Attendre que le service soit prêt
            time.sleep(2)
            
            # Enregistrer dans KIX si disponible
            if self.service_discovery:
                self.service_discovery.register_service(
                    name="jevx",
                    host=self.host,
                    port=self.port,
                    protocol="http",
                    metadata={
                        "path": str(self.jevx_path),
                        "type": "decision-engine",
                        "intent_hash": "0xINTENT_JEVX_SOVEREIGN_OVERLAY_20260919"
                    }
                )
            
            return {
                "status": "started",
                "pid": self.process.pid,
                "port": self.port,
                "host": self.host
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def stop(self) -> Dict[str, Any]:
        """Arrête JEVX."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            time.sleep(1)
            if self.process.poll() is None:
                self.process.kill()
            
            # Supprimer du service discovery
            if self.service_discovery:
                self.service_discovery.deregister_service("jevx")
            
            return {
                "status": "stopped",
                "pid": self.process.pid
            }
        else:
            return {
                "status": "not_running"
            }
    
    def status(self) -> Dict[str, Any]:
        """Retourne le statut de JEVX."""
        running = self.process and self.process.poll() is None
        
        result = {
            "status": "running" if running else "stopped",
            "pid": self.process.pid if running else None,
            "port": self.port,
            "host": self.host
        }
        
        # Vérifier via KIX si disponible
        if self.service_discovery:
            service = self.service_discovery.discover_service("jevx")
            if service:
                result["kix_status"] = service.status
                result["kix_url"] = service.get_url()
        
        return result
    
    def is_healthy(self) -> bool:
        """Vérifie que JEVX répond."""
        try:
            import requests
            resp = requests.get(f"http://{self.host}:{self.port}/health", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False


def main():
    """Point d'entrée CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JEVX Daemon — KIX integration")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"],
                       help="Action à effectuer")
    args = parser.parse_args()
    
    daemon = JevxDaemon()
    
    if args.action == "start":
        result = daemon.start()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("status") in ["started", "already_running"] else 1)
    
    elif args.action == "stop":
        result = daemon.stop()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("status") == "stopped" else 1)
    
    elif args.action == "status":
        result = daemon.status()
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
    elif args.action == "restart":
        daemon.stop()
        time.sleep(1)
        result = daemon.start()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("status") == "started" else 1)


if __name__ == "__main__":
    main()
