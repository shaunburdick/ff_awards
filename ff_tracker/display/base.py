"""
Base formatter interface and common utilities for output formatting.

This module provides the foundation for different output formats while
maintaining consistency and extensibility.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol

from ..models import ChallengeResult, DivisionData, TeamStats, WeeklyChallenge


class OutputFormatter(Protocol):
    """Protocol for output formatters."""

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None
    ) -> str:
        """
        Format the complete output for display.

        Args:
            divisions: List of division data
            challenges: List of season challenge results
            weekly_challenges: List of weekly challenge results (optional)
            current_week: Current fantasy week number

        Returns:
            Formatted output string
        """
        ...


class BaseFormatter(ABC):
    """Base class for output formatters with common functionality."""

    @abstractmethod
    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None
    ) -> str:
        """Format the complete output for display."""
        pass

    def _get_sorted_teams_by_division(self, division: DivisionData) -> list[TeamStats]:
        """Get teams sorted by wins (descending) then points for (descending)."""
        return sorted(division.teams, key=lambda x: (x.wins, x.points_for), reverse=True)

    def _get_overall_top_teams(self, divisions: Sequence[DivisionData], limit: int = 20) -> list[TeamStats]:
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
        return text[:max_length - 1] + "…"
