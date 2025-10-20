"""
Core data models for Fantasy Football Challenge Tracker.

This module defines type-safe data structures using modern Python typing
and dataclasses for representing fantasy football data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..exceptions import DataValidationError


class Validatable(Protocol):
    """Protocol for objects that can validate their data."""

    def validate(self) -> None:
        """Validate the object's data, raising DataValidationError if invalid."""
        ...


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
