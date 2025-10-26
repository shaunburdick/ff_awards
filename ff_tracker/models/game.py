"""
Game result data model for individual matchups.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError


@dataclass(frozen=True)
class GameResult:
    """
    Individual game result with team performance and outcome.

    Represents one team's performance in a single week matchup.
    """
    team_name: str
    score: float
    opponent_name: str
    opponent_score: float
    won: bool
    week: int
    margin: float
    division: str

    def __post_init__(self) -> None:
        """Validate game result data after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate game result data for consistency."""
        if not self.team_name.strip():
            raise DataValidationError("Team name cannot be empty")

        if not self.opponent_name.strip():
            raise DataValidationError("Opponent name cannot be empty")

        if self.score < 0:
            raise DataValidationError(f"Score cannot be negative: {self.score}")

        if self.opponent_score < 0:
            raise DataValidationError(f"Opponent score cannot be negative: {self.opponent_score}")

        if self.week < 1 or self.week > 18:
            raise DataValidationError(f"Week must be between 1 and 18: {self.week}")

        if self.margin < 0:
            raise DataValidationError(f"Margin cannot be negative: {self.margin}")

        # Validate consistency between scores and outcome
        expected_won = self.score > self.opponent_score
        if self.won != expected_won:
            raise DataValidationError(
                f"Win/loss inconsistent with scores: {self.score} vs {self.opponent_score}, won={self.won}"
            )

        # Validate margin calculation
        expected_margin = abs(self.score - self.opponent_score)
        if abs(self.margin - expected_margin) > 0.01:  # Allow for floating point precision
            raise DataValidationError(
                f"Margin inconsistent with scores: expected {expected_margin}, got {self.margin}"
            )
