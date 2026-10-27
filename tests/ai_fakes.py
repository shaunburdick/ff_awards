"""
Shared fixtures for the AI summary tests.

Builders produce the real domain models, so the digest, service and rendering
tests all exercise the same shapes the report produces. No network: the fake
client and fake transport live here too.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Mapping, Sequence

from ff_tracker.exceptions import AIMemoryStoreError, AISummaryError
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
from ff_tracker.services.ai_memory import (
    MemoryEntry,
    MemoryFile,
    MemoryLeague,
    serialize_archive,
)

WEEK = 6
LEAGUE_A = "MM Driveway Surfers"
LEAGUE_B = "My 2026 League"


def make_owner(name: str) -> Owner:
    """Create an owner whose full name is the display name."""
    first, _, last = name.partition(" ")
    return Owner(
        display_name=name, first_name=first, last_name=last, id=name.lower().replace(" ", "-")
    )


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


def make_game(
    team: str,
    score: float,
    opponent: str,
    opponent_score: float,
    *,
    division: str = LEAGUE_A,
    week: int = 1,
) -> GameResult:
    """One team's season game, with the outcome derived from the scores."""
    return GameResult(
        team_name=team,
        score=score,
        opponent_name=opponent,
        opponent_score=opponent_score,
        won=score > opponent_score,
        week=week,
        margin=abs(score - opponent_score),
        division=division,
    )


def make_game_pair(
    team1: str,
    score1: float,
    team2: str,
    score2: float,
    *,
    division: str = LEAGUE_A,
    week: int = 1,
) -> list[GameResult]:
    """Both rows of one season game, as the ESPN extractor emits them."""
    return [
        make_game(team1, score1, team2, score2, division=division, week=week),
        make_game(team2, score2, team1, score1, division=division, week=week),
    ]


def make_season_games(
    scores: Mapping[str, Sequence[float]],
    schedule: Sequence[Sequence[tuple[str, str]]],
    *,
    division: str = LEAGUE_A,
    first_week: int = 1,
) -> list[GameResult]:
    """One game per scheduled pair per week; ``scores[team][index]`` is that week."""
    return [
        game
        for offset, pairs in enumerate(schedule)
        for team1, team2 in pairs
        for game in make_game_pair(
            team1,
            scores[team1][offset],
            team2,
            scores[team2][offset],
            division=division,
            week=first_week + offset,
        )
    ]


def make_teams_from_games(
    names: Sequence[str],
    games: Sequence[GameResult],
    *,
    division: str = LEAGUE_A,
    playoff_slots: int = 2,
) -> list[TeamStats]:
    """Season stats derived from the games, so the standings and history agree."""
    wins: dict[str, int] = dict.fromkeys(names, 0)
    losses: dict[str, int] = dict.fromkeys(names, 0)
    points_for: dict[str, float] = dict.fromkeys(names, 0.0)
    points_against: dict[str, float] = dict.fromkeys(names, 0.0)
    for game in games:
        if game.team_name in wins:
            wins[game.team_name] += 1 if game.won else 0
            losses[game.team_name] += 0 if game.won else 1
            points_for[game.team_name] += game.score
            points_against[game.team_name] += game.opponent_score

    ranked = sorted(names, key=lambda name: (wins[name], points_for[name]), reverse=True)
    in_position = set(ranked[:playoff_slots])
    return [
        make_team(
            name,
            division=division,
            wins=wins[name],
            losses=losses[name],
            points_for=points_for[name],
            points_against=points_against[name],
            in_playoff_position=name in in_position,
        )
        for name in names
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


# Six weeks of scores per team, arranged so week 6 puts the highest score in
# the first division, the biggest winning margin in the second and the closest
# game in the third (AC-027). Records differ per team, so the league-wide
# ranking is not a roster or division order.
THREE_DIVISION_SCORES: dict[str, dict[str, list[float]]] = {
    "MM Driveway Surfers": {
        "Butt Fumble": [110.0, 120.0, 95.0, 130.0, 105.0, 150.0],
        "Donut Lose": [95.0, 100.0, 90.0, 99.0, 98.0, 100.0],
        "In JJ We Trust": [88.0, 92.0, 98.0, 105.0, 97.0, 120.0],
        "Caserta Chumps": [80.0, 85.0, 99.0, 100.0, 95.0, 115.0],
    },
    "My 2026 League": {
        "Sunday Scaries": [105.0, 118.0, 110.0, 125.0, 130.0, 145.0],
        "Waiver Wire": [90.0, 95.0, 100.0, 99.0, 97.0, 75.0],
        "Bench Mob": [88.0, 92.0, 101.0, 98.0, 98.0, 110.0],
        "Trading Places": [85.0, 90.0, 99.0, 95.0, 99.0, 104.0],
    },
    "The Hood 2026": {
        "Hood Rats": [102.0, 111.0, 108.0, 120.0, 118.0, 145.0],
        "Late Round Larry": [99.0, 100.0, 105.0, 110.0, 112.0, 144.5],
        "Two Minute Drill": [90.0, 95.0, 101.0, 94.0, 100.0, 99.0],
        "Sack Exchange": [85.0, 88.0, 99.0, 95.0, 96.0, 90.0],
    },
}
THREE_DIVISION_PAIRS: list[list[tuple[str, str]]] = [
    [("Butt Fumble", "Donut Lose"), ("In JJ We Trust", "Caserta Chumps")],
    [("Sunday Scaries", "Waiver Wire"), ("Bench Mob", "Trading Places")],
    [("Hood Rats", "Late Round Larry"), ("Two Minute Drill", "Sack Exchange")],
]
THREE_DIVISION_PLAYERS: dict[str, tuple[str, str, float]] = {
    "MM Driveway Surfers": ("Christian McCaffrey", "RB", 30.70),
    "My 2026 League": ("Malik Nabers", "WR", 28.50),
    "The Hood 2026": ("Bijan Robinson", "RB", 27.20),
}


def make_three_division_divisions(week: int = 6) -> list[DivisionData]:
    """Three leagues with six weeks behind them and a designed week 6 (AC-027)."""
    divisions: list[DivisionData] = []
    for index, name in enumerate(THREE_DIVISION_SCORES):
        scores = THREE_DIVISION_SCORES[name]
        schedule = [THREE_DIVISION_PAIRS[index]] * len(next(iter(scores.values())))
        games = make_season_games(scores, schedule, division=name)
        player, position, points = THREE_DIVISION_PLAYERS[name]
        final = {team: values[week - 1] for team, values in scores.items()}
        divisions.append(
            make_division(
                name,
                league_id=111 + index,
                teams=make_teams_from_games(list(scores), games, division=name),
                games=games,
                weekly_games=[
                    row
                    for team1, team2 in THREE_DIVISION_PAIRS[index]
                    for row in make_matchup_pair(
                        team1,
                        final[team1],
                        team2,
                        final[team2],
                        division=name,
                        week=week,
                    )
                ],
                weekly_players=[
                    make_player(
                        player,
                        points,
                        position=position,
                        team=THREE_DIVISION_PAIRS[index][0][0],
                        division=name,
                        week=week,
                    )
                ],
                reg_season_count=14,
            )
        )
    return divisions


def make_large_divisions(
    teams_per_division: int = 8, division_count: int = 3
) -> list[DivisionData]:
    """More teams than the console's overall table shows (24 by default)."""
    divisions: list[DivisionData] = []
    for index in range(division_count):
        name = f"League {index + 1}"
        names = [f"Team {index + 1}-{slot + 1}" for slot in range(teams_per_division)]
        games = []
        for slot in range(0, len(names), 2):
            games.extend(
                make_game_pair(
                    names[slot],
                    150.0 - 5.0 * slot - index,
                    names[slot + 1],
                    90.0 + 2.0 * slot + index * 0.5,
                    division=name,
                    week=WEEK,
                )
            )
        divisions.append(
            make_division(
                name,
                league_id=200 + index,
                teams=make_teams_from_games(names, games, division=name),
                games=games,
                reg_season_count=14,
            )
        )
    return divisions


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
            weekly_players=[
                make_player("Malik Nabers", 28.50, position="WR", slot="WR", division=LEAGUE_B)
            ],
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
            weekly_players=[
                make_player("Christian McCaffrey", 30.70, division=LEAGUE_A, week=week)
            ],
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
            weekly_players=[
                make_player("Christian McCaffrey", 30.70, division=LEAGUE_A, week=week)
            ],
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
            model="deepseek-v4.1-flash",
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


class FakeTransport:
    """An ``HTTPTransport`` that records requests and returns bytes or raises."""

    def __init__(self, body: bytes = b"", error: BaseException | None = None) -> None:
        self.body = body
        self.error = error
        self.calls: list[tuple[urllib.request.Request, int]] = []

    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes:
        """Record the request, then return the canned body or raise."""
        self.calls.append((request, timeout))
        if self.error is not None:
            raise self.error
        return self.body


def envelope(
    content: str, finish_reason: str = "stop", usage: dict[str, int] | None = None
) -> bytes:
    """Build a Chat Completions response body."""
    payload: dict[str, object] = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
    }
    if usage is not None:
        payload["usage"] = usage
    return json.dumps(payload).encode("utf-8")


def make_memory_entry(week: int, season: int = 2026) -> MemoryEntry:
    """A published summary for one week, as the memory log stores it."""
    return MemoryEntry(
        week=week,
        generated_at=f"{season}-10-{week:02d}T05:00:00Z",
        headline=f"Week {week} headline",
        season_note=f"Week {week} season note.",
        leagues=[
            MemoryLeague(
                league=LEAGUE_A,
                paragraphs=[f"Week {week} prose about Butt Fumble."],
                bullets=[f"Week {week} bullet"],
            )
        ],
    )


def make_memory_archive(weeks: Sequence[int] = (1, 2, 3, 4, 5, 6), season: int = 2026) -> bytes:
    """A serialised archive with one entry per week, as an earlier run left it."""
    archive = MemoryFile(
        schema=1,
        season=season,
        entries=[make_memory_entry(week, season) for week in weeks],
    )
    return serialize_archive(archive)


class FakeMemoryStore:
    """A ``MemoryStore`` that records calls, holds bytes and can fail per call."""

    def __init__(
        self,
        data: bytes | None = None,
        *,
        read_errors: Sequence[AIMemoryStoreError | None] = (),
        write_errors: Sequence[AIMemoryStoreError | None] = (),
    ) -> None:
        self.data = data
        self._read_errors = list(read_errors)
        self._write_errors = list(write_errors)
        self.read_calls = 0
        self.write_calls = 0

    def load(self) -> bytes | None:
        """Record the read, then return the bytes or raise the canned error."""
        self.read_calls += 1
        error = self._read_errors.pop(0) if self._read_errors else None
        if error is not None:
            raise error
        return self.data

    def save(self, data: bytes) -> None:
        """Record the write, then store the bytes or raise the canned error."""
        self.write_calls += 1
        error = self._write_errors.pop(0) if self._write_errors else None
        if error is not None:
            raise error
        self.data = data
