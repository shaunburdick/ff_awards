"""
Comprehensive tests for WeeklyChallengeCalculator service.

Tests cover all 13 weekly challenges (6 team + 7 player) with realistic scenarios.
"""

from __future__ import annotations

import pytest

from ff_tracker.exceptions import InsufficientDataError
from ff_tracker.models import WeeklyGameResult, WeeklyPlayerStats
from ff_tracker.services.weekly_challenge_service import WeeklyChallengeCalculator


# Test Fixtures - Realistic weekly data
@pytest.fixture
def sample_weekly_games() -> list[WeeklyGameResult]:
    """Create sample weekly game results with various scenarios."""
    return [
        # Highest score (Alice: 150.50)
        WeeklyGameResult(
            team_name="Alice's Team",
            score=150.50,
            projected_score=140.00,
            opponent_name="Bob's Team",
            opponent_score=120.00,
            opponent_projected_score=125.00,
            won=True,
            week=10,
            margin=30.50,
            projection_diff=10.50,
            division="League A",
            starter_projected_score=135.00,
            true_projection_diff=15.50,  # Overachiever
        ),
        WeeklyGameResult(
            team_name="Bob's Team",
            score=120.00,
            projected_score=125.00,
            opponent_name="Alice's Team",
            opponent_score=150.50,
            opponent_projected_score=140.00,
            won=False,
            week=10,
            margin=30.50,
            projection_diff=-5.00,
            division="League A",
        ),
        # Lowest score (Charlie: 75.25)
        WeeklyGameResult(
            team_name="Charlie's Team",
            score=75.25,
            projected_score=95.00,
            opponent_name="Dave's Team",
            opponent_score=100.00,
            opponent_projected_score=90.00,
            won=False,
            week=10,
            margin=24.75,
            projection_diff=-19.75,
            division="League A",
            starter_projected_score=110.00,
            true_projection_diff=-34.75,  # Below expectations
        ),
        WeeklyGameResult(
            team_name="Dave's Team",
            score=100.00,
            projected_score=90.00,
            opponent_name="Charlie's Team",
            opponent_score=75.25,
            opponent_projected_score=95.00,
            won=True,
            week=10,
            margin=24.75,  # Biggest win
            projection_diff=10.00,
            division="League A",
        ),
        # Closest game (margin: 1.25)
        WeeklyGameResult(
            team_name="Eve's Team",
            score=105.25,
            projected_score=100.00,
            opponent_name="Frank's Team",
            opponent_score=104.00,
            opponent_projected_score=105.00,
            won=True,
            week=10,
            margin=1.25,  # Closest game
            projection_diff=5.25,
            division="League B",
        ),
        WeeklyGameResult(
            team_name="Frank's Team",
            score=104.00,
            projected_score=105.00,
            opponent_name="Eve's Team",
            opponent_score=105.25,
            opponent_projected_score=100.00,
            won=False,
            week=10,
            margin=1.25,
            projection_diff=-1.00,
            division="League B",
        ),
    ]


@pytest.fixture
def sample_weekly_players() -> list[WeeklyPlayerStats]:
    """Create sample weekly player stats."""
    return [
        # Top scorer overall
        WeeklyPlayerStats(
            name="Patrick Mahomes",
            position="QB",
            team_name="Alice's Team",
            division="League A",
            points=35.50,  # Top QB and overall top scorer
            projected_points=25.00,
            projection_diff=10.50,
            slot_position="QB",
            week=10,
            pro_team="KC",
            pro_opponent="LAC",
        ),
        # Best RB
        WeeklyPlayerStats(
            name="Christian McCaffrey",
            position="RB",
            team_name="Bob's Team",
            division="League A",
            points=28.75,  # Best RB
            projected_points=20.00,
            projection_diff=8.75,
            slot_position="RB",
            week=10,
            pro_team="SF",
            pro_opponent="SEA",
        ),
        # Best WR
        WeeklyPlayerStats(
            name="Tyreek Hill",
            position="WR",
            team_name="Charlie's Team",
            division="League A",
            points=24.50,  # Best WR
            projected_points=18.00,
            projection_diff=6.50,
            slot_position="WR",
            week=10,
            pro_team="MIA",
            pro_opponent="BUF",
        ),
        # Best TE
        WeeklyPlayerStats(
            name="Travis Kelce",
            position="TE",
            team_name="Dave's Team",
            division="League A",
            points=18.25,  # Best TE
            projected_points=14.00,
            projection_diff=4.25,
            slot_position="TE",
            week=10,
            pro_team="KC",
            pro_opponent="LAC",
        ),
        # Best K
        WeeklyPlayerStats(
            name="Justin Tucker",
            position="K",
            team_name="Eve's Team",
            division="League B",
            points=15.00,  # Best K
            projected_points=9.00,
            projection_diff=6.00,
            slot_position="K",
            week=10,
            pro_team="BAL",
            pro_opponent="CIN",
        ),
        # Best D/ST
        WeeklyPlayerStats(
            name="49ers D/ST",
            position="D/ST",
            team_name="Frank's Team",
            division="League B",
            points=22.00,  # Best D/ST
            projected_points=12.00,
            projection_diff=10.00,
            slot_position="D/ST",
            week=10,
            pro_team="SF",
            pro_opponent="SEA",
        ),
        # Bench player (should be excluded)
        WeeklyPlayerStats(
            name="Bench Player",
            position="RB",
            team_name="Alice's Team",
            division="League A",
            points=30.00,  # High score but on bench
            projected_points=15.00,
            projection_diff=15.00,
            slot_position="BE",  # Bench
            week=10,
            pro_team="DAL",
            pro_opponent="NYG",
        ),
        # Second QB (not highest)
        WeeklyPlayerStats(
            name="Joe Burrow",
            position="QB",
            team_name="Bob's Team",
            division="League A",
            points=22.00,
            projected_points=20.00,
            projection_diff=2.00,
            slot_position="QB",
            week=10,
            pro_team="CIN",
            pro_opponent="BAL",
        ),
    ]


class TestWeeklyChallengeCalculatorBasics:
    """Tests for WeeklyChallengeCalculator initialization and basic operations."""

    def test_init_weekly_challenge_calculator(self) -> None:
        """Test that WeeklyChallengeCalculator can be initialized."""
        calculator = WeeklyChallengeCalculator()
        assert calculator is not None

    def test_invalid_week_number_too_low_raises_error(self) -> None:
        """Test that week < 1 raises InsufficientDataError."""
        calculator = WeeklyChallengeCalculator()
        with pytest.raises(InsufficientDataError, match="Invalid week number: 0"):
            calculator.calculate_all_weekly_challenges([], [], week=0)

    def test_invalid_week_number_too_high_raises_error(self) -> None:
        """Test that week > 18 raises InsufficientDataError."""
        calculator = WeeklyChallengeCalculator()
        with pytest.raises(InsufficientDataError, match="Invalid week number: 19"):
            calculator.calculate_all_weekly_challenges([], [], week=19)

    def test_valid_week_boundaries(
        self,
        sample_weekly_games: list[WeeklyGameResult],
        sample_weekly_players: list[WeeklyPlayerStats],
    ) -> None:
        """Test that weeks 1 and 18 are valid boundaries."""
        calculator = WeeklyChallengeCalculator()

        # Week 1 should work
        results = calculator.calculate_all_weekly_challenges(
            sample_weekly_games, sample_weekly_players, week=1
        )
        assert all(r.week == 1 for r in results)

        # Week 18 should work
        results = calculator.calculate_all_weekly_challenges(
            sample_weekly_games, sample_weekly_players, week=18
        )
        assert all(r.week == 18 for r in results)


class TestCalculateAllWeeklyChallenges:
    """Tests for calculate_all_weekly_challenges method."""

    def test_calculate_all_with_complete_data(
        self,
        sample_weekly_games: list[WeeklyGameResult],
        sample_weekly_players: list[WeeklyPlayerStats],
    ) -> None:
        """Test successful calculation with complete game and player data."""
        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges(
            sample_weekly_games, sample_weekly_players, week=10
        )

        # Should have 13 challenges total (6 team + 7 player)
        # Team: Highest, Lowest, Biggest Win, Closest, Overachiever, Below Expectations
        # Player: Top Scorer + 6 positions (QB, RB, WR, TE, K, D/ST)
        assert len(results) == 13

        challenge_names = [r.challenge_name for r in results]
        assert "Highest Score This Week" in challenge_names
        assert "Lowest Score This Week" in challenge_names
        assert "Biggest Win This Week" in challenge_names
        assert "Closest Game This Week" in challenge_names
        assert "Overachiever" in challenge_names
        assert "Below Expectations" in challenge_names
        assert "Top Scorer (Player)" in challenge_names
        assert "Best QB" in challenge_names
        assert "Best RB" in challenge_names
        assert "Best WR" in challenge_names
        assert "Best TE" in challenge_names
        assert "Best K" in challenge_names
        assert "Best D/ST" in challenge_names

    def test_calculate_all_no_data_returns_empty(self) -> None:
        """Test that no data returns empty results list."""
        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges([], [], week=10)
        assert len(results) == 0

    def test_calculate_all_games_only_no_players(
        self, sample_weekly_games: list[WeeklyGameResult]
    ) -> None:
        """Test with game data but no player data."""
        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges(sample_weekly_games, [], week=10)

        # Should only have team challenges (6 total)
        assert len(results) == 6
        challenge_names = [r.challenge_name for r in results]
        assert "Highest Score This Week" in challenge_names
        assert "Top Scorer (Player)" not in challenge_names

    def test_calculate_all_players_only_no_games(
        self, sample_weekly_players: list[WeeklyPlayerStats]
    ) -> None:
        """Test with player data but no game data."""
        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges([], sample_weekly_players, week=10)

        # Should only have player challenges (7 total)
        assert len(results) == 7
        challenge_names = [r.challenge_name for r in results]
        assert "Top Scorer (Player)" in challenge_names
        assert "Highest Score This Week" not in challenge_names


class TestTeamChallenges:
    """Tests for team-based challenges."""

    def test_highest_score_correct_winner(
        self, sample_weekly_games: list[WeeklyGameResult]
    ) -> None:
        """Test that highest score challenge finds correct winner."""
        calculator = WeeklyChallengeCalculator()
        result = calculator._calculate_highest_score(sample_weekly_games, week=10)

        assert result.challenge_name == "Highest Score This Week"
        assert result.winner == "Alice's Team"  # 150.50 points
        assert result.week == 10
        assert "150.50" in result.value
        assert result.additional_info["opponent"] == "Bob's Team"
        assert result.additional_info["won"] is True

    def test_lowest_score_correct_winner(self, sample_weekly_games: list[WeeklyGameResult]) -> None:
        """Test that lowest score challenge finds correct winner."""
        calculator = WeeklyChallengeCalculator()
        result = calculator._calculate_lowest_score(sample_weekly_games, week=10)

        assert result.challenge_name == "Lowest Score This Week"
        assert result.winner == "Charlie's Team"  # 75.25 points
        assert result.week == 10
        assert "75.25" in result.value
        assert "only" in result.description.lower()

    def test_biggest_win_correct_winner(self, sample_weekly_games: list[WeeklyGameResult]) -> None:
        """Test that biggest win challenge finds correct winner."""
        calculator = WeeklyChallengeCalculator()
        result = calculator._calculate_biggest_win(sample_weekly_games, week=10)

        assert result.challenge_name == "Biggest Win This Week"
        assert (
            result.winner == "Alice's Team"
        )  # Won by 30.50 points (bigger margin than Dave's 24.75)
        assert result.week == 10
        assert "30.50" in result.description
        assert result.additional_info["margin"] == 30.50

    def test_biggest_win_no_wins_returns_placeholder(self) -> None:
        """Test that no wins returns placeholder."""
        # Create games with only losses
        games = [
            WeeklyGameResult(
                team_name="Loser",
                score=80.0,
                projected_score=90.0,
                opponent_name="Winner",
                opponent_score=100.0,
                opponent_projected_score=95.0,
                won=False,
                week=10,
                margin=20.0,
                projection_diff=-10.0,
                division="League",
            )
        ]

        calculator = WeeklyChallengeCalculator()
        result = calculator._calculate_biggest_win(games, week=10)

        assert result.winner == "No Data"
        assert result.value == "N/A"

    def test_closest_game_correct_winner(self, sample_weekly_games: list[WeeklyGameResult]) -> None:
        """Test that closest game challenge finds correct winner."""
        calculator = WeeklyChallengeCalculator()
        result = calculator._calculate_closest_game(sample_weekly_games, week=10)

        assert result.challenge_name == "Closest Game This Week"
        assert result.winner == "Eve's Team"  # Won by 1.25 points
        assert result.week == 10
        assert "1.25" in result.description
        assert result.additional_info["margin"] == 1.25

    def test_closest_game_shows_win_or_loss(self) -> None:
        """Test that closest game description shows won/lost."""
        games = [
            WeeklyGameResult(
                team_name="Close Loser",
                score=100.0,
                projected_score=95.0,
                opponent_name="Close Winner",
                opponent_score=100.5,
                opponent_projected_score=98.0,
                won=False,
                week=10,
                margin=0.5,
                projection_diff=5.0,
                division="League",
            )
        ]

        calculator = WeeklyChallengeCalculator()
        result = calculator._calculate_closest_game(games, week=10)

        assert result.winner == "Close Loser"
        assert "lost" in result.description.lower()


class TestProjectionChallenges:
    """Tests for projection-based challenges (Overachiever, Below Expectations)."""

    def test_overachiever_correct_winner(self, sample_weekly_games: list[WeeklyGameResult]) -> None:
        """Test that overachiever finds team that most exceeded starter projections."""
        calculator = WeeklyChallengeCalculator()

        # Filter to games with projections
        games_with_proj = [g for g in sample_weekly_games if g.true_projection_diff is not None]
        result = calculator._calculate_overachiever(games_with_proj, week=10)

        assert result.challenge_name == "Overachiever"
        assert result.winner == "Alice's Team"  # +15.50 above projections
        assert result.week == 10
        assert "+15.50" in result.value
        assert result.additional_info["true_diff"] == 15.50
        assert result.additional_info["starter_projection"] == 135.00

    def test_below_expectations_correct_winner(
        self, sample_weekly_games: list[WeeklyGameResult]
    ) -> None:
        """Test that below expectations finds team that most underperformed."""
        calculator = WeeklyChallengeCalculator()

        # Filter to games with projections
        games_with_proj = [g for g in sample_weekly_games if g.true_projection_diff is not None]
        result = calculator._calculate_below_expectations(games_with_proj, week=10)

        assert result.challenge_name == "Below Expectations"
        assert result.winner == "Charlie's Team"  # -34.75 below projections
        assert result.week == 10
        assert "-34.75" in result.value
        assert result.additional_info["true_diff"] == -34.75

    def test_projection_challenges_skipped_without_data(
        self, sample_weekly_games: list[WeeklyGameResult]
    ) -> None:
        """Test that projection challenges are skipped when no projection data."""
        # Remove projection data from games
        games_no_proj = [
            WeeklyGameResult(
                team_name=g.team_name,
                score=g.score,
                projected_score=g.projected_score,
                opponent_name=g.opponent_name,
                opponent_score=g.opponent_score,
                opponent_projected_score=g.opponent_projected_score,
                won=g.won,
                week=g.week,
                margin=g.margin,
                projection_diff=g.projection_diff,
                division=g.division,
                starter_projected_score=None,  # No projection data
                true_projection_diff=None,
            )
            for g in sample_weekly_games
        ]

        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges(games_no_proj, [], week=10)

        # Should only have 4 team challenges (not 6)
        assert len(results) == 4
        challenge_names = [r.challenge_name for r in results]
        assert "Overachiever" not in challenge_names
        assert "Below Expectations" not in challenge_names


class TestPlayerChallenges:
    """Tests for player-based challenges."""

    def test_top_player_correct_winner(
        self, sample_weekly_players: list[WeeklyPlayerStats]
    ) -> None:
        """Test that top player challenge finds highest scorer."""
        calculator = WeeklyChallengeCalculator()

        # Filter to starters only
        starters = [p for p in sample_weekly_players if p.is_starter]
        result = calculator._calculate_top_player(starters, week=10)

        assert result.challenge_name == "Top Scorer (Player)"
        assert result.winner == "Patrick Mahomes"  # 35.50 points
        assert result.week == 10
        assert "35.50" in result.value
        assert result.additional_info["position"] == "QB"

    def test_top_player_excludes_bench(
        self, sample_weekly_players: list[WeeklyPlayerStats]
    ) -> None:
        """Test that bench players are excluded from top scorer."""
        calculator = WeeklyChallengeCalculator()

        # Bench Player has 30.00 points but should be excluded
        starters = [p for p in sample_weekly_players if p.is_starter]
        result = calculator._calculate_top_player(starters, week=10)

        assert result.winner != "Bench Player"  # Should not be bench player
        assert result.winner == "Patrick Mahomes"

    def test_top_by_position_all_positions(
        self, sample_weekly_players: list[WeeklyPlayerStats]
    ) -> None:
        """Test that top by position finds best for each position."""
        calculator = WeeklyChallengeCalculator()

        starters = [p for p in sample_weekly_players if p.is_starter]
        results = calculator._calculate_top_by_position(starters, week=10)

        # Should have 6 results (QB, RB, WR, TE, K, D/ST)
        assert len(results) == 6

        # Create lookup by challenge name
        by_name = {r.challenge_name: r for r in results}

        assert by_name["Best QB"].winner == "Patrick Mahomes"
        assert "35.50" in by_name["Best QB"].value

        assert by_name["Best RB"].winner == "Christian McCaffrey"
        assert "28.75" in by_name["Best RB"].value

        assert by_name["Best WR"].winner == "Tyreek Hill"
        assert "24.50" in by_name["Best WR"].value

        assert by_name["Best TE"].winner == "Travis Kelce"
        assert "18.25" in by_name["Best TE"].value

        assert by_name["Best K"].winner == "Justin Tucker"
        assert "15.00" in by_name["Best K"].value

        assert by_name["Best D/ST"].winner == "49ers D/ST"
        assert "22.00" in by_name["Best D/ST"].value

    def test_top_by_position_missing_position_skipped(self) -> None:
        """Test that positions with no players are skipped."""
        # Create players with only QB and RB
        players = [
            WeeklyPlayerStats(
                name="QB Player",
                position="QB",
                team_name="Team",
                division="League",
                points=20.0,
                projected_points=15.0,
                projection_diff=5.0,
                slot_position="QB",
                week=10,
                pro_team="KC",
                pro_opponent="LAC",
            ),
            WeeklyPlayerStats(
                name="RB Player",
                position="RB",
                team_name="Team",
                division="League",
                points=15.0,
                projected_points=12.0,
                projection_diff=3.0,
                slot_position="RB",
                week=10,
                pro_team="SF",
                pro_opponent="SEA",
            ),
        ]

        calculator = WeeklyChallengeCalculator()
        results = calculator._calculate_top_by_position(players, week=10)

        # Should only have 2 results (QB, RB)
        assert len(results) == 2
        challenge_names = [r.challenge_name for r in results]
        assert "Best QB" in challenge_names
        assert "Best RB" in challenge_names
        assert "Best WR" not in challenge_names
        assert "Best TE" not in challenge_names


class TestNoDataPlaceholder:
    """Tests for placeholder creation."""

    def test_create_no_data_placeholder(self) -> None:
        """Test creating a no data placeholder."""
        calculator = WeeklyChallengeCalculator()
        result = calculator._create_no_data_placeholder("Test Challenge", week=10)

        assert result.challenge_name == "Test Challenge"
        assert result.week == 10
        assert result.winner == "No Data"
        assert result.value == "N/A"
        assert result.division == "N/A"
        assert "Insufficient data" in result.description


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_game_all_team_challenges(self) -> None:
        """Test all team challenges with only one game."""
        single_game = [
            WeeklyGameResult(
                team_name="Winner",
                score=100.0,
                projected_score=95.0,
                opponent_name="Loser",
                opponent_score=80.0,
                opponent_projected_score=85.0,
                won=True,
                week=10,
                margin=20.0,
                projection_diff=5.0,
                division="League",
                starter_projected_score=90.0,
                true_projection_diff=10.0,
            )
        ]

        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges(single_game, [], week=10)

        assert len(results) == 6  # All team challenges should work

        # All should point to the same game
        assert all(r.winner == "Winner" for r in results if "Expectations" not in r.challenge_name)

    def test_single_player_all_player_challenges(self) -> None:
        """Test player challenges with only one player."""
        single_player = [
            WeeklyPlayerStats(
                name="Only Player",
                position="QB",
                team_name="Team",
                division="League",
                points=25.0,
                projected_points=20.0,
                projection_diff=5.0,
                slot_position="QB",
                week=10,
                pro_team="KC",
                pro_opponent="LAC",
            )
        ]

        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges([], single_player, week=10)

        # Should have 2 results: Top Scorer + Best QB
        assert len(results) == 2
        assert all(r.winner == "Only Player" for r in results)

    def test_tied_scores_returns_first(self) -> None:
        """Test that tied scores return first occurrence."""
        tied_games = [
            WeeklyGameResult(
                team_name="Team A",
                score=100.0,
                projected_score=95.0,
                opponent_name="Team B",
                opponent_score=90.0,
                opponent_projected_score=88.0,
                won=True,
                week=10,
                margin=10.0,
                projection_diff=5.0,
                division="League",
            ),
            WeeklyGameResult(
                team_name="Team C",
                score=100.0,  # Same score
                projected_score=98.0,
                opponent_name="Team D",
                opponent_score=85.0,
                opponent_projected_score=87.0,
                won=True,
                week=10,
                margin=15.0,
                projection_diff=2.0,
                division="League",
            ),
        ]

        calculator = WeeklyChallengeCalculator()
        result = calculator._calculate_highest_score(tied_games, week=10)

        # Should return one of the tied teams (max returns first occurrence)
        assert result.winner in ["Team A", "Team C"]
        assert "100.00" in result.value

    def test_all_starters_all_bench_mixed(self) -> None:
        """Test filtering starters from mixed starter/bench list."""
        mixed_players = [
            WeeklyPlayerStats(
                name="Starter 1",
                position="QB",
                team_name="Team",
                division="League",
                points=25.0,
                projected_points=20.0,
                projection_diff=5.0,
                slot_position="QB",  # Starter
                week=10,
                pro_team="KC",
                pro_opponent="LAC",
            ),
            WeeklyPlayerStats(
                name="Bench 1",
                position="RB",
                team_name="Team",
                division="League",
                points=30.0,  # Higher than starter but on bench
                projected_points=15.0,
                projection_diff=15.0,
                slot_position="BE",  # Bench
                week=10,
                pro_team="SF",
                pro_opponent="SEA",
            ),
            WeeklyPlayerStats(
                name="IR Player",
                position="WR",
                team_name="Team",
                division="League",
                points=0.0,
                projected_points=10.0,
                projection_diff=-10.0,
                slot_position="IR",  # Injured Reserve
                week=10,
                pro_team="MIA",
                pro_opponent="BUF",
            ),
            WeeklyPlayerStats(
                name="Starter 2",
                position="RB",
                team_name="Team",
                division="League",
                points=20.0,
                projected_points=18.0,
                projection_diff=2.0,
                slot_position="RB",  # Starter
                week=10,
                pro_team="DAL",
                pro_opponent="NYG",
            ),
        ]

        calculator = WeeklyChallengeCalculator()
        results = calculator.calculate_all_weekly_challenges([], mixed_players, week=10)

        # Should only consider Starter 1 and Starter 2
        # Top scorer should be Starter 1 (25.0), not Bench 1 (30.0)
        top_scorer = next(r for r in results if r.challenge_name == "Top Scorer (Player)")
        assert top_scorer.winner == "Starter 1"
        assert "25.00" in top_scorer.value
