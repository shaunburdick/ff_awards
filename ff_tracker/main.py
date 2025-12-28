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

from .cli_utils import (
    get_formatter_args,
    parse_format_args,
    parse_league_ids_from_arg,
    setup_logging,
)
from .display import create_formatter
from .exceptions import FFTrackerError
from .models import WeeklyChallenge, WeeklyGameResult, WeeklyPlayerStats
from .services import ChallengeCalculator, ESPNService, WeeklyChallengeCalculator


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


def build_formatter(format_name: str, year: int, format_args_dict: dict[str, dict[str, str]]):
    """
    Build formatter instance with merged arguments.

    Wrapper around display.create_formatter() that handles argument merging.

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

    # Use factory to create formatter
    return create_formatter(format_name, year, merged_args)


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
                    all_leagues = [espn_service.connect_to_league(lid) for lid in config.league_ids]
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
                formatter = build_formatter(format_name, config.year, format_args_dict)
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
            formatter = build_formatter(args.format, config.year, format_args_dict)
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
