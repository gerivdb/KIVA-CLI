#!/usr/bin/env python3
import json, os, time, platform, logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

try:
    import pylxd
    HAS_PYLXD = True
except ImportError:
    HAS_PYLXD = False

class LXCContainer:
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
    """Manages LXC/LXD containers. Uses pylxd on Linux, JSON simulation on Windows."""

    def __init__(self, data_dir: Optional[str] = None):
        self.is_linux = platform.system() == "Linux"
        if data_dir is None:
            data_dir = os.environ.get("KIVA_LXC_DATA_DIR", "C:\\DevTools\\data\\lxc" if not self.is_linux else "/var/lib/kiva/lxc")
        self.data_dir = Path(data_dir)
        self.containers_file = self.data_dir / "containers.json"
        self.containers: Dict[str, LXCContainer] = {}

        self.client = None
        if self.is_linux and HAS_PYLXD:
            try:
                self.client = pylxd.Client()
            except Exception as e:
                logger.warning(f"Failed to connect to LXD: {e}. Falling back to simulation.")

        self._load_containers()

    def _load_containers(self):
        if self.is_linux and self.client:
            try:
                for c in self.client.containers.all():
                    ipv4 = ""
                    if c.state().network:
                        for iface, data in c.state().network.items():
                            for addr in data.get('addresses', []):
                                if addr.get('family') == 'inet': ipv4 = addr.get('address')
                    self.containers[c.name] = LXCContainer({
                        "name": c.name, "image": c.config.get("image.description", "unknown"),
                        "status": c.status.lower(), "cpu": c.config.get("limits.cpu", 2),
                        "memory": c.config.get("limits.memory", "4GB"),
                        "created_at": c.created_at, "ip_address": ipv4
                    })
                return
            except Exception as e: logger.error(f"LXD Sync error: {e}")

        if self.containers_file.exists():
            try:
                with open(self.containers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for c_data in data.get("containers", []):
                    self.containers[c_data["name"]] = LXCContainer(c_data)
            except Exception: pass

    def _save_containers(self):
        if self.is_linux and self.client: return # Managed by LXD
        data = {"containers": [c.to_dict() for c in self.containers.values()]}
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.containers_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_container(self, name: str, image: str = "ubuntu:22.04", cpu: int = 2, memory: str = "4GB", storage: str = "20GB") -> bool:
        if name in self.containers: return False

        if self.is_linux and self.client:
            try:
                config = {
                    'name': name,
                    'source': {'type': 'image', 'alias': image},
                    'config': {'limits.cpu': str(cpu), 'limits.memory': memory}
                }
                self.client.containers.create(config, wait=True)
                self._load_containers()
                return True
            except Exception as e:
                logger.error(f"LXD Creation error: {e}")
                return False

        self.containers[name] = LXCContainer({
            "name": name, "image": image, "status": "stopped",
            "cpu": cpu, "memory": memory, "storage": storage,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        self._save_containers()
        return True

    def start_container(self, name: str) -> bool:
        if self.is_linux and self.client:
            try:
                c = self.client.containers.get(name)
                c.start(wait=True)
                self._load_containers()
                return True
            except Exception: return False

        if name in self.containers:
            self.containers[name].status = "running"
            self.containers[name].ip_address = f"10.0.0.{len(self.containers)}"
            self._save_containers()
            return True
        return False

    def stop_container(self, name: str) -> bool:
        if self.is_linux and self.client:
            try:
                c = self.client.containers.get(name)
                c.stop(wait=True)
                self._load_containers()
                return True
            except Exception: return False

        if name in self.containers:
            self.containers[name].status = "stopped"
            self.containers[name].ip_address = ""
            self._save_containers()
            return True
        return False

    def delete_container(self, name: str) -> bool:
        if self.is_linux and self.client:
            try:
                c = self.client.containers.get(name)
                if c.status == "Running": c.stop(wait=True)
                c.delete(wait=True)
                if name in self.containers: del self.containers[name]
                return True
            except Exception: return False

        if name in self.containers:
            del self.containers[name]
            self._save_containers()
            return True
        return False

    def list_containers(self) -> List[LXCContainer]:
        self._load_containers()
        return list(self.containers.values())

    def get_container_status(self, name: str) -> Optional[LXCContainer]:
        self._load_containers()
        return self.containers.get(name)

    def get_all_status(self) -> Dict[str, Any]:
        self._load_containers()
        running = len([c for c in self.containers.values() if c.status == "running"])
        return {
            "total_containers": len(self.containers),
            "running_containers": running,
            "stopped_containers": len(self.containers) - running
        }
