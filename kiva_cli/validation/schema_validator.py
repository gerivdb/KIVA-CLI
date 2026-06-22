"""SchemaValidator - JSON schema validation."""

from typing import Dict, Any, List


class SchemaValidator:
    """Validate JSON documents against required schema."""

    REQUIRED_FIELDS = ["manifest_version", "ecosystem_id", "repositories"]

    def validate(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document against schema."""
        errors = [f for f in self.REQUIRED_FIELDS if f not in document]
        if errors:
            return {"status": "INVALID", "errors": errors}
        return {"status": "VALID", "errors": []}
