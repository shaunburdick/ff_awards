"""
Base protocols and interfaces for model validation.
"""

from __future__ import annotations

from typing import Protocol


class Validatable(Protocol):
    """Protocol for objects that can validate their data."""

    def validate(self) -> None:
        """Validate the object's data, raising DataValidationError if invalid."""
        ...
