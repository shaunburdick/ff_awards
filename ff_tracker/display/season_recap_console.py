"""
Console output formatter for Season Recap.

Provides formatted console output with tables for complete season summaries
including regular season, playoffs, and championship results.
"""

from __future__ import annotations

from tabulate import tabulate

from ..models.season_summary import SeasonSummary


class SeasonRecapConsoleFormatter:
    """Formatter for season recap console output with tables."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize season recap console formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        self.year = year
        self.format_args = format_args or {}

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for console formatter."""
        return {
            "note": "Optional notice displayed in box at top of output",
        }

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

    def format(self, summary: SeasonSummary) -> str:
        """
        Format complete season summary for console display.

        Args:
            summary: Complete season summary data

        Returns:
            Formatted console output string
        """
        # Get format arguments
        note = self._get_arg("note")

        output_lines: list[str] = []

        # Header
        output_lines.append("\n" + "=" * 80)
        output_lines.append(" " * 25 + f"🏆 {self.year} SEASON RECAP 🏆")
        output_lines.append("=" * 80)
        output_lines.append(f"📊 {summary.total_divisions} divisions")
        output_lines.append(
            f"📅 Regular Season: Weeks {summary.structure.regular_season_start}-{summary.structure.regular_season_end}"
        )
        if summary.playoffs:
            output_lines.append(
                f"🏈 Playoffs: Weeks {summary.structure.playoff_start}-{summary.structure.playoff_end}"
            )
        if summary.championship:
            output_lines.append(f"🏆 Championship: Week {summary.structure.championship_week}")

        # Optional note
        if note:
            note_content = f"⚠️  {note}"
            note_table = tabulate([[note_content]], tablefmt="fancy_grid")
            output_lines.append("")
            output_lines.append(note_table)

        # Championship Results (if complete)
        if summary.championship:
            output_lines.append("")
            output_lines.append("=" * 80)
            output_lines.append(
                " " * 22 + f"🏆 CHAMPIONSHIP WEEK {summary.structure.championship_week} 🏆"
            )
            output_lines.append(" " * 18 + "DIVISION WINNERS COMPETE FOR OVERALL TITLE")
            output_lines.append("=" * 80)
            championship_table = self._format_championship_leaderboard(summary.championship)
            output_lines.append(championship_table)

            # Champion announcement
            if summary.overall_champion:
                output_lines.append("")
                output_lines.append("🎉" * 40)
                output_lines.append(
                    f"🏆 SEASON CHAMPION: {summary.overall_champion.team_name} "
                    f"({summary.overall_champion.owner_name}) 🏆"
                )
                output_lines.append(f"   Final Score: {summary.overall_champion.score:.2f} points")
                output_lines.append("🎉" * 40)

        # Playoff Results (reverse chronological: Finals → Semifinals)
        if summary.playoffs:
            output_lines.append("")
            output_lines.append("=" * 80)
            output_lines.append(" " * 30 + "🏈 PLAYOFF RESULTS 🏈")
            output_lines.append("=" * 80)

            # Finals (show first - most recent)
            if summary.playoffs.finals:
                finals_output = self._format_playoff_round(summary.playoffs.finals)
                output_lines.append(finals_output)

            # Semifinals (show second - earlier round)
            if summary.playoffs.semifinals:
                semifinals_output = self._format_playoff_round(summary.playoffs.semifinals)
                output_lines.append(semifinals_output)

        # Regular Season Results
        output_lines.append("")
        output_lines.append("=" * 80)
        output_lines.append(" " * 22 + "📊 REGULAR SEASON FINAL RESULTS 📊")
        output_lines.append("=" * 80)

        # Regular Season Division Champions
        output_lines.append("")
        output_lines.append("🏆 REGULAR SEASON DIVISION CHAMPIONS")
        champions_table = self._format_division_champions(summary.regular_season.division_champions)
        output_lines.append(champions_table)

        # Season Challenges
        output_lines.append("")
        output_lines.append("💰 SEASON-LONG CHALLENGE WINNERS")
        challenges_table = self._format_season_challenges(summary.season_challenges)
        output_lines.append(challenges_table)

        # Final Standings by Division
        output_lines.append("")
        output_lines.append("📋 FINAL STANDINGS BY DIVISION")
        for division_data in summary.regular_season.final_standings:
            output_lines.append(f"\n{division_data.name}:")
            standings_table = self._format_division_standings(division_data)
            output_lines.append(standings_table)

        # Footer
        output_lines.append("")
        output_lines.append("=" * 80)
        output_lines.append(f"Report generated: {summary.generated_at}")
        output_lines.append("=" * 80)

        return "\n".join(output_lines)

    def _format_championship_leaderboard(self, championship) -> str:
        """
        Format championship leaderboard table.

        Args:
            championship: ChampionshipLeaderboard with ranked entries

        Returns:
            Formatted table string
        """
        headers = ["Rank", "Team", "Owner", "Division", "Score"]
        rows = []

        for entry in championship.entries:
            # Add trophy emoji for champion
            rank_display = f"🏆 {entry.rank}" if entry.is_champion else str(entry.rank)

            rows.append(
                [
                    rank_display,
                    entry.team_name,
                    entry.owner_name,
                    entry.division_name,
                    f"{entry.score:.2f}",
                ]
            )

        return tabulate(rows, headers=headers, tablefmt="grid")

    def _format_playoff_round(self, playoff_round) -> str:
        """
        Format a single playoff round across all divisions.

        Args:
            playoff_round: PlayoffRound with matchups

        Returns:
            Formatted playoff round string
        """
        output_parts: list[str] = []

        output_parts.append("")
        output_parts.append(f"🏈 {playoff_round.round_name.upper()} - Week {playoff_round.week}")
        output_parts.append("-" * 80)

        for bracket in playoff_round.division_brackets:
            output_parts.append("")
            output_parts.append(f"📍 {bracket.division_name}")

            # Build matchup table
            for idx, matchup in enumerate(bracket.matchups):
                matchup_output = self._format_playoff_matchup(matchup)
                output_parts.append(matchup_output)
                # Add blank line between matchups (but not after the last one)
                if idx < len(bracket.matchups) - 1:
                    output_parts.append("")

        return "\n".join(output_parts)

    def _format_playoff_matchup(self, matchup) -> str:
        """
        Format a single playoff matchup.

        Args:
            matchup: PlayoffMatchup data

        Returns:
            Formatted matchup string
        """
        # Determine if game is complete
        game_complete = matchup.winner_name is not None

        # Format team lines with winner indication
        team1_indicator = (
            "✅" if game_complete and matchup.winner_name == matchup.team1_name else "  "
        )
        team2_indicator = (
            "✅" if game_complete and matchup.winner_name == matchup.team2_name else "  "
        )

        score1 = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
        score2 = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"

        lines = [
            f"  {team1_indicator} (#{matchup.seed1}) {matchup.team1_name} - {score1}",
            f"  {team2_indicator} (#{matchup.seed2}) {matchup.team2_name} - {score2}",
        ]

        if game_complete:
            lines.append(f"     Winner: {matchup.winner_name}")

        return "\n".join(lines)

    def _format_division_champions(self, champions) -> str:
        """
        Format division champions table.

        Args:
            champions: Tuple of DivisionChampion objects

        Returns:
            Formatted table string
        """
        headers = ["Division", "Team", "Owner", "Record", "Points For"]
        rows = []

        for champion in champions:
            rows.append(
                [
                    champion.division_name,
                    champion.team_name,
                    champion.owner_name,
                    champion.record,
                    f"{champion.points_for:.2f}",
                ]
            )

        return tabulate(rows, headers=headers, tablefmt="grid")

    def _format_season_challenges(self, challenges) -> str:
        """
        Format season challenges table.

        Args:
            challenges: Tuple of ChallengeResult objects

        Returns:
            Formatted table string
        """
        headers = ["Challenge", "Winner", "Owner", "Division", "Value"]
        rows = []

        for challenge in challenges:
            rows.append(
                [
                    challenge.challenge_name,
                    challenge.winner,
                    challenge.owner.full_name,
                    challenge.division,
                    challenge.value,
                ]
            )

        return tabulate(rows, headers=headers, tablefmt="grid")

    def _format_division_standings(self, division_data) -> str:
        """
        Format standings table for a single division.

        Args:
            division_data: DivisionData with teams

        Returns:
            Formatted table string
        """
        headers = ["Rank", "Team", "Owner", "Record", "PF", "PA"]
        rows = []

        # Sort teams by record
        sorted_teams = sorted(
            division_data.teams,
            key=lambda t: (t.wins, -t.losses, t.points_for),
            reverse=True,
        )

        for rank, team in enumerate(sorted_teams, 1):
            rows.append(
                [
                    rank,
                    team.name,
                    team.owner.full_name,
                    f"{team.wins}-{team.losses}",
                    f"{team.points_for:.2f}",
                    f"{team.points_against:.2f}",
                ]
            )

        return tabulate(rows, headers=headers, tablefmt="simple")
