"""
Base formatter interface and common utilities for output formatting.

This module provides the foundation for different output formats while
maintaining consistency and extensibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from ..models import (
    ChallengeResult,
    ChampionshipLeaderboard,
    DivisionData,
    TeamStats,
    WeeklyChallenge,
)
from ..models.championship import ChampionshipRoster


class ReportMode(Enum):
    """Report generation mode - determines which data sections to display."""

    REGULAR = "regular"  # Regular season with challenges and standings
    PLAYOFF = "playoff"  # Playoff mode with brackets (Weeks 15-16)
    CHAMPIONSHIP = "championship"  # Championship week with leaderboard (Week 17)


@dataclass
class ReportContext:
    """
    Context object containing all data needed for report formatting.

    This dataclass encapsulates all the parameters previously passed to
    format_output(), reducing method signatures from 6 parameters to 1
    and making the mode detection explicit.

    Attributes:
        mode: Report generation mode (regular/playoff/championship)
        year: Fantasy season year
        current_week: Current fantasy week number
        divisions: List of division data (empty for championship mode)
        challenges: List of season challenge results (empty for championship mode)
        weekly_challenges: List of weekly challenge results (None for championship)
        championship: Championship leaderboard (None for regular/playoff modes)
        championship_rosters: Detailed rosters for championship teams (None for regular/playoff)
    """

    mode: ReportMode
    year: int
    current_week: int | None = None
    divisions: Sequence[DivisionData] = field(default_factory=list)
    challenges: Sequence[ChallengeResult] = field(default_factory=list)
    weekly_challenges: Sequence[WeeklyChallenge] | None = None
    championship: ChampionshipLeaderboard | None = None
    championship_rosters: Sequence[ChampionshipRoster] | None = None

    def is_regular_season(self) -> bool:
        """Check if this is a regular season report."""
        return self.mode == ReportMode.REGULAR

    def is_playoff_mode(self) -> bool:
        """Check if this is a playoff report."""
        return self.mode == ReportMode.PLAYOFF

    def is_championship_mode(self) -> bool:
        """Check if this is a championship report."""
        return self.mode == ReportMode.CHAMPIONSHIP

    def has_weekly_challenges(self) -> bool:
        """Check if weekly challenges data is available."""
        return self.weekly_challenges is not None and len(self.weekly_challenges) > 0

    def has_championship_data(self) -> bool:
        """Check if championship data is available."""
        return self.championship is not None


class OutputFormatter(Protocol):
    """Protocol for output formatters."""

    def format_output(
        self,
        divisions: Sequence[DivisionData] | None = None,
        challenges: Sequence[ChallengeResult] | None = None,
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None,
        championship: ChampionshipLeaderboard | None = None,
        championship_rosters: Sequence[ChampionshipRoster] | None = None,
        context: ReportContext | None = None,
    ) -> str:
        """
        Format the complete output for display.

        This method supports two calling conventions for backward compatibility:

        1. New style (recommended) - pass context object:
           formatter.format_output(context=report_context)

        2. Old style (deprecated) - pass individual parameters:
           formatter.format_output(divisions, challenges, weekly_challenges, ...)

        Args:
            divisions: List of division data (deprecated - use context)
            challenges: List of season challenge results (deprecated - use context)
            weekly_challenges: List of weekly challenge results (deprecated - use context)
            current_week: Current fantasy week number (deprecated - use context)
            championship: Championship leaderboard (deprecated - use context)
            championship_rosters: Detailed rosters for championship teams (deprecated - use context)
            context: ReportContext object containing all report data (new style)

        Returns:
            Formatted output string
        """
        ...


class BaseFormatter(ABC):
    """Base class for output formatters with common functionality."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize formatter with optional arguments.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        self.year = year
        self.format_args = format_args or {}

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """
        Return dictionary of supported argument names and descriptions.

        Subclasses should override this to document their specific arguments.

        Returns:
            Dict mapping argument name to human-readable description
        """
        return {}

    def _get_arg(self, key: str, default: str | None = None) -> str | None:
        """
        Safely retrieve a format argument with optional default.

        Args:
            key: Argument name to retrieve
            default: Default value if argument not provided

        Returns:
            Argument value or default
        """
        return self.format_args.get(key, default)

    def _get_arg_bool(self, key: str, default: bool = False) -> bool:
        """
        Retrieve a format argument as boolean.

        Accepts: "true", "1", "yes", "on" (case-insensitive) as True

        Args:
            key: Argument name to retrieve
            default: Default value if argument not provided

        Returns:
            Boolean value
        """
        value = self._get_arg(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def _get_arg_int(self, key: str, default: int) -> int:
        """
        Retrieve a format argument as integer.

        Args:
            key: Argument name to retrieve
            default: Default value if argument not provided or invalid

        Returns:
            Integer value
        """
        value = self._get_arg(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _build_context_from_params(
        self,
        divisions: Sequence[DivisionData] | None,
        challenges: Sequence[ChallengeResult] | None,
        weekly_challenges: Sequence[WeeklyChallenge] | None,
        current_week: int | None,
        championship: ChampionshipLeaderboard | None,
        championship_rosters: Sequence[ChampionshipRoster] | None,
    ) -> ReportContext:
        """
        Build ReportContext from individual parameters (backward compatibility).

        This helper converts old-style parameter calls to the new context object.
        """
        # Determine mode based on provided data
        if championship is not None:
            mode = ReportMode.CHAMPIONSHIP
        elif divisions and any(d.is_playoff_mode for d in divisions):
            mode = ReportMode.PLAYOFF
        else:
            mode = ReportMode.REGULAR

        return ReportContext(
            mode=mode,
            year=self.year,
            current_week=current_week,
            divisions=divisions or [],
            challenges=challenges or [],
            weekly_challenges=weekly_challenges,
            championship=championship,
            championship_rosters=championship_rosters,
        )

    @abstractmethod
    def format_output(
        self,
        divisions: Sequence[DivisionData] | None = None,
        challenges: Sequence[ChallengeResult] | None = None,
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None,
        championship: ChampionshipLeaderboard | None = None,
        championship_rosters: Sequence[ChampionshipRoster] | None = None,
        context: ReportContext | None = None,
    ) -> str:
        """
        Format the complete output for display.

        Supports both old-style (individual parameters) and new-style (context object).
        Subclasses should implement this method using the context object.
        """
        pass

    def _get_sorted_teams_by_division(self, division: DivisionData) -> list[TeamStats]:
        """Get teams sorted by wins (descending) then points for (descending)."""
        return sorted(division.teams, key=lambda x: (x.wins, x.points_for), reverse=True)

    def _get_overall_top_teams(
        self, divisions: Sequence[DivisionData], limit: int = 20
    ) -> list[TeamStats]:
        """Get top teams across all divisions."""
        all_teams: list[TeamStats] = []
        for division in divisions:
            all_teams.extend(division.teams)

        return sorted(all_teams, key=lambda x: (x.wins, x.points_for), reverse=True)[:limit]

    def _calculate_total_stats(self, divisions: Sequence[DivisionData]) -> tuple[int, int]:
        """Calculate total number of divisions and teams."""
        total_divisions = len(divisions)
        total_teams = sum(len(division.teams) for division in divisions)
        return total_divisions, total_teams

    def _calculate_total_games(self, divisions: Sequence[DivisionData]) -> int:
        """Calculate total number of games processed."""
        return sum(len(division.games) for division in divisions)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length, preserving readability."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 1] + "…"

    def _check_all_games_final(self, rosters: Sequence[ChampionshipRoster] | None) -> bool:
        """
        Check if all games in championship rosters are complete.

        Args:
            rosters: List of championship rosters to check

        Returns:
            True if all games are final, False otherwise
        """
        if not rosters:
            return False

        for roster in rosters:
            for slot in roster.starters:
                if slot.game_status != "final":
                    return False

        return True
