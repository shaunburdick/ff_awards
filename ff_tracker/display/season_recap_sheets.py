"""
Sheets (TSV) output formatter for Season Recap.

Provides tab-separated values format suitable for Google Sheets import,
optimized for spreadsheet analysis and record-keeping.
"""

from __future__ import annotations

from ..models.season_summary import SeasonSummary


class SeasonRecapSheetsFormatter:
    """Formatter for season recap TSV output."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize season recap sheets formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        self.year = year
        self.format_args = format_args or {}

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for sheets formatter."""
        return {
            "note": "Optional notice included as first row",
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
        Format complete season summary as TSV.

        Args:
            summary: Complete season summary data

        Returns:
            TSV string suitable for Google Sheets
        """
        # Get format arguments
        note = self._get_arg("note")

        lines: list[str] = []

        # Optional note row
        if note:
            lines.append(f"NOTE:\t{note}")
            lines.append("")  # Blank line

        # Header section
        lines.append(f"SEASON RECAP\t{self.year}")
        lines.append(f"Divisions\t{summary.total_divisions}")
        lines.append(
            f"Regular Season\tWeeks {summary.structure.regular_season_start}-{summary.structure.regular_season_end}"
        )
        if summary.playoffs:
            lines.append(
                f"Playoffs\tWeeks {summary.structure.playoff_start}-{summary.structure.playoff_end}"
            )
        if summary.championship:
            lines.append(f"Championship\tWeek {summary.structure.championship_week}")
        lines.append("")  # Blank line

        # Championship results (if available)
        if summary.championship:
            lines.append(f"CHAMPIONSHIP WEEK {summary.structure.championship_week}")
            lines.append("Rank\tTeam\tOwner\tDivision\tScore")
            for entry in summary.championship.entries:
                champion_marker = "🏆 " if entry.rank == 1 else ""
                lines.append(
                    f"{entry.rank}\t{champion_marker}{entry.team_name}\t{entry.owner_name}\t"
                    f"{entry.division_name}\t{entry.score:.2f}"
                )
            lines.append("")  # Blank line

        # Playoff results (reverse chronological: Finals → Semifinals)
        if summary.playoffs:
            # Finals (show first - most recent)
            if summary.playoffs.finals:
                lines.append(f"FINALS\tWeek {summary.playoffs.finals.week}")
                for bracket in summary.playoffs.finals.division_brackets:
                    lines.append(f"Division\t{bracket.division_name}")
                    for matchup in bracket.matchups:
                        winner_marker1 = "✓" if matchup.winner_name == matchup.team1_name else ""
                        winner_marker2 = "✓" if matchup.winner_name == matchup.team2_name else ""
                        score1 = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
                        score2 = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"
                        lines.append(
                            f"#{matchup.seed1} {winner_marker1}\t{matchup.team1_name}\t{matchup.owner1_name}\t{score1}"
                        )
                        lines.append(
                            f"#{matchup.seed2} {winner_marker2}\t{matchup.team2_name}\t{matchup.owner2_name}\t{score2}"
                        )
                        lines.append("")  # Blank line between matchups
                lines.append("")  # Blank line

            # Semifinals (show second - earlier round)
            if summary.playoffs.semifinals:
                lines.append(f"SEMIFINALS\tWeek {summary.playoffs.semifinals.week}")
                for bracket in summary.playoffs.semifinals.division_brackets:
                    lines.append(f"Division\t{bracket.division_name}")
                    for matchup in bracket.matchups:
                        winner_marker1 = "✓" if matchup.winner_name == matchup.team1_name else ""
                        winner_marker2 = "✓" if matchup.winner_name == matchup.team2_name else ""
                        score1 = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
                        score2 = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"
                        lines.append(
                            f"#{matchup.seed1} {winner_marker1}\t{matchup.team1_name}\t{matchup.owner1_name}\t{score1}"
                        )
                        lines.append(
                            f"#{matchup.seed2} {winner_marker2}\t{matchup.team2_name}\t{matchup.owner2_name}\t{score2}"
                        )
                        lines.append("")  # Blank line between matchups
                lines.append("")  # Blank line

        # Regular season results
        lines.append("REGULAR SEASON RESULTS")
        lines.append("")  # Blank line

        # Regular Season Division Champions
        lines.append("REGULAR SEASON DIVISION CHAMPIONS")
        lines.append("Division\tTeam\tOwner\tRecord\tPoints For")
        for champion in summary.regular_season.division_champions:
            record = f"{champion.wins}-{champion.losses}"
            lines.append(
                f"{champion.division_name}\t{champion.team_name}\t{champion.owner_name}\t"
                f"{record}\t{champion.points_for:.2f}"
            )
        lines.append("")  # Blank line

        # Season challenges
        lines.append("SEASON-LONG CHALLENGES")
        lines.append("Challenge\tWinner\tDivision\tValue")
        for challenge in summary.season_challenges:
            lines.append(
                f"{challenge.challenge_name}\t{challenge.winner}\t{challenge.division}\t{challenge.value}"
            )
        lines.append("")  # Blank line

        # Final standings by division
        lines.append("FINAL STANDINGS")
        for division_data in summary.regular_season.final_standings:
            lines.append(f"Division\t{division_data.name}")
            lines.append("Rank\tTeam\tOwner\tRecord\tPoints For\tPoints Against")

            # Sort teams
            sorted_teams = sorted(
                division_data.teams, key=lambda t: (t.wins, t.points_for), reverse=True
            )

            for rank, team in enumerate(sorted_teams, start=1):
                record = f"{team.wins}-{team.losses}"
                owner_name = f"{team.owner.first_name} {team.owner.last_name}"
                lines.append(
                    f"{rank}\t{team.name}\t{owner_name}\t{record}\t"
                    f"{team.points_for:.2f}\t{team.points_against:.2f}"
                )
            lines.append("")  # Blank line

        return "\n".join(lines)
