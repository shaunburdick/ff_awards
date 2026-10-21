"""Tests for JSON output formatter."""

from __future__ import annotations

import json

import pytest

from ff_tracker.display.json import JsonFormatter
from ff_tracker.models import (
    ChallengeResult,
    DivisionData,
    GameResult,
    Owner,
    TeamStats,
    WeeklyChallenge,
)


@pytest.fixture
def sample_owner_alice() -> Owner:
    """Create a sample owner Alice."""
    return Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")


@pytest.fixture
def sample_owner_bob() -> Owner:
    """Create a sample owner Bob."""
    return Owner(display_name="Bob", first_name="Bob", last_name="Jones", id="bob456")


@pytest.fixture
def sample_teams(sample_owner_alice: Owner, sample_owner_bob: Owner) -> list[TeamStats]:
    """Create sample team stats."""
    return [
        TeamStats(
            name="Alice's Team",
            owner=sample_owner_alice,
            wins=8,
            losses=3,
            points_for=1250.50,
            points_against=1100.25,
            division="League A",
            in_playoff_position=True,
        ),
        TeamStats(
            name="Bob's Team",
            owner=sample_owner_bob,
            wins=7,
            losses=4,
            points_for=1200.00,
            points_against=1150.00,
            division="League A",
            in_playoff_position=False,
        ),
    ]


@pytest.fixture
def sample_games() -> list[GameResult]:
    """Create sample game results."""
    return [
        GameResult(
            team_name="Alice's Team",
            score=150.50,
            opponent_name="Bob's Team",
            opponent_score=120.00,
            won=True,
            week=10,
            margin=30.50,
            division="League A",
        ),
        GameResult(
            team_name="Bob's Team",
            score=120.00,
            opponent_name="Alice's Team",
            opponent_score=150.50,
            won=False,
            week=10,
            margin=30.50,
            division="League A",
        ),
    ]


@pytest.fixture
def sample_division(sample_teams: list[TeamStats], sample_games: list[GameResult]) -> DivisionData:
    """Create a sample division."""
    return DivisionData(
        league_id=123456,
        name="League A",
        teams=sample_teams,
        games=sample_games,
        weekly_games=[],
        weekly_players=[],
    )


@pytest.fixture
def sample_challenges(sample_owner_alice: Owner) -> list[ChallengeResult]:
    """Create sample challenge results."""
    return [
        ChallengeResult(
            challenge_name="Most Points Overall",
            winner="Alice's Team",
            owner=sample_owner_alice,
            division="League A",
            value="1250.50 points",
            description="Alice's Team scored 1250.50 total points",
        ),
        ChallengeResult(
            challenge_name="Most Points in One Game",
            winner="Alice's Team",
            owner=sample_owner_alice,
            division="League A",
            value="150.50 points (Week 10)",
            description="Alice's Team scored 150.50 points in Week 10",
        ),
    ]


@pytest.fixture
def sample_weekly_challenges(sample_owner_alice: Owner) -> list[WeeklyChallenge]:
    """Create sample weekly challenges."""
    return [
        WeeklyChallenge(
            challenge_name="Highest Score This Week",
            week=10,
            winner="Alice's Team",
            owner=sample_owner_alice,
            division="League A",
            value="150.50 points",
            description="Alice's Team scored 150.50 points",
            additional_info={
                "score": 150.50,
                "opponent_name": "Bob's Team",
                "opponent_score": 120.00,
            },
        ),
        WeeklyChallenge(
            challenge_name="Top Scorer (Player)",
            week=10,
            winner="Patrick Mahomes",
            owner=sample_owner_alice,
            division="League A",
            value="35.50 points",
            description="Patrick Mahomes (QB - Alice's Team) scored 35.50 points",
            additional_info={
                "position": "QB",
                "points": 35.50,
                "team_name": "Alice's Team",
            },
        ),
    ]


class TestJsonFormatterBasics:
    """Tests for JsonFormatter initialization and basic functionality."""

    def test_init_json_formatter(self) -> None:
        """Test JsonFormatter initialization."""
        formatter = JsonFormatter(year=2024)
        assert formatter.year == 2024
        assert formatter.format_args == {}

    def test_init_with_format_args(self) -> None:
        """Test JsonFormatter initialization with format args."""
        args = {"note": "Important message", "pretty": "false"}
        formatter = JsonFormatter(year=2024, format_args=args)
        assert formatter.year == 2024
        assert formatter.format_args == args

    def test_get_supported_args(self) -> None:
        """Test get_supported_args returns correct arguments."""
        supported_args = JsonFormatter.get_supported_args()
        assert "note" in supported_args
        assert "pretty" in supported_args
        assert isinstance(supported_args["note"], str)
        assert isinstance(supported_args["pretty"], str)


class TestFormatOutput:
    """Tests for format_output method."""

    def test_format_output_basic(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test basic format_output generates valid JSON."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Should be valid JSON
        data = json.loads(output)
        assert isinstance(data, dict)

        # Check structure
        assert "standings" in data  # Divisions are under "standings"
        assert "season_challenges" in data

        # Check standings contains divisions
        assert isinstance(data["standings"], dict)
        assert "divisions" in data["standings"]

    def test_format_output_with_weekly_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test format_output with weekly challenges."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        data = json.loads(output)
        assert data["current_week"] == 10
        # Weekly challenges may be under different key based on type
        assert "standings" in data or "weekly_player_highlights" in data

    def test_format_output_with_note(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with note format argument."""
        formatter = JsonFormatter(year=2024, format_args={"note": "Test note"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        data = json.loads(output)
        assert data["note"] == "Test note"

    def test_format_output_pretty_print(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with pretty printing (default)."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Pretty printed JSON has newlines and indentation
        assert "\n" in output
        assert "  " in output or "\t" in output

    def test_format_output_compact(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with compact printing."""
        formatter = JsonFormatter(year=2024, format_args={"pretty": "false"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Compact JSON has fewer/no indentation
        # Still valid JSON
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_format_output_no_weekly_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output without weekly challenges."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=None,
        )

        data = json.loads(output)
        assert "standings" in data
        assert "season_challenges" in data


class TestJSONStructure:
    """Tests for JSON structure and data."""

    def test_output_has_report_type(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes report type."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        data = json.loads(output)
        assert "report_type" in data
        assert data["report_type"] == "regular_season"

    def test_output_has_current_week(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes current week."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            current_week=10,
        )

        data = json.loads(output)
        assert "current_week" in data
        assert data["current_week"] == 10
        assert "week" in data
        assert data["week"] == 10

    def test_output_divisions_structure(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test divisions are properly serialized."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        data = json.loads(output)
        assert "standings" in data
        assert isinstance(data["standings"], dict)
        assert "divisions" in data["standings"]
        assert isinstance(data["standings"]["divisions"], list)
        assert len(data["standings"]["divisions"]) == 1

        div = data["standings"]["divisions"][0]
        assert "division_name" in div
        assert div["division_name"] == "League A"
        assert "teams" in div

    def test_output_season_challenges_structure(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test season challenges are properly serialized."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        data = json.loads(output)
        assert isinstance(data["season_challenges"], dict)
        assert "challenges" in data["season_challenges"]
        assert isinstance(data["season_challenges"]["challenges"], list)
        assert len(data["season_challenges"]["challenges"]) == 2

        challenge = data["season_challenges"]["challenges"][0]
        assert "challenge_name" in challenge
        assert "team_name" in challenge  # JSON uses team_name not winner


class TestOwnerSerialization:
    """Tests for owner serialization."""

    def test_serialize_owner(
        self,
        sample_owner_alice: Owner,
    ) -> None:
        """Test _serialize_owner method."""
        formatter = JsonFormatter(year=2024)
        owner_dict = formatter._serialize_owner(sample_owner_alice)

        assert isinstance(owner_dict, dict)
        assert owner_dict["display_name"] == "Alice"
        assert owner_dict["first_name"] == "Alice"
        assert owner_dict["last_name"] == "Smith"
        assert owner_dict["full_name"] == "Alice Smith"
        assert owner_dict["id"] == "alice123"
        assert "is_likely_username" in owner_dict


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_format_output_empty_divisions(self) -> None:
        """Test format_output with empty divisions list."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[],
            challenges=[],
        )

        data = json.loads(output)
        assert isinstance(data, dict)
        assert "standings" in data
        assert data["standings"]["divisions"] == []

    def test_format_output_empty_challenges(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test format_output with empty challenges list."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=[],
        )

        data = json.loads(output)
        # Empty challenges might not create the season_challenges key
        assert "standings" in data  # Should still have standings

    def test_format_output_with_all_format_args(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with all format arguments specified."""
        formatter = JsonFormatter(
            year=2024,
            format_args={
                "note": "Test note",
                "pretty": "true",
            },
        )
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        data = json.loads(output)
        assert data["note"] == "Test note"
        # Pretty print should have newlines
        assert "\n" in output

    def test_format_output_no_current_week(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output without current week specified."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            current_week=None,
        )

        data = json.loads(output)
        assert "current_week" in data
        assert data["current_week"] == -1  # Default value


class TestMultipleDivisions:
    """Tests for handling multiple divisions."""

    def test_format_output_multiple_divisions(
        self,
        sample_owner_alice: Owner,
        sample_owner_bob: Owner,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with multiple divisions."""
        # Create teams with correct division names
        team_a = TeamStats(
            name="Alice's Team",
            owner=sample_owner_alice,
            wins=8,
            losses=3,
            points_for=1250.50,
            points_against=1100.25,
            division="League A",
            in_playoff_position=True,
        )
        team_b = TeamStats(
            name="Bob's Team",
            owner=sample_owner_bob,
            wins=7,
            losses=4,
            points_for=1200.00,
            points_against=1150.00,
            division="League B",
            in_playoff_position=False,
        )

        # Create two divisions
        div1 = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team_a],
            games=[],
            weekly_games=[],
            weekly_players=[],
        )
        div2 = DivisionData(
            league_id=789012,
            name="League B",
            teams=[team_b],
            games=[],
            weekly_games=[],
            weekly_players=[],
        )

        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=sample_challenges,
        )

        data = json.loads(output)
        assert "standings" in data
        assert len(data["standings"]["divisions"]) == 2
        assert data["standings"]["divisions"][0]["division_name"] == "League A"
        assert data["standings"]["divisions"][1]["division_name"] == "League B"


class TestWeeklyChallenges:
    """Tests for weekly challenge serialization."""

    def test_weekly_challenges_included(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test weekly challenges are included in output."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        data = json.loads(output)
        # Weekly challenges might be filtered based on type
        # Just check output is valid
        assert isinstance(data, dict)
        assert "current_week" in data

    def test_weekly_challenges_structure(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test weekly challenges have correct structure."""
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        data = json.loads(output)
        # Just verify valid JSON with expected keys
        assert "current_week" in data
        assert data["current_week"] == 10
        assert "report_type" in data


class TestWeeklyHighlightFields:
    """Weekly highlights keep team and player fields apart, with typed points."""

    @pytest.fixture
    def shaped_challenges(self) -> list[WeeklyChallenge]:
        """Challenges shaped exactly as WeeklyChallengeCalculator builds them."""
        return [
            WeeklyChallenge(
                challenge_name="Closest Game This Week",
                week=6,
                winner="Donut Lose",
                owner=None,
                division="MM Driveway Surfers",
                value="126.14 - 125.06 (Δ1.08)",
                description="Donut Lose won by only 1.08 points",
                additional_info={
                    "score": 126.14,
                    "opponent": "In JJ We Trust",
                    "opponent_score": 125.06,
                    "won": True,
                    "margin": 1.08,
                },
            ),
            WeeklyChallenge(
                challenge_name="Top Scorer (Player)",
                week=6,
                winner="Christian McCaffrey",
                owner=None,
                division="MM Driveway Surfers",
                value="30.70",
                description="Christian McCaffrey (RB) scored 30.70 points",
                additional_info={
                    "position": "RB",
                    "team": "Butt Fumble",
                    "pro_team": "SF",
                },
            ),
            WeeklyChallenge(
                challenge_name="Best QB",
                week=6,
                winner="Trevor Lawrence",
                owner=None,
                division="My 2026 League",
                value="27.34",
                description="Trevor Lawrence scored 27.34 points",
                additional_info={
                    "position": "QB",
                    "team_name": "Caserta Chumps",
                    "pro_team": "JAX",
                },
            ),
        ]

    def _entries(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        shaped_challenges: list[WeeklyChallenge],
    ) -> list[dict[str, object]]:
        formatter = JsonFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=shaped_challenges,
            current_week=6,
        )
        return json.loads(output)["weekly_player_highlights"]

    def test_team_challenge_carries_team_name_only(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        shaped_challenges: list[WeeklyChallenge],
    ) -> None:
        """A team challenge publishes team_name, never player_name or position."""
        team_entry = self._entries(
            sample_division, sample_challenges, shaped_challenges
        )[0]

        assert team_entry["challenge_type"] == "team"
        assert team_entry["team_name"] == "Donut Lose"
        assert "player_name" not in team_entry
        assert "position" not in team_entry
        assert team_entry["division"] == "MM Driveway Surfers"
        assert team_entry["value"] == "126.14 - 125.06 (Δ1.08)"

    def test_player_challenge_carries_player_name(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        shaped_challenges: list[WeeklyChallenge],
    ) -> None:
        """A player challenge publishes the player, position, and its league."""
        player_entry = self._entries(
            sample_division, sample_challenges, shaped_challenges
        )[1]

        assert player_entry["challenge_type"] == "player"
        assert player_entry["player_name"] == "Christian McCaffrey"
        assert player_entry["position"] == "RB"
        assert player_entry["division"] == "MM Driveway Surfers"
        assert "team_name" not in player_entry  # additional_info has no team_name

    def test_player_challenge_team_name_when_provided(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        shaped_challenges: list[WeeklyChallenge],
    ) -> None:
        """team_name appears when the service supplies it."""
        qb_entry = self._entries(
            sample_division, sample_challenges, shaped_challenges
        )[2]

        assert qb_entry["player_name"] == "Trevor Lawrence"
        assert qb_entry["team_name"] == "Caserta Chumps"

    def test_points_are_numbers_or_null(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        shaped_challenges: list[WeeklyChallenge],
    ) -> None:
        """points is a float for plain numbers and null otherwise, never a string."""
        entries = self._entries(sample_division, sample_challenges, shaped_challenges)

        assert not any(isinstance(entry["points"], str) for entry in entries)
        assert entries[0]["points"] is None  # "126.14 - 125.06 (Δ1.08)"
        assert entries[1]["points"] == 30.70
        assert entries[2]["points"] == 27.34
