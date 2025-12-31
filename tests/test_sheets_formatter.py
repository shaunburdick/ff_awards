"""Tests for Google Sheets TSV output formatter."""

from __future__ import annotations

import pytest

from ff_tracker.display.sheets import SheetsFormatter
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


class TestSheetsFormatterBasics:
    """Tests for SheetsFormatter initialization and basic functionality."""

    def test_init_sheets_formatter(self) -> None:
        """Test SheetsFormatter initialization."""
        formatter = SheetsFormatter(year=2024)
        assert formatter.year == 2024
        assert formatter.format_args == {}

    def test_init_with_format_args(self) -> None:
        """Test SheetsFormatter initialization with format args."""
        args = {"note": "Important message"}
        formatter = SheetsFormatter(year=2024, format_args=args)
        assert formatter.year == 2024
        assert formatter.format_args == args

    def test_get_supported_args(self) -> None:
        """Test get_supported_args returns correct arguments."""
        supported_args = SheetsFormatter.get_supported_args()
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
        formatter = SheetsFormatter(year=2024)
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
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        # Check current week display
        assert "Current Week: 10" in output

        # Check weekly challenge names appear
        assert "Highest Score This Week" in output
        assert "Top Scorer" in output
        assert "Patrick Mahomes" in output
        assert "QB" in output  # Position should be included

    def test_format_output_with_note(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with note format argument."""
        formatter = SheetsFormatter(year=2024, format_args={"note": "Playoffs start next week!"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check note is displayed at top
        lines = output.split("\n")
        # Note should be in first few lines
        first_lines = "\n".join(lines[:5])
        assert "Playoffs start next week!" in first_lines
        assert "📢 NOTE:" in first_lines

    def test_format_output_no_weekly_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output without weekly challenges."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=None,
        )

        # Should contain season challenges
        assert "Most Points Overall" in output
        assert output  # Non-empty output


class TestTSVStructure:
    """Tests for TSV structure and formatting."""

    def test_output_uses_tabs(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output uses tab characters as delimiters."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Should contain tab characters
        assert "\t" in output

        # Check specific TSV rows contain tabs
        lines = output.split("\n")
        # Find a data row (e.g., challenge row)
        for line in lines:
            if "Alice's Team" in line and "Most Points" in line:
                assert "\t" in line
                break

    def test_division_standings_format(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test division standings section has proper TSV format."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        lines = output.split("\n")

        # Find standings header
        header_found = False
        for i, line in enumerate(lines):
            if "Rank\tTeam\tOwner\tPoints For" in line:
                header_found = True
                # Check that data rows follow with tabs
                if i + 1 < len(lines):
                    data_line = lines[i + 1]
                    if data_line.strip():  # If not empty
                        assert "\t" in data_line
                break

        assert header_found, "Standings header not found"

    def test_challenge_section_format(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test season challenges section has proper TSV format."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        lines = output.split("\n")

        # Find challenge header
        header_found = False
        for i, line in enumerate(lines):
            if "Challenge\tWinner\tOwner\tDivision\tDetails" in line:
                header_found = True
                # Check that data rows follow with tabs
                if i + 1 < len(lines):
                    data_line = lines[i + 1]
                    if data_line.strip() and "Game data" not in data_line:
                        assert "\t" in data_line
                break

        assert header_found, "Challenge header not found"

    def test_weekly_challenges_format(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test weekly challenges section has proper TSV format."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        lines = output.split("\n")

        # Find team challenges header
        team_header_found = False
        for line in lines:
            if "Challenge\tTeam\tDivision\tValue" in line:
                team_header_found = True
                break

        # Find player highlights header
        player_header_found = False
        for i, line in enumerate(lines):
            if line == "Challenge\tPlayer\tPoints":
                player_header_found = True
                # Check that data rows follow with tabs
                if i + 1 < len(lines):
                    data_line = lines[i + 1]
                    if data_line.strip():
                        assert "\t" in data_line
                break

        assert team_header_found, "Team challenges header not found"
        assert player_header_found, "Player highlights header not found"

    def test_playoff_indicator_format(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test playoff indicators use Y/N format."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check for Y and N playoff indicators
        lines = output.split("\n")
        found_y = False
        found_n = False

        for line in lines:
            # Look for data rows with record and playoff indicator
            if "\t8-3\t" in line and line.strip().endswith("Y"):
                found_y = True
            if "\t7-4\t" in line and line.strip().endswith("N"):
                found_n = True

        assert found_y, "Playoff position Y not found for qualifying team"
        assert found_n, "Playoff position N not found for non-qualifying team"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_format_output_empty_divisions(self) -> None:
        """Test format_output with empty divisions list."""
        formatter = SheetsFormatter(year=2024)
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
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=[],
        )

        # Should still contain team data
        assert "Alice's Team" in output
        assert "DIVISION STANDINGS" in output

    def test_format_output_special_characters_in_team_name(
        self,
        sample_owner_alice: Owner,
    ) -> None:
        """Test format_output handles special characters in team names."""
        team_with_special_chars = TeamStats(
            name='Alice\'s "Elite" Team',
            owner=sample_owner_alice,
            wins=8,
            losses=3,
            points_for=1250.50,
            points_against=1100.25,
            division="League A",
            in_playoff_position=True,
        )

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team_with_special_chars],
            games=[],
            weekly_games=[],
            weekly_players=[],
        )

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division],
            challenges=[],
        )

        # Special characters should be preserved in TSV
        assert 'Alice\'s "Elite" Team' in output

    def test_format_output_tab_in_team_name(
        self,
        sample_owner_alice: Owner,
    ) -> None:
        """Test format_output with tab character in team name."""
        # This is an edge case - tabs in names could break TSV format
        team_with_tab = TeamStats(
            name="Alice\tTeam",
            owner=sample_owner_alice,
            wins=8,
            losses=3,
            points_for=1250.50,
            points_against=1100.25,
            division="League A",
            in_playoff_position=True,
        )

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team_with_tab],
            games=[],
            weekly_games=[],
            weekly_players=[],
        )

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division],
            challenges=[],
        )

        # Should still produce output (even if imperfect TSV)
        assert "Alice" in output
        assert output

    def test_format_output_empty_weekly_challenges_list(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with empty weekly challenges list."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=10,
        )

        # Should not crash, should still show standings
        assert "DIVISION STANDINGS" in output
        assert "Alice's Team" in output


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

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=sample_challenges,
        )

        # Check header shows correct counts
        assert "2 divisions" in output
        assert "2 teams total" in output

        # Both divisions should appear
        assert "League A" in output
        assert "League B" in output

    def test_format_output_multiple_divisions_with_note(
        self,
        sample_owner_alice: Owner,
        sample_owner_bob: Owner,
    ) -> None:
        """Test format_output with multiple divisions and note."""
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

        formatter = SheetsFormatter(
            year=2024,
            format_args={"note": "Multi-league update"},
        )
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=[],
        )

        # Check note appears
        assert "Multi-league update" in output
        assert "League A" in output
        assert "League B" in output

    def test_overall_top_teams_multiple_divisions(
        self,
        sample_owner_alice: Owner,
        sample_owner_bob: Owner,
    ) -> None:
        """Test overall top teams section with multiple divisions."""
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

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=[],
        )

        # Should have overall top teams section
        assert "OVERALL TOP TEAMS" in output

        # Both teams should appear with division names
        lines = output.split("\n")
        found_alice_with_division = False
        found_bob_with_division = False

        for line in lines:
            if "Alice's Team" in line and "League A" in line:
                found_alice_with_division = True
            if "Bob's Team" in line and "League B" in line:
                found_bob_with_division = True

        assert found_alice_with_division, "Alice's team not shown with division"
        assert found_bob_with_division, "Bob's team not shown with division"


class TestWeeklyChallengeFormatting:
    """Tests for weekly challenge formatting."""

    def test_separate_team_and_player_sections(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that team and player challenges are in separate sections."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        # Check for separate headers
        assert "Team Challenges" in output
        assert "Player Highlights" in output

        # Verify they appear in the right order
        team_pos = output.find("Team Challenges")
        player_pos = output.find("Player Highlights")
        assert team_pos < player_pos, "Team challenges should come before player highlights"

    def test_player_position_included(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that player position is included in player highlights."""
        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        # Player should be shown with position
        assert "Patrick Mahomes (QB)" in output

    def test_weekly_challenges_with_only_team_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_owner_alice: Owner,
    ) -> None:
        """Test weekly challenges section with only team challenges."""
        team_only_challenges = [
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
        ]

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=team_only_challenges,
            current_week=10,
        )

        # Should have team challenges section
        assert "Team Challenges" in output
        assert "Highest Score This Week" in output
        # Should not have player highlights section
        assert "Player Highlights" not in output

    def test_weekly_challenges_with_only_player_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_owner_alice: Owner,
    ) -> None:
        """Test weekly challenges section with only player challenges."""
        player_only_challenges = [
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

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=player_only_challenges,
            current_week=10,
        )

        # Should have player highlights section
        assert "Player Highlights" in output
        assert "Patrick Mahomes" in output
        # Should not have team challenges section
        assert "Team Challenges" not in output


class TestPlayoffMode:
    """Tests for playoff mode functionality."""

    def test_playoff_mode_detection_from_division(
        self,
        sample_owner_alice: Owner,
        sample_owner_bob: Owner,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test that playoff mode is detected when division has playoff bracket."""
        from ff_tracker.models.playoff import PlayoffBracket, PlayoffMatchup

        # Create playoff matchup
        matchup = PlayoffMatchup(
            matchup_id="div1_sf1",
            round_name="Semifinal 1",
            seed1=1,
            team1_name="Alice's Team",
            owner1_name="Alice Smith",
            score1=125.50,
            seed2=4,
            team2_name="Bob's Team",
            owner2_name="Bob Jones",
            score2=110.25,
            winner_name="Alice's Team",
            winner_seed=1,
            division_name="League A",
        )

        # Create playoff bracket
        bracket = PlayoffBracket(
            round="Semifinals",
            week=15,
            division_name="League A",
            matchups=[matchup, matchup],  # Two semifinals
        )

        # Create division with playoff bracket
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

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team_a],
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=bracket,
        )

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division],
            challenges=sample_challenges,
            current_week=15,
        )

        # Should show playoff bracket
        assert "PLAYOFF BRACKET" in output
        assert "Semifinals" in output or "SEMIFINALS" in output

        # Should show regular season standings as historical
        assert "FINAL REGULAR SEASON STANDINGS" in output

    def test_playoff_mode_filters_weekly_challenges_to_players_only(
        self,
        sample_owner_alice: Owner,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that playoff mode only shows player highlights, not team challenges."""
        from ff_tracker.models.playoff import PlayoffBracket, PlayoffMatchup

        matchup = PlayoffMatchup(
            matchup_id="div1_finals",
            round_name="Finals",
            seed1=1,
            team1_name="Alice's Team",
            owner1_name="Alice Smith",
            score1=130.00,
            seed2=2,
            team2_name="Bob's Team",
            owner2_name="Bob Jones",
            score2=125.00,
            winner_name="Alice's Team",
            winner_seed=1,
            division_name="League A",
        )

        bracket = PlayoffBracket(
            round="Finals",
            week=16,
            division_name="League A",
            matchups=[matchup],
        )

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

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team_a],
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=bracket,
        )

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=16,
        )

        # Should show player highlights only
        assert "PLAYER HIGHLIGHTS" in output
        assert "Patrick Mahomes" in output

        # Should NOT show team challenges
        assert "Team Challenges" not in output
        assert "Highest Score This Week" not in output

    def test_playoff_bracket_formatting(
        self,
        sample_owner_alice: Owner,
        sample_owner_bob: Owner,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test playoff bracket section formatting."""
        from ff_tracker.models.playoff import PlayoffBracket, PlayoffMatchup

        # Create two semifinal matchups
        matchup1 = PlayoffMatchup(
            matchup_id="div1_sf1",
            round_name="Semifinal 1",
            seed1=1,
            team1_name="Alice's Team",
            owner1_name="Alice Smith",
            score1=125.50,
            seed2=4,
            team2_name="Bob's Team",
            owner2_name="Bob Jones",
            score2=110.25,
            winner_name="Alice's Team",
            winner_seed=1,
            division_name="League A",
        )

        matchup2 = PlayoffMatchup(
            matchup_id="div1_sf2",
            round_name="Semifinal 2",
            seed1=2,
            team1_name="Charlie's Team",
            owner1_name="Charlie Brown",
            score1=115.00,
            seed2=3,
            team2_name="Dana's Team",
            owner2_name="Dana White",
            score2=120.00,
            winner_name="Dana's Team",
            winner_seed=3,
            division_name="League A",
        )

        bracket = PlayoffBracket(
            round="Semifinals",
            week=15,
            division_name="League A",
            matchups=[matchup1, matchup2],
        )

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

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=[team_a],
            games=[],
            weekly_games=[],
            weekly_players=[],
            playoff_bracket=bracket,
        )

        formatter = SheetsFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division],
            challenges=sample_challenges,
            current_week=15,
        )

        # Check bracket header
        assert "PLAYOFF BRACKET" in output
        assert "SEMIFINALS" in output

        # Check TSV structure for bracket
        lines = output.split("\n")
        bracket_header_found = False
        for line in lines:
            if "Matchup\tSeed\tTeam\tOwner\tScore\tResult" in line:
                bracket_header_found = True
                break

        assert bracket_header_found, "Bracket TSV header not found"

        # Check team names appear
        assert "Alice's Team" in output
        assert "Bob's Team" in output
        assert "Charlie's Team" in output
        assert "Dana's Team" in output

        # Check winner indicators
        assert "WINNER" in output
