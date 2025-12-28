"""
Comprehensive tests for model computed properties and validation.

Tests all computed properties, property edge cases, and validation logic
for all data models to boost coverage to 85%+.
"""

from __future__ import annotations

import pytest

from ff_tracker.exceptions import DataValidationError
from ff_tracker.models import (
    ChallengeResult,
    DivisionData,
    GameResult,
    Owner,
    TeamStats,
    WeeklyChallenge,
    WeeklyGameResult,
    WeeklyPlayerStats,
)

# ============================================================================
# Owner Model Tests
# ============================================================================


class TestOwnerProperties:
    """Test Owner computed properties."""

    def test_full_name_with_both_names(self) -> None:
        """Test full_name when both first and last names are provided."""
        owner = Owner(display_name="alice123", first_name="Alice", last_name="Smith", id="alice123")
        assert owner.full_name == "Alice Smith"

    def test_full_name_with_only_first_name(self) -> None:
        """Test full_name when only first name is provided."""
        owner = Owner(display_name="alice123", first_name="Alice", last_name="", id="alice123")
        assert owner.full_name == "Alice"

    def test_full_name_with_only_last_name(self) -> None:
        """Test full_name when only last name is provided."""
        owner = Owner(display_name="alice123", first_name="", last_name="Smith", id="alice123")
        assert owner.full_name == "Smith"

    def test_full_name_falls_back_to_display_name(self) -> None:
        """Test full_name falls back to display_name when no real names."""
        owner = Owner(display_name="alice123", first_name="", last_name="", id="alice123")
        assert owner.full_name == "alice123"

    def test_full_name_with_whitespace_only_names(self) -> None:
        """Test full_name handles whitespace-only names correctly."""
        owner = Owner(display_name="alice123", first_name="  ", last_name="  ", id="alice123")
        assert owner.full_name == "alice123"

    def test_is_likely_username_for_espnfan_prefix(self) -> None:
        """Test username detection for ESPNFAN prefix."""
        owner = Owner(display_name="ESPNFAN12345", first_name="", last_name="", id="espn123")
        assert owner.is_likely_username is True

    def test_is_likely_username_for_espn_lowercase_prefix(self) -> None:
        """Test username detection for espn lowercase prefix."""
        owner = Owner(display_name="espn_user_123", first_name="", last_name="", id="espn123")
        assert owner.is_likely_username is True

    def test_is_likely_username_for_long_name_with_digits(self) -> None:
        """Test username detection for long names with digits."""
        owner = Owner(display_name="cooluser12345678", first_name="", last_name="", id="user123")
        assert owner.is_likely_username is True

    def test_is_likely_username_for_all_lowercase_long_name(self) -> None:
        """Test username detection for all lowercase long names."""
        owner = Owner(display_name="mylongusername", first_name="", last_name="", id="user123")
        assert owner.is_likely_username is True

    def test_is_likely_username_for_mostly_digits(self) -> None:
        """Test username detection for names that are mostly digits."""
        owner = Owner(display_name="123456", first_name="", last_name="", id="user123")
        assert owner.is_likely_username is True

    def test_is_likely_username_false_for_real_name(self) -> None:
        """Test username detection returns False for real names."""
        owner = Owner(
            display_name="Alice Smith", first_name="Alice", last_name="Smith", id="alice123"
        )
        assert owner.is_likely_username is False

    def test_is_likely_username_for_empty_display_name(self) -> None:
        """Test username detection for empty display name."""
        owner = Owner(display_name="", first_name="Alice", last_name="Smith", id="alice123")
        assert owner.is_likely_username is True


class TestOwnerValidation:
    """Test Owner validation logic."""

    def test_validation_passes_for_valid_owner(self) -> None:
        """Test validation passes for valid owner."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        # If we get here without exception, validation passed
        assert owner.id == "alice123"

    def test_validation_fails_for_empty_id(self) -> None:
        """Test validation fails when ID is empty."""
        with pytest.raises(DataValidationError, match="Owner ID cannot be empty"):
            Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="")

    def test_validation_fails_for_whitespace_only_id(self) -> None:
        """Test validation fails when ID is whitespace only."""
        with pytest.raises(DataValidationError, match="Owner ID cannot be empty"):
            Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="   ")

    def test_validation_fails_for_all_empty_names(self) -> None:
        """Test validation fails when all name fields are empty."""
        with pytest.raises(DataValidationError, match="Owner must have at least one name field"):
            Owner(display_name="", first_name="", last_name="", id="alice123")

    def test_validation_passes_with_only_display_name(self) -> None:
        """Test validation passes with only display_name."""
        owner = Owner(display_name="alice123", first_name="", last_name="", id="alice123")
        assert owner.display_name == "alice123"


# ============================================================================
# TeamStats Model Tests
# ============================================================================


class TestTeamStatsProperties:
    """Test TeamStats computed properties."""

    def test_total_games_calculation(self) -> None:
        """Test total_games property calculation."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        team = TeamStats(
            name="Alice's Team",
            owner=owner,
            points_for=1200.0,
            points_against=1000.0,
            wins=8,
            losses=3,
            division="League A",
        )
        assert team.total_games == 11

    def test_total_games_with_zero_games(self) -> None:
        """Test total_games when no games have been played."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        team = TeamStats(
            name="Alice's Team",
            owner=owner,
            points_for=0.0,
            points_against=0.0,
            wins=0,
            losses=0,
            division="League A",
        )
        assert team.total_games == 0

    def test_win_percentage_calculation(self) -> None:
        """Test win_percentage property calculation."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        team = TeamStats(
            name="Alice's Team",
            owner=owner,
            points_for=1200.0,
            points_against=1000.0,
            wins=8,
            losses=2,
            division="League A",
        )
        assert team.win_percentage == 0.8

    def test_win_percentage_with_zero_games(self) -> None:
        """Test win_percentage returns 0.0 when no games played."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        team = TeamStats(
            name="Alice's Team",
            owner=owner,
            points_for=0.0,
            points_against=0.0,
            wins=0,
            losses=0,
            division="League A",
        )
        assert team.win_percentage == 0.0

    def test_win_percentage_perfect_record(self) -> None:
        """Test win_percentage for perfect record."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        team = TeamStats(
            name="Alice's Team",
            owner=owner,
            points_for=1500.0,
            points_against=800.0,
            wins=10,
            losses=0,
            division="League A",
        )
        assert team.win_percentage == 1.0

    def test_win_percentage_winless_season(self) -> None:
        """Test win_percentage for winless season."""
        owner = Owner(display_name="Bob", first_name="Bob", last_name="Jones", id="bob456")
        team = TeamStats(
            name="Bob's Team",
            owner=owner,
            points_for=800.0,
            points_against=1500.0,
            wins=0,
            losses=10,
            division="League A",
        )
        assert team.win_percentage == 0.0


class TestTeamStatsValidation:
    """Test TeamStats validation logic."""

    def test_validation_fails_for_empty_team_name(self) -> None:
        """Test validation fails when team name is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Team name cannot be empty"):
            TeamStats(
                name="",
                owner=owner,
                points_for=1200.0,
                points_against=1000.0,
                wins=8,
                losses=3,
                division="League A",
            )

    def test_validation_fails_for_negative_points_for(self) -> None:
        """Test validation fails when points_for is negative."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Points for cannot be negative"):
            TeamStats(
                name="Alice's Team",
                owner=owner,
                points_for=-100.0,
                points_against=1000.0,
                wins=8,
                losses=3,
                division="League A",
            )

    def test_validation_fails_for_negative_points_against(self) -> None:
        """Test validation fails when points_against is negative."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Points against cannot be negative"):
            TeamStats(
                name="Alice's Team",
                owner=owner,
                points_for=1200.0,
                points_against=-1000.0,
                wins=8,
                losses=3,
                division="League A",
            )

    def test_validation_fails_for_negative_wins(self) -> None:
        """Test validation fails when wins is negative."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Wins cannot be negative"):
            TeamStats(
                name="Alice's Team",
                owner=owner,
                points_for=1200.0,
                points_against=1000.0,
                wins=-1,
                losses=3,
                division="League A",
            )

    def test_validation_fails_for_negative_losses(self) -> None:
        """Test validation fails when losses is negative."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Losses cannot be negative"):
            TeamStats(
                name="Alice's Team",
                owner=owner,
                points_for=1200.0,
                points_against=1000.0,
                wins=8,
                losses=-3,
                division="League A",
            )

    def test_validation_fails_for_empty_division(self) -> None:
        """Test validation fails when division is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Division name cannot be empty"):
            TeamStats(
                name="Alice's Team",
                owner=owner,
                points_for=1200.0,
                points_against=1000.0,
                wins=8,
                losses=3,
                division="",
            )


# ============================================================================
# GameResult Model Tests
# ============================================================================


class TestGameResultValidation:
    """Test GameResult validation logic."""

    def test_validation_passes_for_valid_win(self) -> None:
        """Test validation passes for valid winning game."""
        game = GameResult(
            team_name="Alice's Team",
            score=120.5,
            opponent_name="Bob's Team",
            opponent_score=100.0,
            won=True,
            week=5,
            margin=20.5,
            division="League A",
        )
        assert game.won is True

    def test_validation_passes_for_valid_loss(self) -> None:
        """Test validation passes for valid losing game."""
        game = GameResult(
            team_name="Alice's Team",
            score=90.0,
            opponent_name="Bob's Team",
            opponent_score=110.5,
            won=False,
            week=5,
            margin=20.5,
            division="League A",
        )
        assert game.won is False

    def test_validation_fails_for_negative_score(self) -> None:
        """Test validation fails when score is negative."""
        with pytest.raises(DataValidationError, match="Score cannot be negative"):
            GameResult(
                team_name="Alice's Team",
                score=-10.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=False,
                week=5,
                margin=110.0,
                division="League A",
            )

    def test_validation_fails_for_negative_opponent_score(self) -> None:
        """Test validation fails when opponent_score is negative."""
        with pytest.raises(DataValidationError, match="Opponent score cannot be negative"):
            GameResult(
                team_name="Alice's Team",
                score=100.0,
                opponent_name="Bob's Team",
                opponent_score=-10.0,
                won=True,
                week=5,
                margin=110.0,
                division="League A",
            )

    def test_validation_fails_for_invalid_week_too_low(self) -> None:
        """Test validation fails when week is less than 1."""
        with pytest.raises(DataValidationError, match="Week must be between 1 and 18"):
            GameResult(
                team_name="Alice's Team",
                score=120.5,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=True,
                week=0,
                margin=20.5,
                division="League A",
            )

    def test_validation_fails_for_invalid_week_too_high(self) -> None:
        """Test validation fails when week is greater than 18."""
        with pytest.raises(DataValidationError, match="Week must be between 1 and 18"):
            GameResult(
                team_name="Alice's Team",
                score=120.5,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=True,
                week=19,
                margin=20.5,
                division="League A",
            )

    def test_validation_fails_for_negative_margin(self) -> None:
        """Test validation fails when margin is negative."""
        with pytest.raises(DataValidationError, match="Margin cannot be negative"):
            GameResult(
                team_name="Alice's Team",
                score=120.5,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=True,
                week=5,
                margin=-20.5,
                division="League A",
            )

    def test_validation_fails_for_win_loss_inconsistency(self) -> None:
        """Test validation fails when won flag doesn't match scores."""
        with pytest.raises(DataValidationError, match="Win/loss inconsistent with scores"):
            GameResult(
                team_name="Alice's Team",
                score=90.0,
                opponent_name="Bob's Team",
                opponent_score=110.0,
                won=True,  # Should be False based on scores
                week=5,
                margin=20.0,
                division="League A",
            )

    def test_validation_fails_for_incorrect_margin(self) -> None:
        """Test validation fails when margin doesn't match score difference."""
        with pytest.raises(DataValidationError, match="Margin inconsistent with scores"):
            GameResult(
                team_name="Alice's Team",
                score=120.5,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=True,
                week=5,
                margin=30.0,  # Should be 20.5
                division="League A",
            )

    def test_validation_fails_for_empty_team_name(self) -> None:
        """Test validation fails when team_name is empty."""
        with pytest.raises(DataValidationError, match="Team name cannot be empty"):
            GameResult(
                team_name="",
                score=120.5,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                won=True,
                week=5,
                margin=20.5,
                division="League A",
            )

    def test_validation_fails_for_empty_opponent_name(self) -> None:
        """Test validation fails when opponent_name is empty."""
        with pytest.raises(DataValidationError, match="Opponent name cannot be empty"):
            GameResult(
                team_name="Alice's Team",
                score=120.5,
                opponent_name="",
                opponent_score=100.0,
                won=True,
                week=5,
                margin=20.5,
                division="League A",
            )


# ============================================================================
# WeeklyPlayerStats Model Tests
# ============================================================================


class TestWeeklyPlayerStatsProperties:
    """Test WeeklyPlayerStats computed properties."""

    def test_is_starter_for_qb_position(self) -> None:
        """Test is_starter returns True for QB slot."""
        player = WeeklyPlayerStats(
            name="Patrick Mahomes",
            position="QB",
            team_name="Alice's Team",
            division="League A",
            points=25.5,
            projected_points=22.0,
            projection_diff=3.5,
            slot_position="QB",
            week=5,
            pro_team="KC",
            pro_opponent="LV",
        )
        assert player.is_starter is True

    def test_is_starter_false_for_bench(self) -> None:
        """Test is_starter returns False for bench slot."""
        player = WeeklyPlayerStats(
            name="Backup QB",
            position="QB",
            team_name="Alice's Team",
            division="League A",
            points=15.0,
            projected_points=18.0,
            projection_diff=-3.0,
            slot_position="BE",
            week=5,
            pro_team="KC",
            pro_opponent="LV",
        )
        assert player.is_starter is False

    def test_is_starter_false_for_injured_reserve(self) -> None:
        """Test is_starter returns False for IR slot."""
        player = WeeklyPlayerStats(
            name="Injured Player",
            position="RB",
            team_name="Alice's Team",
            division="League A",
            points=0.0,
            projected_points=0.0,
            projection_diff=0.0,
            slot_position="IR",
            week=5,
            pro_team="KC",
            pro_opponent="",
        )
        assert player.is_starter is False

    def test_is_starter_case_insensitive(self) -> None:
        """Test is_starter is case-insensitive."""
        player = WeeklyPlayerStats(
            name="Bench Player",
            position="WR",
            team_name="Alice's Team",
            division="League A",
            points=10.0,
            projected_points=12.0,
            projection_diff=-2.0,
            slot_position="be",  # lowercase
            week=5,
            pro_team="KC",
            pro_opponent="LV",
        )
        assert player.is_starter is False

    def test_exceeded_projection_true(self) -> None:
        """Test exceeded_projection returns True when player exceeded projection."""
        player = WeeklyPlayerStats(
            name="Patrick Mahomes",
            position="QB",
            team_name="Alice's Team",
            division="League A",
            points=28.5,
            projected_points=22.0,
            projection_diff=6.5,
            slot_position="QB",
            week=5,
            pro_team="KC",
            pro_opponent="LV",
        )
        assert player.exceeded_projection is True

    def test_exceeded_projection_false(self) -> None:
        """Test exceeded_projection returns False when player underperformed."""
        player = WeeklyPlayerStats(
            name="Bad Week QB",
            position="QB",
            team_name="Alice's Team",
            division="League A",
            points=15.0,
            projected_points=22.0,
            projection_diff=-7.0,
            slot_position="QB",
            week=5,
            pro_team="KC",
            pro_opponent="LV",
        )
        assert player.exceeded_projection is False


class TestWeeklyPlayerStatsValidation:
    """Test WeeklyPlayerStats validation logic."""

    def test_validation_passes_for_valid_player(self) -> None:
        """Test validation passes for valid player stats."""
        player = WeeklyPlayerStats(
            name="Patrick Mahomes",
            position="QB",
            team_name="Alice's Team",
            division="League A",
            points=25.5,
            projected_points=22.0,
            projection_diff=3.5,
            slot_position="QB",
            week=5,
            pro_team="KC",
            pro_opponent="LV",
        )
        assert player.name == "Patrick Mahomes"

    def test_validation_allows_negative_points(self) -> None:
        """Test validation allows negative points (fumbles, INTs)."""
        player = WeeklyPlayerStats(
            name="Bad Day QB",
            position="QB",
            team_name="Alice's Team",
            division="League A",
            points=-5.0,  # Negative points allowed
            projected_points=18.0,
            projection_diff=-23.0,
            slot_position="QB",
            week=5,
            pro_team="KC",
            pro_opponent="LV",
        )
        assert player.points == -5.0

    def test_validation_fails_for_negative_projected_points(self) -> None:
        """Test validation fails when projected_points is negative."""
        with pytest.raises(DataValidationError, match="Projected points cannot be negative"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="QB",
                team_name="Alice's Team",
                division="League A",
                points=25.5,
                projected_points=-22.0,  # Invalid
                projection_diff=47.5,
                slot_position="QB",
                week=5,
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_incorrect_projection_diff(self) -> None:
        """Test validation fails when projection_diff is incorrect."""
        with pytest.raises(DataValidationError, match="Projection diff .* doesn't match"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="QB",
                team_name="Alice's Team",
                division="League A",
                points=25.5,
                projected_points=22.0,
                projection_diff=10.0,  # Should be 3.5
                slot_position="QB",
                week=5,
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_invalid_week(self) -> None:
        """Test validation fails for invalid week number."""
        with pytest.raises(DataValidationError, match="Week must be between 1 and 18"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="QB",
                team_name="Alice's Team",
                division="League A",
                points=25.5,
                projected_points=22.0,
                projection_diff=3.5,
                slot_position="QB",
                week=20,  # Invalid
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_empty_player_name(self) -> None:
        """Test validation fails when player name is empty."""
        with pytest.raises(DataValidationError, match="Player name cannot be empty"):
            WeeklyPlayerStats(
                name="",
                position="QB",
                team_name="Alice's Team",
                division="League A",
                points=25.5,
                projected_points=22.0,
                projection_diff=3.5,
                slot_position="QB",
                week=5,
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_empty_position(self) -> None:
        """Test validation fails when position is empty."""
        with pytest.raises(DataValidationError, match="Position cannot be empty"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="",
                team_name="Alice's Team",
                division="League A",
                points=25.5,
                projected_points=22.0,
                projection_diff=3.5,
                slot_position="QB",
                week=5,
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_empty_team_name(self) -> None:
        """Test validation fails when team name is empty."""
        with pytest.raises(DataValidationError, match="Team name cannot be empty"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="QB",
                team_name="  ",
                division="League A",
                points=25.5,
                projected_points=22.0,
                projection_diff=3.5,
                slot_position="QB",
                week=5,
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_empty_division(self) -> None:
        """Test validation fails when division is empty."""
        with pytest.raises(DataValidationError, match="Division name cannot be empty"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="QB",
                team_name="Alice's Team",
                division="  ",
                points=25.5,
                projected_points=22.0,
                projection_diff=3.5,
                slot_position="QB",
                week=5,
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_empty_slot_position(self) -> None:
        """Test validation fails when slot_position is empty."""
        with pytest.raises(DataValidationError, match="Slot position cannot be empty"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="QB",
                team_name="Alice's Team",
                division="League A",
                points=25.5,
                projected_points=22.0,
                projection_diff=3.5,
                slot_position="  ",
                week=5,
                pro_team="KC",
                pro_opponent="LV",
            )

    def test_validation_fails_for_empty_pro_team(self) -> None:
        """Test validation fails when pro_team is empty."""
        with pytest.raises(DataValidationError, match="Pro team cannot be empty"):
            WeeklyPlayerStats(
                name="Patrick Mahomes",
                position="QB",
                team_name="Alice's Team",
                division="League A",
                points=25.5,
                projected_points=22.0,
                projection_diff=3.5,
                slot_position="QB",
                week=5,
                pro_team="  ",
                pro_opponent="LV",
            )


# ============================================================================
# WeeklyGameResult Model Tests
# ============================================================================


class TestWeeklyGameResultValidation:
    """Test WeeklyGameResult validation logic."""

    def test_validation_passes_for_valid_game(self) -> None:
        """Test validation passes for valid weekly game."""
        game = WeeklyGameResult(
            team_name="Alice's Team",
            score=125.5,
            projected_score=120.0,
            opponent_name="Bob's Team",
            opponent_score=100.0,
            opponent_projected_score=105.0,
            won=True,
            week=5,
            margin=25.5,
            projection_diff=5.5,
            division="League A",
        )
        assert game.score == 125.5

    def test_validation_passes_with_starter_projections(self) -> None:
        """Test validation passes with starter projection fields."""
        game = WeeklyGameResult(
            team_name="Alice's Team",
            score=125.5,
            projected_score=120.0,
            opponent_name="Bob's Team",
            opponent_score=100.0,
            opponent_projected_score=105.0,
            won=True,
            week=5,
            margin=25.5,
            projection_diff=5.5,
            division="League A",
            starter_projected_score=118.0,
            true_projection_diff=7.5,
        )
        assert game.starter_projected_score == 118.0
        assert game.true_projection_diff == 7.5

    def test_validation_fails_for_negative_projected_score(self) -> None:
        """Test validation fails when projected_score is negative."""
        with pytest.raises(DataValidationError, match="Projected score cannot be negative"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=-120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=245.5,
                division="League A",
            )

    def test_validation_fails_for_incorrect_projection_diff(self) -> None:
        """Test validation fails when projection_diff is incorrect."""
        with pytest.raises(DataValidationError, match="Projection diff .* doesn't match"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=20.0,  # Should be 5.5
                division="League A",
            )

    def test_validation_fails_for_negative_starter_projected_score(self) -> None:
        """Test validation fails when starter_projected_score is negative."""
        with pytest.raises(DataValidationError, match="Starter projected score cannot be negative"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
                starter_projected_score=-118.0,
                true_projection_diff=243.5,
            )

    def test_validation_fails_for_incorrect_true_projection_diff(self) -> None:
        """Test validation fails when true_projection_diff is incorrect."""
        with pytest.raises(DataValidationError, match="True projection diff .* doesn't match"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
                starter_projected_score=118.0,
                true_projection_diff=15.0,  # Should be 7.5
            )

    def test_validation_fails_for_empty_team_name(self) -> None:
        """Test validation fails when team_name is empty."""
        with pytest.raises(DataValidationError, match="Team name cannot be empty"):
            WeeklyGameResult(
                team_name="  ",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
            )

    def test_validation_fails_for_empty_opponent_name(self) -> None:
        """Test validation fails when opponent_name is empty."""
        with pytest.raises(DataValidationError, match="Opponent name cannot be empty"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="  ",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
            )

    def test_validation_fails_for_negative_score(self) -> None:
        """Test validation fails when score is negative."""
        with pytest.raises(DataValidationError, match="Score cannot be negative"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=-125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=-245.5,
                division="League A",
            )

    def test_validation_fails_for_negative_opponent_score(self) -> None:
        """Test validation fails when opponent_score is negative."""
        with pytest.raises(DataValidationError, match="Opponent score cannot be negative"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=-100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
            )

    def test_validation_fails_for_negative_opponent_projected_score(self) -> None:
        """Test validation fails when opponent_projected_score is negative."""
        with pytest.raises(
            DataValidationError, match="Opponent projected score cannot be negative"
        ):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=-105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
            )

    def test_validation_fails_for_week_too_low(self) -> None:
        """Test validation fails when week is < 1."""
        with pytest.raises(DataValidationError, match="Week must be between 1 and 18"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=0,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
            )

    def test_validation_fails_for_week_too_high(self) -> None:
        """Test validation fails when week is > 18."""
        with pytest.raises(DataValidationError, match="Week must be between 1 and 18"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=19,
                margin=25.5,
                projection_diff=5.5,
                division="League A",
            )

    def test_validation_fails_for_negative_margin(self) -> None:
        """Test validation fails when margin is negative."""
        with pytest.raises(DataValidationError, match="Margin cannot be negative"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=-25.5,
                projection_diff=5.5,
                division="League A",
            )

    def test_validation_fails_for_empty_division(self) -> None:
        """Test validation fails when division is empty."""
        with pytest.raises(DataValidationError, match="Division name cannot be empty"):
            WeeklyGameResult(
                team_name="Alice's Team",
                score=125.5,
                projected_score=120.0,
                opponent_name="Bob's Team",
                opponent_score=100.0,
                opponent_projected_score=105.0,
                won=True,
                week=5,
                margin=25.5,
                projection_diff=5.5,
                division="  ",
            )


# ============================================================================
# ChallengeResult Model Tests
# ============================================================================


class TestChallengeResultValidation:
    """Test ChallengeResult validation logic."""

    def test_validation_passes_for_valid_challenge(self) -> None:
        """Test validation passes for valid challenge result."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        challenge = ChallengeResult(
            challenge_name="Most Points Overall",
            winner="Alice's Team",
            owner=owner,
            division="League A",
            value="1500.50",
            description="Alice's Team scored the most points",
        )
        assert challenge.winner == "Alice's Team"

    def test_validation_fails_for_empty_division(self) -> None:
        """Test validation fails when division is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Division cannot be empty"):
            ChallengeResult(
                challenge_name="Most Points Overall",
                winner="Alice's Team",
                owner=owner,
                division="",
                value="1500.50",
                description="Alice's Team scored the most points",
            )

    def test_validation_fails_for_empty_challenge_name(self) -> None:
        """Test validation fails when challenge_name is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Challenge name cannot be empty"):
            ChallengeResult(
                challenge_name="  ",
                winner="Alice's Team",
                owner=owner,
                division="League A",
                value="1500.50",
                description="Alice's Team scored the most points",
            )

    def test_validation_fails_for_empty_winner(self) -> None:
        """Test validation fails when winner is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Winner cannot be empty"):
            ChallengeResult(
                challenge_name="Most Points Overall",
                winner="  ",
                owner=owner,
                division="League A",
                value="1500.50",
                description="Alice's Team scored the most points",
            )

    def test_validation_fails_for_empty_description(self) -> None:
        """Test validation fails when description is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Description cannot be empty"):
            ChallengeResult(
                challenge_name="Most Points Overall",
                winner="Alice's Team",
                owner=owner,
                division="League A",
                value="1500.50",
                description="",
            )


# ============================================================================
# WeeklyChallenge Model Tests
# ============================================================================


class TestWeeklyChallengeProperties:
    """Test WeeklyChallenge computed properties."""

    def test_is_player_challenge_with_position_in_additional_info(self) -> None:
        """Test is_player_challenge returns True when position in additional_info."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        challenge = WeeklyChallenge(
            challenge_name="Best QB",
            week=5,
            winner="Patrick Mahomes",
            owner=owner,
            division="League A",
            value="28.5",
            description="Patrick Mahomes scored 28.5 points",
            additional_info={"position": "QB", "team": "Alice's Team"},
        )
        assert challenge.is_player_challenge is True

    def test_is_player_challenge_with_player_in_name(self) -> None:
        """Test is_player_challenge returns True when 'player' in challenge name."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        challenge = WeeklyChallenge(
            challenge_name="Top Scoring Player",
            week=5,
            winner="Patrick Mahomes",
            owner=owner,
            division="League A",
            value="28.5",
            description="Patrick Mahomes scored 28.5 points",
            additional_info={"team": "Alice's Team"},
        )
        assert challenge.is_player_challenge is True

    def test_is_player_challenge_false_for_team_challenge(self) -> None:
        """Test is_player_challenge returns False for team challenges."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        challenge = WeeklyChallenge(
            challenge_name="Highest Score This Week",
            week=5,
            winner="Alice's Team",
            owner=owner,
            division="League A",
            value="150.5",
            description="Alice's Team scored 150.5 points",
            additional_info={},
        )
        assert challenge.is_player_challenge is False

    def test_is_team_challenge_true_for_team_challenge(self) -> None:
        """Test is_team_challenge returns True for team challenges."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        challenge = WeeklyChallenge(
            challenge_name="Biggest Win This Week",
            week=5,
            winner="Alice's Team",
            owner=owner,
            division="League A",
            value="50.0",
            description="Alice's Team won by 50.0 points",
            additional_info={"margin": "50.0"},
        )
        assert challenge.is_team_challenge is True

    def test_is_team_challenge_false_for_player_challenge(self) -> None:
        """Test is_team_challenge returns False for player challenges."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        challenge = WeeklyChallenge(
            challenge_name="Best RB",
            week=5,
            winner="Christian McCaffrey",
            owner=owner,
            division="League A",
            value="32.0",
            description="Christian McCaffrey scored 32.0 points",
            additional_info={"position": "RB"},
        )
        assert challenge.is_team_challenge is False


class TestWeeklyChallengeValidation:
    """Test WeeklyChallenge validation logic."""

    def test_validation_passes_for_valid_challenge(self) -> None:
        """Test validation passes for valid weekly challenge."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        challenge = WeeklyChallenge(
            challenge_name="Highest Score This Week",
            week=5,
            winner="Alice's Team",
            owner=owner,
            division="League A",
            value="150.5",
            description="Alice's Team scored 150.5 points",
            additional_info={},
        )
        assert challenge.week == 5

    def test_validation_passes_with_none_owner(self) -> None:
        """Test validation passes when owner is None (player challenges)."""
        challenge = WeeklyChallenge(
            challenge_name="Best QB",
            week=5,
            winner="Patrick Mahomes",
            owner=None,
            division="League A",
            value="28.5",
            description="Patrick Mahomes scored 28.5 points",
            additional_info={"position": "QB"},
        )
        assert challenge.owner is None

    def test_validation_fails_for_empty_challenge_name(self) -> None:
        """Test validation fails when challenge_name is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Challenge name cannot be empty"):
            WeeklyChallenge(
                challenge_name="",
                week=5,
                winner="Alice's Team",
                owner=owner,
                division="League A",
                value="150.5",
                description="Alice's Team scored 150.5 points",
                additional_info={},
            )

    def test_validation_fails_for_invalid_week(self) -> None:
        """Test validation fails for invalid week number."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Week must be between 1 and 18"):
            WeeklyChallenge(
                challenge_name="Highest Score This Week",
                week=0,
                winner="Alice's Team",
                owner=owner,
                division="League A",
                value="150.5",
                description="Alice's Team scored 150.5 points",
                additional_info={},
            )

    def test_validation_fails_for_empty_winner(self) -> None:
        """Test validation fails when winner is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Winner cannot be empty"):
            WeeklyChallenge(
                challenge_name="Highest Score This Week",
                week=5,
                winner="",
                owner=owner,
                division="League A",
                value="150.5",
                description="Alice's Team scored 150.5 points",
                additional_info={},
            )

    def test_validation_fails_for_empty_division(self) -> None:
        """Test validation fails when division is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Division cannot be empty"):
            WeeklyChallenge(
                challenge_name="Highest Score This Week",
                week=5,
                winner="Alice's Team",
                owner=owner,
                division="",
                value="150.5",
                description="Alice's Team scored 150.5 points",
                additional_info={},
            )

    def test_validation_fails_for_empty_description(self) -> None:
        """Test validation fails when description is empty."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        with pytest.raises(DataValidationError, match="Description cannot be empty"):
            WeeklyChallenge(
                challenge_name="Highest Score This Week",
                week=5,
                winner="Alice's Team",
                owner=owner,
                division="League A",
                value="150.5",
                description="",
                additional_info={},
            )


# ============================================================================
# DivisionData Model Tests
# ============================================================================


class TestDivisionDataProperties:
    """Test DivisionData computed properties."""

    def test_create_with_default_weekly_fields(self) -> None:
        """Test creating division with default weekly fields."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
        ]
        # Don't pass weekly_games or weekly_players to use default factories
        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=teams,
            games=[],
        )
        assert division.weekly_games == []
        assert division.weekly_players == []

    def test_team_count_property(self) -> None:
        """Test team_count property returns correct count."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
            TeamStats(
                name="Team B",
                owner=owner,
                points_for=1100.0,
                points_against=950.0,
                wins=9,
                losses=4,
                division="League A",
            ),
        ]
        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=teams,
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )
        assert division.team_count == 2

    def test_game_count_property(self) -> None:
        """Test game_count property returns correct count."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
        ]
        games = [
            GameResult(
                team_name="Team A",
                score=120.0,
                opponent_name="Team B",
                opponent_score=100.0,
                won=True,
                week=1,
                margin=20.0,
                division="League A",
            ),
            GameResult(
                team_name="Team A",
                score=130.0,
                opponent_name="Team C",
                opponent_score=110.0,
                won=True,
                week=2,
                margin=20.0,
                division="League A",
            ),
        ]
        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=teams,
            games=games,
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )
        assert division.game_count == 2

    def test_is_playoff_mode_false(self) -> None:
        """Test is_playoff_mode is False when no bracket."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
        ]
        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=teams,
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )
        assert division.is_playoff_mode is False

    def test_get_team_by_name_found(self) -> None:
        """Test get_team_by_name returns correct team."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
            TeamStats(
                name="Team B",
                owner=owner,
                points_for=1100.0,
                points_against=950.0,
                wins=9,
                losses=4,
                division="League A",
            ),
        ]
        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=teams,
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )
        team = division.get_team_by_name("Team B")
        assert team is not None
        assert team.name == "Team B"

    def test_get_team_by_name_not_found(self) -> None:
        """Test get_team_by_name returns None for missing team."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
        ]
        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=teams,
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=None,
        )
        team = division.get_team_by_name("Nonexistent Team")
        assert team is None


class TestDivisionDataValidation:
    """Test DivisionData validation logic."""

    def test_validation_fails_for_negative_league_id(self) -> None:
        """Test validation fails for negative league ID."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
        ]
        with pytest.raises(DataValidationError, match="League ID must be positive"):
            DivisionData(
                league_id=-123,
                name="League A",
                teams=teams,
                games=[],
                weekly_games=[],
                weekly_players=[],
                playoff_bracket=None,
            )

    def test_validation_fails_for_empty_name(self) -> None:
        """Test validation fails for empty division name."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
        ]
        with pytest.raises(DataValidationError, match="Division name cannot be empty"):
            DivisionData(
                league_id=123456,
                name="  ",
                teams=teams,
                games=[],
                weekly_games=[],
                weekly_players=[],
                playoff_bracket=None,
            )

    def test_validation_fails_for_no_teams(self) -> None:
        """Test validation fails when division has no teams."""
        with pytest.raises(DataValidationError, match="Division must have at least one team"):
            DivisionData(
                league_id=123456,
                name="League A",
                teams=[],
                games=[],
                weekly_games=[],
                weekly_players=[],
                playoff_bracket=None,
            )

    def test_validation_fails_for_team_with_wrong_division(self) -> None:
        """Test validation fails when team has wrong division name."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="Wrong Division",  # Wrong division
            ),
        ]
        with pytest.raises(
            DataValidationError, match="Team Team A has division 'Wrong Division' but should be"
        ):
            DivisionData(
                league_id=123456,
                name="League A",
                teams=teams,
                games=[],
                weekly_games=[],
                weekly_players=[],
                playoff_bracket=None,
            )

    def test_validation_fails_for_game_with_wrong_division(self) -> None:
        """Test validation fails when game has wrong division name."""
        owner = Owner(display_name="Alice", first_name="Alice", last_name="Smith", id="alice123")
        teams = [
            TeamStats(
                name="Team A",
                owner=owner,
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="League A",
            ),
        ]
        games = [
            GameResult(
                team_name="Team A",
                score=120.0,
                opponent_name="Team B",
                opponent_score=100.0,
                won=True,
                week=1,
                margin=20.0,
                division="Wrong Division",  # Wrong division
            ),
        ]
        with pytest.raises(
            DataValidationError, match="Game has division 'Wrong Division' but should be"
        ):
            DivisionData(
                league_id=123456,
                name="League A",
                teams=teams,
                games=games,
                weekly_games=[],
                weekly_players=[],
                playoff_bracket=None,
            )
