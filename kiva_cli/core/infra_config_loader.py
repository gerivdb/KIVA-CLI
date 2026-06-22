"""
infra_config_loader.py — Loader local pointant vers NEXUS SDK
Évite d'ajouter NEXUS au sys.path dans chaque fichier.
Fallback gracieux si NEXUS non accessible (CI GitHub, etc.)
"""
import sys
import os

_NEXUS_SDK = os.environ.get(
    "NEXUS_SDK_PATH",
    r"D:\DO\WEB\TOOLS\NEXUS\sdk"
)
if _NEXUS_SDK not in sys.path:
    sys.path.insert(0, _NEXUS_SDK)

try:
    from infra_config import get_wsl_distro, get_port, get_path  # noqa: F401
except ImportError:
    # Fallback gracieux si NEXUS non accessible (CI GitHub, etc.)
    def get_wsl_distro():
        return os.environ.get("WSL_DISTRO", "Ubuntu")

    def get_port(service):
        _ports = {"codedb": 6767, "postgresql": 5432, "redis": 6379, "gotrue": 9999}
        return _ports.get(service, 0)

    def get_path(key, platform="windows"):
        return ""
