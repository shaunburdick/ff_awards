from __future__ import annotations

import json
from collections.abc import Sequence

from ..models import ChallengeResult, ChampionshipLeaderboard, DivisionData, Owner, WeeklyChallenge
from .base import BaseFormatter


class JsonFormatter(BaseFormatter):
    """Export fantasy football data as JSON."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize JSON formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        super().__init__(year, format_args)

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for JSON formatter."""
        return {
            "note": "Optional note included in metadata section",
            "pretty": "Pretty-print with indentation (default: true)",
        }

    def _serialize_owner(self, owner: Owner) -> dict[str, object]:
        """Convert Owner object to dictionary for JSON serialization."""
        return {
            "display_name": owner.display_name,
            "first_name": owner.first_name,
            "last_name": owner.last_name,
            "full_name": owner.full_name,
            "id": owner.id,
            "is_likely_username": owner.is_likely_username,
        }

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None,
        championship: ChampionshipLeaderboard | None = None,
    ) -> str:
        """Format results as JSON string."""
        # Get format arguments
        note = self._get_arg("note")
        pretty = self._get_arg_bool("pretty", True)

        # Detect playoff mode
        is_playoff_mode = any(d.is_playoff_mode for d in divisions)
        is_championship_week = championship is not None

        # Base data structure
        data: dict[str, object] = {
            "current_week": current_week if current_week is not None else -1,
            "week": current_week if current_week is not None else -1,
        }

        # Add report type
        if is_championship_week:
            data["report_type"] = "championship_week"
        elif is_playoff_mode:
            playoff_round = (
                divisions[0].playoff_bracket.round if divisions[0].playoff_bracket else "playoffs"
            )
            data["report_type"] = f"playoff_{playoff_round.lower().replace(' ', '_')}"
        else:
            data["report_type"] = "regular_season"

        # Add optional note to metadata
        if note:
            data["note"] = note

        # Add playoff bracket data if in playoff mode (not championship)
        if is_playoff_mode and not is_championship_week:
            playoff_bracket = self._serialize_playoff_bracket(divisions)
            data["playoff_bracket"] = playoff_bracket

        # Add championship data if championship week
        if is_championship_week and championship:
            championship_data = self._serialize_championship(championship)
            data["championship"] = championship_data

        # Add weekly player highlights (filtered for playoffs)
        if weekly_challenges:
            # Filter to player challenges only in playoff mode
            filtered_challenges = weekly_challenges
            if is_playoff_mode or is_championship_week:
                filtered_challenges = [
                    c for c in weekly_challenges if "position" in c.additional_info
                ]

            data["weekly_player_highlights"] = [
                {
                    "challenge_name": challenge.challenge_name,
                    "challenge_type": "player"
                    if "position" in challenge.additional_info
                    else "team",
                    "player_name": challenge.winner,
                    "position": challenge.additional_info.get("position", ""),
                    "fantasy_team": challenge.additional_info.get("team_name", ""),
                    "division": challenge.division,
                    "points": float(challenge.value)
                    if challenge.value.replace(".", "", 1).isdigit()
                    else challenge.value,
                }
                for challenge in filtered_challenges
            ]

        # Add season challenges with historical note
        if challenges:
            season_challenges: dict[str, object] = {
                "challenges": [
                    {
                        "challenge_name": challenge.challenge_name,
                        "team_name": challenge.winner,
                        "owner_name": challenge.owner.full_name,
                        "division": challenge.division,
                        "value": challenge.description,
                        "details": challenge.description,
                    }
                    for challenge in challenges
                ]
            }
            if is_playoff_mode:
                season_challenges["note"] = (
                    "Regular season challenges - finalized at end of week 14"
                )
            data["season_challenges"] = season_challenges

        # Add standings (optional in championship week)
        if not is_championship_week:
            standings: dict[str, object] = {
                "divisions": [
                    {
                        "division_name": div.name,
                        "teams": [
                            {
                                "rank": i,
                                "team_name": team.name,
                                "owner_name": team.owner.full_name,
                                "record": f"{team.wins}-{team.losses}",
                                "points_for": team.points_for,
                                "points_against": team.points_against,
                                "playoff_status": "qualified"
                                if team.in_playoff_position
                                else "eliminated",
                            }
                            for i, team in enumerate(self._get_sorted_teams_by_division(div), 1)
                        ],
                    }
                    for div in divisions
                ]
            }
            if is_playoff_mode:
                standings["note"] = "Final regular season standings - week 14"
            data["standings"] = standings

        # Python's json module with optional pretty printing
        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, ensure_ascii=False)

    def _serialize_playoff_bracket(self, divisions: Sequence[DivisionData]) -> dict[str, object]:
        """Serialize playoff bracket data to dictionary."""
        playoff_divisions = [d for d in divisions if d.playoff_bracket]
        if not playoff_divisions:
            return {}

        bracket_round = (
            playoff_divisions[0].playoff_bracket.round
            if playoff_divisions[0].playoff_bracket
            else "Unknown"
        )

        return {
            "round": bracket_round,
            "divisions": [
                {
                    "division_name": div.name,
                    "matchups": [
                        {
                            "matchup_id": f"div{i + 1}_{'sf' if bracket_round == 'Semifinals' else 'f'}{j + 1}",
                            "round": f"Semifinal {j + 1}"
                            if bracket_round == "Semifinals"
                            else "Finals",
                            "seed1": matchup.seed1,
                            "team1": matchup.team1_name,
                            "owner1": matchup.owner1_name,
                            "score1": matchup.score1,
                            "seed2": matchup.seed2,
                            "team2": matchup.team2_name,
                            "owner2": matchup.owner2_name,
                            "score2": matchup.score2,
                            "winner": matchup.winner_name,
                            "winner_seed": matchup.winner_seed,
                            "division": div.name,
                        }
                        for j, matchup in enumerate(div.playoff_bracket.matchups)
                    ]
                    if div.playoff_bracket
                    else [],
                }
                for i, div in enumerate(playoff_divisions)
            ],
        }

    def _serialize_championship(self, championship: ChampionshipLeaderboard) -> dict[str, object]:
        """Serialize championship data to dictionary."""
        champion = championship.champion

        return {
            "round": "Championship Week",
            "description": "Highest score wins overall championship",
            "leaderboard": [
                {
                    "rank": entry.rank,
                    "medal": "🥇"
                    if entry.rank == 1
                    else "🥈"
                    if entry.rank == 2
                    else "🥉"
                    if entry.rank == 3
                    else "",
                    "team_name": entry.team_name,
                    "owner_name": entry.owner_name,
                    "division": entry.division_name,
                    "division_title": f"{entry.division_name} Champion",
                    "score": entry.score,
                    "is_champion": entry.is_champion,
                }
                for entry in championship.entries
            ],
            "overall_champion": {
                "team_name": champion.team_name,
                "owner_name": champion.owner_name,
                "division": champion.division_name,
                "score": champion.score,
            },
        }
