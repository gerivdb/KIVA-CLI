#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
distribution_dispatcher.py — Distribution Layer Dispatcher (atomic)

Route un artefact vers le bon canal de diffusion ecosystem-wide
selon channels/registry.yaml.

Usage:
    python scripts/distribution_dispatcher.py --artifact INTENT --target repo --file <path>
    python scripts/distribution_dispatcher.py --artifact PRD-MOC --target ALL --content "<yaml>"
    python scripts/distribution_dispatcher.py --list-channels
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "channels" / "registry.yaml"
RUNTIME_CHANNELS_DIR = REPO_ROOT / "RUNTIME" / "channels"
WAZAA_INBOX_PATH = Path(r"D:\DO\WEB\TOOLS\L4-TOOLS\WAZAA\scripts\wazaa_inbox.py")

INTENT_HASH = "0xINTENT_DISTRIBUTION_LAYER_ECOSYSTEM_20260913"

# Mapping artifact type -> default channel
DEFAULT_CHANNEL_MAP = {
    "INTENT": "wazaa-bus",
    "PRD-MOC": "git-multi",
    "ADR": "git-multi",
    "REPORT": "git-multi",
    "CODE": "git-multi",
    "CONFIG": "git-multi",
    "SKILL": "skills-registry",
    "WAL": "wal-sync",
    "PIPELINE": "pipeline-execution",
    "SCRIPT": "devtools-hub",
    "TOOL": "devtools-hub",
    "CONCEPT": "wavefront",
    "ONTOLOGY": "wavefront",
    "BEACON": "boinc-p2p",
    "COMPUTE": "boinc-p2p",
    "MODEL": "boinc-p2p",
    "DATASET": "boinc-p2p",
    "EVENT": "wazaa-bus",
    "METRIC": "wazaa-bus",
    "DEBUG": "wazaa-bus",
    "ERR": "wazaa-bus",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_registry() -> Dict[str, Any]:
    """Charge channels/registry.yaml."""
    if not REGISTRY_PATH.exists():
        return {"channels": []}
    import yaml
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"channels": []}


def _log_runtime(artifact_type: str, channel_id: str, target: str, status: str, detail: str = "") -> None:
    """Log dans RUNTIME/channels/distribution_dispatcher.jsonl."""
    RUNTIME_CHANNELS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RUNTIME_CHANNELS_DIR / "distribution_dispatcher.jsonl"
    entry = {
        "ts": _utcnow_iso(),
        "intent_hash": INTENT_HASH,
        "artifact_type": artifact_type,
        "channel_id": channel_id,
        "target": target,
        "status": status,
        "detail": detail,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _emit_wazaa(artifact_type: str, channel_id: str, target: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Émet un événement WAZAA pour traçabilité."""
    if not WAZAA_INBOX_PATH.exists():
        return None
    try:
        import uuid
        wazaa_dir = WAZAA_INBOX_PATH.parent
        if str(wazaa_dir) not in sys.path:
            sys.path.insert(0, str(wazaa_dir))
        import wazaa_inbox

        sid = "kilo-distribution-" + uuid.uuid4().hex[:8]
        topic = f"distribution.{artifact_type.lower()}"
        body = {
            "intent_hash": INTENT_HASH,
            "artifact_type": artifact_type,
            "channel_id": channel_id,
            "target": target,
            "timestamp_utc": _utcnow_iso(),
            "payload": payload,
        }
        msg = wazaa_inbox.send_message(to="_swarm", from_sid=sid, topic=topic, body=body, ttl=3600)
        return {"status": "sent", "message_id": msg.get("id"), "topic": topic}
    except Exception as e:
        return {"status": "error", "exception": str(e)}


def resolve_channel(artifact_type: str, registry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Résout le canal pour un type d'artefact donné."""
    # 1. Chercher dans registry.yaml par scope
    for ch in registry.get("channels", []):
        if artifact_type in ch.get("scope", []):
            return ch
    # 2. Fallback par default map
    channel_id = DEFAULT_CHANNEL_MAP.get(artifact_type)
    if channel_id:
        for ch in registry.get("channels", []):
            if ch.get("id") == channel_id:
                return ch
    return None


def dispatch(artifact_type: str, target: str, content: str = "", file_path: Optional[str] = None, channel: Optional[str] = None) -> Dict[str, Any]:
    """Dispatch un artefact vers le canal approprié."""
    registry = _load_registry()
    channel_id = channel
    channel_obj = None

    if channel_id:
        # Canal explicite
        for ch in registry.get("channels", []):
            if ch.get("id") == channel_id:
                channel_obj = ch
                break
    else:
        # Résolution automatique
        channel_obj = resolve_channel(artifact_type, registry)
        channel_id = channel_obj.get("id") if channel_obj else None

    if not channel_obj:
        result = {
            "status": "error",
            "error": f"No channel found for artifact_type={artifact_type}",
            "artifact_type": artifact_type,
            "target": target,
        }
        _log_runtime(artifact_type, channel_id or "unknown", target, "error", result["error"])
        return result

    # Construire le payload
    payload: Dict[str, Any] = {
        "artifact_type": artifact_type,
        "target": target,
        "channel_id": channel_id,
        "content": content if content else None,
        "file_path": file_path,
    }

    # Logique de diffusion par canal (stub pour l'instant)
    dispatch_status = "dispatched"
    dispatch_detail = f"routed_to={channel_id}"

    # TODO: implémenter la logique spécifique par canal
    # - git-multi: git push/pull
    # - wazaa-bus: wazaa_inbox.send_message
    # - wavefront: append to wavefront channel
    # - boinc-p2p: beacon publish
    # - skills-registry: skills sync
    # - wal-sync: wal append
    # - pipeline-execution: pipeline trigger
    # - devtools-hub: script copy

    result = {
        "status": dispatch_status,
        "artifact_type": artifact_type,
        "channel_id": channel_id,
        "channel_name": channel_obj.get("name"),
        "target": target,
        "detail": dispatch_detail,
        "payload": payload,
    }

    # Log + WAZAA
    _log_runtime(artifact_type, channel_id, target, dispatch_status, dispatch_detail)
    wazaa_result = _emit_wazaa(artifact_type, channel_id, target, payload)
    if wazaa_result:
        result["wazaa"] = wazaa_result

    return result


def list_channels() -> Dict[str, Any]:
    """Liste tous les canaux disponibles."""
    registry = _load_registry()
    channels = []
    for ch in registry.get("channels", []):
        channels.append({
            "id": ch.get("id"),
            "name": ch.get("name"),
            "type": ch.get("type"),
            "status": ch.get("status"),
            "scope": ch.get("scope", []),
        })
    return {
        "total": len(channels),
        "active": sum(1 for c in channels if c["status"] == "active"),
        "channels": channels,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Distribution Layer Dispatcher")
    parser.add_argument("--artifact", help="Type d'artefact (INTENT, PRD-MOC, ADR, etc.)")
    parser.add_argument("--target", help="Cible (repo name ou ALL)")
    parser.add_argument("--file", help="Chemin du fichier à distribuer")
    parser.add_argument("--content", help="Contenu brut à distribuer")
    parser.add_argument("--channel", help="Canal explicite (override auto-routing)")
    parser.add_argument("--list-channels", action="store_true", help="Lister les canaux disponibles")
    args = parser.parse_args()

    if args.list_channels:
        channels = list_channels()
        print(json.dumps(channels, indent=2, ensure_ascii=False))
        return 0

    if not args.artifact or not args.target:
        print("ERROR: --artifact et --target requis (ou --list-channels)", file=sys.stderr)
        return 1

    if not args.file and not args.content:
        print("ERROR: --file ou --content requis", file=sys.stderr)
        return 1

    content = args.content or ""
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"ERROR: file not found: {args.file}", file=sys.stderr)
            return 1
        content = file_path.read_text(encoding="utf-8")

    result = dispatch(
        artifact_type=args.artifact,
        target=args.target,
        content=content,
        file_path=args.file,
        channel=args.channel,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "dispatched" else 1


if __name__ == "__main__":
    sys.exit(main())
