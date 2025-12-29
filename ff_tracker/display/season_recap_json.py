"""
JSON output formatter for Season Recap.

Provides structured JSON output for season summaries including regular season,
playoffs, and championship results. Suitable for archival, APIs, and data analysis.
"""

from __future__ import annotations

import json
from typing import Any

from ..models.season_summary import SeasonSummary


class SeasonRecapJsonFormatter:
    """Formatter for season recap JSON output."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize season recap JSON formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        self.year = year
        self.format_args = format_args or {}

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for JSON formatter."""
        return {
            "pretty": "Pretty-print with indentation (default: true)",
            "note": "Optional metadata note to include in output",
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
        Format complete season summary as JSON.

        Args:
            summary: Complete season summary data

        Returns:
            JSON string representation
        """
        # Get format arguments
        pretty = self._get_arg_bool("pretty", default=True)
        note = self._get_arg("note")

        # Build JSON structure
        data: dict[str, Any] = {
            "year": summary.year,
            "is_complete": summary.is_complete,
            "total_divisions": summary.total_divisions,
            "season_structure": {
                "regular_season_start": summary.structure.regular_season_start,
                "regular_season_end": summary.structure.regular_season_end,
                "playoff_start": summary.structure.playoff_start,
                "playoff_end": summary.structure.playoff_end,
                "playoff_round_length": summary.structure.playoff_round_length,
                "championship_week": summary.structure.championship_week,
            },
        }

        # Add metadata note if provided
        if note:
            data["metadata"] = {"note": note}

        # Championship results (if available)
        if summary.championship:
            championship_entries = []
            for entry in summary.championship.entries:
                championship_entries.append(
                    {
                        "rank": entry.rank,
                        "team_name": entry.team_name,
                        "owner_name": entry.owner_name,
                        "division_name": entry.division_name,
                        "score": entry.score,
                        "is_champion": entry.rank == 1,
                    }
                )

            data["championship"] = {
                "week": summary.championship.week,
                "entries": championship_entries,
            }

            if summary.overall_champion:
                data["overall_champion"] = {
                    "team_name": summary.overall_champion.team_name,
                    "owner_name": summary.overall_champion.owner_name,
                    "division_name": summary.overall_champion.division_name,
                    "score": summary.overall_champion.score,
                }

        # Playoff results
        if summary.playoffs:
            playoff_rounds = []

            # Finals (show first - most recent)
            if summary.playoffs.finals:
                finals_data = self._format_playoff_round(summary.playoffs.finals)
                playoff_rounds.append(finals_data)

            # Semifinals (show second - earlier round)
            if summary.playoffs.semifinals:
                semifinals_data = self._format_playoff_round(summary.playoffs.semifinals)
                playoff_rounds.append(semifinals_data)

            data["playoffs"] = {"rounds": playoff_rounds}

        # Regular season results
        regular_season_data: dict[str, Any] = {}

        # Division champions
        champions = []
        for champion in summary.regular_season.division_champions:
            champions.append(
                {
                    "division_name": champion.division_name,
                    "team_name": champion.team_name,
                    "owner_name": champion.owner_name,
                    "wins": champion.wins,
                    "losses": champion.losses,
                    "points_for": champion.points_for,
                }
            )
        regular_season_data["division_champions"] = champions

        # Season challenges
        challenges = []
        for challenge in summary.season_challenges:
            challenges.append(
                {
                    "challenge_name": challenge.challenge_name,
                    "winner": challenge.winner,
                    "owner_name": challenge.owner.first_name + " " + challenge.owner.last_name,
                    "division": challenge.division,
                    "value": challenge.value,
                    "description": challenge.description,
                }
            )
        regular_season_data["challenges"] = challenges

        # Final standings by division
        standings = []
        for division_data in summary.regular_season.final_standings:
            division_standings = {
                "division_name": division_data.name,
                "teams": [],
            }

            # Sort teams by wins (desc), then points_for (desc)
            sorted_teams = sorted(
                division_data.teams, key=lambda t: (t.wins, t.points_for), reverse=True
            )

            for rank, team in enumerate(sorted_teams, start=1):
                division_standings["teams"].append(
                    {
                        "rank": rank,
                        "team_name": team.name,
                        "owner_name": team.owner.first_name + " " + team.owner.last_name,
                        "wins": team.wins,
                        "losses": team.losses,
                        "points_for": team.points_for,
                        "points_against": team.points_against,
                    }
                )

            standings.append(division_standings)

        regular_season_data["final_standings"] = standings

        data["regular_season"] = regular_season_data

        # Generate JSON output
        if pretty:
            return json.dumps(data, indent=2)
        return json.dumps(data)

    def _format_playoff_round(self, playoff_round) -> dict[str, Any]:
        """
        Format a single playoff round as JSON.

        Args:
            playoff_round: PlayoffRound data

        Returns:
            Dictionary representation of playoff round
        """
        round_data: dict[str, Any] = {
            "round_name": playoff_round.round_name,
            "week": playoff_round.week,
            "divisions": [],
        }

        for bracket in playoff_round.division_brackets:
            division_data: dict[str, Any] = {
                "division_name": bracket.division_name,
                "matchups": [],
            }

            for matchup in bracket.matchups:
                matchup_data = {
                    "matchup_id": matchup.matchup_id,
                    "round_name": matchup.round_name,
                    "team1": {
                        "seed": matchup.seed1,
                        "team_name": matchup.team1_name,
                        "owner_name": matchup.owner1_name,
                        "score": matchup.score1,
                    },
                    "team2": {
                        "seed": matchup.seed2,
                        "team_name": matchup.team2_name,
                        "owner_name": matchup.owner2_name,
                        "score": matchup.score2,
                    },
                    "winner": {
                        "team_name": matchup.winner_name,
                        "seed": matchup.winner_seed,
                    }
                    if matchup.winner_name
                    else None,
                    "is_complete": matchup.winner_name is not None,
                }

                division_data["matchups"].append(matchup_data)

            round_data["divisions"].append(division_data)

        return round_data
