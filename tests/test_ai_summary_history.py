"""Tests for the season history block (FR-011, AC-024, AC-025, AC-026)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from ai_fakes import (
    LEAGUE_A,
    FakeAIClient,
    make_championship,
    make_division,
    make_playoff_bracket,
    make_season_games,
    make_team,
    make_teams_from_games,
)

from ff_tracker.config import AISummaryConfig
from ff_tracker.models import ChampionshipLeaderboard, DivisionData
from ff_tracker.services.ai_digest import build_digest
from ff_tracker.services.ai_history import AILeagueHistory, AITeamHistory
from ff_tracker.services.ai_summary_service import AISummaryService

# Three weeks of scores with a new pairing in week 3, so streaks and trends are
# not uniform: Butt Fumble is unbeaten, Caserta Chumps has not won.
SCORES = {
    "Butt Fumble": [100.0, 110.0, 120.0],
    "Donut Lose": [90.0, 90.0, 130.0],
    "In JJ We Trust": [80.0, 105.0, 100.0],
    "Caserta Chumps": [70.0, 85.0, 60.0],
}
SCHEDULE = [
    [("Butt Fumble", "Donut Lose"), ("In JJ We Trust", "Caserta Chumps")],
    [("Butt Fumble", "Donut Lose"), ("In JJ We Trust", "Caserta Chumps")],
    [("Butt Fumble", "Caserta Chumps"), ("Donut Lose", "In JJ We Trust")],
]

# Games for weeks 1-3 under ROSTER order, against hand-written standings that
# count a fourth week the games lack.
SHORT_SCORES = {
    "Butt Fumble": [100.0, 90.0, 95.0],
    "Donut Lose": [90.0, 80.0, 85.0],
    "In JJ We Trust": [90.0, 100.0, 105.0],
    "Caserta Chumps": [80.0, 90.0, 95.0],
}
SHORT_SCHEDULE = [
    [("Butt Fumble", "Donut Lose"), ("In JJ We Trust", "Caserta Chumps")],
    [("Butt Fumble", "Donut Lose"), ("In JJ We Trust", "Caserta Chumps")],
    [("Butt Fumble", "Donut Lose"), ("In JJ We Trust", "Caserta Chumps")],
]

RESPONSE = json.dumps(
    {
        "headline": "Headline",
        "leagues": [{"league": LEAGUE_A, "paragraphs": ["A week happened."], "bullets": []}],
        "season_note": "Note.",
    }
)


def _league_history(divisions: list[DivisionData], week: int = 3) -> AILeagueHistory:
    history = build_digest(divisions, [], None, week, None)["leagues"][0]["history"]
    assert history is not None
    return history


def _team(history: AILeagueHistory, name: str) -> AITeamHistory:
    for row in history["teams"]:
        if row["team"] == name:
            return row
    raise AssertionError(f"{name} is missing from the history block")


@pytest.fixture
def played() -> DivisionData:
    """Four teams, weeks 1-3 played, standings derived from the same games."""
    games = make_season_games(SCORES, SCHEDULE)
    return make_division(LEAGUE_A, teams=make_teams_from_games(list(SCORES), games), games=games)


@pytest.fixture
def short_games() -> DivisionData:
    """Games for weeks 1-3, standings that count a fourth week the games lack."""
    games = make_season_games(SHORT_SCORES, SHORT_SCHEDULE)
    teams = [
        make_team("In JJ We Trust", wins=1, losses=3, points_for=440.0),
        make_team("Butt Fumble", wins=2, losses=2, points_for=460.0),
        make_team("Caserta Chumps", wins=3, losses=1, points_for=480.0),
        make_team("Donut Lose", wins=4, losses=0, points_for=500.0),
    ]
    return make_division(LEAGUE_A, teams=teams, games=games)


class TestFixtureOne:
    """AC-024 on a league whose standings and games agree."""

    def test_weeks_included_is_every_week_played_ascending(self, played: DivisionData) -> None:
        assert _league_history([played])["weeks_included"] == [1, 2, 3]

    def test_rank_by_week_is_the_standings_order_at_each_week(self, played: DivisionData) -> None:
        history = _league_history([played])

        assert _team(history, "Butt Fumble")["rank_by_week"] == [
            {"week": 1, "rank": 1},
            {"week": 2, "rank": 1},
            {"week": 3, "rank": 1},
        ]
        assert _team(history, "Donut Lose")["rank_by_week"] == [
            {"week": 1, "rank": 3},
            {"week": 2, "rank": 3},
            {"week": 3, "rank": 3},
        ]
        assert [row["rank"] for row in _team(history, "Caserta Chumps")["rank_by_week"]] == [
            4,
            4,
            4,
        ]

    def test_teams_follow_the_anchor_order(self, played: DivisionData) -> None:
        history = _league_history([played])

        assert [row["team"] for row in history["teams"]] == [
            "Butt Fumble",
            "In JJ We Trust",
            "Donut Lose",
            "Caserta Chumps",
        ]
        assert [row["rank"] for row in _team(history, "In JJ We Trust")["rank_by_week"]] == [
            2,
            2,
            2,
        ]

    def test_head_to_head_is_one_row_per_opponent_sorted_by_name(
        self, played: DivisionData
    ) -> None:
        head_to_head = _team(_league_history([played]), "Butt Fumble")["head_to_head"]

        assert head_to_head == [
            {"opponent": "Caserta Chumps", "wins": 1, "losses": 0},
            {"opponent": "Donut Lose", "wins": 2, "losses": 0},
        ]
        assert all(set(row) == {"opponent", "wins", "losses"} for row in head_to_head)

    def test_streak_is_the_run_at_the_latest_week(self, played: DivisionData) -> None:
        history = _league_history([played])

        assert _team(history, "Butt Fumble")["streak"] == {"kind": "win", "length": 3}
        assert _team(history, "Caserta Chumps")["streak"] == {"kind": "loss", "length": 3}
        assert _team(history, "In JJ We Trust")["streak"] == {"kind": "loss", "length": 1}
        assert _team(history, "Donut Lose")["streak"] == {"kind": "win", "length": 1}

    def test_best_and_worst_week_carry_the_score_and_the_week(self, played: DivisionData) -> None:
        history = _league_history([played])

        assert _team(history, "Butt Fumble")["best_week"] == {"week": 3, "score": 120.0}
        assert _team(history, "Butt Fumble")["worst_week"] == {"week": 1, "score": 100.0}
        assert _team(history, "Caserta Chumps")["worst_week"] == {"week": 3, "score": 60.0}

    def test_average_margin_is_the_signed_mean(self, played: DivisionData) -> None:
        """+30.0 for the unbeaten team, -30.0 for the team that lost every week."""
        history = _league_history([played])

        assert _team(history, "Butt Fumble")["average_margin"] == 30.0
        assert _team(history, "Caserta Chumps")["average_margin"] == -30.0

    def test_largest_win_and_loss_are_magnitudes(self, played: DivisionData) -> None:
        history = _league_history([played])

        assert _team(history, "Butt Fumble")["largest_win"] == 60.0
        assert _team(history, "Caserta Chumps")["largest_loss"] == 60.0
        assert _team(history, "Donut Lose")["largest_win"] == 30.0
        assert _team(history, "Donut Lose")["largest_loss"] == 20.0

    def test_unbeaten_team_has_no_largest_loss(self, played: DivisionData) -> None:
        assert _team(_league_history([played]), "Butt Fumble")["largest_loss"] is None

    def test_winless_team_has_no_largest_win(self, played: DivisionData) -> None:
        assert _team(_league_history([played]), "Caserta Chumps")["largest_win"] is None


class TestScoringTrend:
    """AC-024: one fixture per trend value, each naming the number it beats."""

    @staticmethod
    def _trends() -> dict[str, str | None]:
        scores = {
            "Up Team": [100.0, 120.0],
            "Up Filler": [50.0, 50.0],
            "Down Team": [130.0, 100.0],
            "Down Filler": [50.0, 50.0],
            "Flat Team": [100.0, 100.5],
            "Flat Filler": [50.0, 50.0],
            "Edge Team": [100.0, 101.0],
            "Edge Filler": [50.0, 50.0],
        }
        pairs = [
            ("Up Team", "Up Filler"),
            ("Down Team", "Down Filler"),
            ("Flat Team", "Flat Filler"),
            ("Edge Team", "Edge Filler"),
        ]
        games = make_season_games(scores, [pairs, pairs])
        division = make_division(
            LEAGUE_A, teams=make_teams_from_games(list(scores), games), games=games
        )
        return {
            row["team"]: row["scoring_trend"] for row in _league_history([division], 2)["teams"]
        }

    def test_up_beats_the_earlier_mean_by_more_than_a_point(self) -> None:
        """Latest 120.0 against the earlier mean 100.0 is +20.0, past the 1.0 band."""
        assert self._trends()["Up Team"] == "up"

    def test_down_falls_more_than_a_point_below_the_mean(self) -> None:
        """Latest 100.0 against the earlier mean 130.0 is -30.0."""
        assert self._trends()["Down Team"] == "down"

    def test_flat_is_inside_the_band(self) -> None:
        """Latest 100.5 against 100.0 is +0.5, inside the 1.0 band."""
        assert self._trends()["Flat Team"] == "flat"

    def test_exactly_one_point_is_flat_not_up(self) -> None:
        """+1.0 is the band's edge, not a trend: the comparison is strict."""
        assert self._trends()["Edge Team"] == "flat"


class TestAnchor:
    """AC-024: the newest column comes from the standings, not from the games."""

    def test_latest_week_ranks_are_the_anchor_verbatim(self, short_games: DivisionData) -> None:
        history = _league_history([short_games])

        # The recomputation over weeks <= 3 would say Butt Fumble first; the
        # standings count a week the games lack and say Donut Lose is first.
        assert {row["team"]: row["rank_by_week"][-1]["rank"] for row in history["teams"]} == {
            "Donut Lose": 1,
            "Caserta Chumps": 2,
            "Butt Fumble": 3,
            "In JJ We Trust": 4,
        }
        assert all(
            row["rank_by_week"][-1]["week"] == history["weeks_included"][-1]
            for row in history["teams"]
        )

    def test_weeks_included_only_holds_weeks_the_games_hold(
        self, short_games: DivisionData
    ) -> None:
        assert _league_history([short_games])["weeks_included"] == [1, 2, 3]

    def test_earlier_weeks_keep_the_anchors_relative_order_on_a_tie(
        self, short_games: DivisionData
    ) -> None:
        """Butt Fumble and In JJ We Trust tie at 2-0 / 190.0 through week 2."""
        history = _league_history([short_games])

        assert _team(history, "Butt Fumble")["rank_by_week"][1] == {"week": 2, "rank": 1}
        assert _team(history, "In JJ We Trust")["rank_by_week"][1] == {"week": 2, "rank": 2}

    def test_standings_missing_games_still_lists_every_team(
        self, short_games: DivisionData
    ) -> None:
        history = _league_history([short_games])

        assert [row["team"] for row in history["teams"]] == [
            "Donut Lose",
            "Caserta Chumps",
            "Butt Fumble",
            "In JJ We Trust",
        ]


class TestHonestNulls:
    """FR-011 and plan Decision 12: no game means null, and the team stays listed."""

    def test_team_with_no_game_is_listed_with_nulls(self) -> None:
        games = make_season_games(SCORES, SCHEDULE)
        teams = make_teams_from_games(list(SCORES), games) + [
            make_team("Ghost Team", wins=0, losses=0, points_for=0.0, points_against=0.0)
        ]
        history = _league_history([make_division(LEAGUE_A, teams=teams, games=games)])
        ghost = _team(history, "Ghost Team")

        assert ghost["streak"] is None
        assert ghost["best_week"] is None
        assert ghost["worst_week"] is None
        assert ghost["average_margin"] is None
        assert ghost["head_to_head"] == []
        assert ghost["rank_by_week"] == [{"week": 3, "rank": 5}]
        assert len(history["teams"]) == 5

    def test_a_tie_counts_as_a_loss(self) -> None:
        """``GameResult.won`` is ``score > opponent_score``: a tie is not a win."""
        games = make_season_games(
            {"Even Steven": [100.0], "Also Even": [100.0]},
            [[("Even Steven", "Also Even")]],
        )
        teams = make_teams_from_games(["Even Steven", "Also Even"], games)
        history = _league_history([make_division(LEAGUE_A, teams=teams, games=games)], week=1)

        assert _team(history, "Even Steven")["streak"] == {"kind": "loss", "length": 1}
        assert _team(history, "Even Steven")["largest_loss"] == 0.0
        assert _team(history, "Even Steven")["largest_win"] is None
        assert _team(history, "Even Steven")["head_to_head"] == [
            {"opponent": "Also Even", "wins": 0, "losses": 1}
        ]


class TestNoGames:
    """AC-025: a league with no games sends null."""

    def test_history_is_null(self) -> None:
        division = make_division(LEAGUE_A, teams=[make_team("Butt Fumble")])

        assert build_digest([division], [], None, 6, None)["leagues"][0]["history"] is None

    def test_one_week_has_one_column_a_streak_of_one_and_no_trend(self) -> None:
        games = make_season_games(
            {"Butt Fumble": [120.0], "Donut Lose": [100.0]},
            [[("Butt Fumble", "Donut Lose")]],
        )
        teams = make_teams_from_games(["Butt Fumble", "Donut Lose"], games)
        history = _league_history([make_division(LEAGUE_A, teams=teams, games=games)], week=1)

        assert history["weeks_included"] == [1]
        for row in history["teams"]:
            assert row["scoring_trend"] is None
            assert row["streak"] is not None
            assert row["streak"]["length"] == 1
            assert len(row["rank_by_week"]) == 1


class TestModes:
    """AC-025: the block is present in all three modes and costs no extra call."""

    def _modes(
        self,
    ) -> list[tuple[DivisionData, int, ChampionshipLeaderboard | None]]:
        games = make_season_games(SCORES, SCHEDULE)
        teams = make_teams_from_games(list(SCORES), games)
        with_bracket = make_playoff_bracket(week=15)
        return [
            (make_division(LEAGUE_A, teams=teams, games=games), 3, None),
            (
                make_division(LEAGUE_A, teams=teams, games=games, playoff_bracket=with_bracket),
                15,
                None,
            ),
            (make_division(LEAGUE_A, teams=teams, games=games), 17, make_championship()),
        ]

    def test_every_mode_carries_the_block_and_makes_one_provider_call(self) -> None:
        for division, week, championship in self._modes():
            digest = build_digest([division], [], None, week, championship)
            history = digest["leagues"][0]["history"]
            assert history is not None
            assert history["weeks_included"] == [1, 2, 3]
            assert len(history["teams"]) == 4

            client = FakeAIClient(response=RESPONSE)
            service = AISummaryService(AISummaryConfig(enabled=True, api_key="sk-test"), client)
            with patch("urllib.request.urlopen") as urlopen:
                service.generate([division], [], None, week, championship)

            urlopen.assert_not_called()
            assert len(client.requests) == 1

    def test_championship_keeps_the_anchor_even_though_it_shows_no_standings(self) -> None:
        games = make_season_games(SCORES, SCHEDULE)
        division = make_division(
            LEAGUE_A, teams=make_teams_from_games(list(SCORES), games), games=games
        )

        league = build_digest([division], [], None, 17, make_championship())["leagues"][0]

        assert league["standings"] == []
        assert league["history"] is not None
        assert [row["rank"] for row in league["history"]["teams"][0]["rank_by_week"]] == [
            1,
            1,
            1,
        ]
