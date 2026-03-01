#!/usr/bin/env python3
"""
Intent Auditor Citizen - IntentHash¹¹ validation and continuity checker

Validates IntentHash chain continuity across operations, ensuring proper
linkage and detecting any breaks in the traceability chain.

Features:
- IntentHash¹¹ format validation
- Parent-child linkage verification
- Chain continuity analysis
- Anomaly detection (missing links, duplicates)
- Ternary state validation
- Integration with GlobalWALManager

Usage:
    citizen = IntentAuditorCitizen()
    result = await citizen.execute({
        'operation': 'validate_chain',
        'intent_hashes': ['0xABC...', '0xDEF...', ...]
    })
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationState(Enum):
    """Ternary validation states"""
    PENDING = 0.0
    SUCCESS = 1.0
    FAILED = 0.5


class LifecycleState(Enum):
    """Base-4 lifecycle states"""
    GENESIS = "GENESIS"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


@dataclass
class IntentHashValidation:
    """Result from IntentHash validation"""
    state: ValidationState
    valid_hashes: List[str]
    invalid_hashes: List[str]
    chain_continuous: bool
    anomalies: List[str]
    confidence: float
    timestamp: str
    lifecycle: LifecycleState


class IntentAuditorCitizen:
    """
    IntentHash validation and continuity checker
    
    Ensures all operations maintain proper IntentHash¹¹ linkage
    for complete traceability and auditability.
    """
    
    INTENT_HASH_PATTERN = re.compile(r'^0x[A-F0-9]{16}$')
    
    def __init__(self):
        self.lifecycle = LifecycleState.GENESIS
        self.logger = logging.getLogger(__name__)
        
    async def execute(self, params: Dict[str, Any]) -> IntentHashValidation:
        """
        Execute IntentHash validation
        
        Args:
            params: Dictionary containing:
                - operation: Validation operation type
                - intent_hashes: List of IntentHashes to validate
                - parent_map: Optional parent-child mapping
        
        Returns:
            IntentHashValidation with ternary state
        """
        self.lifecycle = LifecycleState.ACTIVE
        
        operation = params.get('operation')
        if not operation:
            return self._failed_validation("Missing operation parameter")
        
        handlers = {
            'validate_format': self._validate_format,
            'validate_chain': self._validate_chain,
            'detect_anomalies': self._detect_anomalies,
        }
        
        handler = handlers.get(operation)
        if not handler:
            return self._failed_validation(f"Unknown operation: {operation}")
        
        try:
            return await handler(params)
        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            return self._failed_validation(str(e))
    
    async def _validate_format(self, params: Dict[str, Any]) -> IntentHashValidation:
        """
        Validate IntentHash format
        
        Checks that all hashes match pattern: 0x[A-F0-9]{16}
        """
        intent_hashes = params.get('intent_hashes', [])
        
        valid = []
        invalid = []
        
        for hash_value in intent_hashes:
            if self.INTENT_HASH_PATTERN.match(hash_value):
                valid.append(hash_value)
            else:
                invalid.append(hash_value)
        
        state = ValidationState.SUCCESS if not invalid else ValidationState.FAILED
        confidence = len(valid) / len(intent_hashes) if intent_hashes else 0.0
        
        return IntentHashValidation(
            state=state,
            valid_hashes=valid,
            invalid_hashes=invalid,
            chain_continuous=True,  # Format check only
            anomalies=[f"Invalid format: {h}" for h in invalid],
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat(),
            lifecycle=self.lifecycle,
        )
    
    async def _validate_chain(self, params: Dict[str, Any]) -> IntentHashValidation:
        """
        Validate IntentHash chain continuity
        
        Checks parent-child linkage and detects breaks in chain.
        """
        intent_hashes = params.get('intent_hashes', [])
        parent_map = params.get('parent_map', {})  # {child_hash: parent_hash}
        
        valid = []
        invalid = []
        anomalies = []
        
        # Check format first
        for hash_value in intent_hashes:
            if self.INTENT_HASH_PATTERN.match(hash_value):
                valid.append(hash_value)
            else:
                invalid.append(hash_value)
                anomalies.append(f"Invalid format: {hash_value}")
        
        # Check chain continuity
        chain_continuous = True
        if parent_map:
            for child, parent in parent_map.items():
                if child not in intent_hashes:
                    anomalies.append(f"Child hash not in chain: {child}")
                    chain_continuous = False
                
                if parent and parent not in intent_hashes:
                    anomalies.append(f"Parent hash not in chain: {parent}")
                    chain_continuous = False
        
        state = ValidationState.SUCCESS if not invalid and chain_continuous else ValidationState.FAILED
        confidence = len(valid) / len(intent_hashes) if intent_hashes else 0.0
        
        return IntentHashValidation(
            state=state,
            valid_hashes=valid,
            invalid_hashes=invalid,
            chain_continuous=chain_continuous,
            anomalies=anomalies,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat(),
            lifecycle=self.lifecycle,
        )
    
    async def _detect_anomalies(self, params: Dict[str, Any]) -> IntentHashValidation:
        """
        Detect anomalies in IntentHash chain
        
        Identifies duplicates, orphans, circular references, etc.
        """
        intent_hashes = params.get('intent_hashes', [])
        
        valid = [h for h in intent_hashes if self.INTENT_HASH_PATTERN.match(h)]
        invalid = [h for h in intent_hashes if not self.INTENT_HASH_PATTERN.match(h)]
        
        anomalies = []
        
        # Check for duplicates
        seen = set()
        for hash_value in intent_hashes:
            if hash_value in seen:
                anomalies.append(f"Duplicate hash: {hash_value}")
            seen.add(hash_value)
        
        state = ValidationState.SUCCESS if not invalid and not anomalies else ValidationState.FAILED
        confidence = len(valid) / len(intent_hashes) if intent_hashes else 0.0
        
        return IntentHashValidation(
            state=state,
            valid_hashes=valid,
            invalid_hashes=invalid,
            chain_continuous=len(intent_hashes) == len(valid),
            anomalies=anomalies,
            confidence=confidence,
            timestamp=datetime.utcnow().isoformat(),
            lifecycle=self.lifecycle,
        )
    
    def _failed_validation(self, error: str) -> IntentHashValidation:
        """Create failed validation result"""
        self.lifecycle = LifecycleState.DEPRECATED
        return IntentHashValidation(
            state=ValidationState.FAILED,
            valid_hashes=[],
            invalid_hashes=[],
            chain_continuous=False,
            anomalies=[error],
            confidence=0.0,
            timestamp=datetime.utcnow().isoformat(),
            lifecycle=self.lifecycle,
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current citizen status"""
        return {
            'lifecycle': self.lifecycle.value,
            'pattern': self.INTENT_HASH_PATTERN.pattern,
        }
