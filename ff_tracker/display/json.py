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

        # Dictionary comprehension - very pythonic!
        data: dict[str, object] = {
            "current_week": current_week if current_week is not None else -1,
        }

        # Add optional note to metadata
        if note:
            data["note"] = note

        # Add main data sections (typed as object to avoid complex nested type inference)
        main_sections: dict[str, object] = {
            "divisions": [
                {
                    "name": div.name,
                    "league_id": div.league_id,
                    "teams": [
                        {
                            "name": team.name,
                            "owner": self._serialize_owner(team.owner),
                            "points_for": team.points_for,
                            "points_against": team.points_against,
                            "wins": team.wins,
                            "losses": team.losses,
                            "in_playoff_position": team.in_playoff_position,
                        }
                        for team in div.teams  # List comprehension inside dict
                    ],
                    "weekly_games": [
                        {
                            "team_name": game.team_name,
                            "score": game.score,
                            "projected_score": game.projected_score,
                            "starter_projected_score": game.starter_projected_score,
                            "opponent_name": game.opponent_name,
                            "opponent_score": game.opponent_score,
                            "won": game.won,
                            "week": game.week,
                            "margin": game.margin,
                            "projection_diff": game.projection_diff,
                            "true_projection_diff": game.true_projection_diff,
                        }
                        for game in div.weekly_games
                    ]
                    if div.weekly_games
                    else [],
                }
                for div in divisions
            ],
            "weekly_challenges": [
                {
                    "name": challenge.challenge_name,
                    "week": challenge.week,
                    "winner": challenge.winner,
                    "division": challenge.division,
                    "value": challenge.value,
                    "description": challenge.description,
                    "challenge_type": "player"
                    if "position" in challenge.additional_info
                    else "team",
                    "additional_info": challenge.additional_info,
                }
                for challenge in weekly_challenges
            ]
            if weekly_challenges
            else [],
            "challenges": [
                {
                    "name": challenge.challenge_name,
                    "winner": challenge.winner,
                    "owner": self._serialize_owner(challenge.owner),
                    "division": challenge.division,
                    "description": challenge.description,
                }
                for challenge in challenges
            ],
        }
        data.update(main_sections)

        # Python's json module with optional pretty printing
        indent = 2 if pretty else None
        return json.dumps(data, indent=indent, ensure_ascii=False)
