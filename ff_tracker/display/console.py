"""
Console output formatter for Fantasy Football Challenge Tracker.

Provides formatted console output with tables and color coding.
"""

from __future__ import annotations

from collections.abc import Sequence

from tabulate import tabulate

from ..models import ChallengeResult, ChampionshipLeaderboard, DivisionData, WeeklyChallenge
from .base import BaseFormatter


class ConsoleFormatter(BaseFormatter):
    """Formatter for rich console output with tables."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize console formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        super().__init__(year, format_args)

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for console formatter."""
        return {
            "note": "Optional notice displayed in box at top of output",
        }

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None,
        championship: ChampionshipLeaderboard | None = None,
        championship_rosters: Sequence | None = None,
    ) -> str:
        """Format complete output for console display."""
        # Get format arguments
        note = self._get_arg("note")

        # Detect playoff mode
        is_playoff_mode = any(d.is_playoff_mode for d in divisions)
        is_championship_week = championship is not None

        output_lines: list[str] = []

        # Header with special playoff/championship styling
        total_divisions, total_teams = self._calculate_total_stats(divisions)
        if is_championship_week:
            output_lines.append("\n" + "=" * 80)
            output_lines.append(" " * 22 + "🏆 CHAMPIONSHIP WEEK 🏆")
            output_lines.append(" " * 18 + "HIGHEST SCORE WINS OVERALL!")
            output_lines.append("=" * 80)
        elif is_playoff_mode:
            playoff_round = (
                divisions[0].playoff_bracket.round if divisions[0].playoff_bracket else "PLAYOFFS"
            )
            output_lines.append("\n" + "=" * 80)
            output_lines.append(
                " " * (40 - len(playoff_round) // 2) + f"🏈 {playoff_round.upper()} 🏈"
            )
            output_lines.append("=" * 80)
        else:
            output_lines.append(
                f"\n🏈 Fantasy Football Multi-Division Challenge Tracker ({self.year})"
            )
            output_lines.append(f"📊 {total_divisions} divisions, {total_teams} teams total")

        if current_week is not None:
            output_lines.append(f"📅 Current Week: {current_week}")
            # Machine-readable output for scripts
            output_lines.append(f"CURRENT_WEEK={current_week}")

        # Optional note
        if note:
            note_content = f"⚠️  {note}"
            note_table = tabulate([[note_content]], tablefmt="fancy_grid")
            output_lines.append("")
            output_lines.append(note_table)

        # PLAYOFF MODE: Championship Week comes FIRST
        if is_championship_week and championship:
            championship_output = self._format_championship_leaderboard(
                championship, championship_rosters
            )
            output_lines.append("")
            output_lines.append(championship_output)

        # PLAYOFF MODE: Playoff brackets come FIRST (if not championship week)
        if is_playoff_mode and not is_championship_week:
            playoff_output = self._format_playoff_brackets(divisions)
            output_lines.append("")
            output_lines.append(playoff_output)

        # Weekly challenges (filter for playoffs)
        if weekly_challenges and current_week:
            # Filter challenges based on mode
            filtered_challenges = self._filter_playoff_challenges(
                weekly_challenges, is_playoff_mode, is_championship_week
            )
            if filtered_challenges:
                output_lines.append("")
                output_lines.append("=" * 80)
                output_lines.append(
                    " " * 22 + f"🌟 WEEKLY PLAYER HIGHLIGHTS - WEEK {current_week} 🌟"
                )
                output_lines.append("=" * 80)
                weekly_table = self._format_weekly_player_table(filtered_challenges)
                output_lines.append(weekly_table)
                if is_championship_week:
                    output_lines.append("")
                    output_lines.append(
                        "Note: Player highlights include all players across all teams."
                    )

        # Season challenges (with historical note if in playoffs)
        if challenges:
            output_lines.append("")
            output_lines.append("=" * 80)
            if is_playoff_mode:
                output_lines.append(" " * 15 + "📊 REGULAR SEASON FINAL RESULTS (Historical) 📊")
            else:
                output_lines.append(" " * 26 + "💰 SEASON-LONG CHALLENGES")
            output_lines.append("=" * 80)
            challenge_table = self._format_challenge_table(challenges)
            output_lines.append(challenge_table)

        # Regular season standings (LAST in playoff mode, or skip in championship)
        if not is_championship_week:
            if is_playoff_mode:
                output_lines.append("")
                output_lines.append("=" * 80)
                output_lines.append(" " * 20 + "📊 FINAL REGULAR SEASON STANDINGS")
                output_lines.append("=" * 80)
            for division in divisions:
                output_lines.append(f"\n{division.name}:")
                division_table = self._format_division_table(division)
                output_lines.append(division_table)
                if not is_playoff_mode:
                    output_lines.append("  * = Currently in playoff position")

            # Overall top teams (only if not in playoffs)
            if not is_playoff_mode:
                output_lines.append("\n🌟 OVERALL TOP TEAMS (Across All Divisions)")
                overall_table = self._format_overall_table(divisions)
                output_lines.append(overall_table)
                output_lines.append("  * = Currently in playoff position")

        # Game data summary (only in regular season)
        if challenges and not is_playoff_mode:
            total_games = self._calculate_total_games(divisions)
            if total_games > 0:
                output_lines.append(f"\n📊 Game data: {total_games} individual results processed")
            else:
                output_lines.append("\n⚠️  Game data: Limited - some challenges may be incomplete")

        return "\n".join(output_lines)

    def _format_playoff_brackets(self, divisions: Sequence[DivisionData]) -> str:
        """
        Format playoff brackets for all divisions.

        Args:
            divisions: List of division data with playoff brackets

        Returns:
            Formatted playoff bracket string with tables
        """
        output_parts: list[str] = []

        for division in divisions:
            if not division.playoff_bracket:
                continue

            bracket = division.playoff_bracket
            output_parts.append("╔" + "═" * 78 + "╗")
            header_text = f"{division.name} - {bracket.round}".upper()
            padding = (78 - len(header_text)) // 2
            output_parts.append(
                "║" + " " * padding + header_text + " " * (78 - padding - len(header_text)) + "║"
            )
            output_parts.append("╚" + "═" * 78 + "╝")
            output_parts.append("")

            # Build matchup table
            bracket_table: list[list[str]] = []
            for i, matchup in enumerate(bracket.matchups, 1):
                matchup_name = f"Semifinal {i}" if bracket.round == "Semifinals" else "Finals"

                # Team 1 row
                team1_result = "✓" if matchup.winner_name == matchup.team1_name else ""
                bracket_table.append(
                    [
                        matchup_name,
                        f"{matchup.team1_name} ({matchup.owner1_name})",
                        f"#{matchup.seed1}",
                        f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD",
                        team1_result,
                    ]
                )

                # Team 2 row
                team2_result = "✓" if matchup.winner_name == matchup.team2_name else ""
                bracket_table.append(
                    [
                        "",  # Empty matchup cell for second team
                        f"{matchup.team2_name} ({matchup.owner2_name})",
                        f"#{matchup.seed2}",
                        f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD",
                        team2_result,
                    ]
                )

            output_parts.append(
                tabulate(
                    bracket_table,
                    headers=["Matchup", "Team (Owner)", "Seed", "Score", "Result"],
                    tablefmt="fancy_grid",
                )
            )
            output_parts.append("")

        return "\n".join(output_parts)

    def _format_championship_leaderboard(
        self, championship: ChampionshipLeaderboard, rosters: Sequence | None = None
    ) -> str:
        """
        Format championship week leaderboard.

        Args:
            championship: Championship leaderboard with ranked entries
            rosters: Detailed rosters to check game completion status

        Returns:
            Formatted championship leaderboard string
        """
        output_parts: list[str] = []

        # Header section
        output_parts.append("╔" + "═" * 78 + "╗")
        header_text = "CHAMPIONSHIP WEEK LEADERBOARD"
        padding = (78 - len(header_text)) // 2
        output_parts.append(
            "║" + " " * padding + header_text + " " * (78 - padding - len(header_text)) + "║"
        )
        output_parts.append("╚" + "═" * 78 + "╝")
        output_parts.append("")

        # Build leaderboard table
        leaderboard_table: list[list[str]] = []
        for entry in championship.entries:
            # Add medal emoji for top 3
            if entry.rank == 1:
                rank_display = "🥇"
            elif entry.rank == 2:
                rank_display = "🥈"
            elif entry.rank == 3:
                rank_display = "🥉"
            else:
                rank_display = str(entry.rank)

            leaderboard_table.append(
                [
                    rank_display,
                    f"{entry.team_name} ({entry.owner_name})",
                    entry.division_name,
                    f"{entry.score:.2f}",
                ]
            )

        output_parts.append(
            tabulate(
                leaderboard_table,
                headers=["Rank", "Team (Owner)", "Division Champion", "Final Score"],
                tablefmt="fancy_grid",
            )
        )

        # Champion announcement (conditional based on game completion)
        champion = championship.champion
        output_parts.append("")

        # Check if all games are complete
        all_games_final = self._check_all_games_final(rosters) if rosters else False

        if all_games_final:
            output_parts.append(
                f"🎉 OVERALL CHAMPION: {champion.team_name} ({champion.owner_name}) - {champion.division_name} 🎉"
            )
        else:
            output_parts.append(
                f"🏆 CURRENT LEADER: {champion.team_name} ({champion.owner_name}) - {champion.division_name}"
            )
            output_parts.append(
                "⏳ Games still in progress - final champion will be determined when all games complete"
            )

        return "\n".join(output_parts)

    def _filter_playoff_challenges(
        self,
        weekly_challenges: Sequence[WeeklyChallenge],
        is_playoff_mode: bool,
        is_championship_week: bool,
    ) -> list[WeeklyChallenge]:
        """
        Filter weekly challenges based on playoff mode.

        During Semifinals/Finals, only player highlights are shown (7 challenges).
        During Championship Week or regular season, all challenges are shown (13).

        Args:
            weekly_challenges: All weekly challenges
            is_playoff_mode: True if in playoff mode
            is_championship_week: True if Championship Week

        Returns:
            Filtered list of challenges to display
        """
        # Championship week: show all challenges (all teams play)
        if is_championship_week:
            # Filter to only player challenges
            return [c for c in weekly_challenges if "position" in c.additional_info]

        # Semifinals/Finals: show only player highlights (only 4-6 teams playing)
        if is_playoff_mode:
            # Filter to only player challenges
            return [c for c in weekly_challenges if "position" in c.additional_info]

        # Regular season: show all challenges
        return list(weekly_challenges)

    def _format_weekly_player_table(self, player_challenges: Sequence[WeeklyChallenge]) -> str:
        """
        Format player highlights table for playoffs.

        Args:
            player_challenges: Player-only challenges

        Returns:
            Formatted player highlights table
        """
        player_table: list[list[str]] = []
        for challenge in player_challenges:
            # Show player name with position
            position = challenge.additional_info.get("position", "")
            winner_display = f"{challenge.winner} ({position})"
            team_name = challenge.additional_info.get("team_name", "")

            player_table.append(
                [
                    challenge.challenge_name,
                    self._truncate_text(winner_display, 30),
                    self._truncate_text(team_name, 15),
                    challenge.value,
                ]
            )

        return tabulate(
            player_table,
            headers=["Challenge", "Player (Position)", "Team", "Points"],
            tablefmt="fancy_grid",
        )

    def _format_division_table(self, division: DivisionData) -> str:
        """Format a single division's standings table."""
        sorted_teams = self._get_sorted_teams_by_division(division)

        division_table: list[list[str]] = []
        for i, team in enumerate(sorted_teams, 1):
            # Add asterisk to beginning of team name if in playoffs
            team_name = team.name
            if team.in_playoff_position:
                team_name = f"* {team.name}"
            division_table.append(
                [
                    str(i),
                    self._truncate_text(team_name, 25),
                    self._truncate_text(team.owner.full_name, 20),
                    f"{team.points_for:.2f}",
                    f"{team.points_against:.2f}",
                    f"{team.wins}-{team.losses}",
                ]
            )

        return tabulate(
            division_table,
            headers=["Rank", "Team", "Owner", "Points For", "Points Against", "Record"],
            tablefmt="grid",
        )

    def _format_overall_table(self, divisions: Sequence[DivisionData]) -> str:
        """Format the overall top teams table."""
        top_teams = self._get_overall_top_teams(divisions, limit=20)

        overall_table: list[list[str]] = []
        for i, team in enumerate(top_teams, 1):
            # Add asterisk to beginning of team name if in playoffs
            team_name = team.name
            if team.in_playoff_position:
                team_name = f"* {team.name}"

            overall_table.append(
                [
                    str(i),
                    self._truncate_text(team_name, 20),
                    self._truncate_text(team.owner.full_name, 15),
                    self._truncate_text(team.division, 15),
                    f"{team.points_for:.2f}",
                    f"{team.points_against:.2f}",
                    f"{team.wins}-{team.losses}",
                ]
            )

        return tabulate(
            overall_table,
            headers=["Rank", "Team", "Owner", "Division", "Points For", "Points Against", "Record"],
            tablefmt="grid",
        )

    def _format_challenge_table(self, challenges: Sequence[ChallengeResult]) -> str:
        """Format the challenges results table."""
        challenge_table: list[list[str]] = []

        for challenge in challenges:
            challenge_table.append(
                [
                    challenge.challenge_name,
                    self._truncate_text(challenge.winner, 25),
                    self._truncate_text(challenge.owner.full_name, 20),
                    self._truncate_text(challenge.division, 15),
                    self._truncate_text(challenge.description, 35),
                ]
            )

        return tabulate(
            challenge_table,
            headers=["Challenge", "Winner", "Owner", "Division", "Details"],
            tablefmt="grid",
        )

    def _format_weekly_table(self, weekly_challenges: Sequence[WeeklyChallenge]) -> str:
        """Format the weekly challenges results table."""
        # Split into team and player challenges
        team_challenges = [c for c in weekly_challenges if "position" not in c.additional_info]
        player_challenges = [c for c in weekly_challenges if "position" in c.additional_info]

        output_parts: list[str] = []

        # Team challenges table
        if team_challenges:
            team_table: list[list[str]] = []
            for challenge in team_challenges:
                team_table.append(
                    [
                        challenge.challenge_name,
                        self._truncate_text(challenge.winner, 30),
                        self._truncate_text(challenge.division, 15),
                        challenge.value,
                    ]
                )

            output_parts.append("Team Challenges:")
            output_parts.append(
                tabulate(
                    team_table, headers=["Challenge", "Team", "Division", "Value"], tablefmt="grid"
                )
            )

        # Player challenges table
        if player_challenges:
            player_table: list[list[str]] = []
            for challenge in player_challenges:
                # Show player name with position
                position = challenge.additional_info.get("position", "")
                winner_display = f"{challenge.winner} ({position})"

                player_table.append(
                    [
                        challenge.challenge_name,
                        self._truncate_text(winner_display, 30),
                        challenge.value,
                    ]
                )

            if output_parts:
                output_parts.append("")  # Blank line between tables
            output_parts.append("Player Highlights:")
            output_parts.append(
                tabulate(player_table, headers=["Challenge", "Player", "Points"], tablefmt="grid")
            )

        return "\n".join(output_parts)
