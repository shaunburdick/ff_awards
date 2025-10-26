"""
Team statistics data model for season-long performance.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError
from .owner import Owner


@dataclass(frozen=True)
class TeamStats:
    """
    Season statistics for a fantasy team.

    Contains cumulative stats for the entire regular season.
    """
    name: str
    owner: Owner
    points_for: float
    points_against: float
    wins: int
    losses: int
    division: str
    in_playoff_position: bool = False

    def __post_init__(self) -> None:
        """Validate team stats after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate team statistics for consistency."""
        if not self.name.strip():
            raise DataValidationError("Team name cannot be empty")

        # Owner validation is handled by the Owner object itself

        if self.points_for < 0:
            raise DataValidationError(f"Points for cannot be negative: {self.points_for}")

        if self.points_against < 0:
            raise DataValidationError(f"Points against cannot be negative: {self.points_against}")

        if self.wins < 0:
            raise DataValidationError(f"Wins cannot be negative: {self.wins}")

        if self.losses < 0:
            raise DataValidationError(f"Losses cannot be negative: {self.losses}")

        if not self.division.strip():
            raise DataValidationError("Division name cannot be empty")

    @property
    def total_games(self) -> int:
        """Total number of games played."""
        return self.wins + self.losses

    @property
    def win_percentage(self) -> float:
        """Win percentage (0.0 to 1.0)."""
        if self.total_games == 0:
            return 0.0
        return self.wins / self.total_games
