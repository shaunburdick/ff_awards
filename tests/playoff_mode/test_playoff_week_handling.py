#!/usr/bin/env python
"""
Test script for playoff week handling and completion detection.

This test validates that the tool correctly identifies completed playoff weeks
and shows the right playoff round based on the last complete week, not ESPN's
current_week.

This test would have caught the bug where Week 15 Semifinals were skipped
and Week 16 Finals were shown with TBD instead.
"""

from __future__ import annotations

from unittest.mock import Mock

from ff_tracker.config import FFTrackerConfig
from ff_tracker.services.espn_service import ESPNService


def create_mock_team(team_id: int, name: str, seed: int, owner_name: str) -> Mock:
    """Create a mock ESPN Team object."""
    team = Mock()
    team.team_id = team_id
    team.team_name = name
    team.team_abbrev = name[:3].upper()
    team.standing = seed
    team.owners = [
        {"firstName": owner_name.split()[0], "lastName": owner_name.split()[-1], "id": str(team_id)}
    ]
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


def test_determine_max_week_regular_season():
    """Test that _determine_max_week correctly handles regular season weeks."""
    print("Testing _determine_max_week (Regular Season)...")

    config = FFTrackerConfig(league_ids=[123456], year=2025, private=False)
    service = ESPNService(config)

    # Mock league in Week 14 (last regular season week)
    league = Mock()
    league.league_id = 123456
    league.current_week = 14
    league.settings = Mock()
    league.settings.reg_season_count = 14

    # Mock box scores for Week 14 - all games complete
    team1 = create_mock_team(1, "Team A", 1, "John Doe")
    team2 = create_mock_team(2, "Team B", 2, "Jane Smith")
    box_scores = [create_mock_box_score(team1, team2, 145.5, 132.2, is_playoff=False)]
    league.box_scores = Mock(return_value=box_scores)

    # Should return 14 (Week 14 is complete)
    max_week = service._determine_max_week(league, 14, 14)
    assert max_week == 14, f"Expected max_week=14 (complete regular season), got {max_week}"
    print("  ✓ Week 14 complete: max_week = 14")

    # Mock Week 15 not started (current_week=15 means check Week 14 in playoffs logic)
    # When current_week=15 and reg_season=14, it's playoffs so we check week_to_check=14
    # If Week 14 is complete (has scores), should return 14
    # If Week 14 is incomplete (0-0), should return 13
    league.current_week = 15

    # Week 14 complete means we can show Week 14 data
    league.box_scores = Mock(return_value=box_scores)  # Reuse complete Week 14 scores
    max_week = service._determine_max_week(league, 15, 14)
    assert max_week == 14, f"Expected max_week=14 (Week 14 complete), got {max_week}"
    print("  ✓ Week 15 (but checking Week 14 complete): max_week = 14")

    print("_determine_max_week (Regular Season): ALL TESTS PASSED ✅\n")


def test_determine_max_week_playoffs():
    """
    Test that _determine_max_week correctly handles playoff weeks.

    This is the key test that would have caught the bug!
    """
    print("Testing _determine_max_week (Playoffs) - THE BUG FIX TEST...")

    config = FFTrackerConfig(league_ids=[123456], year=2025, private=False)
    service = ESPNService(config)

    league = Mock()
    league.league_id = 123456
    league.settings = Mock()
    league.settings.reg_season_count = 14

    # Create playoff teams
    team1 = create_mock_team(1, "Thunder Cats", 1, "John Doe")
    team2 = create_mock_team(2, "Dream Team", 2, "Jane Smith")
    team3 = create_mock_team(3, "Pineapple Express", 3, "Tom Wilson")
    team4 = create_mock_team(4, "Titans", 4, "Chris Johnson")

    # Scenario 1: Week 16 is ESPN's current_week, Week 15 Semifinals are complete
    # This is the EXACT scenario that caused the bug!
    print("  Scenario: Tuesday after Week 15 Monday night games...")
    league.current_week = 16

    # Week 15 Semifinals completed with real scores
    week15_box_scores = [
        create_mock_box_score(team1, team4, 95.8, 153.26),  # #1 vs #4
        create_mock_box_score(team2, team3, 142.62, 116.1),  # #2 vs #3
    ]

    # Week 16 Finals not started yet (0-0)
    week16_box_scores = [
        create_mock_box_score(team4, team2, 0.0, 0.0),  # Finals TBD
    ]

    def mock_box_scores(week: int):
        if week == 15:
            return week15_box_scores
        elif week == 16:
            return week16_box_scores
        return []

    league.box_scores = mock_box_scores

    # THE KEY TEST: Should return 15 (Week 15 is the last complete playoff week)
    max_week = service._determine_max_week(league, 16, 14)
    assert max_week == 15, f"Expected max_week=15 (Week 15 Semifinals complete), got {max_week}"
    print("    ✓ current_week=16, Week 15 complete: max_week = 15 (SEMIFINALS)")

    # Scenario 2: Week 17 is current, Week 16 Finals are complete
    print("  Scenario: Tuesday after Week 16 Monday night games...")
    league.current_week = 17

    # Week 16 Finals completed
    week16_finals_complete = [
        create_mock_box_score(team4, team2, 155.3, 148.9),
    ]

    # Week 17 not started
    week17_box_scores = [
        create_mock_box_score(team4, Mock(), 0.0, 0.0),
    ]

    def mock_box_scores_week17(week: int):
        if week == 16:
            return week16_finals_complete
        elif week == 17:
            return week17_box_scores
        return []

    league.box_scores = mock_box_scores_week17

    max_week = service._determine_max_week(league, 17, 14)
    assert max_week == 16, f"Expected max_week=16 (Week 16 Finals complete), got {max_week}"
    print("    ✓ current_week=17, Week 16 complete: max_week = 16 (FINALS)")

    # Scenario 3: current_week=17, check Week 16
    # When ESPN says current_week=17, it means Week 16 just ended
    # We check Week 16 (previous week), and if complete, show Week 16 Finals
    print("  Scenario: Tuesday after Week 16 Monday night (ESPN moved to Week 17)...")
    league.current_week = 17

    # Mock shows Week 16 is complete (checking week_to_check = 17-1 = 16)
    league.box_scores = mock_box_scores_week17  # Reuse Week 16 complete scores

    max_week = service._determine_max_week(league, 17, 14)
    assert max_week == 16, f"Expected max_week=16 (Week 16 Finals complete), got {max_week}"
    print("    ✓ current_week=17, Week 16 complete: max_week = 16 (FINALS)")

    # Scenario 4: Week 17 actually in progress (Championship Week started)
    # This would require checking Week 17 itself and seeing games have scores
    # For now, Championship Week handling is out of scope for this bug fix
    # (Championship Week logic would need different handling since it's a leaderboard, not bracket)

    print("_determine_max_week (Playoffs): ALL TESTS PASSED ✅\n")
    print("  🎯 This test would have caught the bug!")


def test_playoff_bracket_uses_correct_week():
    """
    Test that playoff bracket extraction uses self.current_week, not league.current_week.

    This validates the fix where we pass playoff_week parameter to extract the right matchups.
    """
    print("Testing playoff bracket uses correct week...")

    config = FFTrackerConfig(league_ids=[123456], year=2025, private=False)
    service = ESPNService(config)

    # Create playoff teams
    team1 = create_mock_team(1, "Thunder Cats", 1, "John Doe")
    team2 = create_mock_team(2, "Dream Team", 2, "Jane Smith")
    team3 = create_mock_team(3, "Pineapple Express", 3, "Tom Wilson")
    team4 = create_mock_team(4, "Titans", 4, "Chris Johnson")

    # Week 15 Semifinals completed
    week15_box_scores = [
        create_mock_box_score(team1, team4, 95.8, 153.26),
        create_mock_box_score(team2, team3, 142.62, 116.1),
    ]

    # Week 16 Finals not started
    week16_box_scores = [
        create_mock_box_score(team4, team2, 0.0, 0.0),
    ]

    league = Mock()
    league.league_id = 123456
    league.current_week = 16  # ESPN says Week 16
    league.settings = Mock()
    league.settings.name = "Test League"
    league.settings.reg_season_count = 14

    def mock_box_scores(week: int):
        if week == 15:
            return week15_box_scores
        elif week == 16:
            return week16_box_scores
        return []

    league.box_scores = mock_box_scores

    # Extract matchups for Week 15 (the completed Semifinals)
    matchups = service.extract_playoff_matchups(league, "Division 1", playoff_week=15)

    # Should get 2 matchups with real scores (not TBD)
    assert len(matchups) == 2, f"Expected 2 Semifinal matchups, got {len(matchups)}"
    assert matchups[0].score1 == 95.8, "Expected real score from Week 15"
    assert matchups[0].score2 == 153.26, "Expected real score from Week 15"
    assert matchups[0].winner_name == "Titans", "Expected winner from completed game"
    print("  ✓ Extracted Week 15 Semifinals with real scores (not TBD)")

    # Build bracket for Week 15 (should say Semifinals, not Finals)
    bracket = service.build_playoff_bracket(league, "Division 1", playoff_week=15)
    assert bracket.round == "Semifinals", f"Expected 'Semifinals', got '{bracket.round}'"
    assert bracket.week == 15, f"Expected week=15, got {bracket.week}"
    print("  ✓ Bracket shows 'Semifinals' for Week 15 (not Finals)")

    print("playoff bracket uses correct week: ALL TESTS PASSED ✅\n")


def test_get_playoff_round_with_week_parameter():
    """Test that get_playoff_round can determine round based on specific week."""
    print("Testing get_playoff_round with week parameter...")

    config = FFTrackerConfig(league_ids=[123456], year=2025, private=False)
    service = ESPNService(config)

    league = Mock()
    league.league_id = 123456
    league.current_week = 16  # ESPN says Week 16 (Finals)
    league.settings = Mock()
    league.settings.reg_season_count = 14

    # Check Week 15 specifically (Semifinals)
    round_week15 = service.get_playoff_round(league, week=15)
    assert round_week15 == "Semifinals", f"Expected 'Semifinals' for Week 15, got '{round_week15}'"
    print("  ✓ Week 15 = Semifinals (even when current_week=16)")

    # Check Week 16 specifically (Finals)
    round_week16 = service.get_playoff_round(league, week=16)
    assert round_week16 == "Finals", f"Expected 'Finals' for Week 16, got '{round_week16}'"
    print("  ✓ Week 16 = Finals")

    # Check without week parameter (should use current_week)
    round_current = service.get_playoff_round(league)
    assert round_current == "Finals", f"Expected 'Finals' (current_week=16), got '{round_current}'"
    print("  ✓ No week param = uses current_week (Finals)")

    print("get_playoff_round with week parameter: ALL TESTS PASSED ✅\n")


def test_complete_workflow_tuesday_after_week15():
    """
    Integration test simulating the exact scenario from the bug report.

    Tuesday morning after Week 15 Monday night games:
    - ESPN current_week = 16
    - Week 15 Semifinals games are complete
    - Week 16 Finals games haven't started

    Expected behavior:
    - Tool reports Week 15 as current week
    - Shows Semifinals bracket with real scores
    - Weekly highlights from Week 15
    """
    print("Testing complete workflow: Tuesday after Week 15 Monday night...")

    config = FFTrackerConfig(league_ids=[123456], year=2025, private=False)
    service = ESPNService(config)

    # Mock league setup
    league = Mock()
    league.league_id = 123456
    league.current_week = 16  # ESPN says Week 16
    league.settings = Mock()
    league.settings.name = "Test League"
    league.settings.reg_season_count = 14
    league.teams = []

    # Create playoff teams
    team1 = create_mock_team(1, "Thunder Cats", 1, "John Doe")
    team2 = create_mock_team(2, "Dream Team", 2, "Jane Smith")
    team3 = create_mock_team(3, "Pineapple Express", 3, "Tom Wilson")
    team4 = create_mock_team(4, "Titans", 4, "Chris Johnson")

    # Week 15 Semifinals completed with real scores
    week15_box_scores = [
        create_mock_box_score(team1, team4, 95.8, 153.26),
        create_mock_box_score(team2, team3, 142.62, 116.1),
    ]

    # Week 16 Finals not started (TBD)
    week16_box_scores = [
        create_mock_box_score(team4, team2, 0.0, 0.0),
    ]

    def mock_box_scores(week: int):
        if week == 15:
            return week15_box_scores
        elif week == 16:
            return week16_box_scores
        return []

    league.box_scores = mock_box_scores

    # Step 1: Determine max week
    max_week = service._determine_max_week(league, 16, 14)
    assert max_week == 15, f"Step 1 FAILED: Expected max_week=15, got {max_week}"
    print("  ✓ Step 1: _determine_max_week returns 15 (Week 15 complete)")

    # Simulate setting self.current_week
    service.current_week = max_week

    # Step 2: Check if in playoffs
    is_playoffs = service.is_in_playoffs(league)
    assert is_playoffs, "Step 2 FAILED: Should be in playoffs"
    print("  ✓ Step 2: is_in_playoffs returns True")

    # Step 3: Get playoff round for the completed week (15)
    playoff_round = service.get_playoff_round(league, week=service.current_week)
    assert playoff_round == "Semifinals", (
        f"Step 3 FAILED: Expected 'Semifinals', got '{playoff_round}'"
    )
    print("  ✓ Step 3: get_playoff_round(week=15) returns 'Semifinals'")

    # Step 4: Extract matchups for Week 15
    matchups = service.extract_playoff_matchups(
        league, "Test League", playoff_week=service.current_week
    )
    assert len(matchups) == 2, f"Step 4 FAILED: Expected 2 matchups, got {len(matchups)}"
    assert matchups[0].score1 is not None, "Step 4 FAILED: Expected real scores, got None"
    assert matchups[0].winner_name is not None, "Step 4 FAILED: Expected winners, got None"
    print("  ✓ Step 4: extract_playoff_matchups(week=15) returns 2 matchups with scores")

    # Step 5: Build bracket
    bracket = service.build_playoff_bracket(
        league, "Test League", playoff_week=service.current_week
    )
    assert bracket.round == "Semifinals", (
        f"Step 5 FAILED: Expected 'Semifinals', got '{bracket.round}'"
    )
    assert bracket.week == 15, f"Step 5 FAILED: Expected week=15, got {bracket.week}"
    assert len(bracket.matchups) == 2, (
        f"Step 5 FAILED: Expected 2 matchups, got {len(bracket.matchups)}"
    )
    print("  ✓ Step 5: build_playoff_bracket creates Semifinals bracket for Week 15")

    print("\n  🎉 COMPLETE WORKFLOW TEST PASSED!")
    print("  The tool correctly handles Tuesday after Week 15 Monday night games:")
    print("    - Reports Week 15 (not 14)")
    print("    - Shows Semifinals (not Finals)")
    print("    - Displays real scores (not TBD)")
    print()


def main():
    """Run all tests."""
    print("=" * 80)
    print("PLAYOFF WEEK HANDLING & COMPLETION DETECTION - VALIDATION TEST")
    print("=" * 80)
    print()
    print("This test suite validates the bug fix for playoff week handling.")
    print("These tests would have caught the issue where Week 15 Semifinals were")
    print("skipped and Week 16 Finals with TBD were shown instead.")
    print()
    print("=" * 80)
    print()

    test_determine_max_week_regular_season()
    test_determine_max_week_playoffs()
    test_get_playoff_round_with_week_parameter()
    test_playoff_bracket_uses_correct_week()
    test_complete_workflow_tuesday_after_week15()

    print("=" * 80)
    print("ALL PLAYOFF WEEK HANDLING TESTS PASSED! ✅✅✅")
    print("=" * 80)
    print()
    print("These tests validate:")
    print("  1. ✅ _determine_max_week checks playoff weeks (not just regular season)")
    print("  2. ✅ get_playoff_round accepts week parameter for specific week checks")
    print("  3. ✅ Playoff bracket extraction uses correct week (self.current_week)")
    print("  4. ✅ Complete workflow handles Tuesday morning scenario correctly")
    print()


if __name__ == "__main__":
    main()
