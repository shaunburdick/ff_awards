"""Tests for console output formatter."""

from __future__ import annotations

import pytest

from ff_tracker.display.console import ConsoleFormatter
from ff_tracker.models import (
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


class TestConsoleFormatterBasics:
    """Tests for ConsoleFormatter initialization and basic functionality."""

    def test_init_console_formatter(self) -> None:
        """Test ConsoleFormatter initialization."""
        formatter = ConsoleFormatter(year=2024)
        assert formatter.year == 2024
        assert formatter.format_args == {}

    def test_init_with_format_args(self) -> None:
        """Test ConsoleFormatter initialization with format args."""
        args = {"note": "Important message"}
        formatter = ConsoleFormatter(year=2024, format_args=args)
        assert formatter.year == 2024
        assert formatter.format_args == args

    def test_get_supported_args(self) -> None:
        """Test get_supported_args returns correct arguments."""
        supported_args = ConsoleFormatter.get_supported_args()
        assert "note" in supported_args
        assert isinstance(supported_args["note"], str)


class TestFormatOutput:
    """Tests for format_output method."""

    def test_format_output_basic(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test basic format_output with standings and challenges."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check header
        assert "Fantasy Football" in output
        assert "2024" in output
        assert "1 divisions, 2 teams total" in output

        # Check team names appear
        assert "Alice's Team" in output
        assert "Bob's Team" in output

        # Check challenge names appear
        assert "Most Points Overall" in output
        assert "Most Points in One Game" in output

    def test_format_output_with_weekly_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test format_output with weekly challenges."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        # Check current week display
        assert "Week: 10" in output or "Week 10" in output

        # Check weekly challenge names appear
        assert "Highest Score This Week" in output
        assert "Top Scorer" in output
        assert "Patrick Mahomes" in output

    def test_format_output_with_note(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with note format argument."""
        formatter = ConsoleFormatter(year=2024, format_args={"note": "Playoffs start next week!"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check note is displayed
        assert "Playoffs start next week!" in output

    def test_format_output_no_weekly_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output without weekly challenges."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=None,
        )

        # Should contain season challenges
        assert "Most Points Overall" in output
        assert output  # Non-empty output


class TestTableFormatting:
    """Tests for table formatting methods."""

    def test_format_challenge_table(
        self,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test challenge table formatting."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_challenge_table(sample_challenges)

        # All challenges should be present
        assert "Most Points Overall" in output
        assert "Most Points in One Game" in output
        assert "Alice's Team" in output

    def test_format_weekly_table(
        self,
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test weekly challenge table formatting."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_weekly_table(sample_weekly_challenges)

        # All weekly challenges should be present
        assert "Highest Score This Week" in output
        assert "Top Scorer" in output
        assert "Alice's Team" in output
        assert "Patrick Mahomes" in output

    def test_format_weekly_player_table(
        self,
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test weekly player table formatting."""
        # Filter to just player challenges
        player_challenges = [c for c in sample_weekly_challenges if "position" in c.additional_info]

        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_weekly_player_table(player_challenges)

        # Player challenges should be present
        assert "Patrick Mahomes" in output

    def test_format_division_table(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test division table formatting."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_division_table(sample_division)

        # Teams should be present (division name is in header, not table)
        assert "Alice's Team" in output
        assert "Bob's Team" in output
        assert "Alice Smith" in output  # Owner name
        assert "Bob Jones" in output  # Owner name

    def test_format_overall_table(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test overall table formatting."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_overall_table([sample_division])

        # Teams should be present
        assert "Alice's Team" in output
        assert "Bob's Team" in output


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_format_output_empty_divisions(self) -> None:
        """Test format_output with empty divisions list."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[],
            challenges=[],
        )

        # Should still produce valid output
        assert "Fantasy Football" in output
        assert "0 divisions, 0 teams total" in output

    def test_format_output_empty_challenges(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test format_output with empty challenges list."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=[],
        )

        # Should still contain team data
        assert "Alice's Team" in output

    def test_format_challenge_table_empty(self) -> None:
        """Test format_challenge_table with empty list."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_challenge_table([])

        # Should return empty string or minimal output
        assert isinstance(output, str)

    def test_format_weekly_table_empty(self) -> None:
        """Test format_weekly_table with empty list."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_weekly_table([])

        # Should return empty string or minimal output
        assert isinstance(output, str)


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
            division="League B",  # Different division
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

        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=sample_challenges,
        )

        # Check header shows correct counts
        assert "2 divisions" in output

        # Both divisions should appear
        assert "League A" in output
        assert "League B" in output

    def test_format_overall_table_multiple_divisions(
        self,
        sample_owner_alice: Owner,
        sample_owner_bob: Owner,
    ) -> None:
        """Test overall table with multiple divisions."""
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
            division="League B",  # Different division
            in_playoff_position=False,
        )

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

        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_overall_table([div1, div2])

        # Should combine teams from both divisions
        assert "Alice's Team" in output
        assert "Bob's Team" in output


class TestConsoleFormatterArgHelpers:
    """Test format argument helper methods."""

    def test_get_arg_int_with_valid_integer(self) -> None:
        """Test _get_arg_int with valid integer string."""
        formatter = ConsoleFormatter(year=2024, format_args={"max_teams": "5"})
        result = formatter._get_arg_int("max_teams", default=10)
        assert result == 5

    def test_get_arg_int_with_invalid_integer_returns_default(self) -> None:
        """Test _get_arg_int with invalid integer string returns default."""
        formatter = ConsoleFormatter(year=2024, format_args={"max_teams": "invalid"})
        result = formatter._get_arg_int("max_teams", default=10)
        assert result == 10

    def test_get_arg_int_with_missing_key_returns_default(self) -> None:
        """Test _get_arg_int with missing key returns default."""
        formatter = ConsoleFormatter(year=2024, format_args={})
        result = formatter._get_arg_int("max_teams", default=10)
        assert result == 10

    def test_get_arg_bool_with_true_values(self) -> None:
        """Test _get_arg_bool with various true values."""
        test_cases = ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON"]
        for value in test_cases:
            formatter = ConsoleFormatter(year=2024, format_args={"flag": value})
            result = formatter._get_arg_bool("flag", default=False)
            assert result is True, f"Expected True for value '{value}'"

    def test_get_arg_bool_with_false_values(self) -> None:
        """Test _get_arg_bool with false values."""
        test_cases = ["false", "FALSE", "0", "no", "other"]
        for value in test_cases:
            formatter = ConsoleFormatter(year=2024, format_args={"flag": value})
            result = formatter._get_arg_bool("flag", default=True)
            assert result is False, f"Expected False for value '{value}'"

    def test_get_arg_bool_with_missing_key_returns_default(self) -> None:
        """Test _get_arg_bool with missing key returns default."""
        formatter = ConsoleFormatter(year=2024, format_args={})
        result = formatter._get_arg_bool("flag", default=True)
        assert result is True

    def test_get_arg_with_existing_key(self) -> None:
        """Test _get_arg retrieves existing value."""
        formatter = ConsoleFormatter(year=2024, format_args={"note": "Test note"})
        result = formatter._get_arg("note", default="Default")
        assert result == "Test note"

    def test_get_arg_with_missing_key_returns_default(self) -> None:
        """Test _get_arg with missing key returns default."""
        formatter = ConsoleFormatter(year=2024, format_args={})
        result = formatter._get_arg("note", default="Default")
        assert result == "Default"

    def test_get_sorted_teams_by_division(self) -> None:
        """Test _get_sorted_teams_by_division sorts correctly."""
        owner1 = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        owner2 = Owner(display_name="Bob", first_name="Bob", last_name="Jones", id="bob456")
        owner3 = Owner(
            display_name="Charlie", first_name="Charlie", last_name="Brown", id="charlie789"
        )

        # Create teams with different records
        team1 = TeamStats(
            name="High Wins Low Points",
            owner=owner1,
            points_for=1000.0,
            points_against=900.0,
            wins=10,
            losses=3,
            division="League A",
        )
        team2 = TeamStats(
            name="High Wins High Points",
            owner=owner2,
            points_for=1500.0,
            points_against=900.0,
            wins=10,
            losses=3,
            division="League A",
        )
        team3 = TeamStats(
            name="Low Wins",
            owner=owner3,
            points_for=2000.0,  # Even with most points, should be last
            points_against=900.0,
            wins=5,
            losses=8,
            division="League A",
        )

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team1, team2, team3],  # Intentionally unsorted
            games=[],
        )

        formatter = ConsoleFormatter(year=2024)
        sorted_teams = formatter._get_sorted_teams_by_division(division)
        # Should be sorted by wins desc, then points_for desc
        assert sorted_teams[0].name == "High Wins High Points"  # 10 wins, 1500 points
        assert sorted_teams[1].name == "High Wins Low Points"  # 10 wins, 1000 points
        assert sorted_teams[2].name == "Low Wins"  # 5 wins

    def test_get_overall_top_teams(self) -> None:
        """Test _get_overall_top_teams combines and limits teams correctly."""
        owner1 = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        owner2 = Owner(display_name="Bob", first_name="Bob", last_name="Jones", id="bob456")
        owner3 = Owner(
            display_name="Charlie", first_name="Charlie", last_name="Brown", id="charlie789"
        )

        # Create teams across two divisions
        team1 = TeamStats(
            name="Div1 Best",
            owner=owner1,
            points_for=1500.0,
            points_against=900.0,
            wins=12,
            losses=1,
            division="League A",
        )
        team2 = TeamStats(
            name="Div1 Second",
            owner=owner2,
            points_for=1200.0,
            points_against=900.0,
            wins=10,
            losses=3,
            division="League A",
        )
        team3 = TeamStats(
            name="Div2 Best",
            owner=owner3,
            points_for=1600.0,  # Highest points but fewer wins
            points_against=900.0,
            wins=11,
            losses=2,
            division="League B",
        )

        div1 = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team1, team2],
            games=[],
        )
        div2 = DivisionData(
            league_id=789012,
            name="League B",
            teams=[team3],
            games=[],
        )

        formatter = ConsoleFormatter(year=2024)
        top_teams = formatter._get_overall_top_teams([div1, div2], limit=20)

        # Should be sorted by wins desc, then points_for desc
        assert len(top_teams) == 3
        assert top_teams[0].name == "Div1 Best"  # 12 wins
        assert top_teams[1].name == "Div2 Best"  # 11 wins
        assert top_teams[2].name == "Div1 Second"  # 10 wins

    def test_get_overall_top_teams_respects_limit(self) -> None:
        """Test _get_overall_top_teams respects the limit parameter."""
        owner = Owner(display_name="Owner", first_name="O", last_name="Wner", id="owner123")

        # Create 5 teams
        teams = [
            TeamStats(
                name=f"Team {i}",
                owner=owner,
                points_for=1000.0 + (i * 100),
                points_against=900.0,
                wins=10 - i,
                losses=i,
                division="League A",
            )
            for i in range(5)
        ]

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=teams,
            games=[],
        )

        formatter = ConsoleFormatter(year=2024)
        top_teams = formatter._get_overall_top_teams([division], limit=3)

        # Should only return top 3
        assert len(top_teams) == 3


class TestConsoleFormatterPlayoffMode:
    """Test console formatter with playoff mode data."""

    @pytest.fixture
    def playoff_matchup_semifinals(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> PlayoffMatchup:
        """Create a sample semifinals playoff matchup."""
        return PlayoffMatchup(
            matchup_id="SF1",
            round_name="Semifinals",
            team1_name="Thunder Cats",
            owner1_name=sample_owner_alice.full_name,
            score1=145.67,
            seed1=1,
            team2_name="Dream Team",
            owner2_name=sample_owner_bob.full_name,
            score2=98.23,
            seed2=4,
            winner_name="Thunder Cats",
            winner_seed=1,
            division_name="League A",
        )

    @pytest.fixture
    def playoff_matchup_finals(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> PlayoffMatchup:
        """Create a sample finals playoff matchup."""
        return PlayoffMatchup(
            matchup_id="F1",
            round_name="Finals",
            team1_name="Thunder Cats",
            owner1_name=sample_owner_alice.full_name,
            score1=150.0,
            seed1=1,
            team2_name="Touchdown Titans",
            owner2_name=sample_owner_bob.full_name,
            score2=145.0,
            seed2=3,
            winner_name="Thunder Cats",
            winner_seed=1,
            division_name="League A",
        )

    @pytest.fixture
    def playoff_bracket_semifinals(
        self, playoff_matchup_semifinals: PlayoffMatchup, sample_owner_bob: Owner
    ) -> PlayoffBracket:
        """Create a sample semifinals playoff bracket with 2 matchups."""
        matchup2 = PlayoffMatchup(
            matchup_id="SF2",
            round_name="Semifinals",
            team1_name="Pineapple Express",
            owner1_name=sample_owner_bob.full_name,
            score1=130.45,
            seed1=2,
            team2_name="Touchdown Titans",
            owner2_name="Chris Brown",
            score2=135.12,
            seed2=3,
            winner_name="Touchdown Titans",
            winner_seed=3,
            division_name="League A",
        )
        return PlayoffBracket(
            round="Semifinals",
            week=15,
            matchups=[playoff_matchup_semifinals, matchup2],
        )

    @pytest.fixture
    def playoff_bracket_finals(self, playoff_matchup_finals: PlayoffMatchup) -> PlayoffBracket:
        """Create a sample finals playoff bracket with 1 matchup."""
        return PlayoffBracket(
            round="Finals",
            week=16,
            matchups=[playoff_matchup_finals],
        )

    @pytest.fixture
    def division_with_semifinals(
        self,
        sample_teams: list[TeamStats],
        sample_games: list[GameResult],
        playoff_bracket_semifinals: PlayoffBracket,
    ) -> DivisionData:
        """Division data in semifinals playoff mode."""
        return DivisionData(
            league_id=123456,
            name="League A",
            teams=sample_teams,
            games=sample_games,
            playoff_bracket=playoff_bracket_semifinals,
        )

    @pytest.fixture
    def division_with_finals(
        self,
        sample_teams: list[TeamStats],
        sample_games: list[GameResult],
        playoff_bracket_finals: PlayoffBracket,
    ) -> DivisionData:
        """Division data in finals playoff mode."""
        return DivisionData(
            league_id=123456,
            name="League A",
            teams=sample_teams,
            games=sample_games,
            playoff_bracket=playoff_bracket_finals,
        )

    @pytest.fixture
    def championship_leaderboard(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> ChampionshipLeaderboard:
        """Create a sample championship leaderboard."""
        entries = [
            ChampionshipEntry(
                rank=1,
                team_name="Thunder Cats",
                owner_name=sample_owner_alice.full_name,
                division_name="League A",
                score=175.50,
                is_champion=True,
            ),
            ChampionshipEntry(
                rank=2,
                team_name="Dream Team",
                owner_name=sample_owner_bob.full_name,
                division_name="League B",
                score=165.25,
                is_champion=False,
            ),
            ChampionshipEntry(
                rank=3,
                team_name="Pineapple Express",
                owner_name="Tom Jones",
                division_name="League C",
                score=150.00,
                is_champion=False,
            ),
        ]
        return ChampionshipLeaderboard(
            week=17,
            entries=entries,
        )

    @pytest.fixture
    def player_only_weekly_challenges(self, sample_owner_alice: Owner) -> list[WeeklyChallenge]:
        """Create player-only weekly challenges for playoff mode."""
        return [
            WeeklyChallenge(
                challenge_name="Top Scorer (Player)",
                week=15,
                winner="Patrick Mahomes",
                owner=sample_owner_alice,
                division="League A",
                value="35.50 points",
                description="Patrick Mahomes (QB - Thunder Cats) scored 35.50 points",
                additional_info={
                    "position": "QB",
                    "points": 35.50,
                    "team_name": "Thunder Cats",
                },
            ),
            WeeklyChallenge(
                challenge_name="Best RB",
                week=15,
                winner="Derrick Henry",
                owner=sample_owner_alice,
                division="League A",
                value="28.00 points",
                description="Derrick Henry (RB - Thunder Cats) scored 28.00 points",
                additional_info={
                    "position": "RB",
                    "points": 28.00,
                    "team_name": "Thunder Cats",
                },
            ),
        ]

    def test_format_output_with_semifinals_bracket(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test that semifinals playoff bracket is formatted correctly."""
        formatter = ConsoleFormatter(year=2024)

        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=15,
        )

        # Should include playoff header
        assert "SEMIFINALS" in output or "Semifinals" in output
        assert "🏈" in output  # Playoff emoji

        # Should include bracket formatting
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "145.67" in output  # Score from matchup 1
        assert "Pineapple Express" in output  # From matchup 2
        assert "Touchdown Titans" in output  # From matchup 2

        # Should show seeding
        assert "#1" in output
        assert "#4" in output

        # Should show final regular season standings
        assert "FINAL REGULAR SEASON STANDINGS" in output

    def test_format_output_with_finals_bracket(
        self,
        division_with_finals: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test formatting for Finals round."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division_with_finals],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=16,
        )

        # Should include finals header
        assert "FINALS" in output or "Finals" in output
        assert "🏈" in output

        # Should include finals matchup
        assert "Thunder Cats" in output
        assert "Touchdown Titans" in output
        assert "150" in output  # Score (tabulate may format as 150 or 150.00)

    def test_format_output_with_championship_leaderboard(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        championship_leaderboard: ChampionshipLeaderboard,
    ) -> None:
        """Test formatting for Championship Week."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=17,
            championship=championship_leaderboard,
        )

        # Should include championship header
        assert "CHAMPIONSHIP WEEK" in output
        assert "🏆" in output
        assert "HIGHEST SCORE WINS OVERALL" in output

        # Should include championship leaderboard
        assert "CHAMPIONSHIP WEEK LEADERBOARD" in output
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "Pineapple Express" in output
        assert "175.5" in output  # Score (tabulate formats as 175.5)

        # Should show medals for top 3
        assert "🥇" in output  # Gold medal
        assert "🥈" in output  # Silver medal
        assert "🥉" in output  # Bronze medal

        # Should show current leader message (no rosters = not final)
        assert "CURRENT LEADER" in output
        assert "Games still in progress" in output

    def test_playoff_mode_filters_weekly_challenges(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that playoff mode filters out team challenges."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=15,
        )

        # Should show weekly player highlights
        assert "WEEKLY PLAYER HIGHLIGHTS" in output
        assert "Patrick Mahomes" in output

        # Team challenges should NOT appear in weekly section
        # (only in season-long challenges)
        lines = output.split("\n")
        in_weekly_section = False
        for line in lines:
            if "WEEKLY PLAYER HIGHLIGHTS" in line:
                in_weekly_section = True
            elif "SEASON-LONG CHALLENGES" in line:
                in_weekly_section = False

            if in_weekly_section:
                # Should not see team challenge names in weekly section
                assert "Highest Score This Week" not in line

    def test_playoff_mode_shows_player_challenges_only(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
        player_only_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that playoff mode shows only player challenges in weekly section."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=player_only_weekly_challenges,
            current_week=15,
        )

        # Should show player highlights
        assert "WEEKLY PLAYER HIGHLIGHTS" in output
        assert "Patrick Mahomes" in output
        assert "Derrick Henry" in output

    def test_format_playoff_brackets_method(
        self,
        division_with_semifinals: DivisionData,
    ) -> None:
        """Test _format_playoff_brackets method directly."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_playoff_brackets([division_with_semifinals])

        # Should include division name and round
        assert "LEAGUE A" in output
        assert "SEMIFINALS" in output

        # Should include matchup details
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "145.67" in output

        # Should show winners with checkmarks
        assert "✓" in output

    def test_format_championship_leaderboard_method(
        self,
        championship_leaderboard: ChampionshipLeaderboard,
    ) -> None:
        """Test _format_championship_leaderboard method directly."""
        formatter = ConsoleFormatter(year=2024)
        output = formatter._format_championship_leaderboard(championship_leaderboard, rosters=None)

        # Should include header
        assert "CHAMPIONSHIP WEEK LEADERBOARD" in output

        # Should include all entries
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "Pineapple Express" in output

        # Should include scores (tabulate formats as 175.5, not 175.50)
        assert "175.5" in output
        assert "165.25" in output
        assert "150" in output

        # Should show current leader (not final without rosters)
        assert "CURRENT LEADER" in output

    def test_filter_playoff_challenges_semifinals(self) -> None:
        """Test _filter_playoff_challenges for semifinals."""
        formatter = ConsoleFormatter(year=2024)

        # Create mixed challenges
        owner = Owner(display_name="Test", first_name="Test", last_name="User", id="test123")
        challenges = [
            WeeklyChallenge(
                challenge_name="Highest Score This Week",
                week=15,
                winner="Team A",
                owner=owner,
                division="League A",
                value="150.00",
                description="Team challenge",
                additional_info={"score": 150.00},
            ),
            WeeklyChallenge(
                challenge_name="Top Scorer (Player)",
                week=15,
                winner="Player A",
                owner=owner,
                division="League A",
                value="35.00",
                description="Player challenge",
                additional_info={"position": "QB", "points": 35.00},
            ),
        ]

        # Filter for semifinals (is_playoff_mode=True, is_championship_week=False)
        filtered = formatter._filter_playoff_challenges(
            challenges, is_playoff_mode=True, is_championship_week=False
        )

        # Should only include player challenges
        assert len(filtered) == 1
        assert filtered[0].challenge_name == "Top Scorer (Player)"

    def test_filter_playoff_challenges_championship_week(self) -> None:
        """Test _filter_playoff_challenges for championship week."""
        formatter = ConsoleFormatter(year=2024)

        # Create mixed challenges
        owner = Owner(display_name="Test", first_name="Test", last_name="User", id="test123")
        challenges = [
            WeeklyChallenge(
                challenge_name="Highest Score This Week",
                week=17,
                winner="Team A",
                owner=owner,
                division="League A",
                value="150.00",
                description="Team challenge",
                additional_info={"score": 150.00},
            ),
            WeeklyChallenge(
                challenge_name="Top Scorer (Player)",
                week=17,
                winner="Player A",
                owner=owner,
                division="League A",
                value="35.00",
                description="Player challenge",
                additional_info={"position": "QB", "points": 35.00},
            ),
        ]

        # Filter for championship week (is_playoff_mode=False, is_championship_week=True)
        filtered = formatter._filter_playoff_challenges(
            challenges, is_playoff_mode=False, is_championship_week=True
        )

        # Should only include player challenges
        assert len(filtered) == 1
        assert filtered[0].challenge_name == "Top Scorer (Player)"

    def test_filter_playoff_challenges_regular_season(self) -> None:
        """Test _filter_playoff_challenges for regular season."""
        formatter = ConsoleFormatter(year=2024)

        # Create mixed challenges
        owner = Owner(display_name="Test", first_name="Test", last_name="User", id="test123")
        challenges = [
            WeeklyChallenge(
                challenge_name="Highest Score This Week",
                week=10,
                winner="Team A",
                owner=owner,
                division="League A",
                value="150.00",
                description="Team challenge",
                additional_info={"score": 150.00},
            ),
            WeeklyChallenge(
                challenge_name="Top Scorer (Player)",
                week=10,
                winner="Player A",
                owner=owner,
                division="League A",
                value="35.00",
                description="Player challenge",
                additional_info={"position": "QB", "points": 35.00},
            ),
        ]

        # Filter for regular season (is_playoff_mode=False, is_championship_week=False)
        filtered = formatter._filter_playoff_challenges(
            challenges, is_playoff_mode=False, is_championship_week=False
        )

        # Should include all challenges
        assert len(filtered) == 2
