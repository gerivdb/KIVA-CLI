#!/usr/bin/env python3
"""
Distributed WAL Manager - KIVA CLI

Manages distributed Write-Ahead Log replication across multiple nodes.
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class WALEntry:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.timestamp = data.get("timestamp", time.time())
        self.operation = data.get("operation", "")
        self.data = data.get("data", {})
        self.node_id = data.get("node_id", "")
        self.hash = data.get("hash", "")
        self.prev_hash = data.get("prev_hash", "")
        self.committed = data.get("committed", False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "timestamp": self.timestamp,
            "operation": self.operation, "data": self.data,
            "node_id": self.node_id, "hash": self.hash,
            "prev_hash": self.prev_hash, "committed": self.committed
        }


class DistributedWALManager:
    def __init__(self, wal_dir: Optional[str] = None, node_id: Optional[str] = None):
        if wal_dir is None:
            wal_dir = "C:\\DevTools\\data\\wal\\distributed"
        if node_id is None:
            node_id = "node-1"
        self.wal_dir = Path(wal_dir)
        self.node_id = node_id
        self.wal_file = self.wal_dir / f"wal_{node_id}.json"
        self.entries: List[WALEntry] = []
        self.peers: List[str] = []
        self._load_wal()
        self._load_peers()

    def _load_wal(self):
        if self.wal_file.exists():
            try:
                with open(self.wal_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for entry_data in data.get("entries", []):
                    self.entries.append(WALEntry(entry_data))
            except (json.JSONDecodeError, IOError):
                pass

    def _save_wal(self):
        data = {"node_id": self.node_id, "entries": [e.to_dict() for e in self.entries]}
        os.makedirs(os.path.dirname(self.wal_file), exist_ok=True)
        with open(self.wal_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_peers(self):
        peers_file = self.wal_dir / "peers.json"
        if peers_file.exists():
            try:
                with open(peers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.peers = data.get("peers", [])
            except (json.JSONDecodeError, IOError):
                pass

    def _save_peers(self):
        peers_file = self.wal_dir / "peers.json"
        with open(peers_file, 'w', encoding='utf-8') as f:
            json.dump({"peers": self.peers}, f, indent=2, ensure_ascii=False)

    def _compute_hash(self, entry_data: Dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(entry_data, sort_keys=True).encode()).hexdigest()

    def add_entry(self, operation: str, data: Dict[str, Any]) -> WALEntry:
        prev_hash = self.entries[-1].hash if self.entries else ""
        entry_data = {"id": f"{self.node_id}-{len(self.entries) + 1}", "timestamp": time.time(), "operation": operation, "data": data, "node_id": self.node_id, "prev_hash": prev_hash}
        entry_data["hash"] = self._compute_hash(entry_data)
        entry = WALEntry(entry_data)
        self.entries.append(entry)
        self._save_wal()
        return entry

    def add_peer(self, peer_node_id: str) -> bool:
        if peer_node_id not in self.peers and peer_node_id != self.node_id:
            self.peers.append(peer_node_id)
            self._save_peers()
            return True
        return False

    def list_peers(self) -> List[str]:
        return self.peers

    def get_status(self) -> Dict[str, Any]:
        return {"node_id": self.node_id, "total_entries": len(self.entries), "peers_count": len(self.peers)}