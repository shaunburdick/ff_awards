"""
Google Sheets TSV formatter for Fantasy Football Challenge Tracker.

Provides tab-separated values output suitable for copying into Google Sheets.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import ChallengeResult, DivisionData, WeeklyChallenge
from .base import BaseFormatter


class SheetsFormatter(BaseFormatter):
    """Formatter for Google Sheets compatible TSV output."""

    def __init__(self, year: int) -> None:
        """
        Initialize sheets formatter.

        Args:
            year: Fantasy season year for display
        """
        super().__init__()
        self.year = year

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None
    ) -> str:
        """Format complete output for Google Sheets TSV."""
        output_lines: list[str] = []

        # Header
        total_divisions, total_teams = self._calculate_total_stats(divisions)
        output_lines.append(f"Fantasy Football Multi-Division Challenge Tracker ({self.year})")
        output_lines.append(f"{total_divisions} divisions, {total_teams} teams total")

        if current_week is not None:
            output_lines.append(f"Current Week: {current_week}")

        output_lines.append("")

        # Division standings
        for division in divisions:
            output_lines.append(f"{division.name} STANDINGS")
            output_lines.append("Rank\tTeam\tOwner\tPoints For\tPoints Against\tRecord\tPlayoffs")

            sorted_teams = self._get_sorted_teams_by_division(division)
            for i, team in enumerate(sorted_teams, 1):
                playoff_indicator = "Y" if team.in_playoff_position else "N"
                output_lines.append(
                    f"{i}\t{team.name}\t{team.owner.full_name}\t{team.points_for:.1f}\t"
                    f"{team.points_against:.1f}\t{team.wins}-{team.losses}\t{playoff_indicator}"
                )

            output_lines.append("")

        # Overall top teams
        output_lines.append("OVERALL TOP TEAMS (Across All Divisions)")
        output_lines.append("Rank\tTeam\tOwner\tDivision\tPoints For\tPoints Against\tRecord\tPlayoffs")

        top_teams = self._get_overall_top_teams(divisions, limit=20)
        for i, team in enumerate(top_teams, 1):
            playoff_indicator = "Y" if team.in_playoff_position else "N"
            output_lines.append(
                f"{i}\t{team.name}\t{team.owner.full_name}\t{team.division}\t{team.points_for:.1f}\t"
                f"{team.points_against:.1f}\t{team.wins}-{team.losses}\t{playoff_indicator}"
            )

        output_lines.append("")

        # Weekly challenges (appears before season challenges)
        if weekly_challenges and current_week:
            output_lines.append(f"WEEK {current_week} HIGHLIGHTS")
            output_lines.append("Challenge\tWinner\tDivision\tValue\tDetails")

            for challenge in weekly_challenges:
                # For player challenges, include position in winner display
                winner_display = challenge.winner
                if "position" in challenge.additional_info:
                    position = challenge.additional_info["position"]
                    winner_display = f"{challenge.winner} ({position})"

                output_lines.append(
                    f"{challenge.challenge_name}\t{winner_display}\t{challenge.division}\t"
                    f"{challenge.value}\t{challenge.description}"
                )

            output_lines.append("")

        # Challenge results
        if challenges:
            output_lines.append("OVERALL SEASON CHALLENGES")
            output_lines.append("Challenge\tWinner\tOwner\tDivision\tDetails")

            for challenge in challenges:
                output_lines.append(
                    f"{challenge.challenge_name}\t{challenge.winner}\t{challenge.owner.full_name}\t"
                    f"{challenge.division}\t{challenge.description}"
                )

            output_lines.append("")

            total_games = self._calculate_total_games(divisions)
            if total_games > 0:
                output_lines.append(f"Game data: {total_games} individual results processed")
            else:
                output_lines.append("Game data: Limited - some challenges may be incomplete")

        return "\n".join(output_lines)
