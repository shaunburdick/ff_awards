"""
Division data model representing a complete league.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError
from .game import GameResult
from .team import TeamStats


@dataclass(frozen=True)
class DivisionData:
    """
    Complete data for a single division (league).

    Contains all teams and games for one ESPN league.
    """
    league_id: int
    name: str
    teams: list[TeamStats]
    games: list[GameResult]

    def __post_init__(self) -> None:
        """Validate division data after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate division data for consistency."""
        if self.league_id <= 0:
            raise DataValidationError(f"League ID must be positive: {self.league_id}")

        if not self.name.strip():
            raise DataValidationError("Division name cannot be empty")

        if not self.teams:
            raise DataValidationError("Division must have at least one team")

        # Validate all teams are from this division
        for team in self.teams:
            if team.division != self.name:
                raise DataValidationError(
                    f"Team {team.name} has division '{team.division}' but should be '{self.name}'"
                )

        # Validate all games are from this division
        for game in self.games:
            if game.division != self.name:
                raise DataValidationError(
                    f"Game has division '{game.division}' but should be '{self.name}'"
                )

    @property
    def team_count(self) -> int:
        """Number of teams in this division."""
        return len(self.teams)

    @property
    def game_count(self) -> int:
        """Number of games recorded for this division."""
        return len(self.games)

    def get_team_by_name(self, team_name: str) -> TeamStats | None:
        """Find a team by name in this division."""
        for team in self.teams:
            if team.name == team_name:
                return team
        return None
