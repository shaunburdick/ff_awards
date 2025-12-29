"""
Season Recap CLI for Fantasy Football Challenge Tracker.

This script generates comprehensive end-of-season summaries including:
- Regular season standings and division champions
- All 5 season-long challenge results
- Playoff brackets (Semifinals and Finals)
- Championship results (Week 17 overall winner)

Usage:
    uv run ff-season-recap --env --format console
    uv run ff-season-recap 123456,789012,345678 --format email
    uv run ff-season-recap --env --output-dir ./season-recap  # Generate all formats
    uv run ff-season-recap --env --force  # Generate partial recap (incomplete season)

Examples:
    uv run ff-season-recap --env                             # Full season summary
    uv run ff-season-recap --env --format email > recap.html
    uv run ff-season-recap --env --output-dir ./reports      # All formats at once
    uv run ff-season-recap --env --force                     # Partial recap (testing)
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
from .config import create_config
from .display.factory import create_season_recap_formatter
from .exceptions import FFTrackerError, SeasonIncompleteError
from .services.season_recap_service import SeasonRecapService

# Logger for this module
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Fantasy Football Season Recap Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --env                                    # Complete season summary
  %(prog)s 123456,789012,345678 --format email      # Email format with league IDs
  %(prog)s --env --output-dir ./season-recap        # Generate all formats at once
  %(prog)s --env --force                            # Partial recap (incomplete season)
  %(prog)s --env --year 2023                        # Historical season recap

Output Content:
  Regular Season:
    - Division champions with records
    - Complete final standings
    - All 5 season-long challenge winners

  Playoffs:
    - Semifinals matchups (all divisions)
    - Finals matchups (all divisions)

  Championship:
    - Week 17 leaderboard (division winners)
    - Overall champion

Formats:
  console        Human-readable tables with emojis (default)
  sheets         TSV format for Google Sheets
  email          Mobile-friendly HTML for email
  json           Structured JSON for APIs and archival
  markdown       Markdown for GitHub/Slack/Discord

Multi-Output Mode:
  Use --output-dir to generate all 5 formats in a single execution.
  Files created: season-recap.txt, season-recap.tsv, season-recap.html,
                 season-recap.json, season-recap.md

Force Mode:
  Use --force to generate partial recaps before season completes.
  Useful for testing and generating reports during playoffs.
  Will include all available data with clear warnings for missing sections.

Environment Variables:
  LEAGUE_IDS     Comma-separated league IDs (use with --env)
  ESPN_S2        ESPN authentication cookie (for private leagues)
  SWID           ESPN SWID cookie (for private leagues)
""",
    )

    # League ID argument (required unless --env is used)
    parser.add_argument(
        "league_ids",
        nargs="?",
        help="ESPN league IDs (comma-separated: 123456,789012,345678)",
    )

    parser.add_argument(
        "--env",
        action="store_true",
        help="Load league IDs from LEAGUE_IDS environment variable",
    )

    parser.add_argument(
        "--year",
        type=int,
        help="Fantasy season year (default: current year)",
    )

    parser.add_argument(
        "--private",
        action="store_true",
        help="Use private league authentication (requires ESPN_S2 and SWID env vars)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Generate partial recap even if season incomplete (for testing)",
    )

    parser.add_argument(
        "--format",
        choices=["console", "sheets", "email", "json", "markdown"],
        default="console",
        help="Output format (default: console). Ignored if --output-dir is specified.",
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

Markdown-Specific:
  markdown.include_toc=BOOL Include table of contents (default: false)

JSON-Specific:
  json.pretty=BOOL          Pretty-print with indentation (default: true)

Examples:
  --format-arg note="Official 2024 Season Recap"
  --format-arg email.accent_color="#ff0000"
  --format-arg json.pretty="false"
        """,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write all output formats. When specified, generates all formats automatically.",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (very verbose)",
    )

    return parser


def main() -> int:
    """
    Main entry point for season recap CLI.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging (convert flags to verbosity level: 0=WARNING, 1=INFO, 2=DEBUG)
    verbose_level = 2 if args.debug else (1 if args.verbose else 0)
    setup_logging(verbose_level)

    try:
        # Validate arguments
        if not args.league_ids and not args.env:
            parser.error("Either provide league_ids or use --env flag")

        if args.league_ids and args.env:
            parser.error("Cannot use both league_ids and --env flag")

        # Parse format arguments
        format_args_dict = parse_format_args(args.format_args or [])

        # Create configuration
        if args.env:
            # Load multiple leagues from environment
            config = create_config(
                use_env=True,
                year=args.year,
                private=args.private,
            )
        else:
            # Parse league IDs from command line (single or comma-separated)
            league_ids = parse_league_ids_from_arg(args.league_ids)
            config = create_config(
                league_ids=league_ids,
                year=args.year,
                private=args.private,
                use_env=False,
            )

        logger.info(
            f"Generating season recap for {len(config.league_ids)} division(s), year {config.year}"
        )

        # Create season recap service
        recap_service = SeasonRecapService(config)

        # Generate season summary
        try:
            season_summary = recap_service.generate_season_summary(force=args.force)

            if args.force and not season_summary.is_complete:
                logger.warning("⚠️  Generated PARTIAL season recap (--force mode)")

        except SeasonIncompleteError as e:
            logger.error(f"❌ {e.message}")
            logger.error(
                f"   Current week: {e.current_week}, Championship week: {e.championship_week}"
            )
            logger.error("   Use --force to generate partial recap.")
            return 1

        # Parse format arguments
        format_args_dict = parse_format_args(args.format_args or [])

        logger.info("✅ Season summary generated successfully")
        logger.info(f"   Year: {season_summary.year}")
        logger.info(f"   Divisions: {season_summary.total_divisions}")
        if season_summary.championship and season_summary.overall_champion:
            logger.info(f"   🏆 Champion: {season_summary.overall_champion.team_name}")

        # Multi-output mode
        if args.output_dir:
            logger.info(f"📁 Multi-output mode: Writing all formats to {args.output_dir}")
            args.output_dir.mkdir(parents=True, exist_ok=True)

            # Generate all formats
            formats_to_generate = ["console", "json", "sheets", "markdown", "email"]
            for format_name in formats_to_generate:
                try:
                    # Get merged args for this specific formatter
                    merged_args = get_formatter_args(format_name, format_args_dict)

                    # Create formatter
                    formatter = create_season_recap_formatter(format_name, config.year, merged_args)

                    # Generate output
                    output = formatter.format(season_summary)

                    # Write to file
                    file_ext = {
                        "console": "txt",
                        "json": "json",
                        "sheets": "tsv",
                        "markdown": "md",
                        "email": "html",
                    }[format_name]
                    output_path = args.output_dir / f"season-recap.{file_ext}"
                    output_path.write_text(output)
                    logger.info(f"   ✅ Generated {format_name}: {output_path}")

                except Exception as e:
                    logger.error(f"   ❌ Failed to generate {format_name}: {e}")
                    if args.debug:
                        logger.exception("Full traceback:")

            return 0

        # Single format mode
        try:
            # Get merged args for this specific formatter
            merged_args = get_formatter_args(args.format, format_args_dict)

            # Create formatter
            formatter = create_season_recap_formatter(args.format, config.year, merged_args)

            # Generate and print output
            output = formatter.format(season_summary)
            print(output)

        except ValueError as e:
            # Format not yet implemented
            logger.error(f"❌ {e}")
            return 1

        return 0

    except FFTrackerError as e:
        logger.error(f"❌ Error: {e.message}")
        if args.debug:
            logger.exception("Full traceback:")
        return 1

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if args.debug:
            logger.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
