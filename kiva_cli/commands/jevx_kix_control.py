#!/usr/bin/env python3
"""
Contrôle KIX pour JEVX — start/stop/status/restart.

Usage:
    python jevx_kix_control.py start
    python jevx_kix_control.py stop
    python jevx_kix_control.py status
    python jevx_kix_control.py restart
"""

import sys
import json
from pathlib import Path

# Ajouter KIX et JEVX au path
KIX_PATH = Path(r"D:\DO\WEB\TOOLS\L1-INFRA\KIVA-CLI")
JEVX_PATH = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\JEVX")
sys.path.insert(0, str(KIX_PATH))
sys.path.insert(0, str(JEVX_PATH / "scripts"))

try:
    from kiva_cli.core.daemon_manager import DaemonManager
    from kiva_cli.core.service_discovery import ServiceDiscovery
except ImportError as e:
    print(f"ERROR: Cannot import KIX modules: {e}")
    sys.exit(1)


def start_jevx():
    """Démarre JEVX via KIX DaemonManager."""
    manager = DaemonManager()
    discovery = ServiceDiscovery()
    
    # Vérifier si JEVX est déjà enregistré
    existing = discovery.discover_service("jevx")
    if existing and existing.status == "healthy":
        print("JEVX est déjà en cours d'exécution")
        return 0
    
    # Enregistrer le daemon JEVX
    daemon_id = manager.register_daemon(
        name="jevx",
        daemon_type="BASH_SCRIPT",
        script_path=str(JEVX_PATH / "scripts" / "start_jevx.sh"),
        description="Décideur typé LLM-local souverain — JEVX",
        metadata={
            "path": str(JEVX_PATH),
            "port": 8080,
            "host": "127.0.0.1",
            "endpoint": "/v1/systemone",
            "intent_hash": "0xINTENT_JEVX_SOVEREIGN_OVERLAY_20260919"
        }
    )
    
    print(f"Daemon JEVX enregistré: {daemon_id}")
    
    # Démarrer le daemon
    success = manager.start_daemon(daemon_id)
    if success:
        print("JEVX démarré avec succès")
        
        # Enregistrer dans service discovery
        discovery.register_service(
            name="jevx",
            host="127.0.0.1",
            port=8080,
            protocol="http",
            metadata={
                "path": str(JEVX_PATH),
                "type": "decision-engine",
                "daemon_id": daemon_id,
                "intent_hash": "0xINTENT_JEVX_SOVEREIGN_OVERLAY_20260919"
            }
        )
        return 0
    else:
        print("ERROR: Échec du démarrage de JEVX")
        return 1


def stop_jevx():
    """Arrête JEVX via KIX."""
    manager = DaemonManager()
    discovery = ServiceDiscovery()
    
    # Trouver le daemon JEVX
    daemons = manager.list_daemons()
    jevx_daemon = None
    for d in daemons:
        if d.get("name") == "jevx":
            jevx_daemon = d
            break
    
    if not jevx_daemon:
        print("JEVX n'est pas enregistré dans KIX")
        return 1
    
    daemon_id = jevx_daemon.get("daemon_id")
    
    # Arrêter le daemon
    success = manager.stop_daemon(daemon_id)
    if success:
        print("JEVX arrêté avec succès")
        
        # Supprimer du service discovery
        discovery.deregister_service("jevx")
        return 0
    else:
        print("ERROR: Échec de l'arrêt de JEVX")
        return 1


def status_jevx():
    """Affiche le statut de JEVX."""
    manager = DaemonManager()
    discovery = ServiceDiscovery()
    
    # Statut via service discovery
    service = discovery.discover_service("jevx")
    
    result = {
        "service_discovery": {
            "name": service.name if service else "jevx",
            "status": service.status if service else "not_registered",
            "url": service.get_url() if service else "N/A",
            "metadata": service.metadata if service else {}
        }
    }
    
    # Statut via daemon manager
    daemons = manager.list_daemons()
    jevx_daemon = None
    for d in daemons:
        if d.get("name") == "jevx":
            jevx_daemon = d
            break
    
    if jevx_daemon:
        result["daemon"] = {
            "daemon_id": jevx_daemon.get("daemon_id"),
            "status": jevx_daemon.get("runtime_state"),
            "validation": jevx_daemon.get("validation_state"),
            "lifecycle": jevx_daemon.get("lifecycle_state")
        }
    else:
        result["daemon"] = {"status": "not_registered"}
    
    print(json.dumps(result, indent=2))
    return 0


def restart_jevx():
    """Redémarre JEVX."""
    stop_jevx()
    import time
    time.sleep(1)
    return start_jevx()


def main():
    if len(sys.argv) < 2:
        print("Usage: python jevx_kix_control.py <start|stop|status|restart>")
        return 1
    
    action = sys.argv[1].lower()
    
    if action == "start":
        return start_jevx()
    elif action == "stop":
        return stop_jevx()
    elif action == "status":
        return status_jevx()
    elif action == "restart":
        return restart_jevx()
    else:
        print(f"Unknown action: {action}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
