#!/usr/bin/env python
"""
Test script for Phase 3: Playoff Data Extraction

This script validates playoff matchup extraction and bracket building logic.
"""

from __future__ import annotations

from unittest.mock import Mock

from ff_tracker.config import FFTrackerConfig
from ff_tracker.services.espn_service import ESPNService
from ff_tracker.models import PlayoffMatchup, PlayoffBracket


def create_mock_team(team_id: int, name: str, seed: int, owner_first: str, owner_last: str) -> Mock:
    """Create a mock ESPN Team object."""
    team = Mock()
    team.team_id = team_id
    team.team_name = name
    team.standing = seed
    team.playoff_pct = 100.0 if seed <= 4 else 0.0

    # Mock owners
    owner = Mock()
    owner.display_name = f"{owner_first} {owner_last}"
    owner.first_name = owner_first
    owner.last_name = owner_last
    owner.id = str(team_id * 100)
    team.owners = [{"firstName": owner_first, "lastName": owner_last, "id": str(team_id * 100)}]

    return team


def create_mock_box_score(
    home_team: Mock,
    away_team: Mock,
    home_score: float,
    away_score: float,
    is_playoff: bool = True,
    matchup_type: str = "WINNERS_BRACKET",
) -> Mock:
    """Create a mock ESPN BoxScore object."""
    box_score = Mock()
    box_score.home_team = home_team
    box_score.away_team = away_team
    box_score.home_score = home_score
    box_score.away_score = away_score
    box_score.is_playoff = is_playoff
    box_score.matchup_type = matchup_type
    return box_score


def create_mock_league(
    league_id: int, name: str, current_week: int, reg_season_count: int, box_scores: list[Mock]
) -> Mock:
    """Create a mock ESPN League object with box scores."""
    league = Mock()
    league.league_id = league_id
    league.current_week = current_week
    league.settings = Mock()
    league.settings.name = name
    league.settings.reg_season_count = reg_season_count
    league.settings.playoff_team_count = 4
    league.box_scores = Mock(return_value=box_scores)
    return league


def test_extract_playoff_matchups_semifinals():
    """Test playoff matchup extraction for semifinals."""
    print("Testing extract_playoff_matchups (Semifinals)...")

    config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
    service = ESPNService(config)

    # Create mock teams
    team1 = create_mock_team(1, "Thunder Cats", 1, "John", "Doe")
    team2 = create_mock_team(4, "Dream Team", 4, "Sarah", "Smith")
    team3 = create_mock_team(2, "Pineapple Express", 2, "Tom", "Wilson")
    team4 = create_mock_team(3, "Touchdown Titans", 3, "Chris", "Johnson")

    # Create mock box scores for semifinals
    box_scores = [
        create_mock_box_score(team1, team2, 145.67, 98.23),  # Semifinal 1
        create_mock_box_score(team3, team4, 130.45, 135.12),  # Semifinal 2
    ]

    # Create mock league (Week 15 = Semifinals)
    league = create_mock_league(123456, "Test League", 15, 14, box_scores)

    # Extract matchups
    matchups = service.extract_playoff_matchups(league, "Division 1")

    # Validate
    assert len(matchups) == 2, f"Expected 2 matchups, got {len(matchups)}"
    print(f"  ✓ Extracted {len(matchups)} matchups")

    # Check first matchup
    m1 = matchups[0]
    assert isinstance(m1, PlayoffMatchup)
    assert m1.seed1 == 1
    assert m1.seed2 == 4
    assert m1.team1_name == "Thunder Cats"
    assert m1.team2_name == "Dream Team"
    assert m1.score1 == 145.67
    assert m1.score2 == 98.23
    assert m1.winner_name == "Thunder Cats"
    assert m1.winner_seed == 1
    assert m1.round_name == "Semifinal 1"
    print("  ✓ Matchup 1: #1 Thunder Cats (145.67) vs #4 Dream Team (98.23) - Winner: Thunder Cats")

    # Check second matchup
    m2 = matchups[1]
    assert m2.seed1 == 2
    assert m2.seed2 == 3
    assert m2.winner_name == "Touchdown Titans"
    assert m2.winner_seed == 3
    assert m2.round_name == "Semifinal 2"
    print(
        "  ✓ Matchup 2: #2 Pineapple Express (130.45) vs #3 Touchdown Titans (135.12) - Winner: Touchdown Titans"
    )

    print("extract_playoff_matchups (Semifinals): ALL TESTS PASSED ✅\n")


def test_extract_playoff_matchups_finals():
    """Test playoff matchup extraction for finals."""
    print("Testing extract_playoff_matchups (Finals)...")

    config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
    service = ESPNService(config)

    # Create mock teams (winners from semifinals)
    team1 = create_mock_team(1, "Thunder Cats", 1, "John", "Doe")
    team3 = create_mock_team(3, "Touchdown Titans", 3, "Chris", "Johnson")

    # Create mock box score for finals
    box_scores = [
        create_mock_box_score(team1, team3, 152.34, 148.91),  # Finals
    ]

    # Create mock league (Week 16 = Finals)
    league = create_mock_league(123456, "Test League", 16, 14, box_scores)

    # Extract matchups
    matchups = service.extract_playoff_matchups(league, "Division 1")

    # Validate
    assert len(matchups) == 1, f"Expected 1 matchup, got {len(matchups)}"
    print(f"  ✓ Extracted {len(matchups)} matchup")

    # Check finals matchup
    m = matchups[0]
    assert isinstance(m, PlayoffMatchup)
    assert m.round_name == "Finals"
    assert m.winner_name == "Thunder Cats"
    print(
        f"  ✓ Finals: #{m.seed1} {m.team1_name} ({m.score1}) vs #{m.seed2} {m.team2_name} ({m.score2}) - Winner: {m.winner_name}"
    )

    print("extract_playoff_matchups (Finals): ALL TESTS PASSED ✅\n")


def test_extract_playoff_matchups_in_progress():
    """Test playoff matchup extraction with in-progress games."""
    print("Testing extract_playoff_matchups (In Progress)...")

    config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
    service = ESPNService(config)

    # Create mock teams
    team1 = create_mock_team(1, "Thunder Cats", 1, "John", "Doe")
    team2 = create_mock_team(4, "Dream Team", 4, "Sarah", "Smith")

    # Create mock box score with 0-0 (game not started)
    box_scores = [
        create_mock_box_score(team1, team2, 0.0, 0.0),
    ]

    # Create mock league
    league = create_mock_league(123456, "Test League", 15, 14, box_scores)

    # Extract matchups
    matchups = service.extract_playoff_matchups(league, "Division 1")

    # Validate
    assert len(matchups) == 1
    m = matchups[0]
    assert m.score1 is None  # 0.0 converted to None for "not started"
    assert m.score2 is None
    assert m.winner_name is None
    assert m.winner_seed is None
    print("  ✓ In-progress game: scores=None, winner=None (game not started)")

    print("extract_playoff_matchups (In Progress): ALL TESTS PASSED ✅\n")


def test_extract_playoff_matchups_filters_consolation():
    """Test that consolation bracket games are filtered out."""
    print("Testing extract_playoff_matchups (Filters Consolation)...")

    config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
    service = ESPNService(config)

    # Create mock teams
    team1 = create_mock_team(1, "Thunder Cats", 1, "John", "Doe")
    team2 = create_mock_team(4, "Dream Team", 4, "Sarah", "Smith")
    team5 = create_mock_team(5, "Eliminated Team", 5, "Bob", "Brown")
    team6 = create_mock_team(6, "Also Eliminated", 6, "Alice", "Green")

    # Create mixed box scores (winners bracket + consolation)
    box_scores = [
        create_mock_box_score(team1, team2, 145.0, 100.0, matchup_type="WINNERS_BRACKET"),
        create_mock_box_score(team5, team6, 90.0, 85.0, matchup_type="LOSERS_CONSOLATION_LADDER"),
    ]

    # Create mock league
    league = create_mock_league(123456, "Test League", 15, 14, box_scores)

    # Extract matchups
    matchups = service.extract_playoff_matchups(league, "Division 1")

    # Validate - should only have 1 matchup (consolation filtered out)
    assert len(matchups) == 1, f"Expected 1 matchup (consolation filtered), got {len(matchups)}"
    assert matchups[0].team1_name == "Thunder Cats"
    print("  ✓ Consolation bracket filtered out (only winners bracket returned)")

    print("extract_playoff_matchups (Filters Consolation): ALL TESTS PASSED ✅\n")


def test_build_playoff_bracket():
    """Test playoff bracket building."""
    print("Testing build_playoff_bracket...")

    config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
    service = ESPNService(config)

    # Create mock teams
    team1 = create_mock_team(1, "Thunder Cats", 1, "John", "Doe")
    team2 = create_mock_team(4, "Dream Team", 4, "Sarah", "Smith")
    team3 = create_mock_team(2, "Pineapple Express", 2, "Tom", "Wilson")
    team4 = create_mock_team(3, "Touchdown Titans", 3, "Chris", "Johnson")

    # Create mock box scores
    box_scores = [
        create_mock_box_score(team1, team2, 145.67, 98.23),
        create_mock_box_score(team3, team4, 130.45, 135.12),
    ]

    # Create mock league
    league = create_mock_league(123456, "Test League", 15, 14, box_scores)

    # Build bracket
    bracket = service.build_playoff_bracket(league, "Division 1")

    # Validate
    assert isinstance(bracket, PlayoffBracket)
    assert bracket.round == "Semifinals"
    assert bracket.week == 15
    assert len(bracket.matchups) == 2
    print(f"  ✓ Built {bracket.round} bracket for Week {bracket.week}")
    print(f"  ✓ Contains {len(bracket.matchups)} matchups")

    print("build_playoff_bracket: ALL TESTS PASSED ✅\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 3: PLAYOFF DATA EXTRACTION - VALIDATION TEST")
    print("=" * 60)
    print()

    test_extract_playoff_matchups_semifinals()
    test_extract_playoff_matchups_finals()
    test_extract_playoff_matchups_in_progress()
    test_extract_playoff_matchups_filters_consolation()
    test_build_playoff_bracket()

    print("=" * 60)
    print("ALL PHASE 3 TESTS PASSED! ✅✅✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
