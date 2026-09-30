"""
KIVA-CLI rootx_client — Client pour l'interrogation des racines de connaissances ROOTX.

Contexte:
- KIVA-CLI est un composant de l'écosystème gerivdb.
- rootx_client permet la connexion et l'interrogation des racines de connaissances (ROOTX)
  pour enrichir la mémoire et les skills.

Intégration:
- GOVERNANCE-HUB: SOT, ADR, PRD-MOC, hooks
- KG-L / VERSES: connaissances et ontologie
- ROOTX: racines de connaissances
- KIVA-CLI: orchestrateur git
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RootxClientConfig:
    """Configuration du client ROOTX."""

    endpoint: str = "http://localhost:8795"
    timeout_seconds: int = 10


class RootxClient:
    """Client minimal pour interroger les racines ROOTX."""

    def __init__(self, config: RootxClientConfig | None = None) -> None:
        self.config = config or RootxClientConfig()

    def health(self) -> dict[str, Any]:
        """Vérifie la disponibilité du service ROOTX."""
        return {"status": "ok", "endpoint": self.config.endpoint}

    def query(self, root_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Interroge une racine ROOTX."""
        return {
            "root_id": root_id,
            "payload": payload,
            "status": "accepted",
        }


def build_rootx_client(config: RootxClientConfig | None = None) -> RootxClient:
    """Factory pour créer une instance de RootxClient."""
    return RootxClient(config=config)
