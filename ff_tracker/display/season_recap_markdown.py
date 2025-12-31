"""
Markdown output formatter for Season Recap.

Provides formatted Markdown output suitable for GitHub, Slack, Discord,
and other platforms supporting Markdown rendering.
"""

from __future__ import annotations

from ..models.season_summary import SeasonSummary


class SeasonRecapMarkdownFormatter:
    """Formatter for season recap Markdown output."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize season recap markdown formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        self.year = year
        self.format_args = format_args or {}

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for markdown formatter."""
        return {
            "include_toc": "Include table of contents (default: false)",
            "note": "Optional notice displayed as blockquote at top",
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

    def format(self, summary: SeasonSummary) -> str:
        """
        Format complete season summary as Markdown.

        Args:
            summary: Complete season summary data

        Returns:
            Markdown formatted string
        """
        # Get format arguments
        include_toc = self._get_arg_bool("include_toc", default=False)
        note = self._get_arg("note")

        lines: list[str] = []

        # Title
        lines.append(f"# 🏆 {self.year} Season Recap")
        lines.append("")

        # Optional note
        if note:
            lines.append(f"> ⚠️ **{note}**")
            lines.append("")

        # Season info
        lines.append(f"**Divisions:** {summary.total_divisions}")
        lines.append(
            f"**Regular Season:** Weeks {summary.structure.regular_season_start}-{summary.structure.regular_season_end}"
        )
        if summary.playoffs:
            lines.append(
                f"**Playoffs:** Weeks {summary.structure.playoff_start}-{summary.structure.playoff_end}"
            )
        if summary.championship:
            lines.append(f"**Championship:** Week {summary.structure.championship_week}")
        lines.append("")

        # Table of Contents (optional)
        if include_toc:
            lines.append("## Table of Contents")
            lines.append("")
            if summary.championship:
                lines.append("- [Championship Week](#championship-week)")
            if summary.playoffs:
                lines.append("- [Playoff Results](#playoff-results)")
            lines.append("- [Regular Season Results](#regular-season-results)")
            lines.append(
                "  - [Regular Season Division Champions](#regular-season-division-champions)"
            )
            lines.append("  - [Season-Long Challenges](#season-long-challenges)")
            lines.append("  - [Final Standings](#final-standings)")
            lines.append("")

        # Championship results (if available)
        if summary.championship:
            lines.append("## Championship Week")
            lines.append("")
            lines.append(
                f"**Week {summary.structure.championship_week} - Division Winners Compete for Overall Title**"
            )
            lines.append("")
            lines.append("| Rank | Team | Owner | Division | Score |")
            lines.append("|------|------|-------|----------|-------|")
            for entry in summary.championship.entries:
                champion_marker = "🏆 " if entry.rank == 1 else ""
                lines.append(
                    f"| {entry.rank} | {champion_marker}{entry.team_name} | {entry.owner_name} | "
                    f"{entry.division_name} | {entry.score:.2f} |"
                )
            lines.append("")

            if summary.overall_champion:
                lines.append(f"### 🎉 Season Champion: {summary.overall_champion.team_name}")
                lines.append("")
                lines.append(
                    f"**{summary.overall_champion.owner_name}** from **{summary.overall_champion.division_name}** "
                    f"won with **{summary.overall_champion.score:.2f} points**!"
                )
                lines.append("")

        # Playoff results
        if summary.playoffs:
            lines.append("## Playoff Results")
            lines.append("")

            # Finals (show first - most recent)
            if summary.playoffs.finals:
                lines.append(f"### Finals - Week {summary.playoffs.finals.week}")
                lines.append("")
                for bracket in summary.playoffs.finals.division_brackets:
                    lines.append(f"**{bracket.division_name}**")
                    lines.append("")
                    for idx, matchup in enumerate(bracket.matchups):
                        winner1 = "✅ " if matchup.winner_name == matchup.team1_name else ""
                        winner2 = "✅ " if matchup.winner_name == matchup.team2_name else ""
                        score1 = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
                        score2 = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"
                        lines.append(
                            f"- {winner1}**#{matchup.seed1} {matchup.team1_name}** ({matchup.owner1_name}) - {score1}"
                        )
                        lines.append(
                            f"- {winner2}**#{matchup.seed2} {matchup.team2_name}** ({matchup.owner2_name}) - {score2}"
                        )
                        if matchup.winner_name:
                            lines.append(f"  - **Winner:** {matchup.winner_name}")
                        lines.append("")
                        # Add extra blank line between matchups for better separation
                        if idx < len(bracket.matchups) - 1:
                            lines.append("")

            # Semifinals (show second - earlier round)
            if summary.playoffs.semifinals:
                lines.append(f"### Semifinals - Week {summary.playoffs.semifinals.week}")
                lines.append("")
                for bracket in summary.playoffs.semifinals.division_brackets:
                    lines.append(f"**{bracket.division_name}**")
                    lines.append("")
                    for idx, matchup in enumerate(bracket.matchups):
                        winner1 = "✅ " if matchup.winner_name == matchup.team1_name else ""
                        winner2 = "✅ " if matchup.winner_name == matchup.team2_name else ""
                        score1 = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
                        score2 = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"
                        lines.append(
                            f"- {winner1}**#{matchup.seed1} {matchup.team1_name}** ({matchup.owner1_name}) - {score1}"
                        )
                        lines.append(
                            f"- {winner2}**#{matchup.seed2} {matchup.team2_name}** ({matchup.owner2_name}) - {score2}"
                        )
                        if matchup.winner_name:
                            lines.append(f"  - **Winner:** {matchup.winner_name}")
                        lines.append("")
                        # Add extra blank line between matchups for better separation
                        if idx < len(bracket.matchups) - 1:
                            lines.append("")

        # Regular season results
        lines.append("## Regular Season Results")
        lines.append("")

        # Regular Season Division Champions
        lines.append("### Regular Season Division Champions")
        lines.append("")
        lines.append("| Division | Team | Owner | Record | Points For |")
        lines.append("|----------|------|-------|--------|------------|")
        for champion in summary.regular_season.division_champions:
            record = f"{champion.wins}-{champion.losses}"
            lines.append(
                f"| {champion.division_name} | {champion.team_name} | {champion.owner_name} | "
                f"{record} | {champion.points_for:.2f} |"
            )
        lines.append("")

        # Season challenges
        lines.append("### Season-Long Challenges")
        lines.append("")
        lines.append("| Challenge | Winner | Owner | Division | Value |")
        lines.append("|-----------|--------|-------|----------|-------|")
        for challenge in summary.season_challenges:
            lines.append(
                f"| {challenge.challenge_name} | {challenge.winner} | {challenge.owner.full_name} | {challenge.division} | {challenge.value} |"
            )
        lines.append("")

        # Final standings by division
        lines.append("### Final Standings")
        lines.append("")
        for division_data in summary.regular_season.final_standings:
            lines.append(f"#### {division_data.name}")
            lines.append("")
            lines.append("| Rank | Team | Owner | Record | PF | PA |")
            lines.append("|------|------|-------|--------|----|----|")

            # Sort teams
            sorted_teams = sorted(
                division_data.teams, key=lambda t: (t.wins, t.points_for), reverse=True
            )

            for rank, team in enumerate(sorted_teams, start=1):
                record = f"{team.wins}-{team.losses}"
                owner_name = f"{team.owner.first_name} {team.owner.last_name}"
                lines.append(
                    f"| {rank} | {team.name} | {owner_name} | {record} | "
                    f"{team.points_for:.2f} | {team.points_against:.2f} |"
                )
            lines.append("")

        return "\n".join(lines)
