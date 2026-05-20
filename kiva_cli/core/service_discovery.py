#!/usr/bin/env python3
"""
Service Discovery Manager - KIVA CLI

Manages service registration, discovery, and load balancing for ECOS microservices.
"""

import json
import os
import socket
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

HAS_KVCACHE = False
try:
    from kiva_cli.core.kvcache_manager import KVCacheManager
    HAS_KVCACHE = True
except ImportError:
    pass


class ServiceInfo:
    def __init__(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.host = data.get("host", "localhost")
        self.port = data.get("port", 0)
        self.protocol = data.get("protocol", "http")
        self.status = data.get("status", "unknown")
        self.last_heartbeat = data.get("last_heartbeat", "")
        self.metadata = data.get("metadata", {})

    def get_url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"


class ServiceDiscovery:
    def __init__(self, registry_path: Optional[str] = None):
        if registry_path is None:
            registry_path = "C:\\DevTools\\data\\services\\registry.json"
        self.registry_path = Path(registry_path)
        self.services: Dict[str, ServiceInfo] = {}
        self.cache = None
        if HAS_KVCACHE:
            try:
                from kiva_cli.core.kvcache_manager import KVCacheManager
                self.cache = KVCacheManager()
            except Exception:
                pass
        self._load_registry()

    def _load_registry(self):
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, info in data.get("services", {}).items():
                    self.services[name] = ServiceInfo(info)
            except (json.JSONDecodeError, IOError):
                pass

    def _save_registry(self):
        data = {
            "services": {
                name: {
                    "name": s.name,
                    "host": s.host,
                    "port": s.port,
                    "protocol": s.protocol,
                    "status": s.status,
                    "last_heartbeat": s.last_heartbeat,
                    "metadata": s.metadata
                }
                for name, s in self.services.items()
            }
        }
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def register_service(self, name: str, host: str, port: int, protocol: str = "http", metadata: Optional[Dict] = None) -> bool:
        self.services[name] = ServiceInfo({
            "name": name,
            "host": host,
            "port": port,
            "protocol": protocol,
            "status": "active",
            "last_heartbeat": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "metadata": metadata or {}
        })
        self._save_registry()
        return True

    def deregister_service(self, name: str) -> bool:
        if name in self.services:
            del self.services[name]
            self._save_registry()
            return True
        return False

    def discover_service(self, name: str) -> Optional[ServiceInfo]:
        cache_key = f"service_discover:{name}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return ServiceInfo(cached)
        
        service = self.services.get(name)
        if service:
            if self._check_health(service.host, service.port):
                service.status = "healthy"
            else:
                service.status = "unhealthy"
            self._save_registry()
            if self.cache:
                self.cache.put(cache_key, service.__dict__)
        return service

    def list_services(self) -> List[ServiceInfo]:
        return list(self.services.values())

    def _check_health(self, host: str, port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def update_heartbeat(self, name: str) -> bool:
        if name in self.services:
            self.services[name].last_heartbeat = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            self._save_registry()
            return True
        return False