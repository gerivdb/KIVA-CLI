# KIVA CLI - ConfigManager
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class ConfigResult:
    success: bool
    warnings: List[str] = None
    errors: List[str] = None

class ConfigManager:
    def validate_config(self, file: str, strict: bool, schema: Optional[str]) -> ConfigResult:
        file_path = Path(file)
        if not file_path.exists():
            return ConfigResult(success=False, errors=[f"File not found: {file}"])
        return ConfigResult(success=True, warnings=[])
