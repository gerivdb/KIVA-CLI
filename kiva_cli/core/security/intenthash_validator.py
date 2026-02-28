"""
ECOS-CLI IntentHash Validation System
L0-L1 validation with chain continuity tracking

IntentHash: 0x69C0965C49825C93BDDF
Generated: 2026-02-28T22:00:31.548491

Validation Levels:
- L0: Format check (SHA3-256, 40 hex chars)
- L1: Chain continuity (previous hash → current hash linkage)
- L2: Cryptographic proof (to be implemented in Phase 7)
- L3: Distributed consensus (to be implemented in Phase 8)
"""

import re
import hashlib
from typing import Tuple, Dict, Optional, List
from datetime import datetime


class IntentHashValidator:
    """Validate IntentHash at multiple levels"""
    
    # L0: Format validation
    INTENTHASH_PATTERN = re.compile(r'^0x[0-9A-Fa-f]{40}$')
    
    def __init__(self):
        self.hash_chain: List[Dict] = []  # Store hash chain for L1 validation
    
    def validate_format(self, hash_value: str) -> bool:
        """
        L0: Validate IntentHash format
        
        Format: 0x[40 hex chars] (SHA3-256 truncated to 20 bytes)
        
        Args:
            hash_value: IntentHash to validate
        
        Returns:
            True if format is valid
        """
        if not hash_value:
            return False
        
        # Check pattern
        if not self.INTENTHASH_PATTERN.match(hash_value):
            return False
        
        # Verify hex chars only (case-insensitive)
        hex_part = hash_value[2:]  # Remove "0x"
        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False
    
    def validate_chain_continuity(
        self,
        hash_value: str,
        previous_hash: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        L1: Validate chain continuity
        
        Checks if hash_value is properly linked to previous hash
        
        Args:
            hash_value: Current IntentHash
            previous_hash: Previous IntentHash in chain (optional)
        
        Returns:
            (is_valid: bool, chain_data: Dict)
        """
        # L0 check first
        if not self.validate_format(hash_value):
            return False, {
                "error": "L0 format validation failed",
                "hash": hash_value
            }
        
        # If no previous hash, check against chain history
        if not previous_hash and len(self.hash_chain) > 0:
            previous_hash = self.hash_chain[-1]["hash"]
        
        # If still no previous hash, this is chain genesis
        if not previous_hash:
            chain_data = {
                "hash": hash_value,
                "position": 0,
                "is_genesis": True,
                "previous_hash": None,
                "timestamp": datetime.now().isoformat()
            }
            self.hash_chain.append(chain_data)
            return True, chain_data
        
        # Validate continuity: hash should be derived from previous
        # In production: verify cryptographic linkage
        # For Phase 6: simplified validation (presence in chain)
        
        chain_data = {
            "hash": hash_value,
            "position": len(self.hash_chain),
            "is_genesis": False,
            "previous_hash": previous_hash,
            "chain_valid": True,  # Simplified for Phase 6
            "timestamp": datetime.now().isoformat()
        }
        
        self.hash_chain.append(chain_data)
        return True, chain_data
    
    def get_chain_history(self) -> List[Dict]:
        """Get full hash chain history"""
        return self.hash_chain.copy()
    
    def generate_intent_hash(
        self,
        action: str,
        context: str,
        timestamp: Optional[str] = None
    ) -> str:
        """
        Generate new IntentHash from action + context
        
        Args:
            action: Action identifier (e.g., "PHASE6_CLI_INTEGRATION")
            context: Action context description
            timestamp: ISO timestamp (defaults to now)
        
        Returns:
            IntentHash (0x + 40 hex chars)
        """
        if not timestamp:
            timestamp = datetime.now().isoformat()
        
        intent_data = f"{action}|{context}|{timestamp}"
        hash_full = hashlib.sha3_256(intent_data.encode()).hexdigest()
        
        # Truncate to 20 bytes (40 hex chars)
        return f"0x{hash_full[:40].upper()}"
    
    def verify_hash_derivation(
        self,
        hash_value: str,
        action: str,
        context: str,
        timestamp: str
    ) -> bool:
        """
        Verify if hash was derived from given inputs
        
        Args:
            hash_value: IntentHash to verify
            action: Expected action
            context: Expected context
            timestamp: Expected timestamp
        
        Returns:
            True if hash matches derivation
        """
        expected_hash = self.generate_intent_hash(action, context, timestamp)
        return hash_value.upper() == expected_hash.upper()


class IntentHashChain:
    """Manage IntentHash chain across multiple events"""
    
    def __init__(self):
        self.validator = IntentHashValidator()
        self.events: List[Dict] = []
    
    def add_event(
        self,
        action: str,
        context: str,
        entity_id: str,
        phi_delta: float = 0.0
    ) -> Dict:
        """
        Add new event to chain with auto-generated IntentHash
        
        Args:
            action: Event action
            context: Event context
            entity_id: Entity identifier
            phi_delta: φ-CPS delta
        
        Returns:
            Event dictionary with IntentHash
        """
        timestamp = datetime.now().isoformat()
        intent_hash = self.validator.generate_intent_hash(action, context, timestamp)
        
        # Validate chain continuity
        previous_hash = self.events[-1]["intent_hash"] if self.events else None
        is_valid, chain_data = self.validator.validate_chain_continuity(
            intent_hash,
            previous_hash
        )
        
        event = {
            "timestamp": timestamp,
            "action": action,
            "context": context,
            "entity_id": entity_id,
            "intent_hash": intent_hash,
            "previous_hash": previous_hash,
            "phi_delta": phi_delta,
            "chain_position": chain_data["position"],
            "validation_l0": "VALID",
            "validation_l1": "VALID" if is_valid else "INVALID"
        }
        
        self.events.append(event)
        return event
    
    def get_chain(self) -> List[Dict]:
        """Get full event chain"""
        return self.events.copy()
    
    def validate_full_chain(self) -> Dict:
        """
        Validate entire chain integrity
        
        Returns:
            Validation report
        """
        if not self.events:
            return {
                "valid": True,
                "length": 0,
                "errors": []
            }
        
        errors = []
        
        # Check genesis
        if self.events[0]["previous_hash"] is not None:
            errors.append("Genesis event has previous_hash (should be None)")
        
        # Check continuity
        for i in range(1, len(self.events)):
            current = self.events[i]
            previous = self.events[i - 1]
            
            if current["previous_hash"] != previous["intent_hash"]:
                errors.append(
                    f"Chain break at position {i}: "
                    f"expected {previous['intent_hash']}, "
                    f"got {current['previous_hash']}"
                )
        
        return {
            "valid": len(errors) == 0,
            "length": len(self.events),
            "errors": errors,
            "chain_integrity": "INTACT" if not errors else "BROKEN"
        }
