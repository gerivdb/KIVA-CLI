"""Base3Validator - Base-3 ternary validation."""

from typing import Dict, Any


class Base3Validator:
    """Validate ECOS_ROOT manifest using base-3 ternary logic."""

    def validate_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Validate manifest structure."""
        errors = []

        if "manifest_version" not in manifest:
            errors.append("manifest_version")
        if "repositories" not in manifest:
            errors.append("repositories")
        if "global_metrics" not in manifest:
            errors.append("global_metrics")

        if errors:
            return {
                "overall_status": "INVALID",
                "manifest_structure": "INVALID" if "manifest_version" in errors else "VALID",
                "repositories": "INVALID" if "repositories" in errors else "VALID",
                "global_metrics": "INVALID" if "global_metrics" in errors else "VALID",
                "errors": errors
            }

        return {
            "overall_status": "VALID",
            "manifest_structure": "VALID",
            "repositories": "VALID",
            "global_metrics": "VALID"
        }
