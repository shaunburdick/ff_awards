"""
Google Sheets TSV formatter for Fantasy Football Challenge Tracker.

Provides tab-separated values output suitable for copying into Google Sheets.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import ChallengeResult, ChampionshipLeaderboard, DivisionData, WeeklyChallenge
from ..models.championship import ChampionshipRoster
from .base import BaseFormatter


class SheetsFormatter(BaseFormatter):
    """Formatter for Google Sheets compatible TSV output."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize sheets formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        super().__init__(year, format_args)

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for sheets formatter."""
        return {
            "note": "Optional note displayed as first row in TSV output",
        }

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None,
        championship: ChampionshipLeaderboard | None = None,
        championship_rosters: Sequence[ChampionshipRoster] | None = None,
    ) -> str:
        """Format complete output for Google Sheets TSV."""
        output_lines: list[str] = []

        # Get format arguments
        note = self._get_arg("note")

        # Detect playoff mode
        is_playoff_mode = any(d.is_playoff_mode for d in divisions)
        is_championship_week = championship is not None

        # Optional note (first row if present)
        if note:
            output_lines.append(f"📢 NOTE: {note}")
            output_lines.append("")

        # Header
        total_divisions, total_teams = self._calculate_total_stats(divisions)
        output_lines.append(f"Fantasy Football Multi-Division Challenge Tracker ({self.year})")
        output_lines.append(f"{total_divisions} divisions, {total_teams} teams total")

        if current_week is not None:
            output_lines.append(f"Current Week: {current_week}")

        output_lines.append("")

        # Championship leaderboard (first, if championship week)
        if is_championship_week and championship:
            output_lines.extend(
                self._format_championship_leaderboard(championship, championship_rosters)
            )
            output_lines.append("")
            # Add detailed rosters if available
            if championship_rosters:
                output_lines.extend(self._format_championship_rosters(championship_rosters))
                output_lines.append("")

        # Playoff brackets (first, if Semifinals/Finals)
        if is_playoff_mode and not is_championship_week:
            output_lines.extend(self._format_playoff_brackets(divisions))
            output_lines.append("")

        # Weekly player highlights (playoffs only show player challenges)
        if weekly_challenges and current_week:
            if is_playoff_mode or is_championship_week:
                # Filter to player challenges only
                player_challenges = [
                    c for c in weekly_challenges if "position" in c.additional_info
                ]
                if player_challenges:
                    output_lines.extend(
                        self._format_weekly_player_table(player_challenges, current_week)
                    )
                    output_lines.append("")
            else:
                # Regular season: show both team and player challenges
                team_challenges = [
                    c for c in weekly_challenges if "position" not in c.additional_info
                ]
                player_challenges = [
                    c for c in weekly_challenges if "position" in c.additional_info
                ]

                output_lines.append(f"WEEK {current_week} HIGHLIGHTS")
                output_lines.append("")

                # Team challenges
                if team_challenges:
                    output_lines.append("Team Challenges")
                    output_lines.append("Challenge\tTeam\tDivision\tValue")

                    for challenge in team_challenges:
                        output_lines.append(
                            f"{challenge.challenge_name}\t{challenge.winner}\t{challenge.division}\t"
                            f"{challenge.value}"
                        )

                    output_lines.append("")

                # Player highlights
                if player_challenges:
                    output_lines.append("Player Highlights")
                    output_lines.append("Challenge\tPlayer\tPoints")

                    for challenge in player_challenges:
                        # Include position in player display
                        position = challenge.additional_info.get("position", "")
                        winner_display = f"{challenge.winner} ({position})"

                        output_lines.append(
                            f"{challenge.challenge_name}\t{winner_display}\t{challenge.value}"
                        )

                    output_lines.append("")

                output_lines.append("")

        # Season challenges with historical note in playoff mode
        if challenges:
            if is_playoff_mode:
                output_lines.append(
                    "OVERALL SEASON CHALLENGES (Regular season - finalized at end of week 14)"
                )
            else:
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

            output_lines.append("")

        # Final standings (last in playoff mode, labeled as historical)
        if is_playoff_mode:
            output_lines.append("FINAL REGULAR SEASON STANDINGS (Week 14)")
        else:
            output_lines.append("DIVISION STANDINGS")
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
        if is_playoff_mode:
            output_lines.append("OVERALL TOP TEAMS (Final Regular Season - Week 14)")
        else:
            output_lines.append("OVERALL TOP TEAMS (Across All Divisions)")
        output_lines.append(
            "Rank\tTeam\tOwner\tDivision\tPoints For\tPoints Against\tRecord\tPlayoffs"
        )

        top_teams = self._get_overall_top_teams(divisions, limit=20)
        for i, team in enumerate(top_teams, 1):
            playoff_indicator = "Y" if team.in_playoff_position else "N"
            output_lines.append(
                f"{i}\t{team.name}\t{team.owner.full_name}\t{team.division}\t{team.points_for:.1f}\t"
                f"{team.points_against:.1f}\t{team.wins}-{team.losses}\t{playoff_indicator}"
            )

        return "\n".join(output_lines)

    def _format_playoff_brackets(self, divisions: Sequence[DivisionData]) -> list[str]:
        """Format playoff bracket matchups as TSV lines."""
        lines: list[str] = []

        playoff_divisions = [d for d in divisions if d.playoff_bracket]
        if not playoff_divisions:
            return lines

        bracket_round = (
            playoff_divisions[0].playoff_bracket.round
            if playoff_divisions[0].playoff_bracket
            else "Unknown"
        )

        lines.append(f"PLAYOFF BRACKET - {bracket_round.upper()}")
        lines.append("")

        for div in playoff_divisions:
            if not div.playoff_bracket:
                continue

            lines.append(f"{div.name} - {bracket_round}")
            lines.append("Matchup\tSeed\tTeam\tOwner\tScore\tResult")

            for i, matchup in enumerate(div.playoff_bracket.matchups, 1):
                matchup_label = f"Semifinal {i}" if bracket_round == "Semifinals" else "Finals"

                # Team 1
                result1 = "WINNER" if matchup.winner_seed == matchup.seed1 else "---"
                score1_display = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
                lines.append(
                    f"{matchup_label}\t{matchup.seed1}\t{matchup.team1_name}\t"
                    f"{matchup.owner1_name}\t{score1_display}\t{result1}"
                )

                # Team 2
                result2 = "WINNER" if matchup.winner_seed == matchup.seed2 else "---"
                score2_display = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"
                lines.append(
                    f"{matchup_label}\t{matchup.seed2}\t{matchup.team2_name}\t"
                    f"{matchup.owner2_name}\t{score2_display}\t{result2}"
                )

                lines.append("")

        return lines

    def _format_championship_leaderboard(
        self, championship: ChampionshipLeaderboard, rosters: Sequence | None = None
    ) -> list[str]:
        """Format championship leaderboard as TSV lines."""
        lines: list[str] = []

        lines.append("CHAMPIONSHIP WEEK - FINAL LEADERBOARD")
        lines.append("Highest score wins overall championship")
        lines.append("")

        lines.append("Rank\tMedal\tTeam\tOwner\tDivision\tScore")

        for entry in championship.entries:
            medal = ""
            if entry.rank == 1:
                medal = "🥇"
            elif entry.rank == 2:
                medal = "🥈"
            elif entry.rank == 3:
                medal = "🥉"

            lines.append(
                f"{entry.rank}\t{medal}\t{entry.team_name}\t{entry.owner_name}\t"
                f"{entry.division_name}\t{entry.score:.2f}"
            )

        lines.append("")

        # Champion announcement (conditional based on game completion)
        champion = championship.champion

        # Check if all games are complete
        all_games_final = self._check_all_games_final(rosters) if rosters else False

        if all_games_final:
            lines.append("🏆 OVERALL CHAMPION 🏆")
            lines.append(f"{champion.team_name} ({champion.owner_name})")
            lines.append(f"{champion.division_name} Champion - {champion.score:.2f} points")
        else:
            lines.append("🏆 CURRENT LEADER")
            lines.append(f"{champion.team_name} ({champion.owner_name})")
            lines.append(f"{champion.division_name} - {champion.score:.2f} points")
            lines.append("⏳ Games still in progress")

        return lines

    def _format_championship_rosters(self, rosters: Sequence) -> list[str]:
        """Format championship rosters as TSV."""
        lines: list[str] = []

        lines.append("DETAILED ROSTERS")
        lines.append("")

        for roster in rosters:
            lines.append(
                f"{roster.team.team_name} ({roster.team.owner_name}) - {roster.team.division_name}"
            )
            lines.append(
                f"Score: {roster.total_score:.2f} pts | Projected: {roster.projected_score:.2f} pts"
            )
            lines.append("")

            # Starters table
            lines.append("STARTERS")
            lines.append("Status\tPos\tPlayer\tTeam\tPoints")

            for slot in roster.starters:
                status_icon = "✅" if slot.game_status == "final" else "⏳"
                player_display = slot.player_name or "EMPTY"
                team_display = slot.player_team or ""

                lines.append(
                    f"{status_icon}\t{slot.position}\t{player_display}\t{team_display}\t{slot.actual_points:.2f}"
                )

            lines.append("")

        return lines

    def _format_weekly_player_table(
        self, player_challenges: Sequence[WeeklyChallenge], current_week: int
    ) -> list[str]:
        """Format weekly player highlights table."""
        lines: list[str] = []

        lines.append(f"WEEK {current_week} PLAYER HIGHLIGHTS")
        lines.append("Challenge\tPlayer\tPoints")

        for challenge in player_challenges:
            # Include position in player display
            position = challenge.additional_info.get("position", "")
            winner_display = f"{challenge.winner} ({position})"

            lines.append(f"{challenge.challenge_name}\t{winner_display}\t{challenge.value}")

        return lines
