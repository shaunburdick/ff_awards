"""
Comprehensive tests for ESPN service helper methods and validation logic.

Tests focus on methods that can be tested without ESPN API connection:
- Data extraction helpers
- Validation logic
- Data transformation
- Playoff calculations
- Error handling
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from ff_tracker.config import FFTrackerConfig
from ff_tracker.exceptions import ESPNAPIError
from ff_tracker.models import Owner, TeamStats
from ff_tracker.services.espn_service import ESPNService


class TestESPNServiceInit:
    """Tests for ESPNService initialization."""

    def test_init_with_config(self) -> None:
        """Test service initializes with config."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service.config == config
        assert service.current_week is None


class TestPlayoffStatusCalculation:
    """Tests for _calculate_playoff_status method."""

    def test_top_4_teams_qualify_by_wins(self) -> None:
        """Test that top 4 teams by record qualify for playoffs."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Create 6 teams with different records
        teams = [
            TeamStats(
                name="Team A",
                owner=Owner(display_name="Owner A", first_name="", last_name="", id="1"),
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="Test",
            ),
            TeamStats(
                name="Team B",
                owner=Owner(display_name="Owner B", first_name="", last_name="", id="2"),
                points_for=1100.0,
                points_against=950.0,
                wins=9,
                losses=4,
                division="Test",
            ),
            TeamStats(
                name="Team C",
                owner=Owner(display_name="Owner C", first_name="", last_name="", id="3"),
                points_for=1050.0,
                points_against=1000.0,
                wins=8,
                losses=5,
                division="Test",
            ),
            TeamStats(
                name="Team D",
                owner=Owner(display_name="Owner D", first_name="", last_name="", id="4"),
                points_for=1000.0,
                points_against=1050.0,
                wins=7,
                losses=6,
                division="Test",
            ),
            TeamStats(
                name="Team E",
                owner=Owner(display_name="Owner E", first_name="", last_name="", id="5"),
                points_for=950.0,
                points_against=1100.0,
                wins=6,
                losses=7,
                division="Test",
            ),
            TeamStats(
                name="Team F",
                owner=Owner(display_name="Owner F", first_name="", last_name="", id="6"),
                points_for=900.0,
                points_against=1150.0,
                wins=5,
                losses=8,
                division="Test",
            ),
        ]

        playoff_status = service._calculate_playoff_status(teams)

        # Top 4 teams should qualify
        assert playoff_status["Team A"] is True
        assert playoff_status["Team B"] is True
        assert playoff_status["Team C"] is True
        assert playoff_status["Team D"] is True
        # Bottom 2 teams should not qualify
        assert playoff_status["Team E"] is False
        assert playoff_status["Team F"] is False

    def test_tiebreaker_uses_points_for(self) -> None:
        """Test that ties in record use points_for as tiebreaker."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Create 5 teams where positions 4 and 5 have same record
        teams = [
            TeamStats(
                name="Team A",
                owner=Owner(display_name="Owner A", first_name="", last_name="", id="1"),
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="Test",
            ),
            TeamStats(
                name="Team B",
                owner=Owner(display_name="Owner B", first_name="", last_name="", id="2"),
                points_for=1100.0,
                points_against=950.0,
                wins=9,
                losses=4,
                division="Test",
            ),
            TeamStats(
                name="Team C",
                owner=Owner(display_name="Owner C", first_name="", last_name="", id="3"),
                points_for=1050.0,
                points_against=1000.0,
                wins=8,
                losses=5,
                division="Test",
            ),
            # These two teams have same record (7-6), but different points_for
            TeamStats(
                name="Team D",
                owner=Owner(display_name="Owner D", first_name="", last_name="", id="4"),
                points_for=1000.0,
                points_against=1050.0,
                wins=7,
                losses=6,
                division="Test",
            ),
            TeamStats(
                name="Team E",
                owner=Owner(display_name="Owner E", first_name="", last_name="", id="5"),
                points_for=950.0,
                points_against=1100.0,
                wins=7,
                losses=6,
                division="Test",
            ),
        ]

        playoff_status = service._calculate_playoff_status(teams)

        # Team D should make playoffs over Team E due to higher points_for
        assert playoff_status["Team D"] is True
        assert playoff_status["Team E"] is False

    def test_empty_teams_list(self) -> None:
        """Test that empty teams list returns empty dict."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        playoff_status = service._calculate_playoff_status([])

        assert playoff_status == {}

    def test_fewer_than_4_teams(self) -> None:
        """Test that all teams qualify when fewer than 4 teams exist."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        teams = [
            TeamStats(
                name="Team A",
                owner=Owner(display_name="Owner A", first_name="", last_name="", id="1"),
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="Test",
            ),
            TeamStats(
                name="Team B",
                owner=Owner(display_name="Owner B", first_name="", last_name="", id="2"),
                points_for=1100.0,
                points_against=950.0,
                wins=9,
                losses=4,
                division="Test",
            ),
        ]

        playoff_status = service._calculate_playoff_status(teams)

        # Both teams should qualify
        assert playoff_status["Team A"] is True
        assert playoff_status["Team B"] is True

    def test_exactly_4_teams(self) -> None:
        """Test that all 4 teams qualify when exactly 4 teams exist."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        teams = [
            TeamStats(
                name="Team A",
                owner=Owner(display_name="Owner A", first_name="", last_name="", id="1"),
                points_for=1200.0,
                points_against=900.0,
                wins=10,
                losses=3,
                division="Test",
            ),
            TeamStats(
                name="Team B",
                owner=Owner(display_name="Owner B", first_name="", last_name="", id="2"),
                points_for=1100.0,
                points_against=950.0,
                wins=9,
                losses=4,
                division="Test",
            ),
            TeamStats(
                name="Team C",
                owner=Owner(display_name="Owner C", first_name="", last_name="", id="3"),
                points_for=1050.0,
                points_against=1000.0,
                wins=8,
                losses=5,
                division="Test",
            ),
            TeamStats(
                name="Team D",
                owner=Owner(display_name="Owner D", first_name="", last_name="", id="4"),
                points_for=1000.0,
                points_against=1050.0,
                wins=7,
                losses=6,
                division="Test",
            ),
        ]

        playoff_status = service._calculate_playoff_status(teams)

        # All 4 teams should qualify
        assert all(playoff_status.values())


class TestLooksLikeUsername:
    """Tests for _looks_like_username helper method."""

    def test_espnfan_prefix_detected(self) -> None:
        """Test that ESPNFAN prefix is detected as username."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("ESPNFAN12345") is True

    def test_espn_prefix_detected(self) -> None:
        """Test that espn prefix is detected as username."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("espnuser123") is True

    def test_long_name_with_digits_detected(self) -> None:
        """Test that long names with digits are detected as usernames."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("johndoe123456789") is True

    def test_long_lowercase_detected(self) -> None:
        """Test that long all-lowercase names are detected as usernames."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("mylongusername") is True

    def test_mostly_digits_detected(self) -> None:
        """Test that names with mostly digits are detected as usernames."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("12345abc") is True

    def test_real_name_not_detected(self) -> None:
        """Test that normal names are not detected as usernames."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("John Doe") is False

    def test_empty_string_detected(self) -> None:
        """Test that empty string is detected as username."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("") is True

    def test_whitespace_only_detected(self) -> None:
        """Test that whitespace-only string is detected as username."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        assert service._looks_like_username("   ") is True


class TestCreateUnknownOwner:
    """Tests for _create_unknown_owner helper method."""

    def test_creates_valid_owner(self) -> None:
        """Test that unknown owner is created with correct values."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        owner = service._create_unknown_owner()

        assert isinstance(owner, Owner)
        assert owner.display_name == "Unknown Owner"
        assert owner.first_name == ""
        assert owner.last_name == ""
        assert owner.id == "unknown"


class TestConvertTeamOwners:
    """Tests for convert_team_owners method."""

    def test_convert_single_owner(self) -> None:
        """Test converting team with single owner."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Mock ESPN team with typed owners data
        mock_team = Mock()
        mock_team.owners = [
            {"displayName": "John Doe", "firstName": "John", "lastName": "Doe", "id": "12345"}
        ]

        owners = service.convert_team_owners(mock_team)

        assert len(owners) == 1
        assert owners[0].display_name == "John Doe"
        assert owners[0].first_name == "John"
        assert owners[0].last_name == "Doe"
        assert owners[0].id == "12345"

    def test_convert_multiple_owners(self) -> None:
        """Test converting team with multiple owners."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_team = Mock()
        mock_team.owners = [
            {"displayName": "John Doe", "firstName": "John", "lastName": "Doe", "id": "12345"},
            {"displayName": "Jane Smith", "firstName": "Jane", "lastName": "Smith", "id": "67890"},
        ]

        owners = service.convert_team_owners(mock_team)

        assert len(owners) == 2
        assert owners[0].display_name == "John Doe"
        assert owners[1].display_name == "Jane Smith"

    def test_convert_no_owners(self) -> None:
        """Test converting team with no owners."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_team = Mock()
        mock_team.owners = []

        owners = service.convert_team_owners(mock_team)

        assert owners == []

    def test_convert_none_owners(self) -> None:
        """Test converting team with None owners."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_team = Mock()
        mock_team.owners = None

        owners = service.convert_team_owners(mock_team)

        assert owners == []

    def test_convert_missing_fields(self) -> None:
        """Test converting owners with some missing fields (at least one name required)."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_team = Mock()
        mock_team.owners = [
            {
                "displayName": "TestUser",  # Need at least one name field
                "id": "12345",
                # firstName, lastName missing
            }
        ]

        owners = service.convert_team_owners(mock_team)

        assert len(owners) == 1
        assert owners[0].display_name == "TestUser"
        assert owners[0].first_name == ""
        assert owners[0].last_name == ""
        assert owners[0].id == "12345"


class TestCalculateStarterProjections:
    """Tests for _calculate_starter_projections method."""

    def test_calculate_starters_only(self) -> None:
        """Test that only starters are included in projection calculation."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Mock lineup with starters and bench
        mock_lineup = [
            Mock(slot_position="QB", projected_points=20.5),
            Mock(slot_position="RB", projected_points=15.0),
            Mock(slot_position="WR", projected_points=12.5),
            Mock(slot_position="BE", projected_points=10.0),  # Bench - should be excluded
            Mock(slot_position="BE", projected_points=8.5),  # Bench - should be excluded
        ]

        total = service._calculate_starter_projections(mock_lineup)

        # Should only include starters (20.5 + 15.0 + 12.5 = 48.0)
        assert total == 48.0

    def test_calculate_empty_lineup(self) -> None:
        """Test calculating projections for empty lineup."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        total = service._calculate_starter_projections([])

        assert total == 0.0

    def test_calculate_all_bench(self) -> None:
        """Test calculating projections when all players are benched."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_lineup = [
            Mock(slot_position="BE", projected_points=10.0),
            Mock(slot_position="BE", projected_points=8.5),
        ]

        total = service._calculate_starter_projections(mock_lineup)

        assert total == 0.0

    def test_calculate_missing_projected_points(self) -> None:
        """Test handling players without projected_points attribute."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Mock player without projected_points
        mock_player = Mock(slot_position="QB")
        del mock_player.projected_points

        mock_lineup = [
            mock_player,
            Mock(slot_position="RB", projected_points=15.0),
        ]

        total = service._calculate_starter_projections(mock_lineup)

        # Should only include the RB (15.0)
        assert total == 15.0

    def test_calculate_exception_returns_none(self) -> None:
        """Test that exceptions return None."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Mock lineup that will raise exception
        mock_lineup = Mock()
        mock_lineup.__iter__ = Mock(side_effect=Exception("Test error"))

        total = service._calculate_starter_projections(mock_lineup)

        assert total is None


class TestIsInPlayoffs:
    """Tests for is_in_playoffs method."""

    def test_regular_season_returns_false(self) -> None:
        """Test that regular season weeks return False."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 14
        mock_league.settings.reg_season_count = 14

        assert service.is_in_playoffs(mock_league) is False

    def test_playoff_week_returns_true(self) -> None:
        """Test that playoff weeks return True."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 15
        mock_league.settings.reg_season_count = 14

        assert service.is_in_playoffs(mock_league) is True

    def test_last_regular_season_week_returns_false(self) -> None:
        """Test that last regular season week returns False."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 14
        mock_league.settings.reg_season_count = 14

        assert service.is_in_playoffs(mock_league) is False


class TestGetPlayoffRound:
    """Tests for get_playoff_round method."""

    def test_semifinals_week_15(self) -> None:
        """Test that week 15 returns Semifinals."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 15
        mock_league.settings.reg_season_count = 14

        assert service.get_playoff_round(mock_league, 15) == "Semifinals"

    def test_finals_week_16(self) -> None:
        """Test that week 16 returns Finals."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 16
        mock_league.settings.reg_season_count = 14

        assert service.get_playoff_round(mock_league, 16) == "Finals"

    def test_championship_week_17(self) -> None:
        """Test that week 17 returns Championship Week."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 17
        mock_league.settings.reg_season_count = 14

        assert service.get_playoff_round(mock_league, 17) == "Championship Week"

    def test_uses_current_week_when_none(self) -> None:
        """Test that it uses league.current_week when week=None."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 15
        mock_league.settings.reg_season_count = 14

        assert service.get_playoff_round(mock_league, None) == "Semifinals"

    def test_not_in_playoffs_raises_error(self) -> None:
        """Test that non-playoff week raises ESPNAPIError."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 14
        mock_league.settings.reg_season_count = 14
        mock_league.league_id = 123456

        with pytest.raises(ESPNAPIError, match="League is not in playoffs"):
            service.get_playoff_round(mock_league, 14)

    def test_unexpected_playoff_week_raises_error(self) -> None:
        """Test that unexpected playoff week raises ESPNAPIError."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 18
        mock_league.settings.reg_season_count = 14
        mock_league.league_id = 123456

        with pytest.raises(ESPNAPIError, match="Unexpected playoff week"):
            service.get_playoff_round(mock_league, 18)


class TestCheckDivisionSync:
    """Tests for check_division_sync method."""

    def test_single_league_always_synced(self) -> None:
        """Test that single league is always considered synced."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league = Mock()
        mock_league.current_week = 15
        mock_league.settings.reg_season_count = 14
        mock_league.settings.name = "Test League"

        synced, msg = service.check_division_sync([mock_league])

        assert synced is True
        assert msg == ""

    def test_empty_leagues_list(self) -> None:
        """Test that empty leagues list is considered synced."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        synced, msg = service.check_division_sync([])

        assert synced is True
        assert msg == ""

    def test_same_week_same_playoff_state_synced(self) -> None:
        """Test that leagues in same week and playoff state are synced."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league1 = Mock()
        mock_league1.current_week = 15
        mock_league1.settings.reg_season_count = 14
        mock_league1.settings.name = "League 1"

        mock_league2 = Mock()
        mock_league2.current_week = 15
        mock_league2.settings.reg_season_count = 14
        mock_league2.settings.name = "League 2"

        synced, msg = service.check_division_sync([mock_league1, mock_league2])

        assert synced is True
        assert msg == ""

    def test_different_weeks_not_synced(self) -> None:
        """Test that leagues in different weeks are not synced."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_league1 = Mock()
        mock_league1.current_week = 14
        mock_league1.settings.reg_season_count = 14
        mock_league1.settings.name = "League 1"
        mock_league1.league_id = 123456

        mock_league2 = Mock()
        mock_league2.current_week = 15
        mock_league2.settings.reg_season_count = 14
        mock_league2.settings.name = "League 2"
        mock_league2.league_id = 789012

        synced, msg = service.check_division_sync([mock_league1, mock_league2])

        assert synced is False
        assert "different weeks" in msg
        assert "Week 14" in msg
        assert "Week 15" in msg

    def test_mixed_playoff_states_not_synced(self) -> None:
        """Test that leagues in different playoff states are not synced."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Both leagues in week 15, but different playoff states
        mock_league1 = Mock()
        mock_league1.current_week = 15
        mock_league1.settings.reg_season_count = 15  # Still regular season
        mock_league1.settings.name = "League 1"
        mock_league1.league_id = 123456

        mock_league2 = Mock()
        mock_league2.current_week = 15
        mock_league2.settings.reg_season_count = 14  # Now in playoffs
        mock_league2.settings.name = "League 2"
        mock_league2.league_id = 789012

        synced, msg = service.check_division_sync([mock_league1, mock_league2])

        assert synced is False
        assert "mixed playoff states" in msg
        assert "Regular Season" in msg
        assert "Playoffs" in msg

    def test_different_playoff_rounds_not_synced(self) -> None:
        """Test that different weeks are detected (which includes different playoff rounds)."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Different playoff weeks - will be caught by week sync check first
        mock_league1 = Mock()
        mock_league1.current_week = 15
        mock_league1.settings.reg_season_count = 14
        mock_league1.settings.name = "League 1"
        mock_league1.league_id = 123456

        mock_league2 = Mock()
        mock_league2.current_week = 16
        mock_league2.settings.reg_season_count = 14
        mock_league2.settings.name = "League 2"
        mock_league2.league_id = 789012

        synced, msg = service.check_division_sync([mock_league1, mock_league2])

        assert synced is False
        # Week check happens first, so we get "different weeks" message
        assert "different weeks" in msg
        assert "Week 15" in msg
        assert "Week 16" in msg


class TestConnectToLeagueErrorHandling:
    """Tests for connect_to_league error handling without actual API calls."""

    def test_private_league_without_credentials_raises_error(self) -> None:
        """Test that private league without credentials raises LeagueConnectionError."""
        # Create a config with public league first
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        # Manually override to simulate the defensive check in connect_to_league
        # (bypassing the config validation that would normally catch this)
        config_no_creds = FFTrackerConfig.__new__(FFTrackerConfig)
        object.__setattr__(config_no_creds, "league_ids", [123456])
        object.__setattr__(config_no_creds, "year", 2024)
        object.__setattr__(config_no_creds, "private", True)
        object.__setattr__(config_no_creds, "espn_credentials", None)
        object.__setattr__(config_no_creds, "week", None)
        service.config = config_no_creds

        # The error gets caught and re-wrapped as LeagueConnectionError
        from ff_tracker.exceptions import LeagueConnectionError

        with pytest.raises(LeagueConnectionError, match="Failed to connect to league"):
            service.connect_to_league(123456)


class TestCreateWeeklyPlayerStat:
    """Tests for _create_weekly_player_stat helper method."""

    def test_create_with_all_attributes(self) -> None:
        """Test creating player stat with all attributes present."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_box_player = Mock()
        mock_box_player.name = "Patrick Mahomes"
        mock_box_player.position = "QB"
        mock_box_player.points = 28.5
        mock_box_player.projected_points = 25.0
        mock_box_player.slot_position = "QB"
        mock_box_player.proTeam = "KC"
        mock_box_player.pro_opponent = "LV"

        player_stat = service._create_weekly_player_stat(
            mock_box_player, "Team Thunder", "Division 1", 15
        )

        assert player_stat.name == "Patrick Mahomes"
        assert player_stat.position == "QB"
        assert player_stat.team_name == "Team Thunder"
        assert player_stat.division == "Division 1"
        assert player_stat.points == 28.5
        assert player_stat.projected_points == 25.0
        assert player_stat.projection_diff == 3.5
        assert player_stat.slot_position == "QB"
        assert player_stat.week == 15
        assert player_stat.pro_team == "KC"
        assert player_stat.pro_opponent == "LV"

    def test_create_without_pro_team_attributes(self) -> None:
        """Test creating player stat without pro team attributes."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        service = ESPNService(config)

        mock_box_player = Mock()
        mock_box_player.name = "Player Name"
        mock_box_player.position = "RB"
        mock_box_player.points = 15.0
        mock_box_player.projected_points = 12.0
        mock_box_player.slot_position = "RB"
        # proTeam and pro_opponent attributes don't exist
        del mock_box_player.proTeam
        del mock_box_player.pro_opponent

        player_stat = service._create_weekly_player_stat(
            mock_box_player, "Team Test", "Division 1", 10
        )

        assert player_stat.pro_team == "UNK"
        assert player_stat.pro_opponent == ""
