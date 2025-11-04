"""
Weekly game result data model for specific week matchups.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError


@dataclass(frozen=True)
class WeeklyGameResult:
    """
    Game result for a specific week with projections.

    Represents one team's performance in a single week matchup,
    including projected scores for over/under analysis.
    """
    team_name: str
    score: float
    projected_score: float  # ESPN's real-time updated team projection
    opponent_name: str
    opponent_score: float
    opponent_projected_score: float
    won: bool
    week: int
    margin: float
    projection_diff: float  # score - projected_score (ESPN's real-time)
    division: str
    starter_projected_score: float | None = None  # Sum of starter pre-game projections
    true_projection_diff: float | None = None  # score - starter_projected_score

    def __post_init__(self) -> None:
        """Validate weekly game result data after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate weekly game result data for consistency."""
        if not self.team_name.strip():
            raise DataValidationError("Team name cannot be empty")

        if not self.opponent_name.strip():
            raise DataValidationError("Opponent name cannot be empty")

        if self.score < 0:
            raise DataValidationError(f"Score cannot be negative: {self.score}")

        if self.opponent_score < 0:
            raise DataValidationError(f"Opponent score cannot be negative: {self.opponent_score}")

        if self.projected_score < 0:
            raise DataValidationError(f"Projected score cannot be negative: {self.projected_score}")

        if self.opponent_projected_score < 0:
            raise DataValidationError(
                f"Opponent projected score cannot be negative: {self.opponent_projected_score}"
            )

        if self.week < 1 or self.week > 18:
            raise DataValidationError(f"Week must be between 1 and 18: {self.week}")

        if self.margin < 0:
            raise DataValidationError(f"Margin cannot be negative: {self.margin}")

        # Verify projection_diff is calculated correctly
        expected_diff = self.score - self.projected_score
        if abs(self.projection_diff - expected_diff) > 0.01:  # Allow small floating point errors
            raise DataValidationError(
                f"Projection diff {self.projection_diff} doesn't match "
                f"calculated value {expected_diff}"
            )

        # Verify true_projection_diff if starter projections are available
        if self.starter_projected_score is not None:
            if self.starter_projected_score < 0:
                raise DataValidationError(
                    f"Starter projected score cannot be negative: {self.starter_projected_score}"
                )

            if self.true_projection_diff is not None:
                expected_true_diff = self.score - self.starter_projected_score
                if abs(self.true_projection_diff - expected_true_diff) > 0.01:
                    raise DataValidationError(
                        f"True projection diff {self.true_projection_diff} doesn't match "
                        f"calculated value {expected_true_diff}"
                    )

        if not self.division.strip():
            raise DataValidationError("Division name cannot be empty")
