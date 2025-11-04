from __future__ import annotations

import json
from collections.abc import Sequence

from ..models import ChallengeResult, DivisionData, Owner, WeeklyChallenge
from .base import BaseFormatter


class JsonFormatter(BaseFormatter):
    """Export fantasy football data as JSON."""

    def __init__(self, year: int) -> None:
        """
        Initialize console formatter.

        Args:
            year: Fantasy season year for display
        """
        super().__init__()
        self.year = year

    def _serialize_owner(self, owner: Owner) -> dict[str, object]:
        """Convert Owner object to dictionary for JSON serialization."""
        return {
            "display_name": owner.display_name,
            "first_name": owner.first_name,
            "last_name": owner.last_name,
            "full_name": owner.full_name,
            "id": owner.id,
            "is_likely_username": owner.is_likely_username
        }

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None
    ) -> str:
        """Format results as JSON string."""
        # Dictionary comprehension - very pythonic!
        data: dict[str, object] = {
            "current_week": current_week if current_week is not None else -1,
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
                    ] if div.weekly_games else []
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
                    "challenge_type": "player" if "position" in challenge.additional_info else "team",
                    "additional_info": challenge.additional_info,
                }
                for challenge in weekly_challenges
            ] if weekly_challenges else [],
            "challenges": [
                {
                    "name": challenge.challenge_name,
                    "winner": challenge.winner,
                    "owner": self._serialize_owner(challenge.owner),
                    "division": challenge.division,
                    "description": challenge.description,
                }
                for challenge in challenges
            ]
        }

        # Python's json module with pretty printing
        return json.dumps(data, indent=2, ensure_ascii=False)
