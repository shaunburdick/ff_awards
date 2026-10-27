"""
The one overall ranking, shared by the formatters and the digest.

FR-012 requires the league-wide table in the prompt to be in exactly the order
the console's overall table produces, so the rule lives here once rather than
twice and drifting.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import DivisionData, TeamStats


def rank_overall_teams(
    divisions: Sequence[DivisionData], limit: int | None = None
) -> list[TeamStats]:
    """
    Rank every team across divisions by wins, then points for.

    Args:
        divisions: Divisions to combine and rank.
        limit: Maximum number of teams to return. ``None`` or a value of zero
            or less means "no limit" and returns every team.

    Returns:
        Ranked teams, truncated to ``limit`` when one is supplied.
    """
    teams = [team for division in divisions for team in division.teams]
    ranked = sorted(teams, key=lambda team: (team.wins, team.points_for), reverse=True)
    if limit is None or limit <= 0:
        return ranked
    return ranked[:limit]
