"""Tests for email HTML output formatter."""

from __future__ import annotations

import pytest

from ff_tracker.display.email import EmailFormatter
from ff_tracker.models import (
    ChallengeResult,
    ChampionshipEntry,
    ChampionshipLeaderboard,
    DivisionData,
    GameResult,
    Owner,
    PlayoffBracket,
    PlayoffMatchup,
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


class TestEmailFormatterBasics:
    """Tests for EmailFormatter initialization and basic functionality."""

    def test_init_email_formatter(self) -> None:
        """Test EmailFormatter initialization."""
        formatter = EmailFormatter(year=2024)
        assert formatter.year == 2024
        assert formatter.format_args == {}

    def test_init_with_format_args(self) -> None:
        """Test EmailFormatter initialization with format args."""
        args = {"note": "Important message", "accent_color": "#007bff"}
        formatter = EmailFormatter(year=2024, format_args=args)
        assert formatter.year == 2024
        assert formatter.format_args == args

    def test_get_supported_args(self) -> None:
        """Test get_supported_args returns correct arguments."""
        supported_args = EmailFormatter.get_supported_args()
        assert "note" in supported_args
        assert "accent_color" in supported_args
        assert "max_teams" in supported_args
        assert isinstance(supported_args["note"], str)
        assert isinstance(supported_args["accent_color"], str)
        assert isinstance(supported_args["max_teams"], str)


class TestFormatOutput:
    """Tests for format_output method."""

    def test_format_output_basic(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test basic format_output generates valid HTML."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check HTML structure
        assert "<!DOCTYPE html>" in output
        assert '<html lang="en">' in output
        assert "</html>" in output
        assert "<head>" in output
        assert "<body>" in output

        # Check title and year
        assert "2024" in output
        assert "Fantasy Football" in output

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
        formatter = EmailFormatter(year=2024)
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
        formatter = EmailFormatter(year=2024, format_args={"note": "Playoffs start next week!"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check note is displayed
        assert "Playoffs start next week!" in output

    def test_format_output_with_custom_accent_color(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with custom accent color."""
        formatter = EmailFormatter(year=2024, format_args={"accent_color": "#007bff"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check custom color appears in CSS
        assert "#007bff" in output

    def test_format_output_with_max_teams(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output respects max_teams argument."""
        formatter = EmailFormatter(year=2024, format_args={"max_teams": "1"})
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Output should still be valid HTML
        assert "<!DOCTYPE html>" in output
        assert "Alice" in output  # Should have at least top team

    def test_format_output_default_accent_color(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output uses default accent color when not specified."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check default color appears
        assert "#ffc107" in output

    def test_format_output_no_weekly_challenges(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output without weekly challenges."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=None,
        )

        # Should contain season challenges
        assert "Most Points Overall" in output
        assert "<!DOCTYPE html>" in output


class TestHTMLStructure:
    """Tests for HTML structure and formatting."""

    def test_output_has_viewport_meta(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes mobile viewport meta tag."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        assert "viewport" in output
        assert "width=device-width" in output

    def test_output_has_css_styles(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes CSS styles."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        assert "<style>" in output
        assert "</style>" in output
        assert "font-family" in output
        assert "background-color" in output

    def test_output_has_tables(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes HTML tables."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        assert "<table>" in output or "<table " in output
        assert "</table>" in output
        assert "<tr>" in output
        assert "<td>" in output

    def test_output_has_metadata_markers(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test output includes metadata injection markers."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check for metadata markers
        assert "GENERATED_METADATA_START" in output
        assert "GENERATED_METADATA_END" in output


class TestHTMLEscaping:
    """Tests for HTML escaping functionality."""

    def test_escape_html_basic(self) -> None:
        """Test _escape_html handles basic characters."""
        formatter = EmailFormatter(year=2024)

        assert formatter._escape_html("<script>") == "&lt;script&gt;"
        assert formatter._escape_html("Alice & Bob") == "Alice &amp; Bob"
        assert formatter._escape_html('Team "A"') == "Team &quot;A&quot;"

    def test_escape_html_apostrophe(self) -> None:
        """Test _escape_html handles apostrophes."""
        formatter = EmailFormatter(year=2024)

        assert formatter._escape_html("Alice's Team") == "Alice&#x27;s Team"

    def test_escape_html_empty_string(self) -> None:
        """Test _escape_html handles empty string."""
        formatter = EmailFormatter(year=2024)

        assert formatter._escape_html("") == ""

    def test_escape_html_no_special_chars(self) -> None:
        """Test _escape_html leaves normal text unchanged."""
        formatter = EmailFormatter(year=2024)

        text = "Normal Team Name 123"
        assert formatter._escape_html(text) == text


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_format_output_empty_divisions(self) -> None:
        """Test format_output with empty divisions list."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[],
            challenges=[],
        )

        # Should still produce valid HTML
        assert "<!DOCTYPE html>" in output
        assert "<html" in output
        assert "</html>" in output
        assert "0 divisions" in output  # Uses bullet point separator in email
        assert "0 teams" in output

    def test_format_output_empty_challenges(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test format_output with empty challenges list."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=[],
        )

        # Should still contain team data
        assert "Alice" in output
        assert "<!DOCTYPE html>" in output

    def test_format_output_special_characters_in_team_name(
        self,
        sample_owner_alice: Owner,
    ) -> None:
        """Test format_output escapes special characters in team names."""
        team_with_special_chars = TeamStats(
            name='Alice\'s <Team> & "Friends"',
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

        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division],
            challenges=[],
        )

        # Should escape special characters
        assert "&lt;Team&gt;" in output
        assert "&amp;" in output
        assert "&quot;" in output or "&#x27;" in output

    def test_format_output_with_all_format_args(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test format_output with all format arguments specified."""
        formatter = EmailFormatter(
            year=2024,
            format_args={
                "note": "Important notice",
                "accent_color": "#28a745",
                "max_teams": "5",
            },
        )
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
        )

        # Check all args are used
        assert "Important notice" in output
        assert "#28a745" in output
        assert "<!DOCTYPE html>" in output


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

        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=sample_challenges,
        )

        # Check both divisions appear
        assert "League A" in output
        assert "League B" in output
        assert "2 divisions" in output

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

        formatter = EmailFormatter(
            year=2024,
            format_args={"note": "Multi-league update", "accent_color": "#dc3545"},
        )
        output = formatter.format_output(
            divisions=[div1, div2],
            challenges=[],
        )

        # Check note and color
        assert "Multi-league update" in output
        assert "#dc3545" in output
        assert "League A" in output
        assert "League B" in output


class TestWeeklyChallengeFormatting:
    """Tests for weekly challenge formatting."""

    def test_format_weekly_player_table(
        self,
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test _format_weekly_player_table generates valid HTML."""
        # Filter to just player challenges
        player_challenges = [c for c in sample_weekly_challenges if "position" in c.additional_info]

        formatter = EmailFormatter(year=2024)
        output = formatter._format_weekly_player_table(player_challenges, current_week=10)

        # Should contain table and player data
        assert "<table" in output
        assert "Patrick Mahomes" in output
        assert "QB" in output

    def test_format_weekly_player_table_empty(self) -> None:
        """Test _format_weekly_player_table with empty list."""
        formatter = EmailFormatter(year=2024)
        output = formatter._format_weekly_player_table([], current_week=10)

        # Should return empty string or minimal HTML
        assert isinstance(output, str)


class TestEmailFormatterPlayoffMode:
    """Test email formatter with playoff mode data."""

    @pytest.fixture
    def playoff_matchup_semifinals(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> PlayoffMatchup:
        """Create a sample semifinals playoff matchup."""
        return PlayoffMatchup(
            matchup_id="SF1",
            round_name="Semifinals",
            team1_name="Thunder Cats",
            owner1_name=sample_owner_alice.full_name,
            score1=145.67,
            seed1=1,
            team2_name="Dream Team",
            owner2_name=sample_owner_bob.full_name,
            score2=98.23,
            seed2=4,
            winner_name="Thunder Cats",
            winner_seed=1,
            division_name="League A",
        )

    @pytest.fixture
    def playoff_matchup_finals(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> PlayoffMatchup:
        """Create a sample finals playoff matchup."""
        return PlayoffMatchup(
            matchup_id="F1",
            round_name="Finals",
            team1_name="Thunder Cats",
            owner1_name=sample_owner_alice.full_name,
            score1=150.0,
            seed1=1,
            team2_name="Touchdown Titans",
            owner2_name=sample_owner_bob.full_name,
            score2=145.0,
            seed2=3,
            winner_name="Thunder Cats",
            winner_seed=1,
            division_name="League A",
        )

    @pytest.fixture
    def playoff_bracket_semifinals(
        self, playoff_matchup_semifinals: PlayoffMatchup, sample_owner_bob: Owner
    ) -> PlayoffBracket:
        """Create a sample semifinals playoff bracket with 2 matchups."""
        matchup2 = PlayoffMatchup(
            matchup_id="SF2",
            round_name="Semifinals",
            team1_name="Pineapple Express",
            owner1_name=sample_owner_bob.full_name,
            score1=130.45,
            seed1=2,
            team2_name="Touchdown Titans",
            owner2_name="Chris Brown",
            score2=135.12,
            seed2=3,
            winner_name="Touchdown Titans",
            winner_seed=3,
            division_name="League A",
        )
        return PlayoffBracket(
            round="Semifinals",
            week=15,
            division_name="League A",
            matchups=[playoff_matchup_semifinals, matchup2],
        )

    @pytest.fixture
    def playoff_bracket_finals(self, playoff_matchup_finals: PlayoffMatchup) -> PlayoffBracket:
        """Create a sample finals playoff bracket with 1 matchup."""
        return PlayoffBracket(
            round="Finals",
            week=16,
            division_name="League A",
            matchups=[playoff_matchup_finals],
        )

    @pytest.fixture
    def division_with_semifinals(
        self,
        sample_teams: list[TeamStats],
        sample_games: list[GameResult],
        playoff_bracket_semifinals: PlayoffBracket,
    ) -> DivisionData:
        """Division data in semifinals playoff mode."""
        return DivisionData(
            league_id=123456,
            name="League A",
            teams=sample_teams,
            games=sample_games,
            playoff_bracket=playoff_bracket_semifinals,
        )

    @pytest.fixture
    def division_with_finals(
        self,
        sample_teams: list[TeamStats],
        sample_games: list[GameResult],
        playoff_bracket_finals: PlayoffBracket,
    ) -> DivisionData:
        """Division data in finals playoff mode."""
        return DivisionData(
            league_id=123456,
            name="League A",
            teams=sample_teams,
            games=sample_games,
            playoff_bracket=playoff_bracket_finals,
        )

    @pytest.fixture
    def championship_leaderboard(
        self, sample_owner_alice: Owner, sample_owner_bob: Owner
    ) -> ChampionshipLeaderboard:
        """Create a sample championship leaderboard."""
        entries = [
            ChampionshipEntry(
                rank=1,
                team_name="Thunder Cats",
                owner_name=sample_owner_alice.full_name,
                division_name="League A",
                score=175.50,
                is_champion=True,
            ),
            ChampionshipEntry(
                rank=2,
                team_name="Dream Team",
                owner_name=sample_owner_bob.full_name,
                division_name="League B",
                score=165.25,
                is_champion=False,
            ),
            ChampionshipEntry(
                rank=3,
                team_name="Pineapple Express",
                owner_name="Tom Jones",
                division_name="League C",
                score=150.00,
                is_champion=False,
            ),
        ]
        return ChampionshipLeaderboard(
            week=17,
            entries=entries,
        )

    @pytest.fixture
    def player_only_weekly_challenges(self, sample_owner_alice: Owner) -> list[WeeklyChallenge]:
        """Create player-only weekly challenges for playoff mode."""
        return [
            WeeklyChallenge(
                challenge_name="Top Scorer (Player)",
                week=15,
                winner="Patrick Mahomes",
                owner=sample_owner_alice,
                division="League A",
                value="35.50 points",
                description="Patrick Mahomes (QB - Thunder Cats) scored 35.50 points",
                additional_info={
                    "position": "QB",
                    "points": 35.50,
                    "team_name": "Thunder Cats",
                },
            ),
            WeeklyChallenge(
                challenge_name="Best RB",
                week=15,
                winner="Derrick Henry",
                owner=sample_owner_alice,
                division="League A",
                value="28.00 points",
                description="Derrick Henry (RB - Thunder Cats) scored 28.00 points",
                additional_info={
                    "position": "RB",
                    "points": 28.00,
                    "team_name": "Thunder Cats",
                },
            ),
        ]

    def test_format_output_with_semifinals_bracket(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test that semifinals playoff bracket is formatted correctly in HTML."""
        formatter = EmailFormatter(year=2024)

        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=15,
        )

        # Should be valid HTML
        assert "<!DOCTYPE html>" in output
        assert "</html>" in output

        # Should include playoff bracket section
        assert "playoff-bracket" in output
        assert "Playoff Bracket" in output
        assert "Semifinals" in output

        # Should include matchup details
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "145.67" in output
        assert "Pineapple Express" in output
        assert "Touchdown Titans" in output

        # Should show seeds
        assert "#1" in output
        assert "#4" in output

        # Should include winner styling
        assert "playoff-winner" in output

        # Should show historical note for regular season
        assert "Final regular season" in output.lower() or "historical" in output.lower()

    def test_format_output_with_finals_bracket(
        self,
        division_with_finals: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test formatting for Finals round in HTML."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division_with_finals],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=16,
        )

        # Should be valid HTML
        assert "<!DOCTYPE html>" in output

        # Should include finals matchup
        assert "Finals" in output
        assert "Thunder Cats" in output
        assert "Touchdown Titans" in output
        assert "150.00" in output

    def test_format_output_with_championship_leaderboard(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        championship_leaderboard: ChampionshipLeaderboard,
    ) -> None:
        """Test formatting for Championship Week in HTML."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=17,
            championship=championship_leaderboard,
        )

        # Should be valid HTML
        assert "<!DOCTYPE html>" in output

        # Should include championship box styling
        assert "championship-box" in output
        assert "Championship Week" in output
        assert "Final Leaderboard" in output
        assert "Highest score wins overall championship" in output

        # Should include all entries
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "Pineapple Express" in output
        assert "175.50" in output

        # Should show medals
        assert "🥇" in output
        assert "🥈" in output
        assert "🥉" in output

        # Should show current leader message (no rosters = not final)
        assert "CURRENT LEADER" in output
        assert "Games still in progress" in output

    def test_playoff_mode_shows_player_highlights_only(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
        player_only_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that playoff mode shows only player challenges in weekly section."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=player_only_weekly_challenges,
            current_week=15,
        )

        # Should show player highlights
        assert "Player Highlights" in output
        assert "Patrick Mahomes" in output
        assert "Derrick Henry" in output

        # Should NOT show team challenges section
        assert "Team Challenges" not in output

    def test_playoff_mode_filters_to_player_challenges(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that playoff mode filters out team challenges from weekly section."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,  # Has both team and player
            current_week=15,
        )

        # Should show player highlights
        assert "Patrick Mahomes" in output

        # Weekly section should not include team challenge names
        # (they only appear in season-long section)
        # Count occurrences - should be minimal (only in season section if at all)
        assert output.count("Highest Score This Week") <= 1

    def test_format_playoff_brackets_method(
        self,
        division_with_semifinals: DivisionData,
    ) -> None:
        """Test _format_playoff_brackets method directly."""
        formatter = EmailFormatter(year=2024)
        output = formatter._format_playoff_brackets([division_with_semifinals])

        # Should include playoff bracket div
        assert 'class="playoff-bracket"' in output

        # Should include division name and round
        assert "League A" in output
        assert "Semifinals" in output

        # Should include matchup details with HTML tables
        assert "<table" in output
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "145.67" in output

        # Should show winner styling
        assert "playoff-winner" in output

    def test_format_championship_leaderboard_method(
        self,
        championship_leaderboard: ChampionshipLeaderboard,
    ) -> None:
        """Test _format_championship_leaderboard method directly."""
        formatter = EmailFormatter(year=2024)
        output = formatter._format_championship_leaderboard(championship_leaderboard, rosters=None)

        # Should include championship box
        assert 'class="championship-box"' in output

        # Should include all entries
        assert "Thunder Cats" in output
        assert "Dream Team" in output
        assert "Pineapple Express" in output

        # Should include scores
        assert "175.50" in output
        assert "165.25" in output
        assert "150.00" in output

        # Should show current leader (not final without rosters)
        assert "CURRENT LEADER" in output
        assert "Games still in progress" in output

    def test_format_weekly_player_table_playoff_mode(
        self,
        player_only_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test _format_weekly_player_table formatting."""
        formatter = EmailFormatter(year=2024)
        output = formatter._format_weekly_player_table(
            player_only_weekly_challenges, current_week=15
        )

        # Should include weekly highlight div
        assert 'class="weekly-highlight"' in output
        assert "Week 15 Player Highlights" in output

        # Should include table
        assert "<table>" in output

        # Should include player challenges
        assert "Patrick Mahomes" in output
        assert "QB" in output
        assert "Derrick Henry" in output
        assert "RB" in output

    def test_playoff_mode_shows_historical_notes(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test that playoff mode shows historical notes for regular season data."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=15,
        )

        # Should include historical notes
        assert "historical-note" in output
        assert "Regular season challenges finalized" in output or "week 14" in output.lower()
        assert "Final Regular Season Standings" in output
        assert "Final Regular Season - Week 14" in output

    def test_playoff_bracket_with_custom_accent_color(
        self,
        division_with_semifinals: DivisionData,
        sample_challenges: list[ChallengeResult],
    ) -> None:
        """Test playoff bracket uses custom accent colors in styling."""
        formatter = EmailFormatter(year=2024, format_args={"accent_color": "#28a745"})
        output = formatter.format_output(
            divisions=[division_with_semifinals],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=15,
        )

        # Custom color should be in CSS
        assert "#28a745" in output

    def test_championship_with_note_and_custom_color(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        championship_leaderboard: ChampionshipLeaderboard,
    ) -> None:
        """Test championship week with note and custom colors."""
        formatter = EmailFormatter(
            year=2024,
            format_args={"note": "Final championship standings!", "accent_color": "#dc3545"},
        )
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=[],
            current_week=17,
            championship=championship_leaderboard,
        )

        # Should include note
        assert "Final championship standings!" in output
        assert "alert-box" in output

        # Should include custom color
        assert "#dc3545" in output

        # Should include championship content
        assert "Championship Week" in output

    def test_playoff_brackets_empty_list(self) -> None:
        """Test _format_playoff_brackets with empty divisions list."""
        formatter = EmailFormatter(year=2024)
        output = formatter._format_playoff_brackets([])

        # Should return empty string
        assert output == ""

    def test_playoff_brackets_no_playoff_data(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test _format_playoff_brackets with divisions that have no playoff bracket."""
        formatter = EmailFormatter(year=2024)
        output = formatter._format_playoff_brackets([sample_division])

        # Should return empty string (no playoff brackets)
        assert output == ""

    def test_regular_season_weekly_challenges_format(
        self,
        sample_division: DivisionData,
        sample_challenges: list[ChallengeResult],
        sample_weekly_challenges: list[WeeklyChallenge],
    ) -> None:
        """Test that regular season shows both team and player challenges."""
        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=sample_challenges,
            weekly_challenges=sample_weekly_challenges,
            current_week=10,
        )

        # Should show both sections
        assert "Team Challenges" in output
        assert "Player Highlights" in output

        # Should include both challenge types
        assert "Highest Score This Week" in output  # Team challenge
        assert "Patrick Mahomes" in output  # Player challenge

    def test_html_escaping_in_playoff_brackets(
        self,
        sample_owner_alice: Owner,
        sample_teams: list[TeamStats],
        sample_games: list[GameResult],
    ) -> None:
        """Test that playoff brackets properly escape HTML characters."""
        # Create matchup with special characters
        matchup1 = PlayoffMatchup(
            matchup_id="SF1",
            round_name="Semifinals",
            team1_name='Alice\'s <Team> & "Friends"',
            owner1_name=sample_owner_alice.full_name,
            score1=145.67,
            seed1=1,
            team2_name="Bob's Team",
            owner2_name="Bob & Jane",
            score2=98.23,
            seed2=4,
            winner_name='Alice\'s <Team> & "Friends"',
            winner_seed=1,
            division_name="League A",
        )

        # Semifinals needs 2 matchups
        matchup2 = PlayoffMatchup(
            matchup_id="SF2",
            round_name="Semifinals",
            team1_name="Team C",
            owner1_name="Charlie",
            score1=100.0,
            seed1=2,
            team2_name="Team D",
            owner2_name="David",
            score2=90.0,
            seed2=3,
            winner_name="Team C",
            winner_seed=2,
            division_name="League A",
        )

        bracket = PlayoffBracket(
            round="Semifinals",
            week=15,
            division_name="League A",
            matchups=[matchup1, matchup2],
        )

        division = DivisionData(
            league_id=123456,
            name="League A",
            teams=sample_teams,
            games=sample_games,
            playoff_bracket=bracket,
        )

        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[division],
            challenges=[],
            weekly_challenges=[],
            current_week=15,
        )

        # Should escape special characters
        assert "&lt;Team&gt;" in output
        assert "&amp;" in output
        assert "&quot;" in output or "&#x27;" in output

    def test_html_escaping_in_championship_leaderboard(
        self,
        sample_division: DivisionData,
    ) -> None:
        """Test that championship leaderboard properly escapes HTML characters."""
        # Create championship with special characters
        entries = [
            ChampionshipEntry(
                rank=1,
                team_name='Alice\'s <Team> & "Friends"',
                owner_name="Alice & Bob",
                division_name="League <A>",
                score=175.50,
                is_champion=True,
            ),
        ]
        championship = ChampionshipLeaderboard(week=17, entries=entries)

        formatter = EmailFormatter(year=2024)
        output = formatter.format_output(
            divisions=[sample_division],
            challenges=[],
            weekly_challenges=[],
            current_week=17,
            championship=championship,
        )

        # Should escape special characters
        assert "&lt;Team&gt;" in output
        assert "&amp;" in output
        assert "&lt;A&gt;" in output
