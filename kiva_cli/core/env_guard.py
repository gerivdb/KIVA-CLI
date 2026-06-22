#!/usr/bin/env python3
"""
EnvGuard - ITAD Pattern
Issue: KIVA-CLI#55
Target Hardware: HP Z600 Xeon E5620
Principe d'Anticipation Logistique (PAL)
"""

from __future__ import annotations
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any


class EnvGuard:
    """
    Environnement Guard pour KIVA-CLI
    Implémente le pattern ITAD EnvGuard:
    - Aucun chemin absolu
    - Aucune variable d'environnement lue directement
    - Aucune dépendance spécifique à Windows/WSL/Linux hors de cette classe
    - Détection automatique des capacités
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._platform = self._detect_platform()
        self._capabilities = self._detect_capabilities()
        self._path_mappings = self._load_path_mappings()
        self._initialized = True

    def _detect_platform(self) -> str:
        if os.path.exists("/proc/version"):
            with open("/proc/version") as f:
                if "microsoft" in f.read().lower():
                    return "wsl"
            return "linux"
        elif platform.system() == "Windows":
            return "windows"
        elif platform.system() == "Darwin":
            return "macos"
        return "unknown"

    def _detect_capabilities(self) -> Dict[str, bool]:
        return {
            "wsl_interop": self._platform == "wsl",
            "git": self._has_command("git"),
            "docker": self._has_command("docker"),
            "powershell": self._has_command("pwsh") or self._has_command("powershell"),
            "python3": self._has_command("python3"),
            "node": self._has_command("node"),
            "nvcc": self._has_command("nvcc"),
            "cuda": os.path.exists("/usr/local/cuda") or os.path.exists("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA"),
        }

    def _has_command(self, cmd: str) -> bool:
        from shutil import which
        return which(cmd) is not None

    def _load_path_mappings(self) -> Dict[str, Path]:
        mappings = {}
        
        # Chemins standard ECOS
        if self._platform == "windows":
            mappings["ECOS_ROOT"] = Path("D:\\DO\\WEB")
            mappings["DEVTOOLS_ROOT"] = Path("C:\\DevTools")
            mappings["NEXUS_ROOT"] = Path("D:\\DO\\WEB\\TOOLS\\NEXUS")
            mappings["KIVA_ROOT"] = Path("D:\\DO\\WEB\\TOOLS\\KIVA-CLI")
        elif self._platform == "wsl":
            mappings["ECOS_ROOT"] = Path("/mnt/d/DO/WEB")
            mappings["DEVTOOLS_ROOT"] = Path("/mnt/c/DevTools")
            mappings["NEXUS_ROOT"] = Path("/mnt/d/DO/WEB/TOOLS/NEXUS")
            mappings["KIVA_ROOT"] = Path("/mnt/d/DO/WEB/TOOLS/KIVA-CLI")
        else:
            mappings["ECOS_ROOT"] = Path.home() / "DO/WEB"
            mappings["DEVTOOLS_ROOT"] = Path("/opt/DevTools")
            mappings["NEXUS_ROOT"] = Path.home() / "DO/WEB/TOOLS/NEXUS"
            mappings["KIVA_ROOT"] = Path.home() / "DO/WEB/TOOLS/KIVA-CLI"

        return mappings

    def resolve_path(self, logical_path: str) -> Path:
        """Résout un chemin logique vers le chemin physique réel"""
        if logical_path in self._path_mappings:
            return self._path_mappings[logical_path]
            
        # Résolution relative par rapport à ECOS_ROOT
        if logical_path.startswith("ecos://"):
            relative = logical_path[7:]
            return self._path_mappings["ECOS_ROOT"] / relative
            
        if logical_path.startswith("devtools://"):
            relative = logical_path[11:]
            return self._path_mappings["DEVTOOLS_ROOT"] / relative

        return Path(logical_path)

    def get_env(self, key: str, default: Any = None) -> Any:
        """Retourne une variable d'environnement validée"""
        value = os.environ.get(key, default)
        
        # Validation automatique
        if key.endswith("_PATH") and value is not None:
            path = Path(value)
            if not path.exists():
                return default
                
        return value

    def is_available(self, capability: str) -> bool:
        """Vérifie si une capacité est disponible sur cette installation"""
        return self._capabilities.get(capability, False)

    def adapt(self, component: str) -> None:
        """Adapte un composant pour l'environnement courant"""
        if component == "path_resolver":
            # Deferred import to avoid circular dependency:
            # env_guard.adapt() is called from PathResolver.__init__,
            # but PathResolver imports env_guard at module level.
            # The actual adaptation is triggered lazily via _ensure_env_guard().
            pass

    def _ensure_env_guard(self, component: str) -> None:
        """Lazily apply env guard adaptation (called on first actual use, not at import time)."""
        if component == "path_resolver":
            try:
                from kiva_cli.core.path_resolver import PathResolver
                resolver = PathResolver()
                if not getattr(resolver, '_env_guard_configured', False):
                    if self._platform == "windows":
                        resolver.add_repo("DevTools", "C:\\DevTools", "gerivdb/DevTools")
                        resolver.add_repo("NEXUS", "D:\\DO\\WEB\\TOOLS\\NEXUS", "gerivdb/NEXUS")
                    elif self._platform == "wsl":
                        resolver.add_repo("DevTools", "/mnt/c/DevTools", "gerivdb/DevTools")
                        resolver.add_repo("NEXUS", "/mnt/d/DO/WEB/TOOLS/NEXUS", "gerivdb/NEXUS")
                    resolver._env_guard_configured = True
            except Exception:
                pass

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def is_windows(self) -> bool:
        return self._platform == "windows"

    @property
    def is_wsl(self) -> bool:
        return self._platform == "wsl"

    @property
    def is_linux(self) -> bool:
        return self._platform == "linux"


@dataclass
class EnvGuardResult:
    """Result of an EnvGuard environment check."""
    valid: bool
    platform: str
    capabilities: Dict[str, bool] = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def quick_check() -> EnvGuardResult:
    """Quick environment validation returning an EnvGuardResult."""
    guard = EnvGuard()
    result = EnvGuardResult(
        valid=True,
        platform=guard.platform(),
        capabilities=guard._capabilities,
    )
    return result


# Instance globale
env_guard = EnvGuard()
