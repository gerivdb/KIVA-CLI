#!/usr/bin/env python3
"""Tests for Ternary Pytest Framework."""

import pytest
from frameworks.ternary_pytest_template import (
    ValidationState,
    LifecycleState,
    TernaryAssertion,
    assert_ternary_state,
    assert_confidence,
    assert_not_failed,
    assert_lifecycle,
)


class TestValidationState:
    """Test ValidationState enum."""

    def test_pending_state_value(self):
        """Test PENDING state has value 0.0."""
        assert ValidationState.PENDING.value == 0.0

    def test_success_state_value(self):
        """Test SUCCESS state has value 1.0."""
        assert ValidationState.SUCCESS.value == 1.0

    def test_failed_state_value(self):
        """Test FAILED state has value 0.5."""
        assert ValidationState.FAILED.value == 0.5


class TestLifecycleState:
    """Test LifecycleState enum."""

    def test_lifecycle_state_values(self):
        """Test all lifecycle state values."""
        assert LifecycleState.GENESIS.value == "GENESIS"
        assert LifecycleState.ACTIVE.value == "ACTIVE"
        assert LifecycleState.DEPRECATED.value == "DEPRECATED"
        assert LifecycleState.ARCHIVED.value == "ARCHIVED"


class TestTernaryAssertion:
    """Test TernaryAssertion class."""

    def test_assert_state_success(self):
        """Test assert_state passes for matching states."""
        TernaryAssertion.assert_state(
            ValidationState.SUCCESS,
            ValidationState.SUCCESS
        )

    def test_assert_state_failure(self):
        """Test assert_state raises for mismatched states."""
        with pytest.raises(AssertionError):
            TernaryAssertion.assert_state(
                ValidationState.FAILED,
                ValidationState.SUCCESS
            )

    def test_assert_confidence_pass(self):
        """Test assert_confidence passes for high confidence."""
        TernaryAssertion.assert_confidence(0.95, min_threshold=0.8)

    def test_assert_confidence_fail(self):
        """Test assert_confidence raises for low confidence."""
        with pytest.raises(AssertionError):
            TernaryAssertion.assert_confidence(0.5, min_threshold=0.8)

    def test_assert_not_failed_success(self):
        """Test assert_not_failed passes for non-FAILED states."""
        TernaryAssertion.assert_not_failed(ValidationState.SUCCESS)
        TernaryAssertion.assert_not_failed(ValidationState.PENDING)

    def test_assert_not_failed_failure(self):
        """Test assert_not_failed raises for FAILED state."""
        with pytest.raises(AssertionError):
            TernaryAssertion.assert_not_failed(ValidationState.FAILED)


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    def test_assert_ternary_state_wrapper(self):
        """Test assert_ternary_state convenience function."""
        assert_ternary_state(ValidationState.SUCCESS, ValidationState.SUCCESS)
        
        with pytest.raises(AssertionError):
            assert_ternary_state(ValidationState.FAILED, ValidationState.SUCCESS)

    def test_assert_confidence_wrapper(self):
        """Test assert_confidence convenience function."""
        assert_confidence(0.9, min_threshold=0.8)
        
        with pytest.raises(AssertionError):
            assert_confidence(0.5, min_threshold=0.8)

    def test_assert_not_failed_wrapper(self):
        """Test assert_not_failed convenience function."""
        assert_not_failed(ValidationState.SUCCESS)
        
        with pytest.raises(AssertionError):
            assert_not_failed(ValidationState.FAILED)

    def test_assert_lifecycle_wrapper(self):
        """Test assert_lifecycle convenience function."""
        assert_lifecycle(LifecycleState.ACTIVE, LifecycleState.ACTIVE)
        
        with pytest.raises(AssertionError):
            assert_lifecycle(LifecycleState.GENESIS, LifecycleState.ACTIVE)
