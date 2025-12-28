"""
Championship Week CLI for Fantasy Football Challenge Tracker.

This script handles Week 17 Championship Week operations including:
- Leaderboard display (default mode)
- Roster validation (check-rosters mode)
- Data validation (validate mode)

Usage:
    uv run ff-championship --env --format console
    uv run ff-championship 123456,789012,345678 --format email
    uv run ff-championship --env --mode check-rosters
    uv run ff-championship --env --output-dir ./reports  # Generate all formats

Examples:
    uv run ff-championship --env                             # Show leaderboard
    uv run ff-championship --env --format email > report.html
    uv run ff-championship --env --output-dir ./reports      # All formats at once
    uv run ff-championship --env --mode check-rosters        # Validate rosters
    uv run ff-championship --env --mode validate             # Check data quality
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import create_config
from .display import (
    ConsoleFormatter,
    EmailFormatter,
    JsonFormatter,
    MarkdownFormatter,
    SheetsFormatter,
)
from .exceptions import FFTrackerError
from .services.championship_service import ChampionshipService
from .services.espn_service import ESPNService
from .services.roster_validator import RosterValidator

# Logger for this module
logger = logging.getLogger(__name__)


def parse_league_ids_from_arg(league_id_arg: str) -> list[int]:
    """
    Parse league IDs from command line argument.

    Args:
        league_id_arg: Single ID or comma-separated IDs

    Returns:
        List of league IDs

    Raises:
        ValueError: If league IDs are invalid
    """
    try:
        league_ids = [int(id_str.strip()) for id_str in league_id_arg.split(",") if id_str.strip()]
        if not league_ids:
            raise ValueError("No valid league IDs found")
        return league_ids
    except ValueError as e:
        raise ValueError(
            f"Error parsing league IDs: {e}. Format should be: 123456 or 123456,789012,345678"
        ) from e


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Fantasy Football Championship Week Manager (Week 17)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --env                                    # Show championship leaderboard
  %(prog)s 123456,789012,345678 --format email      # Email format with league IDs
  %(prog)s --env --output-dir ./reports             # Generate all formats at once
  %(prog)s --env --mode check-rosters               # Validate all rosters
  %(prog)s --env --mode validate                    # Check data quality

Modes:
  leaderboard    Show championship standings (default)
  check-rosters  Validate rosters for all division winners
  validate       Check ESPN data quality and completeness

Formats:
  console        Human-readable tables with emojis (default)
  sheets         TSV format for Google Sheets
  email          Mobile-friendly HTML for email
  json           Structured JSON for APIs
  markdown       Markdown for GitHub/Slack/Discord

Multi-Output Mode:
  Use --output-dir to generate all 5 formats in a single execution.
  Files created: championship.txt, championship.tsv, championship.html,
                 championship.json, championship.md

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
        "--week",
        type=int,
        default=17,
        help="Championship week number (default: 17)",
    )

    parser.add_argument(
        "--mode",
        choices=["leaderboard", "check-rosters", "validate"],
        default="leaderboard",
        help="Operation mode (default: leaderboard)",
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
        "--division-names",
        help="Division names (comma-separated, defaults to auto-detected league names from ESPN)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def mode_leaderboard(
    service: ChampionshipService,
    leagues: list,
    division_names: list[str],
    week: int,
    output_format: str,
    year: int,
) -> None:
    """
    Display championship leaderboard with detailed rosters.

    Args:
        service: ChampionshipService instance
        leagues: List of ESPN League objects
        division_names: List of division names
        week: Championship week number
        output_format: Output format name
        year: Fantasy season year
    """
    logger.debug(f"Building championship leaderboard for Week {week}")

    # Build leaderboard
    leaderboard = service.build_leaderboard(leagues, division_names, week)

    # Get rosters for detailed display
    winners = service.get_division_winners(leagues, division_names)
    rosters = [service.get_roster(league, winner, week) for winner, league in zip(winners, leagues)]

    # Format and display output using the standard formatter
    formatter = get_formatter(output_format, year)
    output = formatter.format_output(
        divisions=[],  # No regular season data in championship mode
        challenges=[],  # No season challenges in championship mode
        weekly_challenges=None,
        current_week=week,
        championship=leaderboard,
        championship_rosters=rosters,
    )
    print(output)

    # Display detailed rosters (only for console format)
    if output_format == "console":
        from tabulate import tabulate

        print("\n" + "=" * 80)
        print("DETAILED ROSTERS")
        print("=" * 80)

        for roster in rosters:
            print(
                f"\n{roster.team.team_name} ({roster.team.owner_name}) - {roster.team.division_name}"
            )
            print("-" * 60)
            print(
                f"Final Score: {roster.total_score:.2f} pts | Projected: {roster.projected_score:.2f} pts"
            )

            # Build starters table
            starters_table = []
            for slot in roster.starters:
                status_icon = "✅" if slot.game_status == "final" else "⏳"
                player_display = slot.player_name or "EMPTY"
                team_display = slot.player_team or ""
                starters_table.append(
                    [
                        status_icon,
                        slot.position,
                        player_display,
                        team_display,
                        f"{slot.actual_points:.2f}",
                    ]
                )

            # Display starters table
            print("\n🏈 STARTERS:")
            print(
                tabulate(
                    starters_table,
                    headers=["", "Pos", "Player", "Team", "Points"],
                    tablefmt="simple",
                )
            )


def mode_check_rosters(
    service: ChampionshipService,
    validator: RosterValidator,
    leagues: list,
    division_names: list[str],
    week: int,
) -> None:
    """
    Validate rosters for all division winners.

    Args:
        service: ChampionshipService instance
        validator: RosterValidator instance
        leagues: List of ESPN League objects
        division_names: List of division names
        week: Championship week number
    """
    logger.debug(f"Checking rosters for Week {week}")

    # Get division winners
    winners = service.get_division_winners(leagues, division_names)

    # Get rosters
    rosters = []
    for winner, league in zip(winners, leagues):
        roster = service.get_roster(league, winner, week)
        rosters.append(roster)

    # Validate all rosters (for logging purposes)
    _ = validator.validate_all_rosters(rosters)

    # Display results
    print("\n📋 ROSTER VALIDATION RESULTS\n")

    for roster in rosters:
        team_name = roster.team.team_name
        print(f"\n{team_name} ({roster.team.owner_name}) - {roster.team.division_name}")
        print("=" * 60)
        print(f"Score: {roster.total_score:.2f} pts")
        print(f"Projected: {roster.projected_score:.2f} pts")
        print(f"Complete: {'✓' if roster.is_complete else '✗'}")

        summary = validator.get_roster_issues_summary(roster)
        print(f"\n{summary}")

        # Show suggestions
        suggestions = validator.get_optimal_lineup_suggestions(roster)
        if suggestions:
            print("\n💡 Suggestions:")
            for suggestion in suggestions:
                print(f"  • {suggestion}")


def mode_validate(
    service: ChampionshipService,
    leagues: list,
    division_names: list[str],
    week: int,
) -> None:
    """
    Validate ESPN data quality with detailed rosters.

    Args:
        service: ChampionshipService instance
        leagues: List of ESPN League objects
        division_names: List of division names
        week: Championship week number
    """
    logger.debug("Validating ESPN data quality")

    print("\n🔍 DATA VALIDATION\n")

    # Check Week 16 Finals (division winners)
    print("Checking Week 16 Finals...")
    winners = service.get_division_winners(leagues, division_names)
    print(f"✓ Found {len(winners)} division winners")
    for winner in winners:
        print(f"  • {winner.team_name} ({winner.division_name}) - Seed #{winner.seed}")

    # Check Week 17 rosters
    print(f"\nChecking Week {week} data...")
    rosters = [service.get_roster(league, winner, week) for winner, league in zip(winners, leagues)]

    for roster in rosters:
        status = "✓" if roster.is_complete else "✗"
        print(f"{status} {roster.team.team_name}: {len(roster.starters)} starters")

    # Calculate progress
    progress = service.get_progress(rosters)
    print("\n📊 Championship Progress:")
    print(f"Status: {progress.status}")
    print(f"Games: {progress.games_completed}/{progress.total_games} completed")
    print(f"Last Updated: {progress.last_updated}")

    # Show detailed rosters
    from tabulate import tabulate

    print("\n" + "=" * 80)
    print("DETAILED ROSTER BREAKDOWN")
    print("=" * 80)

    for roster in rosters:
        print(f"\n{roster.team.team_name} ({roster.team.owner_name})")
        print("-" * 60)
        print(f"Score: {roster.total_score:.2f} pts | Status: {progress.status}")

        # Build starters table
        starters_table = []
        for slot in roster.starters:
            status_icon = "✅" if slot.game_status == "final" else "⏳"
            player_display = slot.player_name or "EMPTY"
            team_display = slot.player_team or ""
            starters_table.append(
                [
                    status_icon,
                    slot.position,
                    player_display,
                    team_display,
                    f"{slot.actual_points:.2f}",
                ]
            )

        # Display starters table
        print("\n🏈 STARTERS:")
        print(
            tabulate(
                starters_table,
                headers=["", "Pos", "Player", "Team", "Points"],
                tablefmt="simple",
            )
        )


def get_formatter(format_name: str, year: int):
    """
    Get formatter instance by name.

    Args:
        format_name: Name of the formatter (console, sheets, email, json, markdown)
        year: Fantasy season year

    Returns:
        Formatter instance
    """
    formatters = {
        "console": ConsoleFormatter,
        "sheets": SheetsFormatter,
        "email": EmailFormatter,
        "json": JsonFormatter,
        "markdown": MarkdownFormatter,
    }
    formatter_class = formatters.get(format_name)
    if not formatter_class:
        raise ValueError(f"Unknown format: {format_name}")

    return formatter_class(year)


def main() -> int:
    """Main entry point for championship CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Validate league IDs
        if args.env:
            league_ids = None  # Will be loaded from environment
        elif args.league_ids:
            league_ids = parse_league_ids_from_arg(args.league_ids)
        else:
            parser.error("Either league_ids argument or --env flag is required")
            return 1

        # Create configuration
        config = create_config(
            league_ids=league_ids,
            year=args.year,
            private=args.private,
            use_env=args.env,
            week=args.week,
        )

        logger.debug(f"Championship Week script starting for {len(config.league_ids)} leagues")

        # Connect to leagues
        espn_service = ESPNService(config)
        leagues = [espn_service.connect_to_league(league_id) for league_id in config.league_ids]

        # Parse division names (auto-detect from league names if not provided)
        if args.division_names:
            division_names = [name.strip() for name in args.division_names.split(",")]
            if len(division_names) != len(config.league_ids):
                print(
                    f"Error: Number of division names ({len(division_names)}) must match "
                    f"number of leagues ({len(config.league_ids)})",
                    file=sys.stderr,
                )
                return 1
        else:
            # Auto-detect league names from ESPN
            division_names = []
            for league in leagues:
                league_name = league.settings.name if hasattr(league.settings, "name") else None
                if league_name:
                    division_names.append(league_name)
                else:
                    # Fallback to league ID if name not available
                    division_names.append(f"League {league.league_id}")

            logger.debug(f"Auto-detected division names: {division_names}")

        # Create services
        championship_service = ChampionshipService()
        validator = RosterValidator()

        # Execute mode
        if args.mode == "leaderboard":
            # Handle multi-output mode
            if args.output_dir:
                # Multi-output mode: generate all formats to files
                output_dir = args.output_dir
                output_dir.mkdir(parents=True, exist_ok=True)

                # Get championship data once
                leaderboard = championship_service.build_leaderboard(
                    leagues, division_names, args.week
                )
                winners = championship_service.get_division_winners(leagues, division_names)
                rosters = [
                    championship_service.get_roster(league, winner, args.week)
                    for winner, league in zip(winners, leagues)
                ]

                # Define format-to-filename mapping
                format_files = {
                    "console": output_dir / "championship.txt",
                    "sheets": output_dir / "championship.tsv",
                    "email": output_dir / "championship.html",
                    "json": output_dir / "championship.json",
                    "markdown": output_dir / "championship.md",
                }

                # Generate each format and write to file
                for format_name, file_path in format_files.items():
                    formatter = get_formatter(format_name, config.year)
                    output = formatter.format_output(
                        divisions=[],
                        challenges=[],
                        weekly_challenges=None,
                        current_week=args.week,
                        championship=leaderboard,
                        championship_rosters=rosters,
                    )
                    file_path.write_text(output, encoding="utf-8")
                    logger.info(f"Generated {format_name} format: {file_path}")

                logger.info(f"All formats generated successfully to {output_dir}")
            else:
                # Single format mode: output to stdout
                mode_leaderboard(
                    championship_service,
                    leagues,
                    division_names,
                    args.week,
                    args.format,
                    config.year,
                )
        elif args.mode == "check-rosters":
            mode_check_rosters(
                championship_service,
                validator,
                leagues,
                division_names,
                args.week,
            )
        elif args.mode == "validate":
            mode_validate(
                championship_service,
                leagues,
                division_names,
                args.week,
            )

        logger.debug("Championship Week script completed successfully")
        return 0

    except FFTrackerError as e:
        logger.error(f"Application error: {e}")
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        print("\nInterrupted by user", file=sys.stderr)
        return 130

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
