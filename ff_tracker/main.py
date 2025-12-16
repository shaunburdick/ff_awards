"""
Main CLI entry point for Fantasy Football Challenge Tracker.

Usage:
    uv run ff-tracker LEAGUE_ID [--year YEAR] [--private] [--format FORMAT]
    uv run ff-tracker LEAGUE_ID1,LEAGUE_ID2,LEAGUE_ID3 [--year YEAR] [--private] [--format FORMAT]

Examples:
    uv run ff-tracker 123456 --year 2024
    uv run ff-tracker 123456 --private --format email
    uv run ff-tracker 123456789,987654321,678998765 --format sheets
    uv run ff-tracker 123456 --format markdown > report.md
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .display import (
    BaseFormatter,
    ConsoleFormatter,
    EmailFormatter,
    JsonFormatter,
    MarkdownFormatter,
    SheetsFormatter,
)
from .exceptions import FFTrackerError
from .models import WeeklyChallenge, WeeklyGameResult, WeeklyPlayerStats
from .services import ChallengeCalculator, ESPNService, WeeklyChallengeCalculator


def parse_league_ids_from_arg(league_id_arg: str) -> list[int]:
    """
    Parse league IDs from command line argument.

    Args:
        league_id_arg: Single ID or comma-separated IDs (e.g., "123456" or "123456,789012,345678")

    Returns:
        List of league IDs parsed from the argument.

    Raises:
        ValueError: If any league ID is not a valid integer.
    """
    try:
        league_ids = [int(id_str.strip()) for id_str in league_id_arg.split(",") if id_str.strip()]
        if not league_ids:
            raise ValueError("No valid league IDs found")
        return league_ids
    except ValueError as e:
        raise ValueError(
            f"Error parsing league IDs: {e}. "
            f"Format should be a single ID (123456) or comma-separated IDs (123456,789012,345678)"
        ) from e


def parse_format_args(args_list: list[str] | None) -> dict[str, dict[str, str]]:
    """
    Parse format arguments into nested dictionary structure.

    Supports two syntaxes:
    - Global: "key=value" -> {"_global": {"key": "value"}}
    - Formatter-specific: "formatter.key=value" -> {"formatter": {"key": "value"}}

    Global args apply to all formatters. Formatter-specific args override globals.

    Args:
        args_list: List of format argument strings from CLI

    Returns:
        Nested dict with "_global" key and formatter-specific keys

    Raises:
        ValueError: If argument format is invalid

    Examples:
        >>> parse_format_args(["note=Test", "email.accent_color=#ff0000"])
        {"_global": {"note": "Test"}, "email": {"accent_color": "#ff0000"}}
    """
    if not args_list:
        return {}

    result: dict[str, dict[str, str]] = {"_global": {}}

    for arg in args_list:
        if "=" not in arg:
            raise ValueError(
                f"Invalid format argument: '{arg}'. "
                f"Must be in format: key=value or formatter.key=value"
            )

        key, value = arg.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise ValueError(f"Empty key in format argument: '{arg}'")

        # Check if formatter-specific (contains dot)
        if "." in key:
            parts = key.split(".", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(
                    f"Invalid formatter-specific argument: '{arg}'. Must be: formatter.key=value"
                )

            formatter, arg_key = parts
            if formatter not in result:
                result[formatter] = {}
            result[formatter][arg_key] = value
        else:
            # Global argument
            result["_global"][key] = value

    return result


def get_formatter_args(
    format_name: str, format_args_dict: dict[str, dict[str, str]]
) -> dict[str, str]:
    """
    Get merged arguments for a specific formatter.

    Merges global args with formatter-specific args, with formatter-specific
    taking precedence.

    Args:
        format_name: Name of the formatter (e.g., "email", "json")
        format_args_dict: Parsed format arguments dict

    Returns:
        Merged dictionary of arguments for this formatter
    """
    merged_args = dict(format_args_dict.get("_global", {}))
    merged_args.update(format_args_dict.get(format_name, {}))
    return merged_args


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Fantasy Football Multi-Division Challenge Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 123456                                      # Single public league
  %(prog)s 123456 --year 2024                          # Specific year
  %(prog)s 123456 --year 2024 --week 10                # Historical week 10 from 2024
  %(prog)s 123456 --week 15 --private                  # Test week 15 playoff bracket
  %(prog)s 123456 --private                            # Private league (requires .env)
  %(prog)s 123456789,987654321,678998765               # Multiple leagues via CLI
  %(prog)s --env                                       # Multiple leagues from LEAGUE_IDS in .env
  %(prog)s 123456 --format email                       # HTML email output
  %(prog)s 123456 --format sheets                      # TSV for Google Sheets
  %(prog)s 123456789,987654321 --output-dir ./reports  # Multiple leagues, all formats

Output Formats:
  console   Human-readable tables (default)
  sheets    Tab-separated values for Google Sheets
  email     Mobile-friendly HTML for email reports
  json      Structured JSON data for further processing
  markdown  Markdown format for GitHub, Slack, Discord, etc.

Multi-Output Mode:
  Use --output-dir to generate all formats in a single execution:
    - standings.txt  (console format)
    - standings.tsv  (sheets format)
    - standings.html (email format)
    - standings.json (json format)
    - standings.md   (markdown format)

Private League Setup:
  Create a .env file with:
    ESPN_S2=your_espn_s2_cookie
    SWID=your_swid_cookie
        """,
    )

    parser.add_argument(
        "league_id",
        type=str,
        nargs="?",  # Make league_id optional
        help="ESPN Fantasy Football League ID(s) - single ID or comma-separated (e.g., 123456 or 123456,789012,345678). Alternative: use --env for LEAGUE_IDS from environment",
    )

    parser.add_argument(
        "--env", action="store_true", help="Load league IDs from LEAGUE_IDS environment variable"
    )

    parser.add_argument("--year", type=int, help="Fantasy season year (default: current year)")

    parser.add_argument(
        "--week",
        type=int,
        help=(
            "Override current week detection (1-18). "
            "Acts as a snapshot in time - shows data as it would appear at that week. "
            "Useful for: reviewing historical weeks, testing playoff scenarios, debugging. "
            "Can be combined with --year. Note: Cannot specify future weeks."
        ),
    )

    parser.add_argument(
        "--private",
        action="store_true",
        help="Access private league (requires ESPN_S2 and SWID in .env)",
    )

    parser.add_argument(
        "--format",
        choices=["console", "sheets", "email", "json", "markdown"],
        default="console",
        help="Output format (default: console). Ignored if --output-dir is specified.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write all output formats. When specified, generates all formats automatically.",
    )

    parser.add_argument(
        "--format-arg",
        action="append",
        dest="format_args",
        metavar="KEY=VALUE",
        help="""Pass optional arguments to formatters (can be specified multiple times).

Syntax:
  key=value           Global arg (applies to all formatters)
  formatter.key=value Formatter-specific arg (overrides global)

Common Arguments:
  note=TEXT           Display an alert/notice at top of output

Email-Specific:
  email.accent_color=HEX    Hex color for highlights (default: #ffc107)
  email.max_teams=N         Max teams in overall rankings (default: 20)

Markdown-Specific:
  markdown.include_toc=BOOL Include table of contents (default: false)

JSON-Specific:
  json.pretty=BOOL          Pretty-print with indentation (default: true)

Examples:
  --format-arg note="Season ends Week 14!"
  --format-arg email.accent_color="#ff0000"
  --format-arg json.pretty="false"
        """,
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to environment file (default: .env)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Enable verbose logging output (-v for INFO, -vv for DEBUG)",
    )

    return parser


def setup_logging(verbose: int = 0) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbose: 0 = WARNING only, 1 = INFO, 2+ = DEBUG
    """
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:  # verbose >= 2
        level = logging.DEBUG

    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    # Reduce noise from third-party libraries unless in debug mode
    if verbose < 2:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("espn_api").setLevel(logging.WARNING)


def create_formatter(
    format_name: str, year: int, format_args_dict: dict[str, dict[str, str]]
) -> BaseFormatter:
    """
    Create formatter instance based on format name with merged arguments.

    Args:
        format_name: Name of the formatter to create
        year: Fantasy season year
        format_args_dict: Parsed format arguments dictionary

    Returns:
        Configured formatter instance

    Raises:
        ValueError: If format name is unknown
    """
    # Get merged args for this specific formatter
    merged_args = get_formatter_args(format_name, format_args_dict)

    if format_name == "console":
        return ConsoleFormatter(year, merged_args)
    elif format_name == "sheets":
        return SheetsFormatter(year, merged_args)
    elif format_name == "email":
        return EmailFormatter(year, merged_args)
    elif format_name == "json":
        return JsonFormatter(year, merged_args)
    elif format_name == "markdown":
        return MarkdownFormatter(year, merged_args)
    else:
        raise ValueError(f"Unknown format: {format_name}")


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging based on verbosity
    setup_logging(args.verbose)

    try:
        # Validate arguments
        if not args.league_id and not args.env:
            parser.error("Either provide a league_id or use --env flag")

        if args.league_id and args.env:
            parser.error("Cannot use both league_id and --env flag")

        # Parse format arguments
        try:
            format_args_dict = parse_format_args(args.format_args)
        except ValueError as e:
            print(f"Error parsing format arguments: {e}", file=sys.stderr)
            return 1

        # Load configuration
        from .config import create_config

        if args.env:
            # Load multiple leagues from environment
            config = create_config(
                use_env=True, year=args.year, private=args.private, week=args.week
            )
        else:
            # Parse league IDs from command line (single or comma-separated)
            league_ids = parse_league_ids_from_arg(args.league_id)
            config = create_config(
                league_ids=league_ids,
                year=args.year,
                private=args.private,
                use_env=False,
                week=args.week,
            )

        # Initialize services
        espn_service = ESPNService(config)
        challenge_calculator = ChallengeCalculator()
        weekly_calculator = WeeklyChallengeCalculator()

        # Connect to ESPN and extract data (single API call)
        with espn_service:
            divisions = espn_service.load_all_divisions()
            challenges = challenge_calculator.calculate_all_challenges(divisions)

            # Check if Championship Week and build leaderboard
            championship = None
            if divisions and divisions[0].is_playoff_mode:
                # We're in playoffs - check if Championship Week
                # Reconnect to first league to check playoff round
                test_league = espn_service.connect_to_league(config.league_ids[0])
                try:
                    playoff_round = espn_service.get_playoff_round(test_league)
                    if playoff_round == "Championship Week":
                        # Build championship leaderboard
                        logging.info("Championship Week detected - building leaderboard")
                        all_leagues = [
                            espn_service.connect_to_league(lid) for lid in config.league_ids
                        ]
                        division_names = [div.name for div in divisions]
                        championship = espn_service.build_championship_leaderboard(
                            all_leagues, division_names, test_league.current_week
                        )
                except Exception as e:
                    logging.warning(f"Could not build championship leaderboard: {e}")
                    # Continue without championship - not fatal

            # Calculate weekly challenges if we have weekly data
            weekly_challenges: list[WeeklyChallenge] = []
            if espn_service.current_week and espn_service.current_week > 0:
                # Combine all weekly games and players from all divisions
                all_weekly_games: list[WeeklyGameResult] = []
                all_weekly_players: list[WeeklyPlayerStats] = []
                for division in divisions:
                    all_weekly_games.extend(division.weekly_games)
                    all_weekly_players.extend(division.weekly_players)

                # Calculate weekly challenges if we have data
                if all_weekly_games or all_weekly_players:
                    try:
                        weekly_challenges = weekly_calculator.calculate_all_weekly_challenges(
                            all_weekly_games, all_weekly_players, espn_service.current_week
                        )
                    except Exception as e:
                        logging.warning(f"Could not calculate weekly challenges: {e}")
                        # Continue without weekly challenges - not fatal

        # Handle output based on mode
        if args.output_dir:
            # Multi-output mode: generate all formats to files
            output_dir = args.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            # Define format-to-filename mapping
            format_files = {
                "console": output_dir / "standings.txt",
                "sheets": output_dir / "standings.tsv",
                "email": output_dir / "standings.html",
                "json": output_dir / "standings.json",
                "markdown": output_dir / "standings.md",
            }

            # Generate each format and write to file
            for format_name, file_path in format_files.items():
                formatter = create_formatter(format_name, config.year, format_args_dict)
                output = formatter.format_output(
                    divisions,
                    challenges,
                    weekly_challenges if weekly_challenges else None,
                    espn_service.current_week,
                    championship,
                )
                file_path.write_text(output, encoding="utf-8")
                print(f"Generated {format_name} output: {file_path}")

            return 0
        else:
            # Single output mode: print to stdout
            formatter = create_formatter(args.format, config.year, format_args_dict)
            output = formatter.format_output(
                divisions,
                challenges,
                weekly_challenges if weekly_challenges else None,
                espn_service.current_week,
                championship,
            )
            print(output)
            return 0

    except FFTrackerError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
