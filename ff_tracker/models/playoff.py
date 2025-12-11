"""
Playoff data models for Fantasy Football Challenge Tracker.

This module defines type-safe data structures for representing playoff brackets,
championship leaderboards, and related playoff data using modern Python typing
and frozen dataclasses for immutability.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError


@dataclass(frozen=True)
class PlayoffMatchup:
    """
    Represents a single playoff game between two teams in a winners bracket.

    This model captures all information about a playoff matchup including seeds,
    teams, owners, scores, and the winner. Data is immutable after construction
    and validated to ensure consistency.

    Attributes:
        matchup_id: Unique identifier (e.g., "div1_sf1", "div2_finals")
        round_name: Human-readable round name ("Semifinal 1", "Semifinal 2", "Finals")
        seed1: Playoff seed of first team (1-4)
        team1_name: Name of first team
        owner1_name: Owner name of first team
        score1: First team's score (None if game not started)
        seed2: Playoff seed of second team (1-4)
        team2_name: Name of second team
        owner2_name: Owner name of second team
        score2: Second team's score (None if game not started)
        winner_name: Name of winning team (None if game incomplete)
        winner_seed: Seed of winning team (None if game incomplete)
        division_name: Division this matchup belongs to
    """

    matchup_id: str
    round_name: str
    seed1: int
    team1_name: str
    owner1_name: str
    score1: float | None
    seed2: int
    team2_name: str
    owner2_name: str
    score2: float | None
    winner_name: str | None
    winner_seed: int | None
    division_name: str

    def __post_init__(self) -> None:
        """Validate playoff matchup data after construction."""
        # Validate seeds are positive
        if self.seed1 <= 0 or self.seed2 <= 0:
            raise DataValidationError(
                f"Seeds must be positive: seed1={self.seed1}, seed2={self.seed2}"
            )

        # Validate scores are non-negative if present
        if self.score1 is not None and self.score1 < 0:
            raise DataValidationError(f"Score1 cannot be negative: {self.score1}")
        if self.score2 is not None and self.score2 < 0:
            raise DataValidationError(f"Score2 cannot be negative: {self.score2}")

        # Validate winner matches one of the teams
        if self.winner_name is not None:
            if self.winner_name not in (self.team1_name, self.team2_name):
                raise DataValidationError(
                    f"Winner must be one of the teams: {self.winner_name} not in "
                    f"[{self.team1_name}, {self.team2_name}]"
                )

        # Validate winner seed matches
        if self.winner_seed is not None:
            if self.winner_seed not in (self.seed1, self.seed2):
                raise DataValidationError(
                    f"Winner seed must match one of the seeds: {self.winner_seed} not in "
                    f"[{self.seed1}, {self.seed2}]"
                )

        # Validate strings are non-empty
        if not self.matchup_id.strip():
            raise DataValidationError("matchup_id cannot be empty")
        if not self.round_name.strip():
            raise DataValidationError("round_name cannot be empty")
        if not self.team1_name.strip() or not self.team2_name.strip():
            raise DataValidationError("Team names cannot be empty")
        if not self.owner1_name.strip() or not self.owner2_name.strip():
            raise DataValidationError("Owner names cannot be empty")
        if not self.division_name.strip():
            raise DataValidationError("division_name cannot be empty")


@dataclass(frozen=True)
class PlayoffBracket:
    """
    Contains all playoff matchups for a single division in a specific round.

    This model groups related playoff matchups together (e.g., both semifinals
    or the finals matchup) and validates that the structure matches the round type.

    Attributes:
        round: Current playoff round name ("Semifinals" or "Finals")
        week: ESPN week number (15, 16, etc.)
        matchups: List of playoff matchups in this round
    """

    round: str
    week: int
    matchups: list[PlayoffMatchup]

    def __post_init__(self) -> None:
        """Validate playoff bracket structure after construction."""
        # Validate round name
        if self.round not in ("Semifinals", "Finals"):
            raise DataValidationError(f"Round must be 'Semifinals' or 'Finals', got '{self.round}'")

        # Validate week is positive
        if self.week <= 0:
            raise DataValidationError(f"Week must be positive: {self.week}")

        # Validate at least one matchup
        if not self.matchups:
            raise DataValidationError("PlayoffBracket must have at least one matchup")

        # Validate matchup count matches round
        if self.round == "Semifinals" and len(self.matchups) != 2:
            raise DataValidationError(
                f"Semifinals must have exactly 2 matchups, got {len(self.matchups)}"
            )
        if self.round == "Finals" and len(self.matchups) != 1:
            raise DataValidationError(
                f"Finals must have exactly 1 matchup, got {len(self.matchups)}"
            )


@dataclass(frozen=True)
class ChampionshipEntry:
    """
    Represents a single division winner's performance in Championship Week.

    This model captures a division winner's final score in the championship
    free-for-all where the highest scorer across all divisions wins.

    Attributes:
        rank: Rank in championship (1 = champion, 2 = runner-up, etc.)
        team_name: Name of team
        owner_name: Owner name
        division_name: Division this team won
        score: Team's score in Championship Week
        is_champion: True if this is the overall champion (rank=1)
    """

    rank: int
    team_name: str
    owner_name: str
    division_name: str
    score: float
    is_champion: bool

    def __post_init__(self) -> None:
        """Validate championship entry data after construction."""
        # Validate rank is positive
        if self.rank <= 0:
            raise DataValidationError(f"Rank must be positive: {self.rank}")

        # Validate score is non-negative
        if self.score < 0:
            raise DataValidationError(f"Score cannot be negative: {self.score}")

        # Validate strings are non-empty
        if not self.team_name.strip():
            raise DataValidationError("team_name cannot be empty")
        if not self.owner_name.strip():
            raise DataValidationError("owner_name cannot be empty")
        if not self.division_name.strip():
            raise DataValidationError("division_name cannot be empty")

        # Validate is_champion matches rank
        if self.is_champion and self.rank != 1:
            raise DataValidationError(f"Champion flag set but rank is {self.rank}, must be 1")
        if not self.is_champion and self.rank == 1:
            raise DataValidationError("Rank is 1 but champion flag not set")


@dataclass(frozen=True)
class ChampionshipLeaderboard:
    """
    Contains ranked list of all division winners competing in Championship Week.

    This model represents the final championship standings where division winners
    compete in a free-for-all, highest-score-wins format. Validates that entries
    are properly ranked and exactly one champion is declared.

    Attributes:
        week: Championship week number (typically 17)
        entries: Ranked division winners (ordered by rank)
    """

    week: int
    entries: list[ChampionshipEntry]

    def __post_init__(self) -> None:
        """Validate championship leaderboard structure after construction."""
        # Validate week is positive
        if self.week <= 0:
            raise DataValidationError(f"Week must be positive: {self.week}")

        # Validate at least one entry
        if not self.entries:
            raise DataValidationError("ChampionshipLeaderboard must have at least one entry")

        # Validate entries are properly ranked (1, 2, 3, ...)
        expected_ranks = list(range(1, len(self.entries) + 1))
        actual_ranks = [entry.rank for entry in self.entries]
        if actual_ranks != expected_ranks:
            raise DataValidationError(
                f"Entries must be ranked sequentially starting at 1. "
                f"Expected {expected_ranks}, got {actual_ranks}"
            )

        # Validate exactly one champion
        champions = [e for e in self.entries if e.is_champion]
        if len(champions) != 1:
            raise DataValidationError(f"Must have exactly one champion, found {len(champions)}")

        # Validate champion is rank 1
        if self.entries[0].rank != 1 or not self.entries[0].is_champion:
            raise DataValidationError("First entry must be rank 1 and champion")

    @property
    def champion(self) -> ChampionshipEntry:
        """Get the overall champion (highest scorer)."""
        return next(e for e in self.entries if e.is_champion)
