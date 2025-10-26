"""
Challenge result data model for fantasy football challenges.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError
from .owner import Owner


@dataclass(frozen=True)
class ChallengeResult:
    """
    Result of a specific fantasy football challenge.

    Represents the winner and details of one of the 5 tracked challenges.
    """
    challenge_name: str
    winner: str
    owner: Owner
    division: str
    value: str
    description: str

    def __post_init__(self) -> None:
        """Validate challenge result after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate challenge result data."""
        if not self.challenge_name.strip():
            raise DataValidationError("Challenge name cannot be empty")

        if not self.winner.strip():
            raise DataValidationError("Winner cannot be empty")

        # Owner validation is handled by the Owner object itself

        if not self.division.strip():
            raise DataValidationError("Division cannot be empty")

        if not self.description.strip():
            raise DataValidationError("Description cannot be empty")
