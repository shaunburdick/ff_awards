from __future__ import annotations

import json
from collections.abc import Sequence

from ..models import ChallengeResult, DivisionData
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

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        current_week: int | None = None
    ) -> str:
        """Format results as JSON string."""
        # Dictionary comprehension - very pythonic!
        data: dict[str, list[dict[str, object]] | int] = {
            "current_week": current_week if current_week is not None else -1,
            "divisions": [
                {
                    "name": div.name,
                    "league_id": div.league_id,
                    "teams": [
                        {
                            "name": team.name,
                            "owner": team.owner,
                            "points_for": team.points_for,
                            "points_against": team.points_against,
                            "wins": team.wins,
                            "losses": team.losses,
                        }
                        for team in div.teams  # List comprehension inside dict
                    ]
                }
                for div in divisions
            ],
            "challenges": [
                {
                    "name": challenge.challenge_name,
                    "winner": challenge.winner,
                    "owner": challenge.owner,
                    "division": challenge.division,
                    "description": challenge.description,
                }
                for challenge in challenges
            ]
        }

        # Python's json module with pretty printing
        return json.dumps(data, indent=2, ensure_ascii=False)
