"""
FR-011's per-league season history block.

Computed from ``DivisionData.games`` alone — the same collection the season
challenges read — so the narrative can only cite a week the report already
holds. No fetch, no storage, no switch of its own: it rides the feature flag.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, TypedDict

from ..models import GameResult, TeamStats

if TYPE_CHECKING:
    from .ai_digest import AIStandingsRow


# A latest score more than one point off the earlier mean is a trend; inside
# that band it is noise, and one week asserts no trend at all (FR-011).
TREND_THRESHOLD = 1.0


class AIRankByWeek(TypedDict):
    """One team's standings rank at the end of one week."""

    week: int
    rank: int


class AIHeadToHead(TypedDict):
    """One team's record against one opponent. A tie counts as a loss."""

    opponent: str
    wins: int
    losses: int


class AIStreak(TypedDict):
    """The run still standing at a team's latest game."""

    kind: str  # "win" | "loss"
    length: int


class AIWeekScore(TypedDict):
    """One week's score for one team."""

    week: int
    score: float


class AITeamHistory(TypedDict):
    """Everything FR-011 derives about one team, or null where it derives nothing."""

    team: str
    rank_by_week: list[AIRankByWeek]
    head_to_head: list[AIHeadToHead]
    streak: AIStreak | None
    scoring_trend: str | None  # "up" | "down" | "flat" | None
    best_week: AIWeekScore | None
    worst_week: AIWeekScore | None
    average_margin: float | None
    largest_win: float | None
    largest_loss: float | None


class AILeagueHistory(TypedDict):
    """One league's history block."""

    weeks_included: list[int]
    teams: list[AITeamHistory]


def build_history(
    games: Sequence[GameResult],
    teams: Sequence[TeamStats],
    anchor: Sequence[AIStandingsRow],
) -> AILeagueHistory | None:
    """
    Build FR-011's block, anchored on the standings beside it.

    The latest week present takes its ranks from ``anchor`` — the digest's own
    standings rows — because ``DivisionData.games`` is built tolerantly and can
    be missing a week ``TeamStats`` still counts. Every earlier week is
    recomputed under the standings' own order.

    Args:
        games: The league's season games, as ``DivisionData.games`` holds them
        teams: The league's roster, so a team with no game is still listed
        anchor: The ranked standings rows, whose order ``teams[]`` follows

    Returns:
        The block, or ``None`` when the league has no completed games.
    """
    if not games:
        return None

    weeks = sorted({game.week for game in games})
    anchor_order = {row["team"]: row["rank"] for row in anchor}
    by_team = _games_by_team(games)
    ordered_teams = sorted(teams, key=lambda team: _anchor_position(anchor_order, team.name))
    ranks = _ranks_by_team(ordered_teams, by_team, weeks, anchor_order)

    return AILeagueHistory(
        weeks_included=weeks,
        teams=[
            _team_history(team.name, by_team.get(team.name, []), ranks.get(team.name, []))
            for team in ordered_teams
        ],
    )


def _games_by_team(games: Sequence[GameResult]) -> dict[str, list[GameResult]]:
    """Group the collection by team, each list in week order."""
    by_team: dict[str, list[GameResult]] = {}
    for game in games:
        by_team.setdefault(game.team_name, []).append(game)
    return {team: sorted(rows, key=lambda row: row.week) for team, rows in by_team.items()}


def _anchor_position(anchor_order: dict[str, int], name: str) -> int:
    """A team's place in the standings order; one the standings missed sorts last."""
    return anchor_order.get(name, len(anchor_order) + 1)


def _ranks_by_team(
    teams: Sequence[TeamStats],
    by_team: dict[str, list[GameResult]],
    weeks: Sequence[int],
    anchor_order: dict[str, int],
) -> dict[str, list[AIRankByWeek]]:
    """
    One pass per week, then the anchor replaces the latest week's ranks.

    A team with no game in the collection keeps only that anchored row: there
    is nothing to rank before it (FR-011).
    """
    names = [team.name for team in teams]
    ranks: dict[str, list[AIRankByWeek]] = {name: [] for name in names}

    for week in weeks:
        for rank, name in enumerate(_order_at_week(names, by_team, week, anchor_order), 1):
            ranks[name].append(AIRankByWeek(week=week, rank=rank))

    latest_week = weeks[-1]
    for name in names:
        anchored = anchor_order.get(name)
        if anchored is not None:
            ranks[name][-1] = AIRankByWeek(week=latest_week, rank=anchored)
        if not by_team.get(name):
            ranks[name] = ranks[name][-1:]

    return ranks


def _order_at_week(
    names: Sequence[str],
    by_team: dict[str, list[GameResult]],
    week: int,
    anchor_order: dict[str, int],
) -> list[str]:
    """Rank every team by wins, then points for, over its games up to ``week``."""
    records = {name: _record_through(by_team.get(name, []), week) for name in names}
    return sorted(
        names,
        key=lambda name: (
            -records[name][0],
            -records[name][1],
            _anchor_position(anchor_order, name),
        ),
    )


def _record_through(games: Sequence[GameResult], week: int) -> tuple[int, float]:
    """Wins and points for over the games played up to and including ``week``."""
    played = [game for game in games if game.week <= week]
    return sum(1 for game in played if game.won), sum(game.score for game in played)


def _team_history(
    name: str, games: Sequence[GameResult], rank_by_week: Sequence[AIRankByWeek]
) -> AITeamHistory:
    """Derive one team's block; a team with no game gets nulls and stays listed."""
    if not games:
        return AITeamHistory(
            team=name,
            rank_by_week=list(rank_by_week),
            head_to_head=[],
            streak=None,
            scoring_trend=None,
            best_week=None,
            worst_week=None,
            average_margin=None,
            largest_win=None,
            largest_loss=None,
        )

    return AITeamHistory(
        team=name,
        rank_by_week=list(rank_by_week),
        head_to_head=_head_to_head(games),
        streak=_streak(games),
        scoring_trend=_scoring_trend(games),
        best_week=_extreme_week(games, highest=True),
        worst_week=_extreme_week(games, highest=False),
        average_margin=sum(game.score - game.opponent_score for game in games) / len(games),
        largest_win=_largest_margin(games, won=True),
        largest_loss=_largest_margin(games, won=False),
    )


def _head_to_head(games: Sequence[GameResult]) -> list[AIHeadToHead]:
    """One row per opponent met, sorted by opponent name for a stable read."""
    tally: dict[str, list[int]] = {}
    for game in games:
        row = tally.setdefault(game.opponent_name, [0, 0])
        row[0 if game.won else 1] += 1
    return [
        AIHeadToHead(opponent=opponent, wins=wins, losses=losses)
        for opponent, (wins, losses) in sorted(tally.items())
    ]


def _streak(games: Sequence[GameResult]) -> AIStreak:
    """Count back from the latest game while the outcome repeats."""
    latest = games[-1]
    length = 0
    for game in reversed(games):
        if game.won != latest.won:
            break
        length += 1
    return AIStreak(kind="win" if latest.won else "loss", length=length)


def _scoring_trend(games: Sequence[GameResult]) -> str | None:
    """Compare the latest week's score with the mean of the weeks before it."""
    latest = games[-1]
    earlier = [game.score for game in games if game.week < latest.week]
    if not earlier:
        return None

    delta = latest.score - sum(earlier) / len(earlier)
    if delta > TREND_THRESHOLD:
        return "up"
    if delta < -TREND_THRESHOLD:
        return "down"
    return "flat"


def _extreme_week(games: Sequence[GameResult], highest: bool) -> AIWeekScore:
    """The highest or lowest single-week score; the earliest week wins a tie."""
    game = max(games, key=lambda row: row.score) if highest else min(games, key=lambda r: r.score)
    return AIWeekScore(week=game.week, score=game.score)


def _largest_margin(games: Sequence[GameResult], won: bool) -> float | None:
    """The biggest win or loss as a magnitude, or null when the team has none."""
    margins = [game.margin for game in games if game.won == won]
    return max(margins) if margins else None
