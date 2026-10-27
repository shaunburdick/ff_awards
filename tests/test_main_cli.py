"""
Comprehensive tests for the main CLI module.

Tests cover argument parsing, league ID handling, format selection,
output directory mode, format arguments, and error handling.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ai_fakes import (
    FakeAIClient,
    FakeMemoryStore,
    make_division,
    make_memory_archive,
    make_narrative,
    make_regular_divisions,
    make_regular_weekly_challenges,
    make_season_challenge,
)

from ff_tracker.config import AIMemoryConfig, AISummaryConfig, FFTrackerConfig
from ff_tracker.exceptions import AIMemoryStoreError, ConfigurationError
from ff_tracker.main import build_formatter, create_parser
from ff_tracker.models import AISummaryUnavailable


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

    def test_parser_env_file_defaults_to_none(self) -> None:
        """No --env-file means the working-directory .env, which need not exist."""
        parser = create_parser()
        args = parser.parse_args(["123456"])
        assert args.env_file is None

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


class TestAISummaryWiring:
    """FR-001, AC-003, AC-004: one call per run and the Actions warning."""

    def _ai_config(self, enabled: bool = True) -> AISummaryConfig:
        return AISummaryConfig(enabled=enabled, api_key="sk-test" if enabled else "")

    def _run(
        self,
        *,
        enabled: bool = True,
        ai_summary: object = None,
        league_count: int = 1,
        output_dir: Path | None = None,
        github_actions: str | None = None,
        config_error: Exception | None = None,
    ) -> tuple[int, MagicMock, MagicMock]:
        from ff_tracker.main import main

        divisions = [
            make_division(f"League {index}", league_id=100 + index, reg_season_count=14)
            for index in range(league_count)
        ]
        argv = ["ff-tracker", "123456"]
        if output_dir is not None:
            argv += ["--output-dir", str(output_dir)]
        else:
            argv += ["--format", "json"]

        config = FFTrackerConfig(league_ids=[123456], year=2026, private=False)
        env = {"GITHUB_ACTIONS": github_actions or ""}

        with (
            patch.object(sys, "argv", argv),
            patch("ff_tracker.config.create_config", return_value=config),
            patch("ff_tracker.main.ESPNService") as espn_class,
            patch("ff_tracker.main.ChallengeCalculator"),
            patch("ff_tracker.main.WeeklyChallengeCalculator"),
            patch("ff_tracker.main.create_formatter") as formatter_factory,
            patch("ff_tracker.main.AISummaryService") as service_class,
            patch(
                "ff_tracker.main.load_ai_summary_config",
                return_value=self._ai_config(enabled),
            )
            if config_error is None
            else patch("ff_tracker.main.load_ai_summary_config", side_effect=config_error),
            patch.dict(os.environ, env, clear=False),
        ):
            espn = espn_class.return_value
            espn.load_all_divisions.return_value = divisions
            espn.current_week = 6
            service_class.return_value.generate.return_value = ai_summary
            formatter = MagicMock()
            formatter.format_output.return_value = "REPORT"
            formatter_factory.return_value = formatter
            result = main()

        return result, service_class, formatter

    def test_one_call_for_any_league_count(self) -> None:
        for count in (1, 3, 10):
            result, service, _ = self._run(ai_summary=make_narrative(), league_count=count)
            assert result == 0
            assert service.return_value.generate.call_count == 1

    def test_output_dir_mode_calls_once_and_renders_five_formats(self, tmp_path: Path) -> None:
        result, service, formatter = self._run(ai_summary=make_narrative(), output_dir=tmp_path)

        assert result == 0
        assert service.return_value.generate.call_count == 1
        assert formatter.format_output.call_count == 5
        passed = [call.kwargs["ai_summary"] for call in formatter.format_output.call_args_list]
        assert all(summary is passed[0] for summary in passed)

    def test_feature_off_makes_no_call(self) -> None:
        result, service, formatter = self._run(enabled=False)

        assert result == 0
        assert service.return_value.generate.call_count == 0
        assert formatter.format_output.call_args.kwargs["ai_summary"] is None

    def test_warning_only_inside_actions(self, capsys: pytest.CaptureFixture) -> None:
        unavailable = AISummaryUnavailable(reason="timed out after 120s")

        result, _, _ = self._run(ai_summary=unavailable, github_actions=None)
        assert result == 0
        assert "::warning::" not in capsys.readouterr().out

        result, _, _ = self._run(ai_summary=unavailable, github_actions="true")
        out = capsys.readouterr().out
        assert result == 0
        assert out.count("::warning::AI summary unavailable: timed out after 120s.") == 1

    def test_configuration_error_stops_the_run(self, capsys: pytest.CaptureFixture) -> None:
        result, service, formatter = self._run(
            config_error=ConfigurationError("AI_SUMMARY_API_KEY is required")
        )

        assert result == 1
        assert service.return_value.generate.call_count == 0
        assert formatter.format_output.call_count == 0
        assert "AI_SUMMARY_API_KEY" in capsys.readouterr().err

    def test_help_states_the_egress(self) -> None:
        help_text = create_parser().format_help()

        assert "AI Summary (optional)" in help_text
        assert "AI_SUMMARY_API_KEY" in help_text
        assert "AI_SUMMARY_BASE_URL" in help_text
        assert "never printed" in help_text
        assert "do not use it in CI" in help_text


class TestMidBodyFailureShipstheReport:
    """A provider closing mid-body must not reach main's unexpected-error branch."""

    def _run_with_failing_read(self) -> int:
        from ff_tracker.main import main

        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.side_effect = ConnectionResetError("peer reset the connection")

        config = FFTrackerConfig(league_ids=[123456], year=2026, private=False)
        with (
            patch.object(sys, "argv", ["ff-tracker", "123456"]),
            patch("ff_tracker.config.create_config", return_value=config),
            patch("ff_tracker.main.ESPNService") as espn_class,
            patch("ff_tracker.main.ChallengeCalculator") as challenge_calculator,
            patch("ff_tracker.main.WeeklyChallengeCalculator") as weekly_calculator,
            patch(
                "ff_tracker.main.load_ai_summary_config",
                return_value=AISummaryConfig(enabled=True, api_key="sk-test"),
            ),
            patch("urllib.request.urlopen", return_value=response),
            patch.dict(os.environ, {"GITHUB_ACTIONS": ""}, clear=False),
        ):
            espn = espn_class.return_value
            espn.load_all_divisions.return_value = make_regular_divisions()
            espn.current_week = 6
            challenge_calculator.return_value.calculate_all_challenges.return_value = [
                make_season_challenge()
            ]
            weekly_calculator.return_value.calculate_all_weekly_challenges.return_value = (
                make_regular_weekly_challenges()
            )
            return main()

    def test_mid_body_failure_still_ships_the_report_and_exits_zero(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        result = self._run_with_failing_read()
        out = capsys.readouterr()

        assert result == 0
        assert "Unexpected error" not in out.err
        assert (
            "AI summary unavailable: connection failed (opencode.ai). The report is unaffected."
        ) in out.out
        # The deterministic report is still there.
        assert "Fantasy Football Multi-Division Challenge Tracker" in out.out


MEMORY_CONFIG = AIMemoryConfig(enabled=True, gist_id="gist123", gist_token="ghp-test")


def _narrative_for(names: Sequence[str]) -> str:
    """A contract-valid response for leagues with these names."""
    return json.dumps(
        {
            "headline": "Headline",
            "leagues": [
                {"league": name, "paragraphs": [f"{name} had a week."], "bullets": []}
                for name in names
            ],
            "season_note": "Note.",
        }
    )


class TestMemoryWiring:
    """T207: the real service and store behind the CLI, so the counts are production's."""

    def _run(
        self,
        *,
        league_count: int = 1,
        memory: AIMemoryConfig | None = MEMORY_CONFIG,
        store: FakeMemoryStore | None = None,
        github_actions: str | None = "true",
        output_dir: Path | None = None,
        config_error: Exception | None = None,
    ) -> tuple[int, FakeAIClient, FakeMemoryStore, MagicMock]:
        from ff_tracker.main import main

        names = [f"League {index}" for index in range(league_count)]
        divisions = [
            make_division(name, league_id=100 + index, reg_season_count=14)
            for index, name in enumerate(names)
        ]
        client = FakeAIClient(response=_narrative_for(names))
        fake_store = store if store is not None else FakeMemoryStore()
        ai_config = AISummaryConfig(enabled=True, api_key="sk-test", memory=memory)

        argv = ["ff-tracker", "123456"] + (
            ["--output-dir", str(output_dir)] if output_dir is not None else ["--format", "json"]
        )
        config = FFTrackerConfig(league_ids=[123456], year=2026, private=False)
        env = {"GITHUB_ACTIONS": github_actions or ""}

        with (
            patch.object(sys, "argv", argv),
            patch("ff_tracker.config.create_config", return_value=config),
            patch("ff_tracker.main.ESPNService") as espn_class,
            patch("ff_tracker.main.ChallengeCalculator"),
            patch("ff_tracker.main.WeeklyChallengeCalculator"),
            patch("ff_tracker.main.create_formatter") as formatter_factory,
            patch("ff_tracker.main.OpenAICompatibleClient", return_value=client),
            patch("ff_tracker.main.GistMemoryStore", return_value=fake_store) as store_class,
            patch(
                "ff_tracker.main.load_ai_summary_config",
                return_value=ai_config,
            )
            if config_error is None
            else patch("ff_tracker.main.load_ai_summary_config", side_effect=config_error),
            patch.dict(os.environ, env, clear=False),
        ):
            espn = espn_class.return_value
            espn.load_all_divisions.return_value = divisions
            espn.current_week = 6
            formatter = MagicMock()
            formatter.format_output.return_value = "REPORT"
            formatter_factory.return_value = formatter
            result = main()

        return result, client, fake_store, store_class

    @pytest.mark.parametrize("league_count", [1, 3, 10])
    def test_one_provider_call_one_read_one_write(
        self, league_count: int, capsys: pytest.CaptureFixture
    ) -> None:
        result, client, store, _ = self._run(league_count=league_count)

        capsys.readouterr()
        assert result == 0
        assert len(client.requests) == 1
        assert store.read_calls == 1
        assert store.write_calls == 1

    def test_output_dir_mode_makes_the_same_calls(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        result, client, store, _ = self._run(output_dir=tmp_path)

        capsys.readouterr()
        assert result == 0
        assert len(client.requests) == 1
        assert store.read_calls == 1
        assert store.write_calls == 1
        for name in ("standings.txt", "standings.tsv", "standings.html", "standings.json"):
            assert (tmp_path / name).exists()

    def test_memory_off_makes_zero_store_calls(self, capsys: pytest.CaptureFixture) -> None:
        result, client, _, store_class = self._run(memory=None)

        capsys.readouterr()
        assert result == 0
        assert len(client.requests) == 1
        store_class.assert_not_called()

    @pytest.mark.parametrize(
        ("store", "expected"),
        [
            (
                FakeMemoryStore(
                    data=make_memory_archive(), read_errors=[AIMemoryStoreError("auth", "x")]
                ),
                1,
            ),
            (
                FakeMemoryStore(
                    data=make_memory_archive(),
                    read_errors=[AIMemoryStoreError("auth", "x")],
                    write_errors=[AIMemoryStoreError("auth", "x")],
                ),
                2,
            ),
            (FakeMemoryStore(write_errors=[AIMemoryStoreError("server", "x")]), 1),
            (FakeMemoryStore(read_errors=[AIMemoryStoreError("server", "x")]), 0),
            (FakeMemoryStore(read_errors=[AIMemoryStoreError("transport", "x")]), 0),
            (FakeMemoryStore(read_errors=[AIMemoryStoreError("timeout", "x")]), 0),
            (FakeMemoryStore(data=b"{not json"), 1),
        ],
        ids=[
            "auth-read-write-ok",
            "auth-read-and-failed-write",
            "failed-write-only",
            "server-read",
            "transport-read",
            "timeout-read",
            "unparseable-file",
        ],
    )
    def test_warning_counts_are_exact(
        self, store: FakeMemoryStore, expected: int, capsys: pytest.CaptureFixture
    ) -> None:
        result, _, _, _ = self._run(store=store)
        out = capsys.readouterr().out

        assert result == 0
        assert out.count("::warning::") == expected

    def test_no_warning_outside_actions(self, capsys: pytest.CaptureFixture) -> None:
        store = FakeMemoryStore(
            data=make_memory_archive(),
            read_errors=[AIMemoryStoreError("auth", "x")],
            write_errors=[AIMemoryStoreError("auth", "x")],
        )

        result, _, _, _ = self._run(store=store, github_actions=None)

        assert result == 0
        assert "::warning::" not in capsys.readouterr().out

    def test_memory_off_prints_no_warning(self, capsys: pytest.CaptureFixture) -> None:
        result, _, _, _ = self._run(memory=None)

        assert result == 0
        assert "::warning::" not in capsys.readouterr().out

    def test_a_configuration_error_stops_before_any_call(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        result, client, _, store_class = self._run(
            config_error=ConfigurationError("AI_MEMORY_GIST_ID is required")
        )

        captured = capsys.readouterr()
        assert result == 1
        assert client.requests == []
        store_class.assert_not_called()
        assert "AI_MEMORY_GIST_ID" in captured.err
        assert "AI summary unavailable" not in captured.out
