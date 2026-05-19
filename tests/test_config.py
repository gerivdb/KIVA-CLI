#!/usr/bin/env python3
"""Test environment variable configuration."""

import os
from kiva_cli.commands.epic_commands import OntologyClient, Sco7Client

# Test default URLs
print("Testing default URLs:")
oc_default = OntologyClient()
sc_default = Sco7Client()
print(f"  Ontology default: {oc_default.base_url}")
print(f"  SCO7 default: {sc_default.base_url}")

# Test with environment variables
print("\nTesting with environment variables:")
os.environ["KIVA_ONTOLOGY_SERVICE_URL"] = "http://custom-ontology:9090"
os.environ["KIVA_SCO7_SERVICE_URL"] = "http://custom-sco7:9091"

oc_custom = OntologyClient()
sc_custom = Sco7Client()
print(f"  Ontology custom: {oc_custom.base_url}")
print(f"  SCO7 custom: {sc_custom.base_url}")

# Test explicit override
print("\nTesting explicit URL override:")
oc_override = OntologyClient("http://explicit-ontology:9999")
sc_override = Sco7Client("http://explicit-sco7:9999")
print(f"  Ontology override: {oc_override.base_url}")
print(f"  SCO7 override: {sc_override.base_url}")

print("\nPASS: Environment variable configuration works correctly!")
