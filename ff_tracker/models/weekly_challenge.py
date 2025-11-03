"""
Weekly challenge result data model for week-specific challenges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..exceptions import DataValidationError
from .owner import Owner


@dataclass(frozen=True)
class WeeklyChallenge:
    """
    Result of a week-specific fantasy football challenge.

    Represents the winner and details of a weekly challenge.
    Can be team-based or player-based.
    """
    challenge_name: str
    week: int
    winner: str  # Team name or player name
    owner: Owner | None  # None for player-based challenges without team context
    division: str
    value: str  # Formatted value (score, margin, etc.)
    description: str
    additional_info: dict[str, Any]  # Flexible for player details, position, etc.

    def __post_init__(self) -> None:
        """Validate weekly challenge result after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate weekly challenge result data."""
        if not self.challenge_name.strip():
            raise DataValidationError("Challenge name cannot be empty")

        if self.week < 1 or self.week > 18:
            raise DataValidationError(f"Week must be between 1 and 18: {self.week}")

        if not self.winner.strip():
            raise DataValidationError("Winner cannot be empty")

        # Owner can be None for player-based challenges
        # If owner is provided, it validates itself

        if not self.division.strip():
            raise DataValidationError("Division cannot be empty")

        if not self.description.strip():
            raise DataValidationError("Description cannot be empty")

    @property
    def is_player_challenge(self) -> bool:
        """Check if this is a player-based challenge."""
        return "position" in self.additional_info or "player" in self.challenge_name.lower()

    @property
    def is_team_challenge(self) -> bool:
        """Check if this is a team-based challenge."""
        return not self.is_player_challenge
