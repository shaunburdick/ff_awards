"""
Weekly player performance data model.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError


@dataclass(frozen=True)
class WeeklyPlayerStats:
    """
    Individual player stats for a specific week.

    Represents a single player's performance in one week,
    including actual vs projected points.
    """
    name: str
    position: str
    team_name: str  # Fantasy team they're on
    division: str
    points: float
    projected_points: float
    projection_diff: float  # points - projected_points
    slot_position: str  # Starting lineup slot or 'BE' for bench
    week: int
    pro_team: str  # NFL team abbreviation
    pro_opponent: str  # Opponent NFL team abbreviation

    def __post_init__(self) -> None:
        """Validate weekly player stats after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate weekly player stats for consistency."""
        if not self.name.strip():
            raise DataValidationError("Player name cannot be empty")

        if not self.position.strip():
            raise DataValidationError("Position cannot be empty")

        if not self.team_name.strip():
            raise DataValidationError("Team name cannot be empty")

        if not self.division.strip():
            raise DataValidationError("Division name cannot be empty")

        # Points can be negative (e.g., fumbles, interceptions)
        # but projected points should be non-negative
        if self.projected_points < 0:
            raise DataValidationError(
                f"Projected points cannot be negative: {self.projected_points}"
            )

        # Verify projection_diff is calculated correctly
        expected_diff = self.points - self.projected_points
        if abs(self.projection_diff - expected_diff) > 0.01:  # Allow small floating point errors
            raise DataValidationError(
                f"Projection diff {self.projection_diff} doesn't match "
                f"calculated value {expected_diff}"
            )

        if not self.slot_position.strip():
            raise DataValidationError("Slot position cannot be empty")

        if self.week < 1 or self.week > 18:
            raise DataValidationError(f"Week must be between 1 and 18: {self.week}")

        if not self.pro_team.strip():
            raise DataValidationError("Pro team cannot be empty")

        # pro_opponent can be empty for bye weeks
        # if not self.pro_opponent.strip():
        #     raise DataValidationError("Pro opponent cannot be empty")

    @property
    def is_starter(self) -> bool:
        """Check if player was in starting lineup (not on bench)."""
        return self.slot_position.upper() != "BE" and self.slot_position.upper() != "IR"

    @property
    def exceeded_projection(self) -> bool:
        """Check if player exceeded their projection."""
        return self.projection_diff > 0
