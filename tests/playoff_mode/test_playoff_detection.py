#!/usr/bin/env python
"""
Test script for Phase 2: Playoff Detection Logic

This script validates playoff detection methods with mock league data.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from ff_tracker.config import FFTrackerConfig
from ff_tracker.exceptions import ESPNAPIError
from ff_tracker.services.espn_service import ESPNService


def create_mock_league(
    league_id: int, name: str, current_week: int, reg_season_count: int = 14
) -> Mock:
    """Create a mock ESPN League object."""
    league = Mock()
    league.league_id = league_id
    league.current_week = current_week
    league.settings = Mock()
    league.settings.name = name
    league.settings.reg_season_count = reg_season_count
    return league


def test_is_in_playoffs():
    """Test playoff detection logic."""
    print("Testing is_in_playoffs...")

    config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
    service = ESPNService(config)

    # Week 14 - still in regular season
    league_reg = create_mock_league(123456, "Test League", current_week=14, reg_season_count=14)
    assert not service.is_in_playoffs(league_reg)
    print("  ✓ Week 14 (regular season): is_in_playoffs = False")

    # Week 15 - playoffs start
    league_playoffs = create_mock_league(
        123456, "Test League", current_week=15, reg_season_count=14
    )
    assert service.is_in_playoffs(league_playoffs)
    print("  ✓ Week 15 (playoffs): is_in_playoffs = True")

    # Week 16 - still in playoffs
    league_finals = create_mock_league(123456, "Test League", current_week=16, reg_season_count=14)
    assert service.is_in_playoffs(league_finals)
    print("  ✓ Week 16 (playoffs): is_in_playoffs = True")

    # Week 17 - championship
    league_champ = create_mock_league(123456, "Test League", current_week=17, reg_season_count=14)
    assert service.is_in_playoffs(league_champ)
    print("  ✓ Week 17 (playoffs): is_in_playoffs = True")

    print("is_in_playoffs: ALL TESTS PASSED ✅\n")


def test_get_playoff_round():
    """Test playoff round detection."""
    print("Testing get_playoff_round...")

    config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
    service = ESPNService(config)

    # Week 15 - Semifinals
    league_sf = create_mock_league(123456, "Test League", current_week=15, reg_season_count=14)
    assert service.get_playoff_round(league_sf) == "Semifinals"
    print("  ✓ Week 15: Semifinals")

    # Week 16 - Finals
    league_finals = create_mock_league(123456, "Test League", current_week=16, reg_season_count=14)
    assert service.get_playoff_round(league_finals) == "Finals"
    print("  ✓ Week 16: Finals")

    # Week 17 - Championship Week
    league_champ = create_mock_league(123456, "Test League", current_week=17, reg_season_count=14)
    assert service.get_playoff_round(league_champ) == "Championship Week"
    print("  ✓ Week 17: Championship Week")

    # Error: Not in playoffs
    league_reg = create_mock_league(123456, "Test League", current_week=14, reg_season_count=14)
    with pytest.raises(ESPNAPIError, match="not in playoffs"):
        service.get_playoff_round(league_reg)
    print("  ✓ Week 14: Raises error (not in playoffs)")

    # Error: Unexpected playoff week
    league_bad = create_mock_league(123456, "Test League", current_week=18, reg_season_count=14)
    with pytest.raises(ESPNAPIError, match="Unexpected playoff week"):
        service.get_playoff_round(league_bad)
    print("  ✓ Week 18: Raises error (unexpected week)")

    print("get_playoff_round: ALL TESTS PASSED ✅\n")


def test_check_division_sync():
    """Test division synchronization checking."""
    print("Testing check_division_sync...")

    config = FFTrackerConfig(league_ids=[123456, 789012, 345678], year=2024, private=False)
    service = ESPNService(config)

    # All synced - Week 15 Semifinals
    league1 = create_mock_league(111, "Division 1", current_week=15, reg_season_count=14)
    league2 = create_mock_league(222, "Division 2", current_week=15, reg_season_count=14)
    league3 = create_mock_league(333, "Division 3", current_week=15, reg_season_count=14)

    synced, msg = service.check_division_sync([league1, league2, league3])
    assert synced
    assert msg == ""
    print("  ✓ All Week 15 (Semifinals): Synced")

    # All synced - Week 14 Regular Season
    league1_reg = create_mock_league(111, "Division 1", current_week=14, reg_season_count=14)
    league2_reg = create_mock_league(222, "Division 2", current_week=14, reg_season_count=14)
    league3_reg = create_mock_league(333, "Division 3", current_week=14, reg_season_count=14)

    synced, msg = service.check_division_sync([league1_reg, league2_reg, league3_reg])
    assert synced
    assert msg == ""
    print("  ✓ All Week 14 (Regular Season): Synced")

    # Out of sync - Different weeks
    league1_w14 = create_mock_league(111, "Division 1", current_week=14, reg_season_count=14)
    league2_w15 = create_mock_league(222, "Division 2", current_week=15, reg_season_count=14)

    synced, msg = service.check_division_sync([league1_w14, league2_w15])
    assert not synced
    assert "out of sync" in msg
    assert "different weeks" in msg
    print("  ✓ Week 14 vs Week 15: Out of sync (different weeks)")

    # Out of sync - Mixed playoff states (different weeks triggers first)
    league1_playoffs = create_mock_league(111, "Division 1", current_week=15, reg_season_count=14)
    league2_regular = create_mock_league(222, "Division 2", current_week=14, reg_season_count=14)

    synced, msg = service.check_division_sync([league1_playoffs, league2_regular])
    assert not synced
    assert "out of sync" in msg
    # This will trigger "different weeks" error since week check happens first
    assert "different weeks" in msg
    print("  ✓ Playoffs vs Regular Season: Out of sync (different weeks)")

    # Out of sync - Different playoff rounds (different weeks triggers first)
    league1_sf = create_mock_league(111, "Division 1", current_week=15, reg_season_count=14)
    league2_finals = create_mock_league(222, "Division 2", current_week=16, reg_season_count=14)

    synced, msg = service.check_division_sync([league1_sf, league2_finals])
    assert not synced
    assert "out of sync" in msg
    # This will trigger "different weeks" error since week check happens first
    assert "different weeks" in msg
    print("  ✓ Semifinals vs Finals: Out of sync (different weeks)")

    # Edge case - Empty list
    synced, msg = service.check_division_sync([])
    assert synced
    assert msg == ""
    print("  ✓ Empty list: Synced (edge case)")

    # Edge case - Single league
    synced, msg = service.check_division_sync([league1])
    assert synced
    assert msg == ""
    print("  ✓ Single league: Synced (edge case)")

    print("check_division_sync: ALL TESTS PASSED ✅\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 2: PLAYOFF DETECTION LOGIC - VALIDATION TEST")
    print("=" * 60)
    print()

    test_is_in_playoffs()
    test_get_playoff_round()
    test_check_division_sync()

    print("=" * 60)
    print("ALL PHASE 2 TESTS PASSED! ✅✅✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
