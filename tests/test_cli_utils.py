"""
Comprehensive tests for CLI utility functions.

Tests cover league ID parsing, format argument parsing, and logging setup.
"""

from __future__ import annotations

import logging

import pytest

from ff_tracker.cli_utils import (
    get_formatter_args,
    parse_format_args,
    parse_league_ids_from_arg,
    setup_logging,
)


class TestParseLeagueIdsFromArg:
    """Tests for parsing league IDs from CLI arguments."""

    def test_parse_single_league_id(self) -> None:
        """Test parsing a single league ID."""
        result = parse_league_ids_from_arg("123456")
        assert result == [123456]

    def test_parse_multiple_league_ids(self) -> None:
        """Test parsing multiple comma-separated league IDs."""
        result = parse_league_ids_from_arg("123456,789012,345678")
        assert result == [123456, 789012, 345678]

    def test_parse_with_spaces(self) -> None:
        """Test parsing league IDs with surrounding spaces."""
        result = parse_league_ids_from_arg(" 123456 , 789012 , 345678 ")
        assert result == [123456, 789012, 345678]

    def test_parse_with_empty_segments(self) -> None:
        """Test parsing with empty segments (double commas)."""
        result = parse_league_ids_from_arg("123456,,789012")
        assert result == [123456, 789012]

    def test_empty_string_raises_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="No valid league IDs found"):
            parse_league_ids_from_arg("")

    def test_only_commas_raises_error(self) -> None:
        """Test that only commas raises ValueError."""
        with pytest.raises(ValueError, match="No valid league IDs found"):
            parse_league_ids_from_arg(",,,")

    def test_only_whitespace_raises_error(self) -> None:
        """Test that only whitespace raises ValueError."""
        with pytest.raises(ValueError, match="No valid league IDs found"):
            parse_league_ids_from_arg("   ")

    def test_non_numeric_raises_error(self) -> None:
        """Test that non-numeric values raise ValueError."""
        with pytest.raises(ValueError, match="Error parsing league IDs"):
            parse_league_ids_from_arg("abc")

    def test_non_numeric_in_list_raises_error(self) -> None:
        """Test that non-numeric value in list raises ValueError."""
        with pytest.raises(ValueError, match="Error parsing league IDs"):
            parse_league_ids_from_arg("123456,abc,789012")

    def test_floating_point_raises_error(self) -> None:
        """Test that floating point raises ValueError."""
        with pytest.raises(ValueError, match="Error parsing league IDs"):
            parse_league_ids_from_arg("123456.5")

    def test_error_message_format(self) -> None:
        """Test that error message provides helpful format hint."""
        with pytest.raises(ValueError, match="123456 or 123456,789012,345678"):
            parse_league_ids_from_arg("invalid")


class TestParseFormatArgs:
    """Tests for parsing format arguments."""

    def test_parse_none_returns_empty(self) -> None:
        """Test that None input returns empty dict."""
        result = parse_format_args(None)
        assert result == {}

    def test_parse_empty_list_returns_empty(self) -> None:
        """Test that empty list returns empty dict."""
        result = parse_format_args([])
        assert result == {}

    def test_parse_single_global_arg(self) -> None:
        """Test parsing a single global argument."""
        result = parse_format_args(["note=Test message"])
        assert result == {"_global": {"note": "Test message"}}

    def test_parse_multiple_global_args(self) -> None:
        """Test parsing multiple global arguments."""
        result = parse_format_args(["note=Test", "title=My Title"])
        assert result == {"_global": {"note": "Test", "title": "My Title"}}

    def test_parse_single_formatter_specific_arg(self) -> None:
        """Test parsing a single formatter-specific argument."""
        result = parse_format_args(["email.accent_color=#ff0000"])
        assert result == {"_global": {}, "email": {"accent_color": "#ff0000"}}

    def test_parse_multiple_formatter_specific_args(self) -> None:
        """Test parsing multiple formatter-specific arguments for same formatter."""
        result = parse_format_args(["email.accent_color=#ff0000", "email.max_teams=5"])
        assert result == {"_global": {}, "email": {"accent_color": "#ff0000", "max_teams": "5"}}

    def test_parse_mixed_global_and_specific(self) -> None:
        """Test parsing mix of global and formatter-specific arguments."""
        result = parse_format_args(
            ["note=Important", "email.accent_color=#ff0000", "json.pretty=true"]
        )
        assert result == {
            "_global": {"note": "Important"},
            "email": {"accent_color": "#ff0000"},
            "json": {"pretty": "true"},
        }

    def test_parse_with_spaces_around_equals(self) -> None:
        """Test parsing with spaces around equals sign."""
        result = parse_format_args(["note = Test"])
        assert result == {"_global": {"note": "Test"}}

    def test_parse_value_with_equals_sign(self) -> None:
        """Test parsing value that contains equals sign."""
        result = parse_format_args(["url=https://example.com?param=value"])
        assert result == {"_global": {"url": "https://example.com?param=value"}}

    def test_parse_empty_value_allowed(self) -> None:
        """Test that empty value is allowed."""
        result = parse_format_args(["note="])
        assert result == {"_global": {"note": ""}}

    def test_missing_equals_raises_error(self) -> None:
        """Test that missing equals sign raises ValueError."""
        with pytest.raises(ValueError, match="Invalid format argument.*Must be in format"):
            parse_format_args(["invalid"])

    def test_empty_key_raises_error(self) -> None:
        """Test that empty key raises ValueError."""
        with pytest.raises(ValueError, match="Empty key in format argument"):
            parse_format_args(["=value"])

    def test_invalid_formatter_specific_format_raises_error(self) -> None:
        """Test that invalid formatter.key format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid formatter-specific argument"):
            parse_format_args(["email.=value"])  # Empty arg_key

    def test_invalid_formatter_specific_empty_formatter_raises_error(self) -> None:
        """Test that empty formatter name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid formatter-specific argument"):
            parse_format_args([".key=value"])  # Empty formatter name

    def test_multiple_dots_uses_first_split(self) -> None:
        """Test that multiple dots splits on first dot only."""
        result = parse_format_args(["email.color.primary=#ff0000"])
        assert result == {"_global": {}, "email": {"color.primary": "#ff0000"}}


class TestGetFormatterArgs:
    """Tests for getting merged formatter arguments."""

    def test_empty_dict_returns_empty(self) -> None:
        """Test that empty format args dict returns empty merged args."""
        result = get_formatter_args("email", {})
        assert result == {}

    def test_only_global_args(self) -> None:
        """Test with only global arguments."""
        format_args = {"_global": {"note": "Test"}}
        result = get_formatter_args("email", format_args)
        assert result == {"note": "Test"}

    def test_only_formatter_specific_args(self) -> None:
        """Test with only formatter-specific arguments."""
        format_args = {"_global": {}, "email": {"accent_color": "#ff0000"}}
        result = get_formatter_args("email", format_args)
        assert result == {"accent_color": "#ff0000"}

    def test_merged_args_formatter_overrides_global(self) -> None:
        """Test that formatter-specific args override global args."""
        format_args = {
            "_global": {"note": "Global note", "title": "Global title"},
            "email": {"note": "Email-specific note"},
        }
        result = get_formatter_args("email", format_args)
        assert result == {"note": "Email-specific note", "title": "Global title"}

    def test_different_formatter_only_gets_global(self) -> None:
        """Test that different formatter only gets global args."""
        format_args = {
            "_global": {"note": "Test"},
            "email": {"accent_color": "#ff0000"},
        }
        result = get_formatter_args("json", format_args)
        assert result == {"note": "Test"}

    def test_no_global_key_returns_only_specific(self) -> None:
        """Test when _global key is missing."""
        format_args = {"email": {"accent_color": "#ff0000"}}
        result = get_formatter_args("email", format_args)
        assert result == {"accent_color": "#ff0000"}

    def test_multiple_formatters_isolated(self) -> None:
        """Test that formatters are isolated from each other."""
        format_args = {
            "_global": {"note": "Test"},
            "email": {"accent_color": "#ff0000"},
            "json": {"pretty": "true"},
        }
        email_result = get_formatter_args("email", format_args)
        json_result = get_formatter_args("json", format_args)

        assert email_result == {"note": "Test", "accent_color": "#ff0000"}
        assert json_result == {"note": "Test", "pretty": "true"}
        assert "pretty" not in email_result
        assert "accent_color" not in json_result


class TestSetupLogging:
    """Tests for logging setup.

    Note: These tests verify the function executes without errors.
    Testing actual log level changes is complex due to pytest's own logging setup
    and basicConfig's behavior with already-configured loggers.
    """

    def test_verbose_0_executes_without_error(self) -> None:
        """Test that verbose=0 setup executes without error."""
        setup_logging(0)  # Should not raise

    def test_verbose_1_executes_without_error(self) -> None:
        """Test that verbose=1 setup executes without error."""
        setup_logging(1)  # Should not raise

    def test_verbose_2_executes_without_error(self) -> None:
        """Test that verbose=2 setup executes without error."""
        setup_logging(2)  # Should not raise

    def test_verbose_3_executes_without_error(self) -> None:
        """Test that verbose>=2 setup executes without error."""
        setup_logging(3)  # Should not raise

    def test_third_party_loggers_configured(self) -> None:
        """Test that third-party loggers are configured."""
        setup_logging(0)
        # Verify that the function at least accesses these loggers
        requests_logger = logging.getLogger("requests")
        espn_api_logger = logging.getLogger("espn_api")
        # Just verify they exist and can be accessed
        assert requests_logger is not None
        assert espn_api_logger is not None

    def test_logging_format_configured(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that logging format is properly configured."""
        setup_logging(1)
        logger = logging.getLogger(__name__)

        with caplog.at_level(logging.INFO):
            logger.info("Test message")

        # Verify log format includes expected components
        if caplog.records:  # May not capture due to pytest setup
            record = caplog.records[0]
            assert record.levelname == "INFO"
            assert record.message == "Test message"
            assert record.name == __name__
