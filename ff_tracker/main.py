"""
Main CLI entry point for Fantasy Football Challenge Tracker.

Usage:
    uv run ff-tracker LEAGUE_ID [--year YEAR] [--private] [--format FORMAT]
    uv run ff-tracker LEAGUE_ID1,LEAGUE_ID2,LEAGUE_ID3 [--year YEAR] [--private] [--format FORMAT]

Examples:
    uv run ff-tracker 123456 --year 2024
    uv run ff-tracker 123456 --private --format email
    uv run ff-tracker 123456789,987654321,678998765 --format sheets
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .display import BaseFormatter, ConsoleFormatter, EmailFormatter, JsonFormatter, SheetsFormatter
from .exceptions import FFTrackerError
from .services import ChallengeCalculator, ESPNService


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


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Fantasy Football Multi-Division Challenge Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 123456                                      # Single public league
  %(prog)s 123456 --year 2024                          # Specific year
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

Multi-Output Mode:
  Use --output-dir to generate all formats in a single execution:
    - standings.txt  (console format)
    - standings.tsv  (sheets format)
    - standings.html (email format)
    - standings.json (json format)

Private League Setup:
  Create a .env file with:
    ESPN_S2=your_espn_s2_cookie
    SWID=your_swid_cookie
        """
    )

    parser.add_argument(
        "league_id",
        type=str,
        nargs='?',  # Make league_id optional
        help="ESPN Fantasy Football League ID(s) - single ID or comma-separated (e.g., 123456 or 123456,789012,345678). Alternative: use --env for LEAGUE_IDS from environment"
    )

    parser.add_argument(
        "--env",
        action="store_true",
        help="Load league IDs from LEAGUE_IDS environment variable"
    )

    parser.add_argument(
        "--year",
        type=int,
        help="Fantasy season year (default: current year)"
    )

    parser.add_argument(
        "--private",
        action="store_true",
        help="Access private league (requires ESPN_S2 and SWID in .env)"
    )

    parser.add_argument(
        "--format",
        choices=["console", "sheets", "email", "json"],
        default="console",
        help="Output format (default: console). Ignored if --output-dir is specified."
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write all output formats. When specified, generates all formats automatically."
    )

    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to environment file (default: .env)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Enable verbose logging output (-v for INFO, -vv for DEBUG)"
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
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Reduce noise from third-party libraries unless in debug mode
    if verbose < 2:
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('espn_api').setLevel(logging.WARNING)


def create_formatter(format_name: str, year: int) -> BaseFormatter:
    """Create formatter instance based on format name."""
    if format_name == "console":
        return ConsoleFormatter(year)
    elif format_name == "sheets":
        return SheetsFormatter(year)
    elif format_name == "email":
        return EmailFormatter(year)
    elif format_name == "json":
        return JsonFormatter(year)
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

        # Load configuration
        from .config import create_config
        if args.env:
            # Load multiple leagues from environment
            config = create_config(
                use_env=True,
                year=args.year,
                private=args.private
            )
        else:
            # Parse league IDs from command line (single or comma-separated)
            league_ids = parse_league_ids_from_arg(args.league_id)
            config = create_config(
                league_ids=league_ids,
                year=args.year,
                private=args.private,
                use_env=False
            )

        # Initialize services
        espn_service = ESPNService(config)
        challenge_calculator = ChallengeCalculator()

        # Connect to ESPN and extract data (single API call)
        with espn_service:
            divisions = espn_service.load_all_divisions()
            challenges = challenge_calculator.calculate_all_challenges(divisions)

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
            }

            # Generate each format and write to file
            for format_name, file_path in format_files.items():
                formatter = create_formatter(format_name, config.year)
                output = formatter.format_output(divisions, challenges, espn_service.current_week)
                file_path.write_text(output, encoding="utf-8")
                print(f"Generated {format_name} output: {file_path}")

            return 0
        else:
            # Single output mode: print to stdout
            formatter = create_formatter(args.format, config.year)
            output = formatter.format_output(divisions, challenges, espn_service.current_week)
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
