#!/usr/bin/env python3
"""Ternary Pytest Template - Base-3 test logic framework.

Provides utilities for testing with ternary logic:
- PENDING (0.0): Test not started or in progress
- SUCCESS (1.0): Test passed with full confidence
- FAILED (0.5): Test failed or partial success

Fuzzy confidence scores:
- 0.0: No confidence / Unknown
- 0.5: Partial confidence / Warning
- 1.0: Full confidence / Success

Usage:
    from frameworks.ternary_pytest_template import (
        TernaryAssertion,
        ValidationState,
        assert_ternary_state,
        assert_confidence,
    )
    
    def test_example():
        result = some_function()
        assert_ternary_state(result.state, ValidationState.SUCCESS)
        assert_confidence(result.confidence, min_threshold=0.8)
"""

from enum import Enum
from typing import Any, Optional


class ValidationState(Enum):
    """Base-3 ternary validation states."""
    PENDING = 0.0
    SUCCESS = 1.0
    FAILED = 0.5


class LifecycleState(Enum):
    """Base-4 lifecycle states."""
    GENESIS = "GENESIS"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"
    ARCHIVED = "ARCHIVED"


class TernaryAssertion:
    """Assertion utilities for ternary logic."""

    @staticmethod
    def assert_state(actual: ValidationState, expected: ValidationState, message: str = ""):
        """Assert ternary validation state.
        
        Args:
            actual: Actual state
            expected: Expected state
            message: Optional error message
            
        Raises:
            AssertionError: If states don't match
        """
        if actual != expected:
            msg = message or f"Expected state {expected.name}, got {actual.name}"
            raise AssertionError(msg)

    @staticmethod
    def assert_confidence(
        confidence: float,
        min_threshold: float = 0.8,
        message: str = ""
    ):
        """Assert confidence score meets threshold.
        
        Args:
            confidence: Confidence score (0.0 - 1.0)
            min_threshold: Minimum acceptable confidence
            message: Optional error message
            
        Raises:
            AssertionError: If confidence below threshold
        """
        if confidence < min_threshold:
            msg = message or (
                f"Confidence {confidence:.2f} below threshold {min_threshold:.2f}"
            )
            raise AssertionError(msg)

    @staticmethod
    def assert_not_failed(state: ValidationState, message: str = ""):
        """Assert state is not FAILED.
        
        Args:
            state: Validation state to check
            message: Optional error message
            
        Raises:
            AssertionError: If state is FAILED
        """
        if state == ValidationState.FAILED:
            msg = message or "State is FAILED"
            raise AssertionError(msg)

    @staticmethod
    def assert_lifecycle(
        actual: LifecycleState,
        expected: LifecycleState,
        message: str = ""
    ):
        """Assert lifecycle state.
        
        Args:
            actual: Actual lifecycle state
            expected: Expected lifecycle state
            message: Optional error message
            
        Raises:
            AssertionError: If states don't match
        """
        if actual != expected:
            msg = message or f"Expected lifecycle {expected.value}, got {actual.value}"
            raise AssertionError(msg)


# Convenience functions
def assert_ternary_state(actual: ValidationState, expected: ValidationState, message: str = ""):
    """Convenience wrapper for TernaryAssertion.assert_state."""
    TernaryAssertion.assert_state(actual, expected, message)


def assert_confidence(confidence: float, min_threshold: float = 0.8, message: str = ""):
    """Convenience wrapper for TernaryAssertion.assert_confidence."""
    TernaryAssertion.assert_confidence(confidence, min_threshold, message)


def assert_not_failed(state: ValidationState, message: str = ""):
    """Convenience wrapper for TernaryAssertion.assert_not_failed."""
    TernaryAssertion.assert_not_failed(state, message)


def assert_lifecycle(actual: LifecycleState, expected: LifecycleState, message: str = ""):
    """Convenience wrapper for TernaryAssertion.assert_lifecycle."""
    TernaryAssertion.assert_lifecycle(actual, expected, message)
