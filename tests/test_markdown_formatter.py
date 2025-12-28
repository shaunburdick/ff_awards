"""Tests for markdown output formatter."""

from __future__ import annotations

import pytest

from ff_tracker.display.markdown import MarkdownFormatter
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


class TestMarkdownFormatterBasics:
    """Tests for MarkdownFormatter initialization and basic functionality."""

    def test_init_markdown_formatter(self) -> None:
        """Test MarkdownFormatter initialization."""
        formatter = MarkdownFormatter(year=2024)
        assert formatter.year == 2024
        assert formatter.format_args == {}

    def test_init_with_format_args(self) -> None:
        """Test MarkdownFormatter initialization with format args."""
        args = {"note": "Important message", "include_toc": "true"}
        formatter = MarkdownFormatter(year=2024, format_args=args)
        assert formatter.year == 2024
        assert formatter.format_args == args

    def test_get_supported_args(self) -> None:
        """Test get_supported_args returns correct arguments."""
        supported_args = MarkdownFormatter.get_supported_args()
        assert "note" in supported_args
        assert "include_toc" in supported_args
        assert isinstance(supported_args["note"], str)
        assert isinstance(supported_args["include_toc"], str)


class TestFormatOutput:
    """Tests for format_output method."""

    def test_format_output_basic(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test basic format_output generates valid Markdown."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check markdown headers
        assert "# " in output  # H1 header
        assert "## " in output  # H2 header

        # Check year appears
        assert "2024" in output

        # Check team names appear
        assert "Alice" in output
        assert "Bob" in output

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
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        # Check weekly challenges appear
        assert "Week 10" in output or "WEEK 10" in output
        assert "Highest Score This Week" in output
        assert "Top Scorer" in output
        assert "Patrick Mahomes" in output

    def test_format_output_with_note(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with note format argument."""
        formatter = MarkdownFormatter(year=2024, format_args={"note": "Playoffs start next week!"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check note is displayed as blockquote
        assert "Playoffs start next week!" in output
        assert ">" in output  # Markdown blockquote

    def test_format_output_with_toc(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with table of contents."""
        formatter = MarkdownFormatter(year=2024, format_args={"include_toc": "true"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check TOC appears
        assert "Table of Contents" in output or "Contents" in output
        # TOC typically has links with anchors
        assert "#" in output

    def test_format_output_without_toc(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output without table of contents (default)."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Should not contain TOC header
        assert "Table of Contents" not in output

    def test_format_output_no_weekly_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output without weekly challenges."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=None,
        )

        # Should contain season challenges
        assert "Most Points Overall" in output
        assert "# " in output  # Has headers


class TestMarkdownStructure:
    """Tests for Markdown structure and formatting."""

    def test_output_has_headers(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes proper Markdown headers."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check for different header levels
        assert "# " in output  # H1
        assert "## " in output  # H2

    def test_output_has_tables(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes Markdown tables."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Markdown tables use pipe characters
        assert "|" in output
        # Table headers have dashes
        assert "---" in output or "---" in output

    def test_output_has_emojis(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes emojis for visual appeal."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Should have some emojis
        assert "🏈" in output or "🏆" in output or "📊" in output


class TestTableFormatting:
    """Tests for table formatting methods."""

    def test_format_challenge_table(
        self,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test challenge table formatting."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_challenge_table(sample_challenges)

        # All challenges should be present
        assert "Most Points Overall" in output
        assert "Most Points in One Game" in output
        assert "Alice's Team" in output
        # Should be a table
        assert "|" in output

    def test_format_weekly_table(
        self,
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test weekly challenge table formatting."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_weekly_table(sample_weekly_challenges)

        # All weekly challenges should be present
        assert "Highest Score This Week" in output
        assert "Top Scorer" in output
        assert "Alice's Team" in output
        assert "Patrick Mahomes" in output
        # Should be a table
        assert "|" in output

    def test_format_weekly_player_table(
        self,
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test weekly player table formatting."""
        # Filter to just player challenges
        player_challenges = [c for c in sample_weekly_challenges if "position" in c.additional_info]

        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_weekly_player_table(player_challenges)

        # Player challenges should be present
        assert "Patrick Mahomes" in output
        assert "|" in output  # Markdown table

    def test_format_division_table(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test division table formatting."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_division_table(sample_division)

        # Teams should be present
        assert "Alice's Team" in output
        assert "Bob's Team" in output
        assert "|" in output  # Markdown table

    def test_format_overall_table(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test overall table formatting."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_overall_table([sample_division])

        # Teams should be present
        assert "Alice's Team" in output
        assert "Bob's Team" in output
        assert "|" in output  # Markdown table


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_format_output_empty_divisions(self) -> None:
        """Test format_output with empty divisions list."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[],
            challenges=[],
        )

        # Should still produce valid Markdown
        assert "# " in output
        assert "0 divisions" in output
        assert "0 teams" in output

    def test_format_output_empty_challenges(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test format_output with empty challenges list."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=[],
        )

        # Should still contain team data
        assert "Alice" in output

    def test_format_challenge_table_empty(self) -> None:
        """Test format_challenge_table with empty list."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_challenge_table([])

        # Should return empty string or minimal output
        assert isinstance(output, str)

    def test_format_weekly_table_empty(self) -> None:
        """Test format_weekly_table with empty list."""
        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_weekly_table([])

        # Should return empty string or minimal output
        assert isinstance(output, str)

    def test_format_output_with_all_format_args(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with all format arguments specified."""
        formatter = MarkdownFormatter(
            year=2024,
            format_args={
                "note": "Important notice",
                "include_toc": "true",
            },
        )
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check all args are used
        assert "Important notice" in output
        # Should have TOC
        assert "# " in output


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

        formatter = MarkdownFormatter(year=2024)
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=sample_challenges,
        )

        # Check both divisions appear
        assert "League A" in output
        assert "League B" in output
        assert "2 divisions" in output

    def test_format_overall_table_multiple_divisions(
        self,
        sample_owner_alice: Owner,
        sample_owner_bob: Owner,
    ) -> None:
        """Test overall table with multiple divisions."""
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

        formatter = MarkdownFormatter(year=2024)
        output = formatter._format_overall_table([div1, div2])

        # Should combine teams from both divisions
        assert "Alice's Team" in output
        assert "Bob's Team" in output
        assert "|" in output  # Markdown table
