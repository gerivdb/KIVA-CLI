#!/usr/bin/env python3
import re, hashlib
from typing import Tuple, Dict, Optional, List
from datetime import datetime
from enum import Enum

class ValidationResult(Enum):
    UNKNOWN = 0
    VALID = 1
    INVALID = -1

class IntentHashValidator:
    """Validate IntentHash at L0-L1 levels"""
    PATTERN = re.compile(r'^0x[0-9A-Fa-f]{40}$')

    def __init__(self):
        self.hash_chain: List[Dict] = []

    def validate_intent_hash(self, intent_hash: str, context: Optional[Dict] = None) -> ValidationResult:
        if not intent_hash or not self.PATTERN.match(intent_hash):
            return ValidationResult.INVALID
        return ValidationResult.VALID

    def generate_intent_hash(self, action: str, context: str, timestamp: Optional[str] = None) -> str:
        if not timestamp: timestamp = datetime.now().isoformat()
        data = f"{action}|{context}|{timestamp}"
        h = hashlib.sha3_256(data.encode()).hexdigest()
        return f"0x{h[:40].upper()}"

    def validate_chain_continuity(self, hashes: List[str]) -> ValidationResult:
        if not hashes or len(hashes) < 2: return ValidationResult.UNKNOWN
        for i in range(1, len(hashes)):
            if not hashes[i] or not self.PATTERN.match(hashes[i]) or hashes[i] == hashes[i-1]:
                return ValidationResult.INVALID
        return ValidationResult.VALID
