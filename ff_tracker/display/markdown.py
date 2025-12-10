"""
Markdown formatter for Fantasy Football Challenge Tracker.

Provides Markdown formatted output suitable for GitHub, Slack, Discord, or other platforms
that support Markdown rendering.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import ChallengeResult, ChampionshipLeaderboard, DivisionData, WeeklyChallenge
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
        current_week: int | None = None,
        championship: ChampionshipLeaderboard | None = None,
    ) -> str:
        """Format complete output for Markdown display."""
        # Get format arguments
        note = self._get_arg("note")
        include_toc = self._get_arg_bool("include_toc", False)

        # Detect playoff mode
        is_playoff_mode = any(d.is_playoff_mode for d in divisions)
        is_championship_week = championship is not None

        output_lines: list[str] = []

        # Header with playoff styling
        if is_championship_week:
            output_lines.append("# 🏆 CHAMPIONSHIP WEEK 🏆")
            output_lines.append("## HIGHEST SCORE WINS OVERALL!")
        elif is_playoff_mode:
            playoff_round = (
                divisions[0].playoff_bracket.round if divisions[0].playoff_bracket else "PLAYOFFS"
            )
            output_lines.append(f"# 🏈 {playoff_round.upper()} 🏈")
        else:
            total_divisions, total_teams = self._calculate_total_stats(divisions)
            output_lines.append(
                f"# 🏈 Fantasy Football Multi-Division Challenge Tracker ({self.year})"
            )
            output_lines.append("")
            output_lines.append(
                f"📊 **{total_divisions} divisions**, **{total_teams} teams total**"
            )

        if current_week is not None:
            output_lines.append(f"📅 **Current Week:** {current_week}")

        output_lines.append("")

        # Optional note
        if note:
            output_lines.append(f"> ⚠️ **{note}**")
            output_lines.append("")

        # Skip TOC in playoff mode for simplicity
        if include_toc and not is_playoff_mode:
            output_lines.append("## 📋 Table of Contents")
            output_lines.append("")
            for division in divisions:
                output_lines.append(
                    f"- [{division.name} Standings](#{division.name.lower().replace(' ', '-')}-standings)"
                )
            output_lines.append("- [Overall Top Teams](#-overall-top-teams-across-all-divisions)")
            if challenges:
                output_lines.append("- [Season Challenge Results](#-season-challenge-results)")
            if weekly_challenges and current_week:
                output_lines.append(
                    f"- [Week {current_week} Highlights](#-week-{current_week}-highlights)"
                )
            output_lines.append("")

        # PLAYOFF MODE: Championship leaderboard FIRST
        if is_championship_week and championship:
            championship_output = self._format_championship_leaderboard(championship)
            output_lines.append(championship_output)
            output_lines.append("")
            output_lines.append("---")
            output_lines.append("")

        # PLAYOFF MODE: Playoff brackets FIRST
        if is_playoff_mode and not is_championship_week:
            playoff_output = self._format_playoff_brackets(divisions)
            output_lines.append(playoff_output)
            output_lines.append("---")
            output_lines.append("")

        # Weekly challenges (filter for playoffs)
        if weekly_challenges and current_week:
            filtered_challenges = [c for c in weekly_challenges if "position" in c.additional_info]
            if filtered_challenges and (is_playoff_mode or is_championship_week):
                output_lines.append(f"# 🌟 WEEKLY PLAYER HIGHLIGHTS - WEEK {current_week} 🌟")
                output_lines.append("")
                player_table = self._format_weekly_player_table(filtered_challenges)
                output_lines.append(player_table)
                output_lines.append("")
                if is_championship_week:
                    output_lines.append(
                        "_Note: Player highlights include all players across all teams._"
                    )
                    output_lines.append("")
                output_lines.append("---")
                output_lines.append("")
            elif not is_playoff_mode:
                # Regular season: show all challenges
                output_lines.append(f"## 🔥 WEEK {current_week} HIGHLIGHTS")
                output_lines.append("")
                weekly_table = self._format_weekly_table(weekly_challenges)
                output_lines.append(weekly_table)
                output_lines.append("")

        # Season challenges (with historical note if in playoffs)
        if challenges:
            if is_playoff_mode:
                output_lines.append("# 📊 REGULAR SEASON FINAL RESULTS (Historical) 📊")
            else:
                output_lines.append("## 💰 OVERALL SEASON CHALLENGES")
            output_lines.append("")
            challenge_table = self._format_challenge_table(challenges)
            output_lines.append(challenge_table)
            output_lines.append("")
            if is_playoff_mode:
                output_lines.append("---")
                output_lines.append("")

        # Regular season standings (LAST in playoff mode, or skip in championship)
        if not is_championship_week:
            if is_playoff_mode:
                output_lines.append("## FINAL REGULAR SEASON STANDINGS")
                output_lines.append("")
            for division in divisions:
                output_lines.append(f"### {division.name}")
                output_lines.append("")
                division_table = self._format_division_table(division)
                output_lines.append(division_table)
                output_lines.append("")
                if not is_playoff_mode:
                    output_lines.append("_\\* = Currently in playoff position_")
                    output_lines.append("")

            # Overall top teams (only if not in playoffs)
            if not is_playoff_mode:
                output_lines.append("## 🌟 OVERALL TOP TEAMS (Across All Divisions)")
                output_lines.append("")
                overall_table = self._format_overall_table(divisions)
                output_lines.append(overall_table)
                output_lines.append("")
                output_lines.append("_\\* = Currently in playoff position_")
                output_lines.append("")

        # Game data summary (only in regular season)
        if challenges and not is_playoff_mode:
            total_games = self._calculate_total_games(divisions)
            if total_games > 0:
                output_lines.append(f"📊 **Game data:** {total_games} individual results processed")
            else:
                output_lines.append("⚠️ **Game data:** Limited - some challenges may be incomplete")

        return "\n".join(output_lines)

    def _format_playoff_brackets(self, divisions: Sequence[DivisionData]) -> str:
        """
        Format playoff brackets for all divisions in Markdown.

        Args:
            divisions: List of division data with playoff brackets

        Returns:
            Formatted playoff bracket string in Markdown tables
        """
        output_parts: list[str] = []

        for division in divisions:
            if not division.playoff_bracket:
                continue

            bracket = division.playoff_bracket
            output_parts.append(f"## {division.name} - {bracket.round}")
            output_parts.append("")
            output_parts.append("| Matchup | Team (Owner) | Seed | Score | Result |")
            output_parts.append("|---------|--------------|------|-------|--------|")

            for i, matchup in enumerate(bracket.matchups, 1):
                matchup_name = f"Semifinal {i}" if bracket.round == "Semifinals" else "Finals"

                # Team 1 row
                team1_result = "✓ Winner" if matchup.winner_name == matchup.team1_name else ""
                team1_score = (
                    f"{matchup.team1_score:.2f}" if matchup.team1_score is not None else "TBD"
                )
                output_parts.append(
                    f"| **{matchup_name}** | {matchup.team1_name} ({matchup.team1_owner}) | "
                    f"#{matchup.seed1} | {team1_score} | {team1_result} |"
                )

                # Team 2 row
                team2_result = "✓ Winner" if matchup.winner_name == matchup.team2_name else ""
                team2_score = (
                    f"{matchup.team2_score:.2f}" if matchup.team2_score is not None else "TBD"
                )
                output_parts.append(
                    f"|  | {matchup.team2_name} ({matchup.team2_owner}) | "
                    f"#{matchup.seed2} | {team2_score} | {team2_result} |"
                )

            output_parts.append("")

        return "\n".join(output_parts)

    def _format_championship_leaderboard(self, championship: ChampionshipLeaderboard) -> str:
        """
        Format championship week leaderboard in Markdown.

        Args:
            championship: Championship leaderboard with ranked entries

        Returns:
            Formatted championship leaderboard string
        """
        output_parts: list[str] = []

        output_parts.append("## CHAMPIONSHIP WEEK LEADERBOARD")
        output_parts.append("")
        output_parts.append("| Rank | Team (Owner) | Division Champion | Final Score |")
        output_parts.append("|------|--------------|-------------------|-------------|")

        for entry in championship.entries:
            # Add medal emoji for top 3
            if entry.rank == 1:
                rank_display = "🥇"
                team_display = f"**{entry.team_name} ({entry.owner_name})**"
                score_display = f"**{entry.score:.2f}**"
            elif entry.rank == 2:
                rank_display = "🥈"
                team_display = f"{entry.team_name} ({entry.owner_name})"
                score_display = f"{entry.score:.2f}"
            elif entry.rank == 3:
                rank_display = "🥉"
                team_display = f"{entry.team_name} ({entry.owner_name})"
                score_display = f"{entry.score:.2f}"
            else:
                rank_display = str(entry.rank)
                team_display = f"{entry.team_name} ({entry.owner_name})"
                score_display = f"{entry.score:.2f}"

            output_parts.append(
                f"| {rank_display} | {team_display} | {entry.division_name} | {score_display} |"
            )

        # Champion announcement
        champion = championship.champion
        output_parts.append("")
        output_parts.append(
            f"### 🎉 OVERALL CHAMPION: {champion.team_name} ({champion.owner_name}) - {champion.division_name} 🎉"
        )

        return "\n".join(output_parts)

    def _format_weekly_player_table(self, player_challenges: Sequence[WeeklyChallenge]) -> str:
        """
        Format player highlights table for playoffs in Markdown.

        Args:
            player_challenges: Player-only challenges

        Returns:
            Formatted player highlights table
        """
        lines: list[str] = []
        lines.append("| Challenge | Player (Position) | Team | Points |")
        lines.append("|-----------|-------------------|------|--------|")

        for challenge in player_challenges:
            position = challenge.additional_info.get("position", "")
            winner_display = f"{challenge.winner} ({position})"
            team_name = challenge.additional_info.get("team_name", challenge.division)

            lines.append(
                f"| {challenge.challenge_name} | {winner_display} | {team_name} | {challenge.value} |"
            )

        return "\n".join(lines)

    def _format_division_table(self, division: DivisionData) -> str:
        """Format a single division's standings table in Markdown."""
        sorted_teams = self._get_sorted_teams_by_division(division)

        # Table header
        lines = [
            "| Rank | Team | Owner | Points For | Points Against | Record |",
            "|------|------|-------|------------|----------------|--------|",
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
            "|------|------|-------|----------|------------|----------------|--------|",
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
            "|-----------|--------|-------|----------|---------|",
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
