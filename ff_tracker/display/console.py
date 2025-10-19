"""
Console output formatter for Fantasy Football Challenge Tracker.

Provides formatted console output with tables and color coding.
"""

from __future__ import annotations

from collections.abc import Sequence

from tabulate import tabulate

from ..models import ChallengeResult, DivisionData
from .base import BaseFormatter


class ConsoleFormatter(BaseFormatter):
    """Formatter for rich console output with tables."""

    def __init__(self, year: int) -> None:
        """
        Initialize console formatter.

        Args:
            year: Fantasy season year for display
        """
        super().__init__()
        self.year = year

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        current_week: int | None = None
    ) -> str:
        """Format complete output for console display."""
        output_lines: list[str] = []

        # Header
        total_divisions, total_teams = self._calculate_total_stats(divisions)
        output_lines.append(f"\n🏈 Fantasy Football Multi-Division Challenge Tracker ({self.year})")
        output_lines.append(f"📊 {total_divisions} divisions, {total_teams} teams total")

        if current_week is not None:
            output_lines.append(f"📅 Current Week: {current_week}")
            # Machine-readable output for scripts
            output_lines.append(f"CURRENT_WEEK={current_week}")

        # Division standings
        for division in divisions:
            output_lines.append(f"\n🏆 {division.name} STANDINGS")
            division_table = self._format_division_table(division)
            output_lines.append(division_table)

        # Overall top teams
        output_lines.append("\n🌟 OVERALL TOP TEAMS (Across All Divisions)")
        overall_table = self._format_overall_table(divisions)
        output_lines.append(overall_table)

        # Challenge results
        if challenges:
            output_lines.append("\n💰 OVERALL SEASON CHALLENGES")
            challenge_table = self._format_challenge_table(challenges)
            output_lines.append(challenge_table)

            # Game data summary
            total_games = self._calculate_total_games(divisions)
            if total_games > 0:
                output_lines.append(f"📊 Game data: {total_games} individual results processed")
            else:
                output_lines.append("⚠️  Game data: Limited - some challenges may be incomplete")

        return "\n".join(output_lines)

    def _format_division_table(self, division: DivisionData) -> str:
        """Format a single division's standings table."""
        sorted_teams = self._get_sorted_teams_by_division(division)

        division_table: list[list[str]] = []
        for i, team in enumerate(sorted_teams, 1):
            division_table.append([
                str(i),
                self._truncate_text(team.name, 25),
                self._truncate_text(team.owner, 20),
                f"{team.points_for:.1f}",
                f"{team.points_against:.1f}",
                f"{team.wins}-{team.losses}"
            ])

        return tabulate(
            division_table,
            headers=["Rank", "Team", "Owner", "Points For", "Points Against", "Record"],
            tablefmt="grid"
        )

    def _format_overall_table(self, divisions: Sequence[DivisionData]) -> str:
        """Format the overall top teams table."""
        top_teams = self._get_overall_top_teams(divisions, limit=20)

        overall_table: list[list[str]] = []
        for i, team in enumerate(top_teams, 1):
            overall_table.append([
                str(i),
                self._truncate_text(team.name, 20),
                self._truncate_text(team.owner, 15),
                self._truncate_text(team.division, 15),
                f"{team.points_for:.1f}",
                f"{team.points_against:.1f}",
                f"{team.wins}-{team.losses}"
            ])

        return tabulate(
            overall_table,
            headers=["Rank", "Team", "Owner", "Division", "Points For", "Points Against", "Record"],
            tablefmt="grid"
        )

    def _format_challenge_table(self, challenges: Sequence[ChallengeResult]) -> str:
        """Format the challenges results table."""
        challenge_table: list[list[str]] = []

        for challenge in challenges:
            challenge_table.append([
                challenge.challenge_name,
                self._truncate_text(challenge.winner, 25),
                self._truncate_text(challenge.owner, 20),
                self._truncate_text(challenge.division, 15),
                self._truncate_text(challenge.description, 35)
            ])

        return tabulate(
            challenge_table,
            headers=["Challenge", "Winner", "Owner", "Division", "Details"],
            tablefmt="grid"
        )
