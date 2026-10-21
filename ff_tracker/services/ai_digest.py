"""
Build the digest sent to the AI provider from the report's domain models.

The payload is internal: it is assembled once per run and serialised straight
into the user message. It is not the JSON formatter's output and not a public
schema, so it is described with ``TypedDict`` payload types rather than
Article II models — a wrong key here is a mypy error, not a silently degraded
prompt.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from ..models import ChallengeResult, ChampionshipLeaderboard, DivisionData, WeeklyChallenge
from ..models.playoff import PlayoffBracket
from ..models.week import WeeklyGameResult

MODE_REGULAR = "regular_season"
MODE_PLAYOFFS = "playoffs"
MODE_CHAMPIONSHIP = "championship"

NO_MATCHUPS_NOTE = "No matchups this week"


class AIStandingsRow(TypedDict):
    """One team in a league's standings, in the order the formatters display."""

    rank: int
    team: str
    owner: str
    record: str
    points_for: float
    points_against: float
    playoff_status: str  # "qualified" | "eliminated", the JSON formatter's wording


class AIMatchupRow(TypedDict):
    """One team's week from a matchup; the opponent's fields are the mirror row's."""

    team: str
    score: float
    projected_score: float
    true_projection_diff: float | None
    opponent: str
    opponent_score: float
    opponent_projected_score: float
    opponent_true_projection_diff: float | None
    margin: float


class AIWeeklyChallenge(TypedDict):
    """A weekly challenge a league won."""

    challenge: str
    winner: str
    value: str


class AISeasonChallenge(TypedDict):
    """One of the five season-long challenge leaders."""

    challenge: str
    winner: str
    league: str
    value: str
    historical: bool


class AIPlayoffMatchup(TypedDict):
    """One playoff game. No seed: the digest carries the matchup, not a bracket rank."""

    round_name: str
    team1: str
    owner1: str
    score1: float | None
    team2: str
    owner2: str
    score2: float | None
    winner: str | None
    division: str


class AIPlayoffRound(TypedDict):
    """The current playoff round, with a flat matchup list across divisions."""

    round: str
    matchups: list[AIPlayoffMatchup]


class AIChampionshipEntry(TypedDict):
    """One division winner in the Week 17 leaderboard."""

    rank: int
    team: str
    owner: str
    division: str
    score: float
    is_champion: bool


class AIChampionship(TypedDict):
    """The Week 17 leaderboard."""

    leaderboard: list[AIChampionshipEntry]


class AILeagueDigest(TypedDict):
    """Everything the narrative needs about one league."""

    league: str
    teams: int
    week: int | None
    weeks_remaining: int | None
    standings: list[AIStandingsRow]
    matchups: list[AIMatchupRow]
    matchups_note: str | None
    weekly_challenges: list[AIWeeklyChallenge]


class AIDigest(TypedDict):
    """The complete payload sent to the provider."""

    week: int | None
    mode: str  # MODE_REGULAR | MODE_PLAYOFFS | MODE_CHAMPIONSHIP
    leagues: list[AILeagueDigest]
    season_challenges: list[AISeasonChallenge]
    playoffs: AIPlayoffRound | None
    championship: AIChampionship | None


def build_digest(
    divisions: Sequence[DivisionData],
    challenges: Sequence[ChallengeResult],
    weekly_challenges: Sequence[WeeklyChallenge] | None,
    current_week: int | None,
    championship: ChampionshipLeaderboard | None,
) -> AIDigest:
    """
    Build the FR-002 payload from the report's own domain models.

    Carries no league IDs, no credentials and no API key.

    Args:
        divisions: The report's divisions
        challenges: Season-long challenge leaders
        weekly_challenges: Weekly challenge winners, if any
        current_week: The week the report is showing, if known
        championship: The Week 17 leaderboard, when in championship mode

    Returns:
        The digest, ready to be serialised into the user message.
    """
    mode = _derive_mode(divisions, championship)
    playoff_only = mode in (MODE_PLAYOFFS, MODE_CHAMPIONSHIP)

    leagues = [
        _league_digest(division, weekly_challenges, current_week, mode)
        for division in divisions
    ]

    return AIDigest(
        week=current_week,
        mode=mode,
        leagues=leagues,
        season_challenges=_season_challenges(challenges, historical=playoff_only),
        playoffs=_playoff_round(divisions) if mode == MODE_PLAYOFFS else None,
        championship=_championship_digest(championship) if championship else None,
    )


def _derive_mode(
    divisions: Sequence[DivisionData], championship: ChampionshipLeaderboard | None
) -> str:
    """Apply the same two expressions the formatters use, in the same order."""
    if championship is not None:
        return MODE_CHAMPIONSHIP
    if any(division.is_playoff_mode for division in divisions):
        return MODE_PLAYOFFS
    return MODE_REGULAR


def _league_digest(
    division: DivisionData,
    weekly_challenges: Sequence[WeeklyChallenge] | None,
    current_week: int | None,
    mode: str,
) -> AILeagueDigest:
    """Build one league's section of the digest."""
    in_championship = mode == MODE_CHAMPIONSHIP
    player_only = mode in (MODE_PLAYOFFS, MODE_CHAMPIONSHIP)

    standings = [] if in_championship else _standings_rows(division)
    matchups, matchups_note = _matchup_rows(division) if not in_championship else ([], None)

    return AILeagueDigest(
        league=division.name,
        teams=division.team_count,
        week=current_week,
        weeks_remaining=_weeks_remaining(division, current_week),
        standings=standings,
        matchups=matchups,
        matchups_note=matchups_note,
        weekly_challenges=_weekly_challenge_rows(
            weekly_challenges, division.name, player_only
        ),
    )


def _weeks_remaining(division: DivisionData, current_week: int | None) -> int | None:
    """Regular-season weeks left, or None when either input is unknown."""
    if current_week is None or division.reg_season_count is None:
        return None
    return max(0, division.reg_season_count - current_week)


def _standings_rows(division: DivisionData) -> list[AIStandingsRow]:
    """Rank teams exactly as the formatters do: wins, then points for."""
    ordered = sorted(division.teams, key=lambda team: (team.wins, team.points_for), reverse=True)
    return [
        AIStandingsRow(
            rank=index,
            team=team.name,
            owner=team.owner.full_name,
            record=f"{team.wins}-{team.losses}",
            points_for=team.points_for,
            points_against=team.points_against,
            playoff_status="qualified" if team.in_playoff_position else "eliminated",
        )
        for index, team in enumerate(ordered, 1)
    ]


def _matchup_rows(division: DivisionData) -> tuple[list[AIMatchupRow], str | None]:
    """One row per team, with the opponent's true diff read from the mirror row."""
    if not division.weekly_games:
        return [], NO_MATCHUPS_NOTE

    mirror = {(row.team_name, row.opponent_name): row for row in division.weekly_games}
    rows = [
        AIMatchupRow(
            team=row.team_name,
            score=row.score,
            projected_score=row.projected_score,
            true_projection_diff=row.true_projection_diff,
            opponent=row.opponent_name,
            opponent_score=row.opponent_score,
            opponent_projected_score=row.opponent_projected_score,
            opponent_true_projection_diff=_opponent_true_diff(mirror, row),
            margin=row.margin,
        )
        for row in division.weekly_games
    ]
    return rows, None


def _opponent_true_diff(
    mirror: dict[tuple[str, str], WeeklyGameResult], row: WeeklyGameResult
) -> float | None:
    """Read the opponent's true projection diff, or None when there is no mirror row."""
    opponent_row = mirror.get((row.opponent_name, row.team_name))
    if opponent_row is None:
        return None
    return opponent_row.true_projection_diff


def _weekly_challenge_rows(
    weekly_challenges: Sequence[WeeklyChallenge] | None,
    league_name: str,
    player_only: bool,
) -> list[AIWeeklyChallenge]:
    """The challenges this league won, under the mode rule the formatters apply."""
    if not weekly_challenges:
        return []
    return [
        AIWeeklyChallenge(
            challenge=challenge.challenge_name,
            winner=challenge.winner,
            value=challenge.value,
        )
        for challenge in weekly_challenges
        if challenge.division == league_name
        and (not player_only or "position" in challenge.additional_info)
    ]


def _season_challenges(
    challenges: Sequence[ChallengeResult], historical: bool
) -> list[AISeasonChallenge]:
    """The five season-long leaders, marked historical once the regular season ended."""
    return [
        AISeasonChallenge(
            challenge=challenge.challenge_name,
            winner=challenge.winner,
            league=challenge.division,
            value=challenge.value,
            historical=historical,
        )
        for challenge in challenges
    ]


def _playoff_round(divisions: Sequence[DivisionData]) -> AIPlayoffRound | None:
    """Flatten every division's bracket into one round for the digest."""
    brackets: list[PlayoffBracket] = [
        division.playoff_bracket
        for division in divisions
        if division.playoff_bracket is not None
    ]
    if not brackets:
        return None

    return AIPlayoffRound(
        round=brackets[0].round,
        matchups=[
            AIPlayoffMatchup(
                round_name=matchup.round_name,
                team1=matchup.team1_name,
                owner1=matchup.owner1_name,
                score1=matchup.score1,
                team2=matchup.team2_name,
                owner2=matchup.owner2_name,
                score2=matchup.score2,
                winner=matchup.winner_name,
                division=bracket.division_name,
            )
            for bracket in brackets
            for matchup in bracket.matchups
        ],
    )


def _championship_digest(
    championship: ChampionshipLeaderboard | None,
) -> AIChampionship | None:
    """Serialize the Week 17 leaderboard."""
    if championship is None:
        return None
    return AIChampionship(
        leaderboard=[
            AIChampionshipEntry(
                rank=entry.rank,
                team=entry.team_name,
                owner=entry.owner_name,
                division=entry.division_name,
                score=entry.score,
                is_champion=entry.is_champion,
            )
            for entry in championship.entries
        ]
    )
