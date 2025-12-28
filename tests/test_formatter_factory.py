"""
Tests for formatter factory and ReportContext.

Tests the new factory pattern and report context functionality added in Phase 2.
"""

from __future__ import annotations

import pytest

from ff_tracker.display import (
    ConsoleFormatter,
    EmailFormatter,
    JsonFormatter,
    MarkdownFormatter,
    ReportContext,
    ReportMode,
    SheetsFormatter,
    create_formatter,
    get_available_formats,
)


class TestFormatterFactory:
    """Tests for create_formatter factory function."""

    def test_create_console_formatter(self):
        """Test creating console formatter."""
        formatter = create_formatter("console", 2024)

        assert isinstance(formatter, ConsoleFormatter)
        assert formatter.year == 2024
        assert formatter.format_args == {}

    def test_create_sheets_formatter(self):
        """Test creating sheets formatter."""
        formatter = create_formatter("sheets", 2024)

        assert isinstance(formatter, SheetsFormatter)
        assert formatter.year == 2024

    def test_create_email_formatter(self):
        """Test creating email formatter."""
        formatter = create_formatter("email", 2024)

        assert isinstance(formatter, EmailFormatter)
        assert formatter.year == 2024

    def test_create_json_formatter(self):
        """Test creating JSON formatter."""
        formatter = create_formatter("json", 2024)

        assert isinstance(formatter, JsonFormatter)
        assert formatter.year == 2024

    def test_create_markdown_formatter(self):
        """Test creating markdown formatter."""
        formatter = create_formatter("markdown", 2024)

        assert isinstance(formatter, MarkdownFormatter)
        assert formatter.year == 2024

    def test_create_formatter_with_args(self):
        """Test creating formatter with format arguments."""
        format_args = {"note": "Test note", "accent_color": "#ff0000"}
        formatter = create_formatter("email", 2024, format_args)

        assert isinstance(formatter, EmailFormatter)
        assert formatter.format_args == format_args

    def test_create_formatter_invalid_name(self):
        """Test error handling for invalid formatter name."""
        with pytest.raises(ValueError, match="Unknown format.*invalid"):
            create_formatter("invalid", 2024)

    def test_create_formatter_error_message_includes_valid_formats(self):
        """Test that error message lists valid formats."""
        with pytest.raises(ValueError) as exc_info:
            create_formatter("bad_format", 2024)

        error_msg = str(exc_info.value)
        assert "console" in error_msg
        assert "sheets" in error_msg
        assert "email" in error_msg
        assert "json" in error_msg
        assert "markdown" in error_msg


class TestGetAvailableFormats:
    """Tests for get_available_formats function."""

    def test_get_available_formats(self):
        """Test getting list of available formatter names."""
        formats = get_available_formats()

        assert isinstance(formats, list)
        assert len(formats) == 5
        assert "console" in formats
        assert "sheets" in formats
        assert "email" in formats
        assert "json" in formats
        assert "markdown" in formats


class TestReportMode:
    """Tests for ReportMode enum."""

    def test_report_mode_values(self):
        """Test ReportMode enum values."""
        assert ReportMode.REGULAR.value == "regular"
        assert ReportMode.PLAYOFF.value == "playoff"
        assert ReportMode.CHAMPIONSHIP.value == "championship"

    def test_report_mode_enum_members(self):
        """Test all expected modes are present."""
        modes = list(ReportMode)
        assert len(modes) == 3
        assert ReportMode.REGULAR in modes
        assert ReportMode.PLAYOFF in modes
        assert ReportMode.CHAMPIONSHIP in modes


class TestReportContext:
    """Tests for ReportContext dataclass."""

    def test_report_context_regular_mode(self):
        """Test creating context for regular season report."""
        context = ReportContext(
            mode=ReportMode.REGULAR,
            year=2024,
            current_week=10,
            divisions=[],
            challenges=[],
        )

        assert context.mode == ReportMode.REGULAR
        assert context.year == 2024
        assert context.current_week == 10
        assert context.is_regular_season() is True
        assert context.is_playoff_mode() is False
        assert context.is_championship_mode() is False

    def test_report_context_playoff_mode(self):
        """Test creating context for playoff report."""
        context = ReportContext(
            mode=ReportMode.PLAYOFF,
            year=2024,
            current_week=15,
        )

        assert context.mode == ReportMode.PLAYOFF
        assert context.is_regular_season() is False
        assert context.is_playoff_mode() is True
        assert context.is_championship_mode() is False

    def test_report_context_championship_mode(self):
        """Test creating context for championship report."""
        context = ReportContext(
            mode=ReportMode.CHAMPIONSHIP,
            year=2024,
            current_week=17,
        )

        assert context.mode == ReportMode.CHAMPIONSHIP
        assert context.is_regular_season() is False
        assert context.is_playoff_mode() is False
        assert context.is_championship_mode() is True

    def test_report_context_has_weekly_challenges(self):
        """Test checking for weekly challenges data."""
        # No weekly challenges
        context1 = ReportContext(
            mode=ReportMode.REGULAR,
            year=2024,
            weekly_challenges=None,
        )
        assert context1.has_weekly_challenges() is False

        # Empty weekly challenges
        context2 = ReportContext(
            mode=ReportMode.REGULAR,
            year=2024,
            weekly_challenges=[],
        )
        assert context2.has_weekly_challenges() is False

        # Has weekly challenges (using mock object)
        from unittest.mock import Mock

        mock_challenge = Mock()
        context3 = ReportContext(
            mode=ReportMode.REGULAR,
            year=2024,
            weekly_challenges=[mock_challenge],
        )
        assert context3.has_weekly_challenges() is True

    def test_report_context_has_championship_data(self):
        """Test checking for championship data."""
        # No championship data
        context1 = ReportContext(
            mode=ReportMode.REGULAR,
            year=2024,
            championship=None,
        )
        assert context1.has_championship_data() is False

        # Has championship data (using mock object)
        from unittest.mock import Mock

        mock_championship = Mock()
        context2 = ReportContext(
            mode=ReportMode.CHAMPIONSHIP,
            year=2024,
            championship=mock_championship,
        )
        assert context2.has_championship_data() is True

    def test_report_context_defaults(self):
        """Test ReportContext default values."""
        context = ReportContext(mode=ReportMode.REGULAR, year=2024)

        assert context.current_week is None
        assert context.divisions == []
        assert context.challenges == []
        assert context.weekly_challenges is None
        assert context.championship is None
        assert context.championship_rosters is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
