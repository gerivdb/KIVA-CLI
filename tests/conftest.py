"""Pytest conftest — path setup for KIVA-CLI anything-cli tests."""
import sys
from pathlib import Path

KIVA_ROOT = Path(__file__).parent
sys.path.insert(0, str(KIVA_ROOT))
sys.path.insert(0, str(KIVA_ROOT / "kiva_cli" / "core"))
sys.path.insert(0, str(KIVA_ROOT / "kiva_cli" / "core" / "metrics"))
sys.path.insert(0, str(KIVA_ROOT / "kiva_cli" / "core" / "auto_rollback_pipeline"))
sys.path.insert(0, str(KIVA_ROOT / "kiva_cli" / "workflows"))

# Mock external dependencies
import types
for mod_name in ["duckdb"]:
    if mod_name not in sys.modules:
        mod = types.ModuleType(mod_name)
        sys.modules[mod_name] = mod
