"""
Owner data model for ESPN team owners.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError


@dataclass(frozen=True)
class Owner:
    """
    ESPN team owner information.

    Represents the person who owns/manages a fantasy football team,
    including their display name, real name, and notification preferences.
    """
    display_name: str
    first_name: str
    last_name: str
    id: str

    def __post_init__(self) -> None:
        """Validate owner data after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate owner data."""
        if not self.id.strip():
            raise DataValidationError("Owner ID cannot be empty")

        # At least one name field should be provided
        if not any([
            self.display_name.strip(),
            self.first_name.strip(),
            self.last_name.strip()
        ]):
            raise DataValidationError("Owner must have at least one name field")

    @property
    def full_name(self) -> str:
        """Get the owner's full name, preferring real name over display name."""
        if self.first_name.strip() and self.last_name.strip():
            return f"{self.first_name} {self.last_name}"
        elif self.first_name.strip():
            return self.first_name
        elif self.last_name.strip():
            return self.last_name
        else:
            return self.display_name

    @property
    def is_likely_username(self) -> bool:
        """Check if the display name looks like a username rather than real name."""
        name = self.display_name.strip()
        if not name:
            return True

        # Common username patterns
        username_indicators = [
            name.startswith('ESPNFAN'),
            name.startswith('espn'),
            len(name) > 15 and any(c.isdigit() for c in name),
            name.islower() and len(name) > 8,
            sum(c.isdigit() for c in name) > len(name) // 2,
        ]

        return any(username_indicators)
