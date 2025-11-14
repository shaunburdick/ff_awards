"""
Markdown formatter for Fantasy Football Challenge Tracker.

Provides Markdown formatted output suitable for GitHub, Slack, Discord, or other platforms
that support Markdown rendering.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import ChallengeResult, DivisionData, WeeklyChallenge
from .base import BaseFormatter


class MarkdownFormatter(BaseFormatter):
    """Formatter for Markdown output."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize markdown formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        super().__init__(year, format_args)

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for markdown formatter."""
        return {
            "note": "Optional notice displayed as blockquote at top",
            "include_toc": "Include table of contents (default: false)",
        }

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None
    ) -> str:
        """Format complete output for Markdown display."""
        # Get format arguments
        note = self._get_arg("note")
        include_toc = self._get_arg_bool("include_toc", False)

        output_lines: list[str] = []

        # Header
        total_divisions, total_teams = self._calculate_total_stats(divisions)
        output_lines.append(f"# 🏈 Fantasy Football Multi-Division Challenge Tracker ({self.year})")
        output_lines.append("")
        output_lines.append(f"📊 **{total_divisions} divisions**, **{total_teams} teams total**")

        if current_week is not None:
            output_lines.append(f"📅 **Current Week:** {current_week}")

        output_lines.append("")

        # Optional note
        if note:
            output_lines.append(f"> ⚠️ **{note}**")
            output_lines.append("")

        # Optional table of contents
        if include_toc:
            output_lines.append("## 📋 Table of Contents")
            output_lines.append("")
            # Add TOC entries for each major section
            for division in divisions:
                output_lines.append(f"- [{division.name} Standings](#{division.name.lower().replace(' ', '-')}-standings)")
            output_lines.append("- [Overall Top Teams](#-overall-top-teams-across-all-divisions)")
            if challenges:
                output_lines.append("- [Season Challenge Results](#-season-challenge-results)")
            if weekly_challenges and current_week:
                output_lines.append(f"- [Week {current_week} Highlights](#-week-{current_week}-highlights)")
            output_lines.append("")

        # Division standings
        for division in divisions:
            output_lines.append(f"## 🏆 {division.name} STANDINGS")
            output_lines.append("")
            division_table = self._format_division_table(division)
            output_lines.append(division_table)
            output_lines.append("")
            output_lines.append("_\\* = Currently in playoff position_")
            output_lines.append("")

        # Overall top teams
        output_lines.append("## 🌟 OVERALL TOP TEAMS (Across All Divisions)")
        output_lines.append("")
        overall_table = self._format_overall_table(divisions)
        output_lines.append(overall_table)
        output_lines.append("")
        output_lines.append("_\\* = Currently in playoff position_")
        output_lines.append("")

        # Weekly challenges (appears before season challenges)
        if weekly_challenges and current_week:
            output_lines.append(f"## 🔥 WEEK {current_week} HIGHLIGHTS")
            output_lines.append("")
            weekly_table = self._format_weekly_table(weekly_challenges)
            output_lines.append(weekly_table)
            output_lines.append("")

        # Challenge results
        if challenges:
            output_lines.append("## 💰 OVERALL SEASON CHALLENGES")
            output_lines.append("")
            challenge_table = self._format_challenge_table(challenges)
            output_lines.append(challenge_table)
            output_lines.append("")

            # Game data summary
            total_games = self._calculate_total_games(divisions)
            if total_games > 0:
                output_lines.append(f"📊 **Game data:** {total_games} individual results processed")
            else:
                output_lines.append("⚠️ **Game data:** Limited - some challenges may be incomplete")

        return "\n".join(output_lines)

    def _format_division_table(self, division: DivisionData) -> str:
        """Format a single division's standings table in Markdown."""
        sorted_teams = self._get_sorted_teams_by_division(division)

        # Table header
        lines = [
            "| Rank | Team | Owner | Points For | Points Against | Record |",
            "|------|------|-------|------------|----------------|--------|"
        ]

        # Table rows
        for i, team in enumerate(sorted_teams, 1):
            # Add asterisk to team name if in playoffs
            team_name = team.name
            if team.in_playoff_position:
                team_name = f"\\* {team.name}"

            lines.append(
                f"| {i} | {team_name} | {team.owner.full_name} | "
                f"{team.points_for:.2f} | {team.points_against:.2f} | "
                f"{team.wins}-{team.losses} |"
            )

        return "\n".join(lines)

    def _format_overall_table(self, divisions: Sequence[DivisionData]) -> str:
        """Format overall top teams table in Markdown."""
        top_teams = self._get_overall_top_teams(divisions, limit=20)

        # Table header
        lines = [
            "| Rank | Team | Owner | Division | Points For | Points Against | Record |",
            "|------|------|-------|----------|------------|----------------|--------|"
        ]

        # Table rows
        for i, team in enumerate(top_teams, 1):
            # Add asterisk to team name if in playoffs
            team_name = team.name
            if team.in_playoff_position:
                team_name = f"\\* {team.name}"

            lines.append(
                f"| {i} | {team_name} | {team.owner.full_name} | {team.division} | "
                f"{team.points_for:.2f} | {team.points_against:.2f} | "
                f"{team.wins}-{team.losses} |"
            )

        return "\n".join(lines)

    def _format_challenge_table(self, challenges: Sequence[ChallengeResult]) -> str:
        """Format challenge results table in Markdown."""
        # Table header
        lines = [
            "| Challenge | Winner | Owner | Division | Details |",
            "|-----------|--------|-------|----------|---------|"
        ]

        # Table rows
        for challenge in challenges:
            lines.append(
                f"| {challenge.challenge_name} | {challenge.winner} | "
                f"{challenge.owner.full_name} | {challenge.division} | "
                f"{challenge.description} |"
            )

        return "\n".join(lines)

    def _format_weekly_table(self, weekly_challenges: Sequence[WeeklyChallenge]) -> str:
        """Format weekly challenge results table in Markdown."""
        # Split into team and player challenges
        team_challenges = [c for c in weekly_challenges if "position" not in c.additional_info]
        player_challenges = [c for c in weekly_challenges if "position" in c.additional_info]

        lines: list[str] = []

        # Team challenges table
        if team_challenges:
            lines.append("**Team Challenges:**")
            lines.append("")
            lines.append("| Challenge | Team | Division | Value |")
            lines.append("|-----------|------|----------|-------|")

            for challenge in team_challenges:
                lines.append(
                    f"| {challenge.challenge_name} | {challenge.winner} | "
                    f"{challenge.division} | {challenge.value} |"
                )

            lines.append("")

        # Player highlights table
        if player_challenges:
            lines.append("**Player Highlights:**")
            lines.append("")
            lines.append("| Challenge | Player | Points |")
            lines.append("|-----------|--------|--------|")

            for challenge in player_challenges:
                # Include position in player display
                position = challenge.additional_info.get("position", "")
                winner_display = f"{challenge.winner} ({position})"

                lines.append(
                    f"| {challenge.challenge_name} | {winner_display} | {challenge.value} |"
                )

            lines.append("")

        return "\n".join(lines)
