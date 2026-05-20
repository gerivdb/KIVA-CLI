#!/usr/bin/env python3
"""
Multi-Host Cluster Manager - KIVA CLI

Manages multi-host clustering for ECOS infrastructure.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any


class ClusterNode:
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.host = data.get("host", "")
        self.port = data.get("port", 0)
        self.role = data.get("role", "worker")
        self.status = data.get("status", "unknown")
        self.last_heartbeat = data.get("last_heartbeat", "")

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "host": self.host, "port": self.port, "role": self.role, "status": self.status, "last_heartbeat": self.last_heartbeat}


class ClusterManager:
    def __init__(self, cluster_dir: Optional[str] = None):
        if cluster_dir is None:
            cluster_dir = "C:\\DevTools\\data\\cluster"
        self.cluster_dir = Path(cluster_dir)
        self.cluster_file = self.cluster_dir / "cluster.json"
        self.nodes: Dict[str, ClusterNode] = {}
        self.cluster_name = ""
        self._load_cluster()

    def _load_cluster(self):
        if self.cluster_file.exists():
            try:
                with open(self.cluster_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.cluster_name = data.get("cluster_name", "default")
                for node_data in data.get("nodes", []):
                    self.nodes[node_data["id"]] = ClusterNode(node_data)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_cluster(self):
        data = {"cluster_name": self.cluster_name, "nodes": [n.to_dict() for n in self.nodes.values()]}
        os.makedirs(os.path.dirname(self.cluster_file), exist_ok=True)
        with open(self.cluster_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def init_cluster(self, cluster_name: str, master_host: str, master_port: int) -> bool:
        self.cluster_name = cluster_name
        self.nodes = {"master": ClusterNode({"id": "master", "host": master_host, "port": master_port, "role": "master", "status": "active", "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ")})}
        self._save_cluster()
        return True

    def join_cluster(self, node_id: str, host: str, port: int, role: str = "worker") -> bool:
        if node_id in self.nodes:
            return False
        self.nodes[node_id] = ClusterNode({"id": node_id, "host": host, "port": port, "role": role, "status": "active", "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
        self._save_cluster()
        return True

    def leave_cluster(self, node_id: str) -> bool:
        if node_id in self.nodes and node_id != "master":
            del self.nodes[node_id]
            self._save_cluster()
            return True
        return False

    def list_nodes(self) -> List[ClusterNode]:
        return list(self.nodes.values())

    def get_cluster_status(self) -> Dict[str, Any]:
        return {"cluster_name": self.cluster_name, "total_nodes": len(self.nodes), "active_nodes": len([n for n in self.nodes.values() if n.status == "active"])}