"""
Shared fixtures for the AI summary tests.

Builders produce the real domain models, so the digest, service and rendering
tests all exercise the same shapes the report produces. No network: the fake
client and fake transport live here too.
"""

from __future__ import annotations

from collections.abc import Sequence

from ff_tracker.exceptions import AISummaryError
from ff_tracker.models import (
    AIProvenance,
    AISummary,
    AISummaryLeague,
    ChallengeResult,
    ChampionshipEntry,
    ChampionshipLeaderboard,
    DivisionData,
    GameResult,
    Owner,
    PlayoffBracket,
    PlayoffMatchup,
    TeamStats,
    WeeklyChallenge,
    WeeklyGameResult,
    WeeklyPlayerStats,
)
from ff_tracker.services.ai_client import AIRequest

WEEK = 6
LEAGUE_A = "MM Driveway Surfers"
LEAGUE_B = "My 2026 League"


def make_owner(name: str) -> Owner:
    """Create an owner whose full name is the display name."""
    first, _, last = name.partition(" ")
    return Owner(display_name=name, first_name=first, last_name=last, id=name.lower().replace(" ", "-"))


def make_team(
    name: str,
    *,
    division: str = LEAGUE_A,
    wins: int = 6,
    losses: int = 0,
    points_for: float = 800.0,
    points_against: float = 700.0,
    in_playoff_position: bool = True,
) -> TeamStats:
    """Create one team's season stats."""
    return TeamStats(
        name=name,
        owner=make_owner(f"Owner {name}"),
        wins=wins,
        losses=losses,
        points_for=points_for,
        points_against=points_against,
        division=division,
        in_playoff_position=in_playoff_position,
    )


def make_week_row(
    team: str,
    score: float,
    *,
    opponent: str = "Opponent",
    opponent_score: float = 100.0,
    won: bool = True,
    division: str = LEAGUE_A,
    week: int = WEEK,
    true_projection_diff: float | None = None,
    projected_score: float = 100.0,
    opponent_projected_score: float = 100.0,
) -> WeeklyGameResult:
    """One team's week, with an explicit true projection diff."""
    return WeeklyGameResult(
        team_name=team,
        score=score,
        projected_score=projected_score,
        opponent_name=opponent,
        opponent_score=opponent_score,
        opponent_projected_score=opponent_projected_score,
        won=won,
        week=week,
        margin=abs(score - opponent_score),
        projection_diff=score - projected_score,
        division=division,
        starter_projected_score=(
            None if true_projection_diff is None else score - true_projection_diff
        ),
        true_projection_diff=true_projection_diff,
    )


def make_matchup_pair(
    team1: str,
    score1: float,
    team2: str,
    score2: float,
    *,
    division: str = LEAGUE_A,
    week: int = WEEK,
    true_diff1: float | None = None,
    true_diff2: float | None = None,
) -> list[WeeklyGameResult]:
    """Both rows of one matchup, as the ESPN extractor emits them."""
    return [
        make_week_row(
            team1,
            score1,
            opponent=team2,
            opponent_score=score2,
            won=score1 > score2,
            division=division,
            week=week,
            true_projection_diff=true_diff1,
        ),
        make_week_row(
            team2,
            score2,
            opponent=team1,
            opponent_score=score1,
            won=score2 > score1,
            division=division,
            week=week,
            true_projection_diff=true_diff2,
        ),
    ]


def make_player(
    name: str,
    points: float,
    *,
    position: str = "RB",
    team: str = "Butt Fumble",
    division: str = LEAGUE_A,
    slot: str = "RB",
    week: int = WEEK,
    projected: float = 10.0,
) -> WeeklyPlayerStats:
    """One starter's week."""
    return WeeklyPlayerStats(
        name=name,
        position=position,
        team_name=team,
        division=division,
        points=points,
        projected_points=projected,
        projection_diff=points - projected,
        slot_position=slot,
        week=week,
        pro_team="SF",
        pro_opponent="SEA",
    )


def make_team_challenge(
    name: str, winner: str, *, division: str = LEAGUE_A, value: str = "126.14"
) -> WeeklyChallenge:
    """A team challenge won by a team in ``division``."""
    return WeeklyChallenge(
        challenge_name=name,
        week=WEEK,
        winner=winner,
        owner=None,
        division=division,
        value=value,
        description=f"{winner} won {name}",
        additional_info={"score": 126.14, "won": True},
    )


def make_player_challenge(
    name: str, winner: str, *, division: str = LEAGUE_A, value: str = "30.70"
) -> WeeklyChallenge:
    """A player challenge won by a player in ``division``."""
    return WeeklyChallenge(
        challenge_name=name,
        week=WEEK,
        winner=winner,
        owner=None,
        division=division,
        value=value,
        description=f"{winner} scored {value}",
        additional_info={"position": "RB", "team": "Butt Fumble", "pro_team": "SF"},
    )


def make_season_challenge(
    name: str = "Most Points Overall",
    winner: str = "Butt Fumble",
    *,
    division: str = LEAGUE_A,
    value: str = "1250.50",
) -> ChallengeResult:
    """One season-long challenge leader."""
    return ChallengeResult(
        challenge_name=name,
        winner=winner,
        owner=make_owner("Season Owner"),
        division=division,
        value=value,
        description=f"{winner} leads {name}",
    )


def make_playoff_bracket(
    *,
    round_name: str = "Semifinals",
    week: int = 15,
    division: str = LEAGUE_A,
) -> PlayoffBracket:
    """A two-matchup semifinal bracket."""
    return PlayoffBracket(
        round=round_name,
        week=week,
        division_name=division,
        matchups=[
            PlayoffMatchup(
                matchup_id=f"{division}-sf1",
                round_name="Semifinal 1",
                seed1=1,
                team1_name="Butt Fumble",
                owner1_name="Owner Butt Fumble",
                score1=132.40,
                seed2=4,
                team2_name="Donut Lose",
                owner2_name="Owner Donut Lose",
                score2=101.10,
                winner_name="Butt Fumble",
                winner_seed=1,
                division_name=division,
            ),
            PlayoffMatchup(
                matchup_id=f"{division}-sf2",
                round_name="Semifinal 2",
                seed1=2,
                team1_name="In JJ We Trust",
                owner1_name="Owner In JJ We Trust",
                score1=None,
                seed2=3,
                team2_name="Caserta Chumps",
                owner2_name="Owner Caserta Chumps",
                score2=None,
                winner_name=None,
                winner_seed=None,
                division_name=division,
            ),
        ],
    )


def make_championship(week: int = 17) -> ChampionshipLeaderboard:
    """A three-league Week 17 leaderboard."""
    return ChampionshipLeaderboard(
        week=week,
        entries=[
            ChampionshipEntry(
                rank=1,
                team_name="Butt Fumble",
                owner_name="Owner Butt Fumble",
                division_name=LEAGUE_A,
                score=155.20,
                is_champion=True,
            ),
            ChampionshipEntry(
                rank=2,
                team_name="Caserta Chumps",
                owner_name="Owner Caserta Chumps",
                division_name=LEAGUE_B,
                score=140.05,
                is_champion=False,
            ),
        ],
    )


def make_division(
    name: str = LEAGUE_A,
    *,
    league_id: int = 111,
    teams: Sequence[TeamStats] | None = None,
    weekly_games: Sequence[WeeklyGameResult] = (),
    weekly_players: Sequence[WeeklyPlayerStats] = (),
    playoff_bracket: PlayoffBracket | None = None,
    reg_season_count: int | None = None,
    games: Sequence[GameResult] = (),
) -> DivisionData:
    """One league. Defaults to a two-team league with no weekly data."""
    return DivisionData(
        league_id=league_id,
        name=name,
        teams=list(teams)
        if teams is not None
        else [make_team("Butt Fumble", division=name), make_team("Donut Lose", division=name)],
        games=list(games),
        weekly_games=list(weekly_games),
        weekly_players=list(weekly_players),
        playoff_bracket=playoff_bracket,
        reg_season_count=reg_season_count,
    )


def make_regular_divisions(week: int = WEEK) -> list[DivisionData]:
    """Two leagues mid-season, with matchups, players and a known season length."""
    games_a = make_matchup_pair(
        "Butt Fumble", 147.78, "Donut Lose", 106.50, division=LEAGUE_A, week=week, true_diff1=9.82
    ) + make_matchup_pair(
        "In JJ We Trust", 125.06, "Caserta Chumps", 112.00, division=LEAGUE_B, week=week
    )
    return [
        make_division(
            LEAGUE_A,
            league_id=111,
            teams=[
                make_team("Butt Fumble", division=LEAGUE_A, wins=6, points_for=812.34),
                make_team(
                    "Donut Lose",
                    division=LEAGUE_A,
                    wins=2,
                    losses=4,
                    points_for=690.11,
                    in_playoff_position=False,
                ),
            ],
            weekly_games=[row for row in games_a if row.division == LEAGUE_A],
            weekly_players=[
                make_player("Christian McCaffrey", 30.70, division=LEAGUE_A),
                make_player("Trevor Lawrence", 27.34, position="QB", slot="QB", division=LEAGUE_A),
            ],
            reg_season_count=14,
        ),
        make_division(
            LEAGUE_B,
            league_id=222,
            teams=[
                make_team("In JJ We Trust", division=LEAGUE_B, wins=5, points_for=740.20),
                make_team(
                    "Caserta Chumps",
                    division=LEAGUE_B,
                    wins=3,
                    losses=3,
                    points_for=701.00,
                    in_playoff_position=False,
                ),
            ],
            weekly_games=[row for row in games_a if row.division == LEAGUE_B],
            weekly_players=[make_player("Malik Nabers", 28.50, position="WR", slot="WR", division=LEAGUE_B)],
            reg_season_count=14,
        ),
    ]


def make_regular_weekly_challenges() -> list[WeeklyChallenge]:
    """A mix of team and player challenges across both leagues."""
    return [
        make_team_challenge("Highest Score This Week", "Butt Fumble", division=LEAGUE_A),
        make_team_challenge("Closest Game This Week", "Donut Lose", division=LEAGUE_A),
        make_player_challenge("Top Scorer (Player)", "Christian McCaffrey", division=LEAGUE_A),
        make_player_challenge("Best WR", "Malik Nabers", division=LEAGUE_B),
    ]


def make_playoff_divisions(week: int = 15) -> list[DivisionData]:
    """One league in the semifinals, with player data and a bracket."""
    return [
        make_division(
            LEAGUE_A,
            league_id=111,
            weekly_players=[make_player("Christian McCaffrey", 30.70, division=LEAGUE_A, week=week)],
            playoff_bracket=make_playoff_bracket(week=week, division=LEAGUE_A),
            reg_season_count=14,
        )
    ]


def make_championship_divisions(week: int = 17) -> list[DivisionData]:
    """One league in Week 17: no bracket, player data only."""
    return [
        make_division(
            LEAGUE_A,
            league_id=111,
            weekly_players=[make_player("Christian McCaffrey", 30.70, division=LEAGUE_A, week=week)],
            reg_season_count=14,
        )
    ]


def make_narrative(
    *,
    headline: str = "Six weeks in and nobody has an answer",
    leagues: Sequence[AISummaryLeague] | None = None,
    season_note: str = "Halfway there, and the middle of the table is a car park.",
    truncated: bool = False,
) -> AISummary:
    """A valid narrative with one league unless told otherwise."""
    return AISummary(
        headline=headline,
        leagues=list(leagues)
        if leagues is not None
        else [
            AISummaryLeague(
                league=LEAGUE_A,
                paragraphs=["Butt Fumble stayed unbeaten through six weeks."],
                bullets=["Donut Lose won by 1.08"],
            )
        ],
        season_note=season_note,
        provenance=AIProvenance(
            model="glm-5.3-flash",
            prompt_sha="9f2c1ab4e7d0",
            generated_at="2026-10-14T05:03:11Z",
            truncated=truncated,
        ),
    )


class FakeAIClient:
    """An ``AIClient`` that records requests and returns a canned response."""

    def __init__(self, response: str = "", error: AISummaryError | None = None) -> None:
        self.response = response
        self.error = error
        self.requests: list[AIRequest] = []

    def complete(self, request: AIRequest) -> str:
        """Record the request, then return the canned response or raise."""
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return self.response
