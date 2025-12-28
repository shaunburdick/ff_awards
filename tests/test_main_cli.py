"""
Comprehensive tests for the main CLI module.

Tests cover argument parsing, league ID handling, format selection,
output directory mode, format arguments, and error handling.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ff_tracker.main import build_formatter, create_parser


class TestArgumentParsing:
    """Tests for CLI argument parser configuration."""

    def test_parser_created_successfully(self) -> None:
        """Test that parser can be created without errors."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "pytest"  # pytest sets this

    def test_parser_has_league_id_argument(self) -> None:
        """Test that parser includes league_id positional argument."""
        parser = create_parser()
        # Parse with single league ID
        args = parser.parse_args(["123456"])
        assert args.league_id == "123456"

    def test_parser_league_id_optional_with_env_flag(self) -> None:
        """Test that league_id is optional when using --env flag."""
        parser = create_parser()
        args = parser.parse_args(["--env"])
        assert args.league_id is None
        assert args.env is True

    def test_parser_has_env_flag(self) -> None:
        """Test that parser includes --env flag."""
        parser = create_parser()
        args = parser.parse_args(["--env"])
        assert args.env is True

    def test_parser_has_year_argument(self) -> None:
        """Test that parser includes --year argument."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--year", "2024"])
        assert args.year == 2024

    def test_parser_has_week_argument(self) -> None:
        """Test that parser includes --week argument."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--week", "15"])
        assert args.week == 15

    def test_parser_has_private_flag(self) -> None:
        """Test that parser includes --private flag."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--private"])
        assert args.private is True

    def test_parser_has_format_argument(self) -> None:
        """Test that parser includes --format argument."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format", "email"])
        assert args.format == "email"

    def test_parser_format_default_is_console(self) -> None:
        """Test that default format is console."""
        parser = create_parser()
        args = parser.parse_args(["123456"])
        assert args.format == "console"

    def test_parser_has_output_dir_argument(self) -> None:
        """Test that parser includes --output-dir argument."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--output-dir", "./reports"])
        assert args.output_dir == Path("./reports")

    def test_parser_has_format_arg_argument(self) -> None:
        """Test that parser includes --format-arg argument."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format-arg", "note=Test"])
        assert args.format_args == ["note=Test"]

    def test_parser_format_arg_can_be_repeated(self) -> None:
        """Test that --format-arg can be specified multiple times."""
        parser = create_parser()
        args = parser.parse_args(
            ["123456", "--format-arg", "note=Test", "--format-arg", "email.accent_color=#ff0000"]
        )
        assert args.format_args == ["note=Test", "email.accent_color=#ff0000"]

    def test_parser_has_env_file_argument(self) -> None:
        """Test that parser includes --env-file argument."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--env-file", ".env.test"])
        assert args.env_file == Path(".env.test")

    def test_parser_env_file_default_is_dotenv(self) -> None:
        """Test that default env-file is .env."""
        parser = create_parser()
        args = parser.parse_args(["123456"])
        assert args.env_file == Path(".env")

    def test_parser_has_verbose_flag(self) -> None:
        """Test that parser includes --verbose flag."""
        parser = create_parser()
        args = parser.parse_args(["123456", "-v"])
        assert args.verbose == 1

    def test_parser_verbose_can_be_repeated(self) -> None:
        """Test that --verbose can be specified multiple times."""
        parser = create_parser()
        args = parser.parse_args(["123456", "-vv"])
        assert args.verbose == 2


class TestFormatSelection:
    """Tests for format argument validation."""

    def test_console_format_accepted(self) -> None:
        """Test that console format is accepted."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format", "console"])
        assert args.format == "console"

    def test_sheets_format_accepted(self) -> None:
        """Test that sheets format is accepted."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format", "sheets"])
        assert args.format == "sheets"

    def test_email_format_accepted(self) -> None:
        """Test that email format is accepted."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format", "email"])
        assert args.format == "email"

    def test_json_format_accepted(self) -> None:
        """Test that json format is accepted."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format", "json"])
        assert args.format == "json"

    def test_markdown_format_accepted(self) -> None:
        """Test that markdown format is accepted."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format", "markdown"])
        assert args.format == "markdown"

    def test_invalid_format_raises_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test that invalid format raises SystemExit."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["123456", "--format", "invalid"])


class TestLeagueIDHandling:
    """Tests for league ID argument handling."""

    def test_single_league_id_parsed(self) -> None:
        """Test that single league ID is parsed correctly."""
        parser = create_parser()
        args = parser.parse_args(["123456"])
        assert args.league_id == "123456"
        assert args.env is False

    def test_multiple_league_ids_parsed_as_string(self) -> None:
        """Test that comma-separated league IDs are parsed as string."""
        parser = create_parser()
        args = parser.parse_args(["123456,789012,345678"])
        assert args.league_id == "123456,789012,345678"
        assert args.env is False

    def test_env_flag_sets_env_true(self) -> None:
        """Test that --env flag sets env to True."""
        parser = create_parser()
        args = parser.parse_args(["--env"])
        assert args.env is True
        assert args.league_id is None

    def test_league_id_with_private_flag(self) -> None:
        """Test that league ID can be combined with --private."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--private"])
        assert args.league_id == "123456"
        assert args.private is True

    def test_env_flag_with_private_flag(self) -> None:
        """Test that --env can be combined with --private."""
        parser = create_parser()
        args = parser.parse_args(["--env", "--private"])
        assert args.env is True
        assert args.private is True


class TestOutputDirectory:
    """Tests for output directory mode."""

    def test_output_dir_creates_path_object(self) -> None:
        """Test that --output-dir creates Path object."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--output-dir", "./reports"])
        assert isinstance(args.output_dir, Path)
        assert args.output_dir == Path("./reports")

    def test_output_dir_with_absolute_path(self) -> None:
        """Test that --output-dir accepts absolute path."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--output-dir", "/tmp/reports"])
        assert args.output_dir == Path("/tmp/reports")

    def test_output_dir_with_format_arg(self) -> None:
        """Test that --output-dir can be combined with --format-arg."""
        parser = create_parser()
        args = parser.parse_args(
            ["123456", "--output-dir", "./reports", "--format-arg", "note=Test"]
        )
        assert args.output_dir == Path("./reports")
        assert args.format_args == ["note=Test"]

    def test_output_dir_default_is_none(self) -> None:
        """Test that output_dir defaults to None."""
        parser = create_parser()
        args = parser.parse_args(["123456"])
        assert args.output_dir is None


class TestFormatArguments:
    """Tests for format argument parsing."""

    def test_format_arg_single_global(self) -> None:
        """Test that single global format arg is parsed."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format-arg", "note=Test message"])
        assert args.format_args == ["note=Test message"]

    def test_format_arg_formatter_specific(self) -> None:
        """Test that formatter-specific format arg is parsed."""
        parser = create_parser()
        args = parser.parse_args(["123456", "--format-arg", "email.accent_color=#ff0000"])
        assert args.format_args == ["email.accent_color=#ff0000"]

    def test_format_arg_multiple_args(self) -> None:
        """Test that multiple format args are parsed."""
        parser = create_parser()
        args = parser.parse_args(
            [
                "123456",
                "--format-arg",
                "note=Test",
                "--format-arg",
                "email.accent_color=#ff0000",
                "--format-arg",
                "json.pretty=true",
            ]
        )
        assert args.format_args == ["note=Test", "email.accent_color=#ff0000", "json.pretty=true"]

    def test_format_arg_default_is_none(self) -> None:
        """Test that format_args defaults to None."""
        parser = create_parser()
        args = parser.parse_args(["123456"])
        assert args.format_args is None


class TestBuildFormatter:
    """Tests for build_formatter function."""

    def test_build_formatter_console(self) -> None:
        """Test building console formatter."""
        with patch("ff_tracker.main.create_formatter") as mock_create:
            mock_formatter = MagicMock()
            mock_create.return_value = mock_formatter

            result = build_formatter("console", 2024, {})

            mock_create.assert_called_once_with("console", 2024, {})
            assert result == mock_formatter

    def test_build_formatter_email(self) -> None:
        """Test building email formatter."""
        with patch("ff_tracker.main.create_formatter") as mock_create:
            mock_formatter = MagicMock()
            mock_create.return_value = mock_formatter

            result = build_formatter("email", 2024, {})

            mock_create.assert_called_once_with("email", 2024, {})
            assert result == mock_formatter

    def test_build_formatter_with_global_args(self) -> None:
        """Test building formatter with global format args."""
        with patch("ff_tracker.main.create_formatter") as mock_create:
            mock_formatter = MagicMock()
            mock_create.return_value = mock_formatter

            format_args_dict = {"_global": {"note": "Test"}}
            result = build_formatter("console", 2024, format_args_dict)

            # Should merge global args for console formatter
            mock_create.assert_called_once_with("console", 2024, {"note": "Test"})
            assert result == mock_formatter

    def test_build_formatter_with_specific_args(self) -> None:
        """Test building formatter with formatter-specific args."""
        with patch("ff_tracker.main.create_formatter") as mock_create:
            mock_formatter = MagicMock()
            mock_create.return_value = mock_formatter

            format_args_dict = {"_global": {"note": "Test"}, "email": {"accent_color": "#ff0000"}}
            result = build_formatter("email", 2024, format_args_dict)

            # Should merge global + email-specific args
            mock_create.assert_called_once_with(
                "email", 2024, {"note": "Test", "accent_color": "#ff0000"}
            )
            assert result == mock_formatter

    def test_build_formatter_specific_overrides_global(self) -> None:
        """Test that formatter-specific args override global args."""
        with patch("ff_tracker.main.create_formatter") as mock_create:
            mock_formatter = MagicMock()
            mock_create.return_value = mock_formatter

            format_args_dict = {"_global": {"note": "Global note"}, "email": {"note": "Email note"}}
            result = build_formatter("email", 2024, format_args_dict)

            # Email-specific note should override global
            mock_create.assert_called_once_with("email", 2024, {"note": "Email note"})
            assert result == mock_formatter


class TestMainFunction:
    """Tests for main() function execution flow."""

    def test_main_requires_league_id_or_env(self, capsys: pytest.CaptureFixture) -> None:
        """Test that main() requires either league_id or --env flag."""
        with patch.object(sys, "argv", ["ff-tracker"]):
            from ff_tracker.main import main

            # parser.error() calls sys.exit(2)
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 2
            captured = capsys.readouterr()
            assert "Either provide a league_id or use --env flag" in captured.err

    def test_main_with_invalid_format_arg_syntax(self, capsys: pytest.CaptureFixture) -> None:
        """Test that main() handles invalid format arg syntax."""
        with patch.object(sys, "argv", ["ff-tracker", "123456", "--format-arg", "invalid"]):
            from ff_tracker.main import main

            result = main()

            assert result == 1
            captured = capsys.readouterr()
            assert "Error parsing format arguments" in captured.err

    def test_main_keyboard_interrupt_handling(self, capsys: pytest.CaptureFixture) -> None:
        """Test that main() handles KeyboardInterrupt gracefully."""
        with patch.object(sys, "argv", ["ff-tracker", "123456"]):
            # Patch the config module's create_config
            with patch("ff_tracker.config.create_config") as mock_config:
                mock_config.side_effect = KeyboardInterrupt()

                from ff_tracker.main import main

                result = main()

                assert result == 1
                captured = capsys.readouterr()
                assert "cancelled by user" in captured.err

    def test_main_handles_ff_tracker_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test that main() handles FFTrackerError gracefully."""
        with patch.object(sys, "argv", ["ff-tracker", "123456"]):
            # Patch the config module's create_config
            with patch("ff_tracker.config.create_config") as mock_config:
                from ff_tracker.exceptions import FFTrackerError

                mock_config.side_effect = FFTrackerError("Test error")

                from ff_tracker.main import main

                result = main()

                assert result == 1
                captured = capsys.readouterr()
                assert "Error: Test error" in captured.err

    def test_main_handles_unexpected_error(self, capsys: pytest.CaptureFixture) -> None:
        """Test that main() handles unexpected exceptions gracefully."""
        with patch.object(sys, "argv", ["ff-tracker", "123456"]):
            # Patch the config module's create_config
            with patch("ff_tracker.config.create_config") as mock_config:
                mock_config.side_effect = RuntimeError("Unexpected error")

                from ff_tracker.main import main

                result = main()

                assert result == 1
                captured = capsys.readouterr()
                assert "Unexpected error" in captured.err


class TestArgumentValidation:
    """Tests for argument validation logic in main()."""

    def test_main_rejects_both_league_id_and_env(self, capsys: pytest.CaptureFixture) -> None:
        """Test that providing both league_id and --env is rejected."""
        with patch.object(sys, "argv", ["ff-tracker", "123456", "--env"]):
            from ff_tracker.main import main

            # parser.error() calls sys.exit(2)
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 2
            captured = capsys.readouterr()
            assert "Cannot use both league_id and --env flag" in captured.err

    def test_main_calls_setup_logging(self) -> None:
        """Test that main() calls setup_logging with verbose level."""
        with patch.object(sys, "argv", ["ff-tracker", "123456", "-vv"]):
            with patch("ff_tracker.main.setup_logging") as mock_setup:
                # Patch the config module's create_config
                with patch("ff_tracker.config.create_config") as mock_config:
                    # Raise error to short-circuit execution
                    from ff_tracker.exceptions import FFTrackerError

                    mock_config.side_effect = FFTrackerError("Stop")

                    from ff_tracker.main import main

                    main()

                    # Should have called setup_logging with verbose=2
                    mock_setup.assert_called_once_with(2)

    def test_main_parses_league_ids_from_arg(self) -> None:
        """Test that main() calls parse_league_ids_from_arg for CLI input."""
        with patch.object(sys, "argv", ["ff-tracker", "123456,789012"]):
            with patch("ff_tracker.main.parse_league_ids_from_arg") as mock_parse:
                mock_parse.return_value = [123456, 789012]
                # Patch the config module's create_config
                with patch("ff_tracker.config.create_config") as mock_config:
                    # Raise error to short-circuit execution
                    from ff_tracker.exceptions import FFTrackerError

                    mock_config.side_effect = FFTrackerError("Stop")

                    from ff_tracker.main import main

                    main()

                    # Should have called parse_league_ids_from_arg
                    mock_parse.assert_called_once_with("123456,789012")
