"""KIVA-012 S3 — Reusable ABC instantiation test pattern.

Provides a mixin class that validates concrete implementations
properly implement all abstract methods.
"""
from __future__ import annotations

import inspect
from abc import ABC
from typing import Type


class ABCContractValidator:
    """Mixin for validating ABC contracts are fully implemented."""

    @staticmethod
    def assert_instantiable(cls: Type) -> None:
        """Assert that a concrete class can be instantiated without TypeError.

        Raises:
            TypeError: If abstract methods are not implemented
        """
        try:
            cls()
        except TypeError as exc:
            raise AssertionError(
                f"{cls.__name__} cannot be instantiated: {exc}"
            ) from exc

    @staticmethod
    def assert_abstract_methods_implemented(cls: Type) -> list[str]:
        """Return list of unimplemented abstract methods for a class.

        Returns:
            List of abstract method names that are not implemented
        """
        if not issubclass(cls, ABC):
            return []

        abstract_methods = set()
        for base in cls.__mro__:
            for name, method in inspect.getmembers(base, predicate=inspect.isfunction):
                if getattr(method, "__isabstractmethod__", False):
                    abstract_methods.add(name)

        # Check if implemented in concrete class
        unimplemented = []
        for name in abstract_methods:
            # Check if implemented in the class itself or its subclasses
            for c in cls.__mro__:
                if name in c.__dict__ and not getattr(c.__dict__[name], "__isabstractmethod__", False):
                    break
            else:
                unimplemented.append(name)

        return unimplemented


# Example usage:
# class TestMyProvider(ABCContractValidator):
#     def test_provider_can_be_instantiated(self):
#         self.assert_instantiable(MyProvider)
#
#     def test_no_unimplemented_abstract_methods(self):
#         missing = self.assert_abstract_methods_implemented(MyProvider)
#         assert missing == [], f"Unimplemented abstract methods: {missing}"
