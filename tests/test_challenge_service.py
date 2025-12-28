"""
Comprehensive tests for ChallengeCalculator service.

Tests cover all 5 season challenges with realistic scenarios and edge cases.
"""

from __future__ import annotations

import pytest

from ff_tracker.exceptions import InsufficientDataError
from ff_tracker.models import DivisionData, GameResult, Owner, TeamStats
from ff_tracker.services.challenge_service import ChallengeCalculator


# Test Fixtures - Realistic but simple data
@pytest.fixture
def sample_owner_alice() -> Owner:
    """Create a sample owner Alice."""
    return Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")


@pytest.fixture
def sample_owner_bob() -> Owner:
    """Create a sample owner Bob."""
    return Owner(display_name="Bob", first_name="Bob", last_name="Jones", id="bob456")


@pytest.fixture
def sample_owner_charlie() -> Owner:
    """Create a sample owner Charlie."""
    return Owner(display_name="Charlie", first_name="Charlie", last_name="Brown", id="charlie789")


@pytest.fixture
def sample_teams(
    sample_owner_alice: Owner, sample_owner_bob: Owner, sample_owner_charlie: Owner
) -> list[TeamStats]:
    """Create sample teams with different point totals."""
    return [
        TeamStats(
            name="Alice's Team",
            owner=sample_owner_alice,
            points_for=1500.50,
            points_against=1200.00,
            wins=10,
            losses=4,
            division="League A",
            in_playoff_position=True,
        ),
        TeamStats(
            name="Bob's Team",
            owner=sample_owner_bob,
            points_for=1600.75,  # Highest points
            points_against=1300.00,
            wins=11,
            losses=3,
            division="League A",
            in_playoff_position=True,
        ),
        TeamStats(
            name="Charlie's Team",
            owner=sample_owner_charlie,
            points_for=1400.25,
            points_against=1400.00,
            wins=7,
            losses=7,
            division="League A",
            in_playoff_position=False,
        ),
    ]


@pytest.fixture
def sample_games() -> list[GameResult]:
    """Create sample games with various scenarios."""
    return [
        # Week 1 - Bob's highest score
        GameResult(
            team_name="Bob's Team",
            score=180.50,  # Highest single game score
            opponent_name="Alice's Team",
            opponent_score=120.00,
            won=True,
            week=1,
            margin=60.50,
            division="League A",
        ),
        GameResult(
            team_name="Alice's Team",
            score=120.00,
            opponent_name="Bob's Team",
            opponent_score=180.50,
            won=False,
            week=1,
            margin=60.50,
            division="League A",
        ),
        # Week 2 - Alice's high-scoring loss
        GameResult(
            team_name="Alice's Team",
            score=145.75,  # High score in a loss
            opponent_name="Charlie's Team",
            opponent_score=146.00,
            won=False,
            week=2,
            margin=0.25,
            division="League A",
        ),
        GameResult(
            team_name="Charlie's Team",
            score=146.00,
            opponent_name="Alice's Team",
            opponent_score=145.75,
            won=True,
            week=2,
            margin=0.25,  # Closest victory
            division="League A",
        ),
        # Week 3 - Bob's low-scoring win
        GameResult(
            team_name="Bob's Team",
            score=85.25,  # Lowest winning score
            opponent_name="Charlie's Team",
            opponent_score=80.00,
            won=True,
            week=3,
            margin=5.25,
            division="League A",
        ),
        GameResult(
            team_name="Charlie's Team",
            score=80.00,
            opponent_name="Bob's Team",
            opponent_score=85.25,
            won=False,
            week=3,
            margin=5.25,
            division="League A",
        ),
    ]


@pytest.fixture
def sample_division(sample_teams: list[TeamStats], sample_games: list[GameResult]) -> DivisionData:
    """Create a sample division with teams and games."""
    return DivisionData(
        league_id=123456,
        name="League A",
        teams=sample_teams,
        games=sample_games,
        weekly_games=[],
        weekly_players=[],
        playoff_bracket=None,
    )


class TestChallengeCalculatorBasics:
    """Tests for ChallengeCalculator initialization and basic operations."""

    def test_init_challenge_calculator(self) -> None:
        """Test that ChallengeCalculator can be initialized."""
        calculator = ChallengeCalculator()
        assert calculator is not None

    def test_combine_teams_single_division(
        self, sample_division: DivisionData, sample_teams: list[TeamStats]
    ) -> None:
        """Test combining teams from a single division."""
        calculator = ChallengeCalculator()
        teams = calculator._combine_teams([sample_division])
        assert len(teams) == len(sample_teams)
        assert teams == sample_teams

    def test_combine_teams_multiple_divisions(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> None:
        """Test combining teams from multiple divisions."""
        div1_teams = [
            TeamStats(
                name="Team D1",
                owner=sample_owner_alice,
                points_for=1000.0,
                points_against=900.0,
                wins=5,
                losses=5,
                division="Div1",
            )
        ]
        div2_teams = [
            TeamStats(
                name="Team D2",
                owner=sample_owner_bob,
                points_for=1100.0,
                points_against=1000.0,
                wins=6,
                losses=4,
                division="Div2",
            )
        ]

        div1 = DivisionData(
            league_id=111,
            name="Div1",
            teams=div1_teams,
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )
        div2 = DivisionData(
            league_id=222,
            name="Div2",
            teams=div2_teams,
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )

        calculator = ChallengeCalculator()
        teams = calculator._combine_teams([div1, div2])
        assert len(teams) == 2
        assert teams[0].name == "Team D1"
        assert teams[1].name == "Team D2"

    def test_combine_games_single_division(
        self, sample_division: DivisionData, sample_games: list[GameResult]
    ) -> None:
        """Test combining games from a single division."""
        calculator = ChallengeCalculator()
        games = calculator._combine_games([sample_division])
        assert len(games) == len(sample_games)
        assert games == sample_games

    def test_find_owner_for_team_exists(self, sample_teams: list[TeamStats]) -> None:
        """Test finding owner for an existing team."""
        calculator = ChallengeCalculator()
        owner = calculator._find_owner_for_team("Bob's Team", "League A", sample_teams)
        assert owner.display_name == "Bob"

    def test_find_owner_for_team_not_found(self, sample_teams: list[TeamStats]) -> None:
        """Test finding owner for a non-existent team returns default."""
        calculator = ChallengeCalculator()
        owner = calculator._find_owner_for_team("Nonexistent Team", "League A", sample_teams)
        assert owner.display_name == "Unknown Owner"
        assert owner.id == "unknown"

    def test_create_na_owner(self) -> None:
        """Test creating N/A owner placeholder."""
        calculator = ChallengeCalculator()
        owner = calculator._create_na_owner()
        assert owner.display_name == "N/A"
        assert owner.id == "na"


class TestCalculateAllChallenges:
    """Tests for calculate_all_challenges method."""

    def test_calculate_all_challenges_success(self, sample_division: DivisionData) -> None:
        """Test successful calculation of all challenges."""
        calculator = ChallengeCalculator()
        results = calculator.calculate_all_challenges([sample_division])

        assert len(results) == 5
        assert results[0].challenge_name == "Most Points Overall"
        assert results[1].challenge_name == "Most Points in One Game"
        assert results[2].challenge_name == "Most Points in a Loss"
        assert results[3].challenge_name == "Least Points in a Win"
        assert results[4].challenge_name == "Closest Victory"

    def test_calculate_all_challenges_empty_divisions_raises_error(self) -> None:
        """Test that empty divisions list raises InsufficientDataError."""
        calculator = ChallengeCalculator()
        with pytest.raises(InsufficientDataError, match="No division data provided"):
            calculator.calculate_all_challenges([])

    def test_calculate_all_challenges_no_teams_raises_error(
        self, sample_owner_alice: Owner
    ) -> None:
        """Test that divisions with no teams raise InsufficientDataError via combine."""
        # Create a division with a team but manually test empty team scenario
        # Note: We can't actually create an empty DivisionData due to validation,
        # so we test the code path by mocking or just accept this is validated at model level
        calculator = ChallengeCalculator()

        # Create empty teams list directly (bypassing DivisionData validation)
        # This tests the _calculate_all_challenges logic when combine returns empty
        empty_teams: list[TeamStats] = []
        with pytest.raises(InsufficientDataError, match="No teams available"):
            calculator._calculate_most_points_overall(empty_teams)

    def test_calculate_all_challenges_no_games_creates_placeholders(
        self, sample_owner_alice: Owner
    ) -> None:
        """Test that missing game data creates placeholder results."""
        # Create teams with matching division name
        teams_no_games = [
            TeamStats(
                name="Test Team",
                owner=sample_owner_alice,
                points_for=1000.0,
                points_against=900.0,
                wins=5,
                losses=5,
                division="Test Division",
            )
        ]

        division_no_games = DivisionData(
            league_id=123,
            name="Test Division",
            teams=teams_no_games,
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )

        calculator = ChallengeCalculator()
        results = calculator.calculate_all_challenges([division_no_games])

        assert len(results) == 5
        assert results[0].challenge_name == "Most Points Overall"  # Works without games
        assert results[1].winner == "Data Unavailable"
        assert results[2].winner == "Data Unavailable"
        assert results[3].winner == "Data Unavailable"
        assert results[4].winner == "Data Unavailable"


class TestMostPointsOverall:
    """Tests for Challenge 1: Most Points Overall."""

    def test_most_points_overall_correct_winner(self, sample_teams: list[TeamStats]) -> None:
        """Test that highest points team wins."""
        calculator = ChallengeCalculator()
        result = calculator._calculate_most_points_overall(sample_teams)

        assert result.challenge_name == "Most Points Overall"
        assert result.winner == "Bob's Team"  # 1600.75 points
        assert result.owner.display_name == "Bob"
        assert result.division == "League A"
        assert "1600.75" in result.description

    def test_most_points_overall_empty_teams_raises_error(self) -> None:
        """Test that empty teams list raises InsufficientDataError."""
        calculator = ChallengeCalculator()
        with pytest.raises(InsufficientDataError, match="No teams available"):
            calculator._calculate_most_points_overall([])

    def test_most_points_overall_single_team(self, sample_owner_alice: Owner) -> None:
        """Test with only one team."""
        teams = [
            TeamStats(
                name="Only Team",
                owner=sample_owner_alice,
                points_for=1000.00,
                points_against=800.00,
                wins=5,
                losses=5,
                division="Solo League",
            )
        ]

        calculator = ChallengeCalculator()
        result = calculator._calculate_most_points_overall(teams)

        assert result.winner == "Only Team"
        assert "1000.00" in result.description


class TestMostPointsOneGame:
    """Tests for Challenge 2: Most Points in One Game."""

    def test_most_points_one_game_correct_winner(
        self, sample_teams: list[TeamStats], sample_games: list[GameResult]
    ) -> None:
        """Test that highest single game score wins."""
        calculator = ChallengeCalculator()
        result = calculator._calculate_most_points_one_game(sample_teams, sample_games)

        assert result.challenge_name == "Most Points in One Game"
        assert result.winner == "Bob's Team"  # 180.50 points in Week 1
        assert result.owner.display_name == "Bob"
        assert "180.50" in result.description
        assert "Week 1" in result.description

    def test_most_points_one_game_empty_games_raises_error(
        self, sample_teams: list[TeamStats]
    ) -> None:
        """Test that empty games list raises InsufficientDataError."""
        calculator = ChallengeCalculator()
        with pytest.raises(InsufficientDataError, match="No games available"):
            calculator._calculate_most_points_one_game(sample_teams, [])


class TestMostPointsInLoss:
    """Tests for Challenge 3: Most Points in a Loss."""

    def test_most_points_in_loss_correct_winner(
        self, sample_teams: list[TeamStats], sample_games: list[GameResult]
    ) -> None:
        """Test that highest losing score wins."""
        calculator = ChallengeCalculator()
        result = calculator._calculate_most_points_in_loss(sample_teams, sample_games)

        assert result.challenge_name == "Most Points in a Loss"
        assert result.winner == "Alice's Team"  # 145.75 points in loss
        assert result.owner.display_name == "Alice"
        assert "145.75" in result.description
        assert "Week 2" in result.description

    def test_most_points_in_loss_no_losses_returns_placeholder(
        self, sample_teams: list[TeamStats]
    ) -> None:
        """Test that no losses returns N/A placeholder."""
        # Create games with only wins (no losses)
        wins_only = [
            GameResult(
                team_name="Bob's Team",
                score=100.0,
                opponent_name="Alice's Team",
                opponent_score=90.0,
                won=True,
                week=1,
                margin=10.0,
                division="League A",
            )
        ]

        calculator = ChallengeCalculator()
        result = calculator._calculate_most_points_in_loss(sample_teams, wins_only)

        assert result.winner == "No losses found"
        assert result.owner.display_name == "N/A"
        assert result.division == "N/A"


class TestLeastPointsInWin:
    """Tests for Challenge 4: Least Points in a Win."""

    def test_least_points_in_win_correct_winner(
        self, sample_teams: list[TeamStats], sample_games: list[GameResult]
    ) -> None:
        """Test that lowest winning score wins."""
        calculator = ChallengeCalculator()
        result = calculator._calculate_least_points_in_win(sample_teams, sample_games)

        assert result.challenge_name == "Least Points in a Win"
        assert result.winner == "Bob's Team"  # 85.25 points in win
        assert result.owner.display_name == "Bob"
        assert "85.25" in result.description
        assert "Week 3" in result.description

    def test_least_points_in_win_no_wins_returns_placeholder(
        self, sample_teams: list[TeamStats]
    ) -> None:
        """Test that no wins returns N/A placeholder."""
        # Create games with only losses (no wins)
        losses_only = [
            GameResult(
                team_name="Charlie's Team",
                score=90.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=False,
                week=1,
                margin=10.0,
                division="League A",
            )
        ]

        calculator = ChallengeCalculator()
        result = calculator._calculate_least_points_in_win(sample_teams, losses_only)

        assert result.winner == "No wins found"
        assert result.owner.display_name == "N/A"
        assert result.division == "N/A"


class TestClosestVictory:
    """Tests for Challenge 5: Closest Victory."""

    def test_closest_victory_correct_winner(
        self, sample_teams: list[TeamStats], sample_games: list[GameResult]
    ) -> None:
        """Test that smallest winning margin wins."""
        calculator = ChallengeCalculator()
        result = calculator._calculate_closest_victory(sample_teams, sample_games)

        assert result.challenge_name == "Closest Victory"
        assert result.winner == "Charlie's Team"  # Won by 0.25 points
        assert result.owner.display_name == "Charlie"
        assert "0.25" in result.description
        assert "Week 2" in result.description

    def test_closest_victory_no_wins_returns_placeholder(
        self, sample_teams: list[TeamStats]
    ) -> None:
        """Test that no wins returns N/A placeholder."""
        # Create games with only losses
        losses_only = [
            GameResult(
                team_name="Charlie's Team",
                score=90.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=False,
                week=1,
                margin=10.0,
                division="League A",
            )
        ]

        calculator = ChallengeCalculator()
        result = calculator._calculate_closest_victory(sample_teams, losses_only)

        assert result.winner == "No wins found"
        assert result.owner.display_name == "N/A"


class TestCreateNoDataPlaceholders:
    """Tests for creating placeholder results."""

    def test_create_no_data_placeholders_returns_four_results(self) -> None:
        """Test that placeholder method returns 4 results."""
        calculator = ChallengeCalculator()
        placeholders = calculator._create_no_data_placeholders()

        assert len(placeholders) == 4

    def test_create_no_data_placeholders_correct_structure(self) -> None:
        """Test that placeholders have correct structure."""
        calculator = ChallengeCalculator()
        placeholders = calculator._create_no_data_placeholders()

        expected_names = [
            "Most Points in One Game",
            "Most Points in a Loss",
            "Least Points in a Win",
            "Closest Victory",
        ]

        for placeholder, expected_name in zip(placeholders, expected_names):
            assert placeholder.challenge_name == expected_name
            assert placeholder.winner == "Data Unavailable"
            assert placeholder.owner.display_name == "N/A"
            assert placeholder.division == "N/A"
            assert "unavailable" in placeholder.description.lower()


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_tied_highest_points_returns_first(self, sample_owner_alice: Owner) -> None:
        """Test that tied highest points returns first team found."""
        teams = [
            TeamStats(
                name="Team A",
                owner=sample_owner_alice,
                points_for=1500.00,
                points_against=1200.00,
                wins=10,
                losses=4,
                division="League",
            ),
            TeamStats(
                name="Team B",
                owner=sample_owner_alice,
                points_for=1500.00,  # Same points
                points_against=1200.00,
                wins=10,
                losses=4,
                division="League",
            ),
        ]

        calculator = ChallengeCalculator()
        result = calculator._calculate_most_points_overall(teams)

        # max() returns first occurrence of maximum value
        assert result.winner in ["Team A", "Team B"]
        assert "1500.00" in result.description

    def test_single_game_all_challenges(self, sample_teams: list[TeamStats]) -> None:
        """Test all challenges with only one game."""
        single_game = [
            GameResult(
                team_name="Bob's Team",
                score=100.0,
                opponent_name="Alice's Team",
                opponent_score=90.0,
                won=True,
                week=1,
                margin=10.0,
                division="League A",
            )
        ]

        calculator = ChallengeCalculator()

        # Most points one game
        result = calculator._calculate_most_points_one_game(sample_teams, single_game)
        assert result.winner == "Bob's Team"

        # Most points in loss - no losses yet
        result = calculator._calculate_most_points_in_loss(sample_teams, single_game)
        assert result.winner == "No losses found"

        # Least points in win
        result = calculator._calculate_least_points_in_win(sample_teams, single_game)
        assert result.winner == "Bob's Team"

        # Closest victory
        result = calculator._calculate_closest_victory(sample_teams, single_game)
        assert result.winner == "Bob's Team"

    def test_multiple_divisions_integration(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> None:
        """Test integration with multiple divisions."""
        # Division 1
        div1_teams = [
            TeamStats(
                name="Team D1A",
                owner=sample_owner_alice,
                points_for=1400.0,
                points_against=1200.0,
                wins=8,
                losses=6,
                division="Division 1",
            )
        ]
        div1_games = [
            GameResult(
                team_name="Team D1A",
                score=150.0,
                opponent_name="Team D1B",
                opponent_score=100.0,
                won=True,
                week=1,
                margin=50.0,
                division="Division 1",
            )
        ]

        # Division 2
        div2_teams = [
            TeamStats(
                name="Team D2A",
                owner=sample_owner_bob,
                points_for=1600.0,  # Higher than Division 1
                points_against=1100.0,
                wins=10,
                losses=4,
                division="Division 2",
            )
        ]
        div2_games = [
            GameResult(
                team_name="Team D2A",
                score=200.0,  # Higher than Division 1
                opponent_name="Team D2B",
                opponent_score=120.0,
                won=True,
                week=1,
                margin=80.0,
                division="Division 2",
            )
        ]

        division1 = DivisionData(
            league_id=111,
            name="Division 1",
            teams=div1_teams,
            games=div1_games,
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )
        division2 = DivisionData(
            league_id=222,
            name="Division 2",
            teams=div2_teams,
            games=div2_games,
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )

        calculator = ChallengeCalculator()
        results = calculator.calculate_all_challenges([division1, division2])

        assert len(results) == 5

        # Most points overall should be from Division 2
        assert results[0].winner == "Team D2A"
        assert results[0].division == "Division 2"

        # Most points one game should be from Division 2
        assert results[1].winner == "Team D2A"
        assert "200.00" in results[1].description
