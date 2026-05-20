#!/usr/bin/env python3
"""
LXC Orchestration Manager - KIVA CLI

Manages LXC/LXD containers for ECOS infrastructure.
Provides container lifecycle management, resource allocation, and monitoring.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any


class LXCContainer:
    """Represents an LXC container."""
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.image = data.get("image", "ubuntu:22.04")
        self.status = data.get("status", "stopped")
        self.cpu = data.get("cpu", 2)
        self.memory = data.get("memory", "4GB")
        self.storage = data.get("storage", "20GB")
        self.created_at = data.get("created_at", "")
        self.ip_address = data.get("ip_address", "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "image": self.image, "status": self.status,
            "cpu": self.cpu, "memory": self.memory, "storage": self.storage,
            "created_at": self.created_at, "ip_address": self.ip_address
        }


class LXCManager:
    """Manages LXC/LXD containers."""

    def __init__(self, containers_dir: Optional[str] = None):
        if containers_dir is None:
            containers_dir = "C:\\DevTools\\data\\lxc"
        self.containers_dir = Path(containers_dir)
        self.containers_file = self.containers_dir / "containers.json"
        self.containers: Dict[str, LXCContainer] = {}
        self._load_containers()

    def _load_containers(self):
        if self.containers_file.exists():
            try:
                with open(self.containers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for c_data in data.get("containers", []):
                    self.containers[c_data["name"]] = LXCContainer(c_data)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_containers(self):
        data = {"containers": [c.to_dict() for c in self.containers.values()]}
        os.makedirs(os.path.dirname(self.containers_file), exist_ok=True)
        with open(self.containers_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_container(self, name: str, image: str = "ubuntu:22.04", cpu: int = 2, memory: str = "4GB", storage: str = "20GB") -> bool:
        if name in self.containers:
            return False
        self.containers[name] = LXCContainer({
            "name": name, "image": image, "status": "stopped",
            "cpu": cpu, "memory": memory, "storage": storage,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        self._save_containers()
        return True

    def start_container(self, name: str) -> bool:
        if name in self.containers:
            self.containers[name].status = "running"
            self.containers[name].ip_address = "10.0.0.{}".format(len(self.containers))
            self._save_containers()
            return True
        return False

    def stop_container(self, name: str) -> bool:
        if name in self.containers:
            self.containers[name].status = "stopped"
            self.containers[name].ip_address = ""
            self._save_containers()
            return True
        return False

    def delete_container(self, name: str) -> bool:
        if name in self.containers:
            del self.containers[name]
            self._save_containers()
            return True
        return False

    def list_containers(self) -> List[LXCContainer]:
        return list(self.containers.values())

    def get_container_status(self, name: str) -> Optional[LXCContainer]:
        return self.containers.get(name)

    def get_all_status(self) -> Dict[str, Any]:
        running = len([c for c in self.containers.values() if c.status == "running"])
        return {
            "total_containers": len(self.containers),
            "running_containers": running,
            "stopped_containers": len(self.containers) - running
        }