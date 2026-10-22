"""Tests for the AI digest payload (FR-002)."""

from __future__ import annotations

import json

from ai_fakes import (
    LEAGUE_A,
    LEAGUE_B,
    WEEK,
    make_championship,
    make_championship_divisions,
    make_division,
    make_matchup_pair,
    make_player_challenge,
    make_playoff_divisions,
    make_regular_divisions,
    make_regular_weekly_challenges,
    make_season_challenge,
    make_team,
    make_team_challenge,
)

from ff_tracker.models import (
    ChallengeResult,
    ChampionshipLeaderboard,
    DivisionData,
    WeeklyChallenge,
)
from ff_tracker.services.ai_digest import (
    MODE_CHAMPIONSHIP,
    MODE_PLAYOFFS,
    MODE_REGULAR,
    NO_MATCHUPS_NOTE,
    AIDigest,
    build_digest,
)

# Authored from FR-002's field list, not captured from the builder: a snapshot
# would bless a key the spec never asked for.
EXPECTED_KEYS: dict[str, set[str]] = {
    "digest": {"week", "mode", "leagues", "season_challenges", "playoffs", "championship"},
    "league": {
        "league",
        "teams",
        "week",
        "weeks_remaining",
        "standings",
        "standings_note",
        "matchups",
        "matchups_note",
        "weekly_challenges",
    },
    "standings_row": {
        "rank",
        "team",
        "owner",
        "record",
        "points_for",
        "points_against",
        "playoff_status",
    },
    "matchup_row": {
        "team",
        "score",
        "projected_score",
        "true_projection_diff",
        "opponent",
        "opponent_score",
        "opponent_projected_score",
        "opponent_true_projection_diff",
        "margin",
    },
    "weekly_challenge": {"challenge", "winner", "value"},
    "season_challenge": {"challenge", "winner", "league", "value", "historical"},
    "playoff_round": {"round", "matchups"},
    "playoff_matchup": {
        "round_name",
        "team1",
        "owner1",
        "score1",
        "team2",
        "owner2",
        "score2",
        "winner",
        "division",
    },
    "championship": {"leaderboard"},
    "championship_entry": {"rank", "team", "owner", "division", "score", "is_champion"},
}


def _digest(
    divisions: list[DivisionData],
    *,
    challenges: list[ChallengeResult] | None = None,
    weekly: list[WeeklyChallenge] | None = None,
    current_week: int | None = WEEK,
    championship: ChampionshipLeaderboard | None = None,
) -> AIDigest:
    return build_digest(
        divisions,
        challenges if challenges is not None else [make_season_challenge()],
        weekly if weekly is not None else make_regular_weekly_challenges(),
        current_week,
        championship,
    )


class TestRegularSeasonDigest:
    """The mid-season payload."""

    def test_mode_and_week(self) -> None:
        digest = _digest(make_regular_divisions())
        assert digest["mode"] == MODE_REGULAR
        assert digest["week"] == WEEK
        assert digest["playoffs"] is None
        assert digest["championship"] is None

    def test_one_entry_per_league_in_report_order(self) -> None:
        digest = _digest(make_regular_divisions())
        assert [league["league"] for league in digest["leagues"]] == [LEAGUE_A, LEAGUE_B]

    def test_league_carries_team_count_and_weeks_remaining(self) -> None:
        league = _digest(make_regular_divisions())["leagues"][0]
        assert league["teams"] == 2
        assert league["week"] == WEEK
        assert league["weeks_remaining"] == 8  # 14 regular-season weeks, week 6

    def test_standings_are_ranked_like_the_formatters(self) -> None:
        league = _digest(make_regular_divisions())["leagues"][0]
        rows = league["standings"]
        assert [row["rank"] for row in rows] == [1, 2]
        assert rows[0]["team"] == "Butt Fumble"  # 6 wins beats 2
        assert rows[0]["record"] == "6-0"
        assert rows[1]["playoff_status"] == "outside_playoff_position"
        assert rows[0]["playoff_status"] == "in_playoff_position"

    def test_standings_note_explains_the_status_field(self) -> None:
        """The model has paraphrased a bare status into an outcome; the note is the guard."""
        league = _digest(make_regular_divisions())["leagues"][0]

        assert league["standings_note"] is not None
        assert league["standings_note"].startswith("playoff_status is the current position")
        assert "not a final outcome" in league["standings_note"]

    def test_matchups_carry_both_sides_and_the_mirror_true_diff(self) -> None:
        league = _digest(make_regular_divisions())["leagues"][0]
        rows = league["matchups"]
        first = rows[0]
        assert first["team"] == "Butt Fumble"
        assert first["opponent"] == "Donut Lose"
        assert first["score"] == 147.78
        assert first["margin"] == 41.28
        assert first["true_projection_diff"] == 9.82
        # The opponent's true diff comes from the mirror row.
        assert first["opponent_true_projection_diff"] is None

    def test_opponent_true_diff_is_read_from_the_mirror_row(self) -> None:
        divisions = [
            make_division(
                LEAGUE_A,
                teams=[make_team("Butt Fumble"), make_team("Donut Lose")],
                weekly_games=make_matchup_pair(
                    "Butt Fumble", 126.14, "Donut Lose", 125.06, true_diff2=3.14
                ),
                reg_season_count=14,
            )
        ]
        first = _digest(divisions)["leagues"][0]["matchups"][0]

        assert first["true_projection_diff"] is None
        assert first["opponent_true_projection_diff"] == 3.14

    def test_weekly_challenges_are_attributed_to_the_winning_league(self) -> None:
        digest = _digest(make_regular_divisions())
        league_a = digest["leagues"][0]["weekly_challenges"]
        league_b = digest["leagues"][1]["weekly_challenges"]
        assert [row["challenge"] for row in league_a] == [
            "Highest Score This Week",
            "Closest Game This Week",
            "Top Scorer (Player)",
        ]
        assert [row["challenge"] for row in league_b] == ["Best WR"]

    def test_season_challenges_are_not_historical_mid_season(self) -> None:
        digest = _digest(make_regular_divisions())
        assert digest["season_challenges"][0]["historical"] is False
        assert digest["season_challenges"][0]["league"] == LEAGUE_A


class TestDigestUnknowns:
    """Unknown inputs are null, never invented."""

    def test_unknown_week(self) -> None:
        league = _digest(make_regular_divisions(), current_week=None)["leagues"][0]
        assert league["week"] is None
        assert league["weeks_remaining"] is None

    def test_unknown_season_length(self) -> None:
        divisions = [
            make_division(
                LEAGUE_A,
                teams=[make_team("Butt Fumble")],
                reg_season_count=None,
            )
        ]
        league = _digest(divisions)["leagues"][0]
        assert league["week"] == WEEK
        assert league["weeks_remaining"] is None

    def test_weeks_remaining_never_goes_negative(self) -> None:
        divisions = [make_division(LEAGUE_A, teams=[make_team("Butt Fumble")], reg_season_count=14)]
        league = _digest(divisions, current_week=18)["leagues"][0]
        assert league["weeks_remaining"] == 0

    def test_league_with_no_matchups_says_so(self) -> None:
        divisions = [make_division(LEAGUE_A, teams=[make_team("Butt Fumble")])]
        league = _digest(divisions)["leagues"][0]
        assert league["matchups"] == []
        assert league["matchups_note"] == NO_MATCHUPS_NOTE

    def test_league_with_no_weekly_data_has_no_challenges(self) -> None:
        divisions = [make_division(LEAGUE_A, teams=[make_team("Butt Fumble")])]
        league = _digest(divisions, weekly=[])["leagues"][0]
        assert league["weekly_challenges"] == []


class TestPlayoffDigest:
    """Weeks 15-16: bracket instead of team material, player highlights only."""

    def test_mode_and_bracket(self) -> None:
        digest = _digest(make_playoff_divisions(), current_week=15)
        assert digest["mode"] == MODE_PLAYOFFS
        assert digest["playoffs"] is not None
        assert digest["playoffs"]["round"] == "Semifinals"
        assert len(digest["playoffs"]["matchups"]) == 2

    def test_bracket_rows_are_flat_with_no_seed_key(self) -> None:
        digest = _digest(make_playoff_divisions(), current_week=15)
        assert digest["playoffs"] is not None
        row = digest["playoffs"]["matchups"][0]
        assert set(row) == EXPECTED_KEYS["playoff_matchup"]
        assert "seed1" not in row
        assert row["winner"] == "Butt Fumble"
        assert row["division"] == LEAGUE_A

    def test_unfinished_games_keep_none_scores(self) -> None:
        digest = _digest(make_playoff_divisions(), current_week=15)
        assert digest["playoffs"] is not None
        row = digest["playoffs"]["matchups"][1]
        assert row["score1"] is None
        assert row["score2"] is None
        assert row["winner"] is None

    def test_only_player_highlights_survive(self) -> None:
        weekly = [
            make_team_challenge("Highest Score This Week", "Butt Fumble"),
            make_player_challenge("Top Scorer (Player)", "Christian McCaffrey"),
        ]
        league = _digest(make_playoff_divisions(), weekly=weekly, current_week=15)["leagues"][0]
        assert [row["challenge"] for row in league["weekly_challenges"]] == ["Top Scorer (Player)"]

    def test_standings_remain_visible_in_playoffs(self) -> None:
        league = _digest(make_playoff_divisions(), current_week=15)["leagues"][0]
        assert len(league["standings"]) == 2
        assert league["standings_note"] is not None

    def test_matchups_are_suppressed_in_playoffs(self) -> None:
        """FR-002: the bracket is the playoff mode's matchup section."""
        divisions = make_playoff_divisions()
        divisions[0] = make_division(
            LEAGUE_A,
            teams=divisions[0].teams,
            weekly_games=make_matchup_pair("Butt Fumble", 132.40, "Donut Lose", 101.10),
            playoff_bracket=divisions[0].playoff_bracket,
            reg_season_count=14,
        )
        league = _digest(divisions, current_week=15)["leagues"][0]

        assert league["matchups"] == []
        assert league["matchups_note"] is None
        assert _digest(divisions, current_week=15)["playoffs"] is not None

    def test_season_challenges_are_historical(self) -> None:
        digest = _digest(make_playoff_divisions(), current_week=15)
        assert digest["season_challenges"][0]["historical"] is True


class TestChampionshipDigest:
    """Week 17: the leaderboard replaces standings and matchups."""

    def test_mode_and_leaderboard(self) -> None:
        digest = _digest(
            make_championship_divisions(), current_week=17, championship=make_championship()
        )
        assert digest["mode"] == MODE_CHAMPIONSHIP
        assert digest["championship"] is not None
        entries = digest["championship"]["leaderboard"]
        assert [entry["rank"] for entry in entries] == [1, 2]
        assert entries[0]["is_champion"] is True

    def test_championship_wins_the_mode_race_over_a_bracket(self) -> None:
        digest = _digest(
            make_playoff_divisions(),
            current_week=17,
            championship=make_championship(),
        )
        assert digest["mode"] == MODE_CHAMPIONSHIP
        assert digest["playoffs"] is None

    def test_no_standings_and_no_matchups(self) -> None:
        league = _digest(
            make_championship_divisions(), current_week=17, championship=make_championship()
        )["leagues"][0]
        assert league["standings"] == []
        assert league["standings_note"] is None
        assert league["matchups"] == []
        assert league["matchups_note"] is None

    def test_only_player_highlights(self) -> None:
        weekly = [
            make_team_challenge("Highest Score This Week", "Butt Fumble"),
            *make_regular_weekly_challenges()[2:3],
        ]
        league = _digest(
            make_championship_divisions(),
            weekly=weekly,
            current_week=17,
            championship=make_championship(),
        )["leagues"][0]
        assert [row["challenge"] for row in league["weekly_challenges"]] == ["Top Scorer (Player)"]


class TestDigestPrivacy:
    """FR-002: no league IDs, no credentials, no key."""

    def test_no_league_ids(self) -> None:
        divisions = [make_division(LEAGUE_A, league_id=987654321, teams=[make_team("Butt Fumble")])]
        serialised = json.dumps(_digest(divisions))
        assert "987654321" not in serialised
        assert "league_id" not in serialised

    def test_no_credentials_are_read_from_environment(self) -> None:
        serialised = json.dumps(_digest(make_regular_divisions()))
        for forbidden in ("ESPN_S2", "SWID", "AI_SUMMARY_API_KEY", "Bearer"):
            assert forbidden not in serialised


class TestDigestGoldenKeys:
    """The exact recursive key set, so a rename cannot pass silently."""

    def test_regular_digest_keys(self) -> None:
        digest = _digest(make_regular_divisions())
        assert set(digest) == EXPECTED_KEYS["digest"]
        assert len(digest["leagues"]) == 2
        for league in digest["leagues"]:
            assert set(league) == EXPECTED_KEYS["league"]
            assert league["standings"], "regular season must carry standings"
            for row in league["standings"]:
                assert set(row) == EXPECTED_KEYS["standings_row"]
            assert league["matchups"], "regular season must carry matchups"
            for matchup in league["matchups"]:
                assert set(matchup) == EXPECTED_KEYS["matchup_row"]
            for challenge in league["weekly_challenges"]:
                assert set(challenge) == EXPECTED_KEYS["weekly_challenge"]
        for challenge in digest["season_challenges"]:
            assert set(challenge) == EXPECTED_KEYS["season_challenge"]

    def test_playoff_digest_keys(self) -> None:
        digest = _digest(make_playoff_divisions(), current_week=15)
        assert set(digest) == EXPECTED_KEYS["digest"]
        assert digest["playoffs"] is not None
        assert set(digest["playoffs"]) == EXPECTED_KEYS["playoff_round"]
        for matchup in digest["playoffs"]["matchups"]:
            assert set(matchup) == EXPECTED_KEYS["playoff_matchup"]
        for league in digest["leagues"]:
            assert set(league) == EXPECTED_KEYS["league"]

    def test_championship_digest_keys(self) -> None:
        digest = _digest(
            make_championship_divisions(), current_week=17, championship=make_championship()
        )
        assert set(digest) == EXPECTED_KEYS["digest"]
        assert digest["championship"] is not None
        assert set(digest["championship"]) == EXPECTED_KEYS["championship"]
        for entry in digest["championship"]["leaderboard"]:
            assert set(entry) == EXPECTED_KEYS["championship_entry"]
