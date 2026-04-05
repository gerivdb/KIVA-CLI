#!/usr/bin/env python3
"""
Path Memory Manager - KIVA CLI

Learns from path resolution errors and provides ultra-reliable path management.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


class PathErrorMemory:
    def __init__(self, memory_file: Optional[str] = None):
        if memory_file is None:
            memory_file = "C:\\DevTools\\data\\path_memory\\errors.json"
        self.memory_file = Path(memory_file)
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.errors: Dict[str, int] = {}
        self.corrections: Dict[str, str] = {}
        self._load()
    
    def _load(self):
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.errors = data.get("errors", {})
                self.corrections = data.get("corrections", {})
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save(self):
        data = {"errors": self.errors, "corrections": self.corrections}
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def record_error(self, original_path: str, corrected_path: str):
        key = original_path.lower()
        self.errors[key] = self.errors.get(key, 0) + 1
        self.corrections[key] = corrected_path
        self._save()
    
    def get_correction(self, path: str) -> Optional[str]:
        return self.corrections.get(path.lower())
    
    def get_common_errors(self, top_n: int = 10) -> List[Tuple[str, int]]:
        return sorted(self.errors.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    def clear(self):
        self.errors.clear()
        self.corrections.clear()
        self._save()
    
    def clear(self):
        self.errors.clear()
        self.corrections.clear()
        self._save()


class UltraReliablePathResolver:
    """Ultra-reliable path resolver with automatic correction."""
    
    KNOWN_ROOTS = {
        "devtools": "C:\\DevTools",
        "kiva": "D:\\DO\\WEB\\TOOLS\\KIVA",
        "kiva-cli": "D:\\DO\\WEB\\TOOLS\\KIVA-CLI",
        "ecosystem": "D:\\DO\\WEB\\TOOLS\\ECOYSTEM",
        "brain": "D:\\DO\\WEB\\BRAIN",
        "brain-docs": "D:\\DO\\WEB\\TOOLS\\BRAIN-DOCS",
        "skills": "D:\\DO\\WEB\\TOOLS\\SKILLS",
        "fluence": "D:\\DO\\WEB\\FLUENCE",
    }
    
    def __init__(self, memory: Optional[PathErrorMemory] = None):
        self.memory = memory or PathErrorMemory()
        self._current_roots = dict(self.KNOWN_ROOTS)
    
    def resolve(self, path: str, base_dir: Optional[str] = None) -> str:
        if not path:
            return ""
        
        correction = self.memory.get_correction(path)
        if correction and os.path.exists(correction):
            return correction
        
        # Apply common fixes FIRST
        fixed_path = self._apply_common_fixes(path)
        if fixed_path != path:
            resolved = self._try_resolve(fixed_path, base_dir)
            if resolved and os.path.exists(resolved):
                self.memory.record_error(path, resolved)
                return resolved
        
        # Try keyword resolution
        resolved = self._resolve_by_keyword(path)
        if resolved and os.path.exists(resolved):
            self.memory.record_error(path, resolved)
            return resolved
        
        # Try keyword resolution on fixed path
        if fixed_path != path:
            resolved = self._resolve_by_keyword(fixed_path)
            if resolved and os.path.exists(resolved):
                self.memory.record_error(path, resolved)
                return resolved
        
        # Standard resolution
        resolved = self._try_resolve(path, base_dir)
        if resolved and os.path.exists(resolved):
            return resolved
        
        return resolved or path
    
    def _try_resolve(self, path: str, base_dir: Optional[str] = None) -> str:
        try:
            normalized = path.replace('/', '\\').replace('\\\\', '\\')
            if os.path.isabs(normalized):
                return os.path.normpath(normalized)
            if base_dir:
                return os.path.normpath(os.path.join(base_dir, normalized))
            return os.path.normpath(os.path.join(os.getcwd(), normalized))
        except (ValueError, TypeError):
            return path
    
    def _apply_common_fixes(self, path: str) -> str:
        fixed = path.replace('\\\\', '\\').replace('/', '\\').rstrip('\\')
        typos = {
            "devtoosl": "devtools",
            "deotools": "devtools", 
            "kivva": "kiva",
            "ecosytem": "ecosystem",
            "brn": "brain",
            "skils": "skills"
        }
        for typo, correct in typos.items():
            if typo in fixed.lower():
                fixed = re.sub(re.escape(typo), correct, fixed, flags=re.IGNORECASE)
        return fixed
    
    def _resolve_by_keyword(self, path: str) -> str:
        path_lower = path.lower().replace('\\', '/').split('/')[0]
        for keyword, root in self._current_roots.items():
            if path_lower == keyword or path_lower.startswith(keyword + '/') or path_lower.startswith(keyword + '\\'):
                remainder = path[len(keyword):].lstrip('\\/')
                if remainder:
                    resolved = os.path.join(root, remainder.replace('/', '\\'))
                else:
                    resolved = root
                return resolved
        return ""
    
    def get_known_roots(self) -> Dict[str, str]:
        return dict(self._current_roots)
    
    def get_error_stats(self) -> Dict[str, Any]:
        return {
            "total_errors": sum(self.memory.errors.values()),
            "unique_errors": len(self.memory.errors),
            "known_roots": len(self._current_roots)
        }