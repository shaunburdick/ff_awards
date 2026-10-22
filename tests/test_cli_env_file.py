"""--env-file across the three CLIs: surface, wiring and failure behaviour."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ai_fakes import make_division

from ff_tracker.config import AISummaryConfig, FFTrackerConfig
from ff_tracker.exceptions import ConfigurationError

HELP = "Path to environment file (default: .env in the working directory)"


def _parsers() -> dict[str, Callable[[], argparse.ArgumentParser]]:
    from ff_tracker.championship import create_parser as championship_parser
    from ff_tracker.main import create_parser as tracker_parser
    from ff_tracker.season_recap import create_parser as recap_parser

    return {
        "ff-tracker": tracker_parser,
        "ff-championship": championship_parser,
        "ff-season-recap": recap_parser,
    }


class TestEnvFileSurface:
    """Article IX: the three CLIs expose the same flag with the same help.

    `ff-championship` and `ff-season-recap` reuse `ff_tracker.main.create_parser`
    when their own module has no parser of its own, so the check tolerates that.
    """

    @pytest.mark.parametrize("cli", sorted(_parsers()))
    def test_flag_exists_with_the_shared_help(self, cli: str) -> None:
        parser = _parsers()[cli]()
        action = next(
            (a for a in parser._actions if "--env-file" in getattr(a, "option_strings", [])),
            None,
        )

        assert action is not None, f"{cli} does not expose --env-file"
        assert action.help == HELP
        assert action.default is None

    def test_missing_explicit_path_is_a_configuration_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "absent.env"

        with pytest.raises(ConfigurationError, match=f"Environment file not found: {missing}"):
            from ff_tracker.config import load_environment

            load_environment(missing)


class TestMainForwardsThePath:
    """main.py must pass the flag to both loaders, not just the report config."""

    def test_create_config_and_the_ai_loader_receive_the_path(self, tmp_path: Path) -> None:
        from ff_tracker.main import main

        alt = tmp_path / "alt.env"
        alt.write_text("LEAGUE_IDS=123456\n", encoding="utf-8")
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)

        with (
            patch.object(
                sys, "argv", ["ff-tracker", "--env", "--env-file", str(alt), "--format", "json"]
            ),
            patch("ff_tracker.config.create_config", return_value=config) as create_config,
            patch(
                "ff_tracker.main.load_ai_summary_config",
                return_value=AISummaryConfig(),
            ) as ai_loader,
            patch("ff_tracker.main.ESPNService") as espn_class,
            patch("ff_tracker.main.ChallengeCalculator"),
            patch("ff_tracker.main.WeeklyChallengeCalculator"),
            patch("ff_tracker.main.create_formatter") as formatter_factory,
        ):
            espn = espn_class.return_value
            espn.load_all_divisions.return_value = [make_division("League")]
            espn.current_week = 6
            formatter = MagicMock()
            formatter.format_output.return_value = "REPORT"
            formatter_factory.return_value = formatter

            assert main() == 0

        assert create_config.call_args.kwargs["env_file"] == alt
        assert ai_loader.call_args.args == (alt,)
