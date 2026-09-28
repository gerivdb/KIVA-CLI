#!/usr/bin/env python3
"""
ACT-016: Implémentation centrale artifact-layers-design.
"""

from pathlib import Path
from datetime import datetime, timezone


class ArtifactLayers:
    """Validation des couches d'artefacts (core, adapter, presentation)."""

    def __init__(self, context: dict | None = None):
        self.context = context or {}
        self.validation_time = datetime.now(timezone.utc).isoformat()

    def validate(self, context: dict | None = None) -> dict:
        """Valide que les couches d'artefacts sont respectées."""
        if context:
            self.context = context

        layers = self.context.get("layers", [])
        valid_layers = {"core", "adapter", "presentation"}

        invalid = [layer for layer in layers if layer not in valid_layers]

        return {
            "design": "artifact-layers-design",
            "status": "OK" if not invalid else "INVALID_LAYERS",
            "layers_found": layers,
            "invalid_layers": invalid,
            "timestamp": self.validation_time,
        }

    def get_layer(self, layer_name: str) -> dict:
        """Retourne la définition d'une couche."""
        layer_defs = {
            "core": {"description": "Core business logic", "dependencies": []},
            "adapter": {"description": "External adapters", "dependencies": ["core"]},
            "presentation": {"description": "UI/API layer", "dependencies": ["core", "adapter"]},
        }
        return layer_defs.get(layer_name, {})


def validate_artifact_layers(context: dict) -> dict:
    """Point d'entrée principal."""
    layers = ArtifactLayers()
    return layers.validate(context)


if __name__ == "__main__":
    test_context = {
        "layers": ["core", "adapter", "presentation"],
    }
    result = validate_artifact_layers(test_context)
    print(f"[ACT-016] artifact-layers-design validation: {result['status']}")
