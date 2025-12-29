"""
Data models for season recap functionality.

This module defines models for comprehensive end-of-season summaries,
including season structure, regular season results, playoff data,
and complete season summaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..exceptions import DataValidationError

if TYPE_CHECKING:
    from .challenge import ChallengeResult
    from .division import DivisionData
    from .playoff import ChampionshipEntry, ChampionshipLeaderboard, PlayoffBracket


@dataclass(frozen=True)
class SeasonStructure:
    """
    Dynamic season structure calculated from ESPN API.

    Contains week boundaries for all phases of the fantasy season,
    calculated from league settings rather than hardcoded.
    """

    regular_season_start: int
    regular_season_end: int
    playoff_start: int
    playoff_end: int
    championship_week: int
    playoff_rounds: int
    playoff_round_length: int

    def __post_init__(self) -> None:
        """Validate season structure is logical."""
        if self.regular_season_start < 1:
            raise DataValidationError(
                f"Regular season must start at week 1 or later, got {self.regular_season_start}"
            )

        if self.regular_season_end < self.regular_season_start:
            raise DataValidationError(
                f"Regular season end ({self.regular_season_end}) must be after start "
                f"({self.regular_season_start})"
            )

        if self.playoff_start != self.regular_season_end + 1:
            raise DataValidationError(
                f"Playoffs must start immediately after regular season. "
                f"Expected week {self.regular_season_end + 1}, got {self.playoff_start}"
            )

        if self.playoff_end < self.playoff_start:
            raise DataValidationError(
                f"Playoff end ({self.playoff_end}) must be after start ({self.playoff_start})"
            )

        if self.championship_week != self.playoff_end + 1:
            raise DataValidationError(
                f"Championship must be immediately after playoffs. "
                f"Expected week {self.playoff_end + 1}, got {self.championship_week}"
            )

        if self.playoff_rounds < 1:
            raise DataValidationError(
                f"Must have at least one playoff round, got {self.playoff_rounds}"
            )

        if self.playoff_round_length < 1:
            raise DataValidationError(
                f"Playoff round length must be at least 1 week, got {self.playoff_round_length}"
            )


@dataclass(frozen=True)
class DivisionChampion:
    """
    Regular season division champion.

    Represents the team with the best record in a division at the end
    of the regular season.
    """

    division_name: str
    team_name: str
    owner_name: str
    wins: int
    losses: int
    points_for: float
    points_against: float
    final_rank: int

    def __post_init__(self) -> None:
        """Validate champion data."""
        if not self.team_name.strip():
            raise DataValidationError("Team name cannot be empty")

        if not self.division_name.strip():
            raise DataValidationError("Division name cannot be empty")

        if self.wins < 0:
            raise DataValidationError(f"Wins cannot be negative: {self.wins}")

        if self.losses < 0:
            raise DataValidationError(f"Losses cannot be negative: {self.losses}")

        if self.points_for < 0:
            raise DataValidationError(f"Points for cannot be negative: {self.points_for}")

        if self.points_against < 0:
            raise DataValidationError(f"Points against cannot be negative: {self.points_against}")

        if self.final_rank < 1:
            raise DataValidationError(f"Final rank must be at least 1, got {self.final_rank}")

    @property
    def record(self) -> str:
        """Get formatted record string (e.g., '10-4')."""
        return f"{self.wins}-{self.losses}"


@dataclass(frozen=True)
class RegularSeasonSummary:
    """
    Summary of regular season results across all divisions.

    Contains division champions and complete final standings.
    """

    structure: SeasonStructure
    division_champions: tuple[DivisionChampion, ...]
    final_standings: tuple[DivisionData, ...]

    def __post_init__(self) -> None:
        """Validate regular season summary."""
        if len(self.division_champions) != len(self.final_standings):
            raise DataValidationError(
                f"Must have one champion per division. "
                f"Got {len(self.division_champions)} champions and {len(self.final_standings)} divisions"
            )

        if not self.division_champions:
            raise DataValidationError("Must have at least one division champion")

    @property
    def total_teams(self) -> int:
        """Total number of teams across all divisions."""
        return sum(len(div.teams) for div in self.final_standings)

    @property
    def division_count(self) -> int:
        """Number of divisions."""
        return len(self.division_champions)

    @property
    def regular_season_weeks(self) -> tuple[int, int]:
        """Regular season week range (start, end)."""
        return (self.structure.regular_season_start, self.structure.regular_season_end)


@dataclass(frozen=True)
class PlayoffRound:
    """
    Results for one playoff round across all divisions.

    Contains playoff brackets for all divisions for a specific round
    (e.g., all semifinals, or all finals).
    """

    round_name: str
    week: int
    division_brackets: tuple[PlayoffBracket, ...]

    def __post_init__(self) -> None:
        """Validate round data."""
        if not self.round_name.strip():
            raise DataValidationError("Round name cannot be empty")

        if self.week < 1:
            raise DataValidationError(f"Week must be at least 1, got {self.week}")

        if not self.division_brackets:
            raise DataValidationError(
                f"Playoff round '{self.round_name}' must have at least one division bracket"
            )


@dataclass(frozen=True)
class PlayoffSummary:
    """
    Complete playoff results for all rounds.

    Contains all playoff rounds (typically Semifinals and Finals)
    across all divisions.
    """

    structure: SeasonStructure
    rounds: tuple[PlayoffRound, ...]

    def __post_init__(self) -> None:
        """Validate playoff summary."""
        if not self.rounds:
            raise DataValidationError("Playoff summary must have at least one round")

        # Validate round weeks are within playoff boundaries
        for round_data in self.rounds:
            if not (self.structure.playoff_start <= round_data.week <= self.structure.playoff_end):
                raise DataValidationError(
                    f"Round week {round_data.week} is outside playoff boundaries "
                    f"({self.structure.playoff_start}-{self.structure.playoff_end})"
                )

    @property
    def semifinals(self) -> PlayoffRound | None:
        """Get semifinals round if it exists."""
        return next((r for r in self.rounds if "Semifinal" in r.round_name), None)

    @property
    def finals(self) -> PlayoffRound | None:
        """Get finals round if it exists."""
        return next((r for r in self.rounds if "Final" in r.round_name), None)

    @property
    def playoff_weeks(self) -> tuple[int, int]:
        """Playoff week range (start, end)."""
        return (self.structure.playoff_start, self.structure.playoff_end)


@dataclass(frozen=True)
class SeasonSummary:
    """
    Complete summary of a fantasy football season.

    Top-level container for all season data: regular season, challenges,
    playoffs, and championship.
    """

    year: int
    generated_at: str
    structure: SeasonStructure
    regular_season: RegularSeasonSummary
    season_challenges: tuple[ChallengeResult, ...]
    playoffs: PlayoffSummary
    championship: ChampionshipLeaderboard | None

    def __post_init__(self) -> None:
        """Validate season summary."""
        # Sanity check on year
        if self.year < 2000 or self.year > 2100:
            raise DataValidationError(f"Invalid year: {self.year}. Must be between 2000 and 2100")

        # Validate ISO 8601 timestamp format (basic check)
        if not self.generated_at or "T" not in self.generated_at:
            raise DataValidationError(
                f"Invalid timestamp format: {self.generated_at}. Expected ISO 8601 format"
            )

        # Must have exactly 5 season challenges
        if len(self.season_challenges) != 5:
            raise DataValidationError(
                f"Must have exactly 5 season challenges, got {len(self.season_challenges)}"
            )

    @property
    def is_complete(self) -> bool:
        """Check if season summary includes championship."""
        return self.championship is not None

    @property
    def total_divisions(self) -> int:
        """Total number of divisions."""
        return len(self.regular_season.division_champions)

    @property
    def overall_champion(self) -> ChampionshipEntry | None:
        """Get overall champion if championship complete."""
        if self.championship:
            return self.championship.champion
        return None


__all__ = [
    "DivisionChampion",
    "PlayoffRound",
    "PlayoffSummary",
    "RegularSeasonSummary",
    "SeasonStructure",
    "SeasonSummary",
]
