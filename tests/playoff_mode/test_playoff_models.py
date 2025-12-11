#!/usr/bin/env python
"""
Test script for Phase 1: Playoff Data Models

This script validates that all playoff models work correctly with proper
validation and error handling.
"""

from __future__ import annotations

from ff_tracker.exceptions import DataValidationError, DivisionSyncError
from ff_tracker.models import (
    ChampionshipEntry,
    ChampionshipLeaderboard,
    DivisionData,
    Owner,
    PlayoffBracket,
    PlayoffMatchup,
    TeamStats,
)


def test_playoff_matchup():
    """Test PlayoffMatchup model validation."""
    print("Testing PlayoffMatchup...")

    # Valid matchup (complete game)
    matchup = PlayoffMatchup(
        matchup_id="div1_sf1",
        round_name="Semifinal 1",
        seed1=1,
        team1_name="Thunder Cats",
        owner1_name="John",
        score1=145.67,
        seed2=4,
        team2_name="Dream Team",
        owner2_name="Sarah",
        score2=98.23,
        winner_name="Thunder Cats",
        winner_seed=1,
        division_name="Division 1",
    )
    assert matchup.matchup_id == "div1_sf1"
    assert matchup.winner_name == "Thunder Cats"
    print("  ✓ Valid complete matchup created")

    # Valid matchup (in progress)
    in_progress = PlayoffMatchup(
        matchup_id="div2_finals",
        round_name="Finals",
        seed1=1,
        team1_name="Pineapple Express",
        owner1_name="Tom",
        score1=0.0,
        seed2=3,
        team2_name="Touchdown Titans",
        owner2_name="Chris",
        score2=0.0,
        winner_name=None,
        winner_seed=None,
        division_name="Division 2",
    )
    assert in_progress.winner_name is None
    print("  ✓ Valid in-progress matchup created")

    # Test validation - invalid seed
    try:
        PlayoffMatchup(
            matchup_id="bad",
            round_name="Semifinal 1",
            seed1=0,  # Invalid
            team1_name="Team1",
            owner1_name="Owner1",
            score1=100.0,
            seed2=2,
            team2_name="Team2",
            owner2_name="Owner2",
            score2=90.0,
            winner_name="Team1",
            winner_seed=0,
            division_name="Division 1",
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "Seeds must be positive" in str(e)
        print("  ✓ Invalid seed validation works")

    # Test validation - invalid winner
    try:
        PlayoffMatchup(
            matchup_id="bad",
            round_name="Semifinal 1",
            seed1=1,
            team1_name="Team1",
            owner1_name="Owner1",
            score1=100.0,
            seed2=2,
            team2_name="Team2",
            owner2_name="Owner2",
            score2=90.0,
            winner_name="Team3",  # Invalid
            winner_seed=1,
            division_name="Division 1",
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "Winner must be one of the teams" in str(e)
        print("  ✓ Invalid winner validation works")

    print("PlayoffMatchup: ALL TESTS PASSED ✅\n")


def test_playoff_bracket():
    """Test PlayoffBracket model validation."""
    print("Testing PlayoffBracket...")

    # Create matchups
    matchup1 = PlayoffMatchup(
        matchup_id="div1_sf1",
        round_name="Semifinal 1",
        seed1=1,
        team1_name="Thunder Cats",
        owner1_name="John",
        score1=145.67,
        seed2=4,
        team2_name="Dream Team",
        owner2_name="Sarah",
        score2=98.23,
        winner_name="Thunder Cats",
        winner_seed=1,
        division_name="Division 1",
    )

    matchup2 = PlayoffMatchup(
        matchup_id="div1_sf2",
        round_name="Semifinal 2",
        seed1=2,
        team1_name="Pineapple Express",
        owner1_name="Tom",
        score1=130.45,
        seed2=3,
        team2_name="Touchdown Titans",
        owner2_name="Chris",
        score2=135.12,
        winner_name="Touchdown Titans",
        winner_seed=3,
        division_name="Division 1",
    )

    # Valid Semifinals bracket (2 matchups)
    semifinals = PlayoffBracket(round="Semifinals", week=15, matchups=[matchup1, matchup2])
    assert semifinals.round == "Semifinals"
    assert len(semifinals.matchups) == 2
    print("  ✓ Valid Semifinals bracket created (2 matchups)")

    # Valid Finals bracket (1 matchup)
    finals = PlayoffBracket(round="Finals", week=16, matchups=[matchup1])
    assert finals.round == "Finals"
    assert len(finals.matchups) == 1
    print("  ✓ Valid Finals bracket created (1 matchup)")

    # Test validation - wrong matchup count for Semifinals
    try:
        PlayoffBracket(
            round="Semifinals",
            week=15,
            matchups=[matchup1],  # Should be 2
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "Semifinals must have exactly 2 matchups" in str(e)
        print("  ✓ Semifinals matchup count validation works")

    # Test validation - wrong matchup count for Finals
    try:
        PlayoffBracket(
            round="Finals",
            week=16,
            matchups=[matchup1, matchup2],  # Should be 1
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "Finals must have exactly 1 matchup" in str(e)
        print("  ✓ Finals matchup count validation works")

    # Test validation - invalid round name
    try:
        PlayoffBracket(
            round="Championship",  # Invalid
            week=17,
            matchups=[matchup1],
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "Round must be 'Semifinals' or 'Finals'" in str(e)
        print("  ✓ Invalid round name validation works")

    print("PlayoffBracket: ALL TESTS PASSED ✅\n")


def test_championship_entry():
    """Test ChampionshipEntry model validation."""
    print("Testing ChampionshipEntry...")

    # Valid champion (rank 1)
    champion = ChampionshipEntry(
        rank=1,
        team_name="Pineapple Express",
        owner_name="Tom",
        division_name="Division 2",
        score=163.45,
        is_champion=True,
    )
    assert champion.rank == 1
    assert champion.is_champion
    print("  ✓ Valid champion entry created")

    # Valid runner-up (rank 2)
    runner_up = ChampionshipEntry(
        rank=2,
        team_name="Thunder Cats",
        owner_name="John",
        division_name="Division 1",
        score=156.78,
        is_champion=False,
    )
    assert runner_up.rank == 2
    assert not runner_up.is_champion
    print("  ✓ Valid runner-up entry created")

    # Test validation - champion flag mismatch with rank
    try:
        ChampionshipEntry(
            rank=2,
            team_name="Bad Entry",
            owner_name="Owner",
            division_name="Division 1",
            score=150.0,
            is_champion=True,  # Invalid - rank != 1
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "Champion flag set but rank is 2" in str(e)
        print("  ✓ Champion flag validation works")

    # Test validation - rank 1 without champion flag
    try:
        ChampionshipEntry(
            rank=1,
            team_name="Bad Entry",
            owner_name="Owner",
            division_name="Division 1",
            score=150.0,
            is_champion=False,  # Invalid - rank == 1
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "Rank is 1 but champion flag not set" in str(e)
        print("  ✓ Rank 1 champion flag validation works")

    print("ChampionshipEntry: ALL TESTS PASSED ✅\n")


def test_championship_leaderboard():
    """Test ChampionshipLeaderboard model validation."""
    print("Testing ChampionshipLeaderboard...")

    # Create valid entries
    entry1 = ChampionshipEntry(
        rank=1,
        team_name="Pineapple Express",
        owner_name="Tom",
        division_name="Division 2",
        score=163.45,
        is_champion=True,
    )
    entry2 = ChampionshipEntry(
        rank=2,
        team_name="Thunder Cats",
        owner_name="John",
        division_name="Division 1",
        score=156.78,
        is_champion=False,
    )
    entry3 = ChampionshipEntry(
        rank=3,
        team_name="End Zone Warriors",
        owner_name="Mike",
        division_name="Division 3",
        score=149.23,
        is_champion=False,
    )

    # Valid leaderboard
    leaderboard = ChampionshipLeaderboard(week=17, entries=[entry1, entry2, entry3])
    assert leaderboard.week == 17
    assert len(leaderboard.entries) == 3
    assert leaderboard.champion.team_name == "Pineapple Express"
    print("  ✓ Valid championship leaderboard created")
    print(f"  ✓ Champion property works: {leaderboard.champion.team_name}")

    # Test validation - non-sequential ranks
    bad_entry2 = ChampionshipEntry(
        rank=3,  # Should be 2
        team_name="Thunder Cats",
        owner_name="John",
        division_name="Division 1",
        score=156.78,
        is_champion=False,
    )
    try:
        ChampionshipLeaderboard(week=17, entries=[entry1, bad_entry2])
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "ranked sequentially" in str(e)
        print("  ✓ Sequential rank validation works")

    # Test validation - multiple champions
    bad_champion2 = ChampionshipEntry(
        rank=1,
        team_name="Thunder Cats",
        owner_name="John",
        division_name="Division 1",
        score=156.78,
        is_champion=True,  # Duplicate champion
    )
    bad_entry_not_champion = ChampionshipEntry(
        rank=2,
        team_name="Other Team",
        owner_name="Other",
        division_name="Division 2",
        score=145.0,
        is_champion=False,
    )
    try:
        ChampionshipLeaderboard(
            week=17,
            entries=[entry1, bad_champion2],  # Two champions
        )
        assert False, "Should have raised validation error"
    except DataValidationError as e:
        assert "ranked sequentially" in str(e)  # Will fail on rank validation first
        print("  ✓ Duplicate rank validation works")

    print("ChampionshipLeaderboard: ALL TESTS PASSED ✅\n")


def test_division_data_extension():
    """Test DivisionData playoff_bracket field and is_playoff_mode property."""
    print("Testing DivisionData extension...")

    # Create test team
    owner = Owner(display_name="John Doe", first_name="John", last_name="Doe", id="12345")
    team = TeamStats(
        name="Thunder Cats",
        owner=owner,
        points_for=1500.0,
        points_against=1400.0,
        wins=10,
        losses=4,
        division="Division 1",
        in_playoff_position=True,
    )

    # Regular season division (no playoff bracket)
    regular_season = DivisionData(
        league_id=123456, name="Division 1", teams=[team], games=[], playoff_bracket=None
    )
    assert not regular_season.is_playoff_mode
    print("  ✓ Regular season: is_playoff_mode = False")

    # Create playoff bracket
    matchup = PlayoffMatchup(
        matchup_id="div1_sf1",
        round_name="Semifinal 1",
        seed1=1,
        team1_name="Thunder Cats",
        owner1_name="John",
        score1=145.67,
        seed2=4,
        team2_name="Dream Team",
        owner2_name="Sarah",
        score2=98.23,
        winner_name="Thunder Cats",
        winner_seed=1,
        division_name="Division 1",
    )
    bracket = PlayoffBracket(round="Finals", week=16, matchups=[matchup])

    # Playoff mode division
    playoff_division = DivisionData(
        league_id=123456, name="Division 1", teams=[team], games=[], playoff_bracket=bracket
    )
    assert playoff_division.is_playoff_mode
    assert playoff_division.playoff_bracket.round == "Finals"
    print("  ✓ Playoff mode: is_playoff_mode = True")
    print("  ✓ Playoff bracket accessible from DivisionData")

    print("DivisionData: ALL TESTS PASSED ✅\n")


def test_division_sync_error():
    """Test DivisionSyncError exception."""
    print("Testing DivisionSyncError...")

    try:
        states = {"Division 1": "Week 15 (Playoffs)", "Division 2": "Week 14 (Regular Season)"}
        raise DivisionSyncError("Divisions are out of sync", division_states=states)
    except DivisionSyncError as e:
        assert "out of sync" in str(e)
        assert "Division 1" in e.division_states
        assert "Division 2" in e.division_states
        print("  ✓ DivisionSyncError can be raised and caught")
        print("  ✓ Division states accessible via exception attribute")

    print("DivisionSyncError: ALL TESTS PASSED ✅\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PHASE 1: PLAYOFF DATA MODELS - VALIDATION TEST")
    print("=" * 60)
    print()

    test_playoff_matchup()
    test_playoff_bracket()
    test_championship_entry()
    test_championship_leaderboard()
    test_division_data_extension()
    test_division_sync_error()

    print("=" * 60)
    print("ALL PHASE 1 TESTS PASSED! ✅✅✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
