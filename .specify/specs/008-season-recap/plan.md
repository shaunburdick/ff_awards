# Implementation Plan: Season Recap Script

> **Spec ID**: 008
> **Status**: Active
> **Created**: 2024-12-29
> **Last Updated**: 2024-12-29

## Technology Choices

### Primary Stack
- **Language**: Python 3.9+ (using modern type syntax with `str | None`)
- **ESPN API Library**: espn-api 0.45.1 (existing dependency)
- **Key Libraries**: 
  - `dataclasses` (frozen=True for immutable season summary models)
  - `tabulate[widechars]` (existing - for console output)
  - `python-dotenv` (existing - for configuration)
  - No new dependencies required

### Rationale
All functionality can be implemented using the existing stack and dependencies. This feature reuses:
- All existing data models (Team, Challenge, Playoff, Championship)
- All existing services (ESPN API, challenge calculation, championship calculation)
- All existing formatters (console, sheets, email, json, markdown)
- Proven ESPN API patterns from `ff-tracker` and `ff-championship`

**Constitutional Compliance**:
- Article I: 100% type coverage with Python 3.9+ syntax (`str | None`, no `Any` types)
- Article II: Immutable data models using `@dataclass(frozen=True)` with `__post_init__` validation
- Article III: Fail-fast error handling with clear, actionable messages
- Article IV: Clean layer separation (Models → Services → Display)
- Article V: Efficient API usage - reuse ESPN connections across all data extraction

---

## Architecture Pattern

**Pattern**: Separate Script with Shared Infrastructure (Service Layer Orchestration)

**Justification**: 
- Season recap is a distinct use case (end-of-season summary, run once after Week 17)
- Different from weekly reports (`ff-tracker`) and championship reports (`ff-championship`)
- Orchestrates existing services to build comprehensive summary
- New script: `ff_tracker/season_recap.py` with CLI entry point
- New service: `SeasonRecapService` to coordinate data extraction
- New models: `SeasonSummary`, `RegularSeasonSummary`, `DivisionChampion`, etc.
- Formatters extended to render season recap (new layout, same formatter classes)

**Constitutional Compliance**:
- Article III: Fail-fast with clear errors for incomplete seasons (--force flag for testing)
- Article IV: Clean layer separation - new service orchestrates existing services
- Article VI: All formatters receive identical season summary data
- Article IX: CLI follows established patterns (--env, --private, --format, --output-dir)

---

## Key Architectural Decisions

### Decision 1: Separate Formatters vs. Extending Existing
**Approach**: Create separate formatter classes for season recap (not extending weekly formatters)

**Rationale**:
- Season recap has fundamentally different structure than weekly/playoff reports
- Different input data model (`SeasonSummary` vs `DivisionData`)
- Different sections and layout (full season story vs weekly snapshot)
- Existing formatters already handle 3 modes (regular, playoff, championship)
- Separate classes maintain single responsibility (Article IV)
- Independent evolution without breaking existing functionality
- Clearer code organization and easier testing
- No risk of formatter method explosion

**Implementation**:
```
ff_tracker/display/
├── console.py                    # Weekly/playoff formatter (unchanged)
├── season_recap_console.py       # NEW: Season recap formatter
├── email.py                      # Weekly/playoff formatter (unchanged)
├── season_recap_email.py         # NEW: Season recap formatter
└── ... (similar pattern for all formats)
```

**Alternatives Considered**:
- Add `format_season_recap()` to existing formatters: ❌ Violates single responsibility, formatters too complex
- Reuse existing `format_output()`: ❌ Incompatible data models

### Decision 2: Separate Script vs. Mode Flag
**Approach**: Create separate `ff-season-recap` script (new CLI entry point)

**Rationale**: 
- Single responsibility - recap is fundamentally different from weekly/championship reports
- Simpler implementation - no complex conditionals in existing scripts
- Independent evolution - can add historical features without affecting other scripts
- Follows Unix philosophy - do one thing well

### Decision 3: Dynamic Season Structure Detection
**Approach**: Calculate all season boundaries from ESPN API settings
```python
reg_season_end = league.settings.reg_season_count  # e.g., 14
playoff_start = reg_season_end + 1  # e.g., 15
playoff_end = league.finalScoringPeriod  # e.g., 16
championship_week = playoff_end + 1  # e.g., 17 (custom cross-division)
playoff_rounds = (playoff_end - playoff_start + 1) // league.settings.playoff_matchup_period_length
```

**Rationale**: 
- No hardcoded week numbers or playoff lengths
- Supports any ESPN league configuration
- Reuses proven playoff detection logic from spec 006
- Matches existing `ff-tracker` behavior

### Decision 4: Incomplete Season Handling
**Approach**: Flexible validation with `--force` flag

**Normal Mode**:
```bash
uv run ff-season-recap --env
# Error: "Season incomplete: Championship week has not occurred yet. Use --force to generate partial recap."
```

**Force Mode**:
```bash
uv run ff-season-recap --env --force
# Generates: Whatever sections are available with clear warnings
# Output: "⚠️ WARNING: Championship week data not available. Showing regular season and playoffs only."
```

**Rationale**: 
- Need to test before Week 17 completes (December 24, 2024)
- Useful for generating partial recaps if needed
- Maintains fail-fast philosophy while enabling testing

### Decision 5: Division Naming Strategy
**Approach**: Hybrid - ESPN names with sensible fallback
```python
def get_division_name(league: League, index: int) -> str:
    """Use ESPN league name or fallback to positional naming."""
    return league.settings.name or f"Division {index + 1}"
```

**Rationale**: 
- Uses meaningful ESPN names when available
- Sensible defaults when data missing
- No additional configuration required
- Consistent with "detect what we can, sensible defaults" philosophy

### Decision 6: Data Persistence Strategy
**Approach**: Multi-output mode saves files including JSON (no automatic archival)

**Single Format** (stdout):
```bash
uv run ff-season-recap --env --format console
uv run ff-season-recap --env --format json > 2024-recap.json
```

**Multi-Output** (files):
```bash
uv run ff-season-recap --env --output-dir ./season-recap
# Creates: season-recap.txt, .tsv, .html, .json, .md
```

**Rationale**: 
- Consistent with existing `ff-tracker` and `ff-championship` behavior
- User has explicit control over file creation
- JSON format preserved for record-keeping when using --output-dir
- Simple and predictable

**Note**: No year-over-year comparisons in v1 (players change divisions annually)

### Decision 6: Separate Formatters vs Extending Existing
**Approach**: Create separate formatter classes for season recap

**Rationale**:
- Season recap is fundamentally different from weekly/playoff reports
- Different data model (`SeasonSummary` vs `DivisionData`)
- Different layout, structure, and sections
- Weekly formatters already complex with playoff and championship modes
- Separate classes follow single responsibility principle (Article IV)
- Allows independent evolution without risk of breaking existing output
- Cleaner code organization and testing

**Implementation**:
- New files: `season_recap_console.py`, `season_recap_sheets.py`, etc.
- New factory: `create_season_recap_formatter()` in `factory.py`
- Each formatter has single `format()` method (not `format_season_recap()`)
- All inherit from `BaseFormatter` for format args system

**Alternatives Considered**:
- Add `format_season_recap()` method to existing formatters: ❌ Violates single responsibility
- Reuse existing formatters as-is: ❌ Data models incompatible

### Decision 7: Season Awards Scope
**Approach**: NOT included in v1

**v1 Scope** (included):
- ✅ Regular season standings & division champions
- ✅ All 5 season challenge winners
- ✅ Playoff results (all rounds, all divisions)
- ✅ Championship results (overall winner)

**Out of Scope for v1**:
- ❌ Most Consistent (stddev calculations)
- ❌ Boom or Bust (stddev calculations)
- ❌ Best Playoff Run, Heartbreaker, Lucky Winner, Benchwarmer

**Rationale**: 
- Keep v1 focused and deliverable
- Core facts are most important for season story
- Awards can be Phase 2 enhancement
- Ship early, iterate based on feedback

---

## Component Breakdown

### Component 1: Season Summary Data Models

**Purpose**: Type-safe, immutable containers for complete season summary

**Responsibilities**:
- Store season year and generation timestamp
- Contain regular season, challenges, playoffs, championship sections
- Validate completeness at construction time
- Support optional sections (for --force mode)

**Interface**:
```python
@dataclass(frozen=True)
class SeasonStructure:
    """Dynamic season structure calculated from ESPN API."""
    regular_season_start: int
    regular_season_end: int
    playoff_start: int
    playoff_end: int
    championship_week: int
    playoff_rounds: int
    playoff_round_length: int
    
    def __post_init__(self) -> None:
        """Validate season structure is logical."""
        if self.regular_season_start < 1:
            raise DataValidationError("Regular season must start at week 1 or later")
        if self.regular_season_end < self.regular_season_start:
            raise DataValidationError("Regular season end must be after start")
        if self.playoff_start != self.regular_season_end + 1:
            raise DataValidationError("Playoffs must start immediately after regular season")

@dataclass(frozen=True)
class DivisionChampion:
    """Regular season division champion."""
    division_name: str
    team_name: str
    owner_name: str
    wins: int
    losses: int
    points_for: float
    points_against: float
    final_rank: int  # Should be 1 for champion
    
    def __post_init__(self) -> None:
        """Validate champion data."""
        if not self.team_name.strip():
            raise DataValidationError("Team name cannot be empty")
        if self.wins < 0 or self.losses < 0:
            raise DataValidationError("Wins and losses must be non-negative")
        if self.points_for < 0:
            raise DataValidationError(f"Points for cannot be negative: {self.points_for}")

@dataclass(frozen=True)
class RegularSeasonSummary:
    """Summary of regular season results."""
    structure: SeasonStructure
    division_champions: tuple[DivisionChampion, ...]
    final_standings: tuple[DivisionData, ...]  # Reuse existing model
    
    def __post_init__(self) -> None:
        """Validate regular season summary."""
        if len(self.division_champions) != len(self.final_standings):
            raise DataValidationError("Must have one champion per division")

@dataclass(frozen=True)
class PlayoffSummary:
    """Summary of playoff results (all rounds)."""
    structure: SeasonStructure
    rounds: tuple[PlayoffRound, ...]  # Can be 2+ rounds depending on league
    
    @property
    def semifinals(self) -> PlayoffRound | None:
        """Get semifinals round if it exists."""
        return next((r for r in self.rounds if "Semifinal" in r.round_name), None)
    
    @property
    def finals(self) -> PlayoffRound | None:
        """Get finals round if it exists."""
        return next((r for r in self.rounds if "Final" in r.round_name), None)

@dataclass(frozen=True)
class PlayoffRound:
    """Results for one playoff round across all divisions."""
    round_name: str  # "Semifinals", "Finals"
    week: int
    division_brackets: tuple[PlayoffBracket, ...]  # One per division
    
    def __post_init__(self) -> None:
        """Validate round data."""
        if not self.division_brackets:
            raise DataValidationError(f"Playoff round {self.round_name} must have at least one division")

@dataclass(frozen=True)
class SeasonSummary:
    """Complete summary of a fantasy football season."""
    year: int
    generated_at: str  # ISO 8601 timestamp
    structure: SeasonStructure
    regular_season: RegularSeasonSummary
    season_challenges: tuple[ChallengeResult, ...]  # Reuse existing model
    playoffs: PlayoffSummary
    championship: ChampionshipLeaderboard | None  # May be None with --force
    
    def __post_init__(self) -> None:
        """Validate season summary."""
        if self.year < 2000 or self.year > 2100:
            raise DataValidationError(f"Invalid year: {self.year}")
        if len(self.season_challenges) != 5:
            raise DataValidationError(f"Must have exactly 5 season challenges, got {len(self.season_challenges)}")
```

**Dependencies**: 
- Existing models: `DivisionData`, `ChallengeResult`, `PlayoffBracket`, `ChampionshipLeaderboard`
- Standard library: `dataclasses`, `datetime` (for ISO timestamp)
- Existing: `DataValidationError` from `exceptions.py`

**Data Structures**:
- All immutable (`frozen=True`)
- Tuples for collections (immutable sequences)
- Optional championship data for --force mode

**Constraints**:
- Full validation in `__post_init__` methods
- No business logic (data only)
- 100% type coverage

### Component 2: Season Recap Service

**Purpose**: Orchestrate data extraction from multiple sources to build complete season summary

**Responsibilities**:
- Calculate season structure dynamically from ESPN API
- Extract regular season champions and standings
- Extract all 5 season challenge winners
- Extract playoff results for all rounds
- Extract championship leaderboard
- Validate season completeness (with --force support)
- Coordinate existing services (ESPN, Challenge, Championship)

**Interface**:
```python
class SeasonRecapService:
    """Service for generating complete season recap."""
    
    def __init__(
        self,
        espn_service: ESPNService,
        challenge_calculator: ChallengeCalculator,
        championship_service: ChampionshipService
    ):
        """Initialize with existing services."""
        self.espn = espn_service
        self.challenges = challenge_calculator
        self.championships = championship_service
    
    def calculate_season_structure(self, league: League) -> SeasonStructure:
        """
        Calculate season structure dynamically from ESPN API.
        
        Uses:
        - league.settings.reg_season_count (regular season end)
        - league.finalScoringPeriod (playoff end)
        - league.settings.playoff_matchup_period_length (round length)
        
        Returns:
            SeasonStructure with all week boundaries
        """
        reg_end = league.settings.reg_season_count
        playoff_end = league.finalScoringPeriod
        round_length = league.settings.playoff_matchup_period_length
        
        return SeasonStructure(
            regular_season_start=1,
            regular_season_end=reg_end,
            playoff_start=reg_end + 1,
            playoff_end=playoff_end,
            championship_week=playoff_end + 1,
            playoff_rounds=(playoff_end - reg_end) // round_length,
            playoff_round_length=round_length
        )
    
    def validate_season_complete(
        self,
        leagues: list[League],
        force: bool = False
    ) -> tuple[bool, str, dict[str, bool]]:
        """
        Check if season is complete enough for recap.
        
        Args:
            leagues: List of ESPN league objects
            force: If True, allow partial recap generation
        
        Returns:
            (is_complete, message, available_sections)
            - is_complete: True if all required data present
            - message: Explanation of what's missing (if any)
            - available_sections: Dict of which sections have data
              {"regular_season": bool, "playoffs": bool, "championship": bool}
        
        Raises:
            ESPNAPIError: If unable to check season status
        """
        # Calculate structure from first league (all should match)
        structure = self.calculate_season_structure(leagues[0])
        current_week = leagues[0].current_week
        
        available = {
            "regular_season": current_week > structure.regular_season_end,
            "playoffs": current_week > structure.playoff_end,
            "championship": current_week > structure.championship_week
        }
        
        all_complete = all(available.values())
        
        if all_complete:
            return True, "Season complete", available
        
        if force:
            missing = [k for k, v in available.items() if not v]
            return False, f"Partial recap mode (missing: {', '.join(missing)})", available
        
        return False, f"Season incomplete: Championship week (Week {structure.championship_week}) has not occurred yet. Use --force to generate partial recap.", available
    
    def get_regular_season_summary(
        self,
        leagues: list[League],
        division_names: list[str],
        structure: SeasonStructure
    ) -> RegularSeasonSummary:
        """
        Extract regular season results.
        
        Returns:
            RegularSeasonSummary with champions and final standings
        """
        champions: list[DivisionChampion] = []
        standings: list[DivisionData] = []
        
        for league, div_name in zip(leagues, division_names):
            # Get all teams sorted by record (wins desc, points_for desc)
            teams = sorted(
                league.teams,
                key=lambda t: (t.wins, t.points_for),
                reverse=True
            )
            
            # First place is champion
            champion_team = teams[0]
            champions.append(DivisionChampion(
                division_name=div_name,
                team_name=champion_team.team_name,
                owner_name=champion_team.owner or "Unknown Owner",
                wins=champion_team.wins,
                losses=champion_team.losses,
                points_for=champion_team.points_for,
                points_against=champion_team.points_against,
                final_rank=1
            ))
            
            # Load full division data for standings
            division_data = self.espn.load_division_data(league, div_name)
            standings.append(division_data)
        
        return RegularSeasonSummary(
            structure=structure,
            division_champions=tuple(champions),
            final_standings=tuple(standings)
        )
    
    def get_playoff_summary(
        self,
        leagues: list[League],
        division_names: list[str],
        structure: SeasonStructure
    ) -> PlayoffSummary:
        """
        Extract playoff results for all rounds.
        
        Uses existing playoff detection logic from spec 006.
        
        Returns:
            PlayoffSummary with all playoff rounds
        """
        # For each playoff week, extract brackets across all divisions
        rounds: list[PlayoffRound] = []
        
        for week_num in range(structure.playoff_start, structure.playoff_end + 1):
            week_offset = week_num - structure.playoff_start
            round_num = week_offset // structure.playoff_round_length + 1
            
            # Determine round name (Semifinals, Finals, etc.)
            if round_num == 1:
                round_name = "Semifinals"
            elif round_num == structure.playoff_rounds:
                round_name = "Finals"
            else:
                round_name = f"Round {round_num}"
            
            # Extract brackets for this week from all divisions
            brackets: list[PlayoffBracket] = []
            for league, div_name in zip(leagues, division_names):
                # Reuse playoff extraction logic from ESPNService
                bracket = self.espn.build_playoff_bracket(league, div_name, week_num)
                if bracket:
                    brackets.append(bracket)
            
            if brackets:
                rounds.append(PlayoffRound(
                    round_name=round_name,
                    week=week_num,
                    division_brackets=tuple(brackets)
                ))
        
        return PlayoffSummary(
            structure=structure,
            rounds=tuple(rounds)
        )
    
    def get_championship_summary(
        self,
        leagues: list[League],
        division_names: list[str],
        structure: SeasonStructure
    ) -> ChampionshipLeaderboard | None:
        """
        Extract championship week results.
        
        Reuses championship service logic from ff-championship script.
        
        Returns:
            ChampionshipLeaderboard or None if data not available
        """
        try:
            # Use existing championship service
            leaderboard = self.championships.build_championship_leaderboard(
                leagues=leagues,
                division_names=division_names,
                championship_week=structure.championship_week
            )
            return leaderboard
        except ESPNAPIError as e:
            # Championship data not available yet
            return None
    
    def generate_season_summary(
        self,
        leagues: list[League],
        division_names: list[str],
        year: int,
        force: bool = False
    ) -> SeasonSummary:
        """
        Generate complete season summary.
        
        Args:
            leagues: ESPN league objects for all divisions
            division_names: Names for each division
            year: Season year
            force: If True, allow partial recap
            
        Returns:
            Complete SeasonSummary object
            
        Raises:
            InsufficientDataError: If season data incomplete and not force mode
            ESPNAPIError: If API data extraction fails
        """
        # Calculate season structure
        structure = self.calculate_season_structure(leagues[0])
        
        # Validate season completeness
        is_complete, message, available = self.validate_season_complete(leagues, force)
        
        if not is_complete and not force:
            raise InsufficientDataError(message)
        
        # Extract all components
        regular_season = self.get_regular_season_summary(leagues, division_names, structure)
        
        # Get season challenges (reuse existing calculator)
        all_games = [game for league in leagues for game in league.box_scores()]
        challenges = self.challenges.calculate_all_challenges(all_games)
        
        playoffs = self.get_playoff_summary(leagues, division_names, structure)
        
        championship = None
        if available["championship"]:
            championship = self.get_championship_summary(leagues, division_names, structure)
        
        # Build complete summary
        from datetime import datetime
        return SeasonSummary(
            year=year,
            generated_at=datetime.utcnow().isoformat() + "Z",
            structure=structure,
            regular_season=regular_season,
            season_challenges=tuple(challenges),
            playoffs=playoffs,
            championship=championship
        )
    
    def get_division_name(self, league: League, index: int) -> str:
        """
        Get division name from ESPN or fallback to positional naming.
        
        Args:
            league: ESPN League object
            index: Zero-based position in LEAGUE_IDS list
            
        Returns:
            Division name (e.g., "Rough Street" or "Division 1")
        """
        return league.settings.name or f"Division {index + 1}"
```

**Dependencies**:
- Existing services: `ESPNService`, `ChallengeCalculator`, `ChampionshipService`
- New models: `SeasonSummary`, `RegularSeasonSummary`, etc.
- Existing exceptions: `ESPNAPIError`, `InsufficientDataError` (new)

**Data Flow**:
1. Calculate season structure from ESPN API
2. Validate season completeness
3. Extract regular season data (champions, standings)
4. Calculate season challenges (reuse existing calculator)
5. Extract playoff data for all rounds
6. Extract championship data (if available)
7. Build and return complete `SeasonSummary`

**Constraints**:
- Must preserve existing single-API-call efficiency where possible
- Must fail-fast on incomplete data (unless --force)
- Must reuse existing service logic (no duplication)

### Component 3: CLI Entry Point

**Purpose**: Command-line interface for season recap script

**Responsibilities**:
- Parse command-line arguments (--env, --private, --year, --format, --force, etc.)
- Load configuration from environment
- Initialize services (ESPN, Challenge, Championship, SeasonRecap)
- Generate season summary
- Format output (single format or multi-output mode)
- Handle errors with clear messages

**Interface**:
```python
# ff_tracker/season_recap.py

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from ff_tracker.config import Config
from ff_tracker.display.factory import create_formatter, parse_format_args
from ff_tracker.exceptions import FFTrackerError, InsufficientDataError
from ff_tracker.services.challenge_service import ChallengeCalculator
from ff_tracker.services.championship_service import ChampionshipService
from ff_tracker.services.espn_service import ESPNService
from ff_tracker.services.season_recap_service import SeasonRecapService


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for season recap CLI."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive end-of-season recap report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate season recap for current season
  uv run ff-season-recap --env --private
  
  # Specific year
  uv run ff-season-recap --env --year 2024
  
  # All formats
  uv run ff-season-recap --env --output-dir ./season-recap
  
  # With custom note
  uv run ff-season-recap --env --format email \\
    --format-arg note="Thanks for a great season!"
  
  # Force partial recap (testing)
  uv run ff-season-recap --env --force
        """
    )
    
    # League identification
    league_group = parser.add_mutually_exclusive_group(required=True)
    league_group.add_argument(
        "--env",
        action="store_true",
        help="Load league IDs from LEAGUE_IDS environment variable"
    )
    league_group.add_argument(
        "league_ids",
        nargs="*",
        help="Comma-separated league IDs (e.g., 123456789,987654321)"
    )
    
    # Authentication
    parser.add_argument(
        "--private",
        action="store_true",
        help="Use ESPN authentication for private leagues (requires ESPN_S2 and SWID env vars)"
    )
    
    # Season specification
    parser.add_argument(
        "--year",
        type=int,
        default=datetime.now().year,
        help="Season year (default: current year)"
    )
    
    # Output control
    parser.add_argument(
        "--format",
        choices=["console", "sheets", "email", "json", "markdown"],
        default="console",
        help="Output format (default: console)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Generate all formats to directory (creates season-recap.txt, .tsv, .html, .json, .md)"
    )
    
    parser.add_argument(
        "--format-arg",
        action="append",
        dest="format_args",
        help="Format-specific argument (e.g., note='Message' or email.accent_color='#007bff')"
    )
    
    # Validation override
    parser.add_argument(
        "--force",
        action="store_true",
        help="Generate recap even if season incomplete (for testing)"
    )
    
    return parser


def main() -> None:
    """Main entry point for season recap CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = Config.from_env()
        
        # Parse league IDs
        if args.env:
            league_ids = config.league_ids
        else:
            league_ids = [
                league_id.strip()
                for ids_str in args.league_ids
                for league_id in ids_str.split(",")
            ]
        
        if not league_ids:
            raise ConfigurationError(
                "No league IDs provided. Use --env with LEAGUE_IDS environment variable, "
                "or pass league IDs as arguments."
            )
        
        # Parse format arguments
        format_args = parse_format_args(args.format_args or [])
        
        # Initialize services
        with ESPNService(config) as espn:
            # Load all leagues
            leagues = [espn.connect_league(league_id, args.year) for league_id in league_ids]
            
            # Get division names
            recap_service = SeasonRecapService(
                espn_service=espn,
                challenge_calculator=ChallengeCalculator(),
                championship_service=ChampionshipService(espn)
            )
            division_names = [
                recap_service.get_division_name(league, idx)
                for idx, league in enumerate(leagues)
            ]
            
            # Generate season summary
            try:
                summary = recap_service.generate_season_summary(
                    leagues=leagues,
                    division_names=division_names,
                    year=args.year,
                    force=args.force
                )
            except InsufficientDataError as e:
                print(f"Error: {e}", file=sys.stderr)
                print(f"\nSeason structure:", file=sys.stderr)
                structure = recap_service.calculate_season_structure(leagues[0])
                print(f"  Regular season: Weeks {structure.regular_season_start}-{structure.regular_season_end}", file=sys.stderr)
                print(f"  Playoffs: Weeks {structure.playoff_start}-{structure.playoff_end}", file=sys.stderr)
                print(f"  Championship: Week {structure.championship_week}", file=sys.stderr)
                sys.exit(1)
            
            # Show warnings if partial recap
            is_complete, message, available = recap_service.validate_season_complete(leagues, args.force)
            if not is_complete and args.force:
                print(f"⚠️  WARNING: {message}", file=sys.stderr)
                missing = [k for k, v in available.items() if not v]
                print(f"⚠️  Missing sections: {', '.join(missing)}", file=sys.stderr)
                print(file=sys.stderr)
            
            # Generate output
            if args.output_dir:
                # Multi-output mode: generate all formats
                args.output_dir.mkdir(parents=True, exist_ok=True)
                
                formats = ["console", "sheets", "email", "json", "markdown"]
                extensions = {"console": "txt", "sheets": "tsv", "email": "html", "json": "json", "markdown": "md"}
                
                for fmt in formats:
                    formatter = create_season_recap_formatter(fmt, args.year, format_args)
                    output = formatter.format(summary)
                    
                    output_path = args.output_dir / f"season-recap.{extensions[fmt]}"
                    output_path.write_text(output)
                    print(f"Generated: {output_path}", file=sys.stderr)
            else:
                # Single format mode: output to stdout
                formatter = create_season_recap_formatter(args.format, args.year, format_args)
                output = formatter.format(summary)
                print(output)
    
    except FFTrackerError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Dependencies**:
- New service: `SeasonRecapService`
- Existing services: `ESPNService`, `ChallengeCalculator`, `ChampionshipService`
- Existing infrastructure: `Config`, formatter factory, exception hierarchy
- Standard library: `argparse`, `sys`, `pathlib`, `datetime`

**Constraints**:
- Follow established CLI patterns from `ff-tracker` and `ff-championship`
- Provide clear help text and examples
- Handle all errors gracefully with actionable messages

### Component 4: Separate Season Recap Formatters

**Purpose**: Dedicated formatters for season recap output (separate from weekly/playoff formatters)

**Responsibilities**:
- Render complete season summary with distinct sections
- Maintain consistent structure across all 5 formats
- Support format arguments (note, etc.)
- Single responsibility: format season recap only

**Approach**: Create separate formatter classes (not extending existing formatters)

**Rationale**:
- Season recap is fundamentally different from weekly/playoff reports
- Different data model (`SeasonSummary` vs `DivisionData`)
- Different layout and section structure
- Allows independent evolution without affecting existing formatters
- Follows Article IV (single responsibility)
- Cleaner code organization

**New Formatter Files**:
```
ff_tracker/display/
├── season_recap_console.py    # SeasonRecapConsoleFormatter
├── season_recap_sheets.py     # SeasonRecapSheetsFormatter
├── season_recap_email.py      # SeasonRecapEmailFormatter
├── season_recap_json.py       # SeasonRecapJsonFormatter
└── season_recap_markdown.py   # SeasonRecapMarkdownFormatter
```

**Base Interface**:
```python
class SeasonRecapConsoleFormatter(BaseFormatter):
    """Console formatter for season recap (separate from weekly formatter)."""
    
    def format(self, summary: SeasonSummary) -> str:
        """
        Format complete season recap for console display.
        
        Args:
            summary: Complete season summary data
            
        Returns:
            Formatted string output
            
        Sections:
        1. Header with year and generation timestamp
        2. Regular season summary (champions, standings)
        3. Season challenge winners (all 5)
        4. Playoff results (all rounds)
        5. Championship results (if available)
        6. Optional note (via format args)
        """
        output_lines: list[str] = []
        
        # Optional note at top
        note = self._get_arg("note")
        if note:
            output_lines.append(self._format_note(note))
        
        # Large banner header
        output_lines.append(self._format_header(summary.year))
        
        # Regular season section
        output_lines.append(self._format_regular_season(summary.regular_season))
        
        # Season challenges section
        output_lines.append(self._format_season_challenges(summary.season_challenges))
        
        # Playoffs section
        output_lines.append(self._format_playoffs(summary.playoffs))
        
        # Championship section (if available)
        if summary.championship:
            output_lines.append(self._format_championship(summary.championship))
        
        return "\n".join(output_lines)
```

**Console Formatter Details**:
- Large banner header: "🏆 2024 SEASON RECAP 🏆" (fancy_grid table)
- Section dividers with emojis (📅, 🏅, 🏈, 🥇)
- Tabulate tables for champions, challenges, playoff brackets
- Championship winner highlighted with gold styling
- Optional note table at top (if provided)

**Sheets (TSV) Formatter Details**:
- Header row: "2024 SEASON RECAP"
- Separate TSV sections for each component
- Blank rows between sections
- Championship leaderboard as final table
- Optional note as first row

**Email (HTML) Formatter Details**:
- Responsive HTML with mobile-first design
- Collapsible sections for each phase
- Color-coded sections (blue=regular, orange=playoffs, gold=championship)
- Summary stats at top
- Optional note alert box
- Footer with generation timestamp

**JSON Formatter Details**:
- Structured data matching `SeasonSummary` model exactly
- Version field: "1.0" for future compatibility
- Optional metadata section with note
- All data preserved for archival
- Direct serialization of data models

**Markdown Formatter Details**:
- Clean GitHub/Slack/Discord formatting
- H2 headers for sections
- Tables for champions, challenges, brackets
- Medal emojis for championship (🥇🥈🥉)
- Optional note blockquote

**Formatter Factory Integration**:
```python
# Update ff_tracker/display/factory.py
from ff_tracker.display.season_recap_console import SeasonRecapConsoleFormatter
from ff_tracker.display.season_recap_email import SeasonRecapEmailFormatter
# ... etc

def create_season_recap_formatter(
    format_type: str,
    year: int,
    format_args: dict[str, str] | None = None
) -> BaseFormatter:
    """Create season recap formatter (separate from weekly formatter)."""
    formatters = {
        "console": SeasonRecapConsoleFormatter,
        "sheets": SeasonRecapSheetsFormatter,
        "email": SeasonRecapEmailFormatter,
        "json": SeasonRecapJsonFormatter,
        "markdown": SeasonRecapMarkdownFormatter,
    }
    
    formatter_class = formatters.get(format_type)
    if not formatter_class:
        raise ValueError(f"Unknown format type: {format_type}")
    
    return formatter_class(year, format_args)
```

**Dependencies**: 
- New models: `SeasonSummary`, `RegularSeasonSummary`, etc.
- Existing base: `BaseFormatter` (for format args system)
- Existing utilities: `tabulate` (console), formatting helpers

**Constraints**:
- Each formatter completely independent
- Must handle partial summaries (missing championship)
- Must support format arguments
- No shared state between formatters
- All inherit from `BaseFormatter` for consistency

---

## Data Flow

### High-Level Flow

```
1. CLI invoked → Parse args (--env, --year, --format, --force, etc.)
2. Load configuration from environment
3. Initialize services (ESPN, Challenge, Championship, SeasonRecap)
4. Connect to all leagues via ESPN API
5. Calculate season structure dynamically
6. Validate season completeness (fail if incomplete unless --force)
7. Extract regular season data:
   - Division champions (highest record per division)
   - Final standings (all teams, all divisions)
8. Calculate season challenges (reuse existing calculator with all games)
9. Extract playoff data:
   - For each playoff week (start to end)
   - Extract brackets from all divisions
   - Build playoff rounds (Semifinals, Finals, etc.)
10. Extract championship data (if available):
    - Division winners from Finals
    - Week 17 scores
    - Build leaderboard with ranking
11. Build complete SeasonSummary object
12. Format output:
    - Single format → stdout
    - Multi-output → files in directory
13. Show warnings if partial recap (--force mode)
```

### Detailed Flow with Decision Points

```
Input: CLI args (league IDs, year, format, force flag)
    ↓
Load Config from environment
    ↓
Parse league IDs
    ├─ --env flag? → Load from LEAGUE_IDS env var
    └─ CLI args? → Parse comma-separated list
    ↓
No league IDs? ──Yes──> ConfigurationError: "No league IDs provided..."
    ↓ No
Initialize Services:
    - ESPNService (with optional private auth)
    - ChallengeCalculator
    - ChampionshipService
    - SeasonRecapService
    ↓
Connect to all leagues via ESPN API
    ↓
Calculate season structure from first league:
    - reg_season_end = league.settings.reg_season_count
    - playoff_start = reg_season_end + 1
    - playoff_end = league.finalScoringPeriod
    - championship_week = playoff_end + 1
    - playoff_rounds = (playoff_end - playoff_start + 1) // round_length
    ↓
Validate season completeness:
    current_week = league.current_week
    available = {
        "regular_season": current_week > reg_season_end,
        "playoffs": current_week > playoff_end,
        "championship": current_week > championship_week
    }
    ↓
All sections available? ──No──> Force flag? ──No──> InsufficientDataError
    ↓ Yes                          ↓ Yes           Show error + season structure
Extract regular season data:                       Exit with code 1
    For each league:
        - Sort teams by record (wins desc, points_for desc)
        - Champion = teams[0]
        - Build DivisionChampion model
        - Load full DivisionData for standings
    ↓
Calculate season challenges:
    - Get all games from all leagues
    - Use existing ChallengeCalculator.calculate_all_challenges()
    - Returns list[ChallengeResult]
    ↓
Extract playoff data:
    For each playoff week (playoff_start to playoff_end):
        - Calculate round number and name
        - For each league:
            - Build playoff bracket (reuse spec 006 logic)
        - Create PlayoffRound with all brackets
    ↓
Extract championship data:
    Championship week available? ──No──> championship = None
        ↓ Yes
    Use ChampionshipService to build leaderboard:
        - Find division winners from Finals
        - Get Week 17 scores
        - Rank by score (highest wins)
        - Build ChampionshipLeaderboard
    ↓
Build SeasonSummary:
    - year = CLI arg
    - generated_at = datetime.utcnow().isoformat()
    - structure = calculated structure
    - regular_season = RegularSeasonSummary
    - season_challenges = tuple(challenges)
    - playoffs = PlayoffSummary
    - championship = ChampionshipLeaderboard | None
    ↓
Force mode AND partial? ──Yes──> Show warnings to stderr
    ↓ No
Format output:
    Multi-output mode (--output-dir)?
        ├─ Yes → Generate all 5 formats to files
        │        Print "Generated: {path}" for each
        │        
        └─ No → Generate single format to stdout
    ↓
Success (exit 0)
```

### Error Paths

- **ConfigurationError**: No league IDs provided
  - **Handling**: Show error + usage hint, exit code 1
  - **Message**: "No league IDs provided. Use --env with LEAGUE_IDS environment variable, or pass league IDs as arguments."

- **InsufficientDataError**: Season incomplete (no --force)
  - **Handling**: Show error + season structure explanation, exit code 1
  - **Message**: "Season incomplete: Championship week (Week 17) has not occurred yet. Use --force to generate partial recap."
  - **Additional Info**: Show calculated season structure (regular season weeks, playoff weeks, championship week)

- **ESPNAPIError**: API connection or data extraction fails
  - **Handling**: Show error with context, exit code 1
  - **Message**: Preserve ESPN API error message, add context about which league failed

- **DataValidationError**: Invalid data from ESPN API
  - **Handling**: Show error with details, exit code 1
  - **Message**: Include field name and invalid value

- **KeyboardInterrupt**: User cancels operation
  - **Handling**: Clean shutdown, exit code 130
  - **Message**: "Operation cancelled by user."

---

## Implementation Phases

### Phase 1: Foundation - Data Models (2-3 hours)

**Goal**: Create all season recap data models with full validation

**Tasks**:
- [ ] Create `ff_tracker/models/season_summary.py` with new models:
  - `SeasonStructure`
  - `DivisionChampion`
  - `RegularSeasonSummary`
  - `PlayoffSummary`
  - `PlayoffRound`
  - `SeasonSummary`
- [ ] Add full validation in `__post_init__` methods
- [ ] Add new exception `InsufficientDataError` to `ff_tracker/exceptions.py`
- [ ] Update `ff_tracker/models/__init__.py` to export new models
- [ ] Write docstrings for all models and properties

**Deliverable**: All season recap models defined with 100% type coverage

**Validation**: 
- Models can be imported: `from ff_tracker.models import SeasonSummary`
- Models can be instantiated with valid data
- Invalid data raises `DataValidationError`
- All fields properly typed

**Dependencies**: None

### Phase 2: Service Layer - Season Recap Service (3-4 hours)

**Goal**: Implement service to orchestrate data extraction

**Tasks**:
- [ ] Create `ff_tracker/services/season_recap_service.py`
- [ ] Implement `SeasonRecapService.__init__()` with service dependencies
- [ ] Implement `calculate_season_structure()` method
- [ ] Implement `validate_season_complete()` with force flag support
- [ ] Implement `get_regular_season_summary()` method
- [ ] Implement `get_playoff_summary()` method (reuse spec 006 logic)
- [ ] Implement `get_championship_summary()` method (reuse championship service)
- [ ] Implement `generate_season_summary()` orchestration method
- [ ] Implement `get_division_name()` helper method
- [ ] Update `ff_tracker/services/__init__.py` to export `SeasonRecapService`
- [ ] Write comprehensive docstrings

**Deliverable**: Service can generate complete season summary from ESPN data

**Validation**:
- Service instantiates with existing services
- Can calculate season structure from league object
- Can validate season completeness
- Can extract each section independently
- Complete `generate_season_summary()` returns valid `SeasonSummary`

**Dependencies**: Phase 1 complete

### Phase 3: CLI Entry Point (1-2 hours)

**Goal**: Create command-line interface for season recap

**Tasks**:
- [ ] Create `ff_tracker/season_recap.py` with CLI implementation
- [ ] Implement `create_parser()` with all arguments
- [ ] Implement `main()` function:
  - Parse arguments
  - Load configuration
  - Initialize services
  - Generate season summary
  - Handle errors with clear messages
  - Support single format and multi-output modes
- [ ] Add script entry point to `pyproject.toml`:
  ```toml
  [project.scripts]
  ff-season-recap = "ff_tracker.season_recap:main"
  ```
- [ ] Write help text and examples
- [ ] Test CLI with `--help` flag

**Deliverable**: Working CLI that can be invoked with `uv run ff-season-recap`

**Validation**:
- `uv run ff-season-recap --help` shows usage
- CLI parses all arguments correctly
- Error handling works (try with no league IDs)
- Can connect to ESPN API and initialize services

**Dependencies**: Phase 2 complete

### Phase 4: Separate Console Formatter (2-3 hours)

**Goal**: Create dedicated console formatter for season recap

**Tasks**:
- [ ] Create `ff_tracker/display/season_recap_console.py`
- [ ] Implement `SeasonRecapConsoleFormatter` class (inherits from `BaseFormatter`)
- [ ] Implement `format()` method with season recap layout:
  - Large banner header with year (fancy_grid table)
  - Regular season section (champions table, standings)
  - Season challenges section (all 5 challenges with details)
  - Playoff section (all rounds with brackets)
  - Championship section (leaderboard, overall champion)
  - Optional note table at top (if provided via format args)
- [ ] Implement private helper methods:
  - `_format_header()` - Banner with year
  - `_format_regular_season()` - Champions and standings
  - `_format_season_challenges()` - Challenge winners list
  - `_format_playoffs()` - Playoff brackets for all rounds
  - `_format_championship()` - Championship leaderboard
  - `_format_note()` - Optional note display
- [ ] Use tabulate with `fancy_grid` style
- [ ] Add emojis for visual appeal (🏆, 📅, 🏅, 🏈, 🥇, 🥈, 🥉)
- [ ] Handle partial recaps (missing championship)
- [ ] Test with real ESPN data

**Deliverable**: Separate console formatter renders beautiful season recap

**Validation**:
- `SeasonRecapConsoleFormatter` instantiates correctly
- `format()` method produces complete output
- All sections present and formatted clearly
- Emojis display correctly
- Missing championship shows appropriate message
- No dependencies on weekly formatter code

**Dependencies**: Phase 3 complete

### Phase 5: Other Separate Formatters (2-3 hours)

**Goal**: Create dedicated formatters for all other output types

**Tasks**:
- [ ] Create `ff_tracker/display/season_recap_sheets.py`:
  - `SeasonRecapSheetsFormatter` class
  - `format()` method returning TSV
  - TSV sections with headers
  - Separate tables for champions, challenges, playoffs, championship
  - Optional note as first row
- [ ] Create `ff_tracker/display/season_recap_email.py`:
  - `SeasonRecapEmailFormatter` class
  - `format()` method returning HTML
  - Responsive HTML with mobile-first design
  - Collapsible sections
  - Color-coded phases (blue=regular, orange=playoffs, gold=championship)
  - Optional note alert box
  - Footer with generation timestamp
- [ ] Create `ff_tracker/display/season_recap_json.py`:
  - `SeasonRecapJsonFormatter` class
  - `format()` method returning JSON
  - Structured data matching `SeasonSummary` model exactly
  - Version field: "1.0"
  - Optional metadata with note
- [ ] Create `ff_tracker/display/season_recap_markdown.py`:
  - `SeasonRecapMarkdownFormatter` class
  - `format()` method returning Markdown
  - Clean tables with proper formatting
  - H2 headers for sections
  - Medal emojis for championship (🥇🥈🥉)
  - Optional note blockquote
- [ ] Update `ff_tracker/display/factory.py`:
  - Add `create_season_recap_formatter()` function
  - Import all new formatter classes
- [ ] Update `ff_tracker/display/__init__.py` to export new formatters
- [ ] Test all formatters with same data
- [ ] Verify format arguments work (note, etc.)

**Deliverable**: All 5 separate formatters support season recap

**Validation**:
- Each formatter class instantiates independently
- Each `format()` method produces valid output
- Structure consistent across formats
- Format arguments work correctly
- Partial recaps handled gracefully
- Multi-output mode generates all files
- No code shared with weekly/playoff formatters (except BaseFormatter)

**Dependencies**: Phase 4 complete

### Phase 6: Integration Testing (2-3 hours)

**Goal**: End-to-end testing with real and mock data

**Tasks**:
- [ ] Test with real 2024 season data (if available, or mock)
- [ ] Test all CLI arguments:
  - `--env` with `LEAGUE_IDS`
  - `--year 2024`
  - `--format console` (and other formats)
  - `--output-dir ./test-recap`
  - `--force` (with incomplete season)
  - `--format-arg note="Test message"`
- [ ] Test error scenarios:
  - No league IDs
  - Invalid year
  - Incomplete season without --force
  - ESPN API failure
- [ ] Test partial recap mode (--force):
  - Verify warnings displayed
  - Verify missing sections handled
- [ ] Test with multiple divisions (1, 2, 3+)
- [ ] Verify data accuracy against `ff-tracker` and `ff-championship` outputs
- [ ] Performance test (should complete in < 30 seconds for 3 divisions)

**Deliverable**: Fully tested season recap feature

**Validation**:
- All acceptance criteria from spec verified
- Data matches existing scripts exactly
- Error handling works correctly
- Performance meets requirements
- All output formats generate correctly

**Dependencies**: Phase 5 complete

### Phase 7: Documentation (1 hour)

**Goal**: Update project documentation

**Tasks**:
- [ ] Update main `README.md` with season recap usage
- [ ] Add season recap examples to README
- [ ] Update `CHANGELOG.md` with v3.3 changes
- [ ] Verify `quickstart.md` in spec directory is accurate
- [ ] Add any necessary troubleshooting tips
- [ ] Update project version in `pyproject.toml` (3.3.0)

**Deliverable**: Complete documentation for season recap feature

**Validation**:
- README clearly explains season recap
- Examples work when copy-pasted
- CHANGELOG accurately describes changes
- Version updated correctly

**Dependencies**: Phase 6 complete

**OPTIONAL** Phase 8: GitHub Actions Integration (1 hour) - Not required for v1

**Goal**: Add automated season recap workflow

**Tasks**:
- [ ] Create `.github/workflows/season-recap.yml`
- [ ] Manual trigger only (workflow_dispatch)
- [ ] Support year input parameter
- [ ] Generate all 5 formats
- [ ] Upload artifacts with 365-day retention
- [ ] Optional email sending (like championship workflow)

**Deliverable**: Automated season recap generation via GitHub Actions

**Validation**:
- Workflow can be manually triggered
- All formats generated correctly
- Artifacts uploaded successfully

**Dependencies**: Phase 7 complete

**Note**: This phase is optional for v1. Can be added later if desired.

---

## Risk Assessment

### Risk 1: Data Accuracy Mismatch

**Likelihood**: Medium
**Impact**: High (would undermine trust in tool)
**Mitigation**: 
- Reuse existing, proven services (`ChallengeCalculator`, `ChampionshipService`, playoff logic)
- Compare outputs against `ff-tracker` and `ff-championship` during testing
- Use identical ESPN API calls and data structures
**Fallback**: If discrepancies found, investigate and fix in shared services (benefits all scripts)

### Risk 2: Season Structure Variability

**Likelihood**: Low (most leagues follow standard structure)
**Impact**: Medium (recap might show wrong weeks)
**Mitigation**:
- Dynamic detection from ESPN API settings
- No hardcoded week numbers or playoff lengths
- Clear error messages if unexpected structure encountered
**Fallback**: Add validation to warn about non-standard structures

### Risk 3: Incomplete Data Handling Complexity

**Likelihood**: Low (--force flag handles this)
**Impact**: Low (testing only, not production use)
**Mitigation**:
- Clear separation between normal and force modes
- Explicit warnings when generating partial recaps
- Each section independently optional
**Fallback**: If force mode proves problematic, can remove and require complete season

### Risk 4: Formatter Complexity

**Likelihood**: Low (formatters are well-established pattern)
**Impact**: Low (one formatter failing doesn't affect others)
**Mitigation**:
- Each formatter independent
- Can implement incrementally (start with console, add others)
- Existing formatters provide proven patterns
**Fallback**: Ship with subset of formatters if time constrained (e.g., console + JSON only)

### Risk 5: Performance Degradation

**Likelihood**: Low (data volume same as existing scripts)
**Impact**: Low (recap is run once after season)
**Mitigation**:
- Reuse existing efficient ESPN API patterns
- Single API call per league
- No additional data fetching beyond existing scripts
**Fallback**: If performance issues arise, can add caching or optimize queries

---

## Testing Strategy

### Unit Testing

**Scope**: Individual methods and functions

**Test Cases**:
- **Data Models**:
  - Valid data creates models successfully
  - Invalid data raises `DataValidationError`
  - Computed properties work correctly
  - Immutability enforced (can't modify fields)
- **Season Structure Calculation**:
  - Correct weeks calculated from various league settings
  - Edge cases (different regular season lengths, playoff rounds)
- **Season Validation**:
  - Correctly identifies complete vs incomplete seasons
  - Force flag behavior works correctly
  - Available sections dictionary accurate
- **Division Name Extraction**:
  - Uses ESPN name when available
  - Falls back to "Division N" when missing
  - Handles special characters in names

### Integration Testing

**Scope**: End-to-end data flow

**Test Cases**:
- **Regular Season Extraction**:
  - Champions identified correctly (highest record)
  - Standings include all teams
  - Data matches `ff-tracker` output exactly
- **Season Challenges**:
  - All 5 challenges calculated correctly
  - Results match `ff-tracker` output exactly
- **Playoff Extraction**:
  - All rounds detected and extracted
  - Brackets match `ff-tracker` playoff output exactly
- **Championship Extraction**:
  - Division winners identified correctly
  - Leaderboard matches `ff-championship` output exactly
- **Complete Flow**:
  - Full season summary generated successfully
  - All sections present and accurate
  - Multi-output mode creates all files

### Validation Against Spec

**Acceptance Criteria Verification**:

**US-1: View Complete Season Summary**
- [ ] Shows regular season division champions (highest ranked teams by record)
- [ ] Shows all 5 season challenge winners with details
- [ ] Shows playoff results for all divisions (semifinals and finals)
- [ ] Shows championship week results with overall champion
- [ ] Available in all 5 output formats
- [ ] Clearly structured with distinct sections for each phase

**US-2: Share Season Recap with League Members**
- [ ] Email format optimized for mobile viewing
- [ ] Markdown format ready for Slack/Discord posting
- [ ] JSON format for archival/analysis
- [ ] Console format for quick viewing
- [ ] Sheets format for manual manipulation

**US-3: Archive Season Results**
- [ ] All formats include year/season identifier
- [ ] JSON format includes all raw data for analysis
- [ ] File naming includes season year for easy archival (when using --output-dir)
- [ ] Can run for previous seasons (not just current)

**Functional Requirements**:
- [ ] FR-001: Regular season summary with dynamic week detection
- [ ] FR-002: All 5 season challenge winners displayed
- [ ] FR-003: Playoff results with dynamic round detection
- [ ] FR-004: Championship results with dynamic week calculation
- [ ] FR-005: All 5 output formats working
- [ ] FR-006: CLI interface with all specified arguments
- [ ] FR-007: Data validation with --force flag support

**Edge Cases**:
- [ ] Incomplete season without --force shows error
- [ ] Incomplete season with --force shows warnings
- [ ] Missing championship data handled gracefully
- [ ] Multiple divisions (1, 2, 3+) all work
- [ ] Non-standard league structures (different playoff lengths)

### Manual Testing Checklist

**Before Release**:
- [ ] Test with real 2024 season data (after Week 17)
- [ ] Compare outputs to existing script reports for accuracy
- [ ] Test all CLI arguments individually
- [ ] Test all error scenarios
- [ ] Test all output formats
- [ ] Test multi-output mode
- [ ] Test format arguments (note, etc.)
- [ ] Verify help text is accurate and helpful
- [ ] Performance test with 3+ divisions
- [ ] Test on clean Python environment

---

## Performance Considerations

**Expected Load**: 
- 3-4 divisions typical
- 30-40 teams total
- 180+ games regular season + playoffs
- Full season data (Weeks 1-17)

**Performance Target**: Complete recap generation in < 30 seconds for 3 divisions

**Current Baseline**:
- `ff-tracker`: ~3-5 seconds for 3 divisions
- `ff-championship`: ~2-3 seconds for 3 divisions
- Season recap combines both: ~5-8 seconds expected

**Optimization Strategy**:
- Reuse ESPN API connections (context manager)
- Single API call per league (no redundant requests)
- Efficient data structures (immutable models, no defensive copying)
- Lazy evaluation where possible (computed properties)
- No caching needed (run once after season)

**Performance Budget**:
- ESPN API calls: 1 per league (3-4 total)
- Data extraction: < 2 seconds
- Challenge calculation: < 1 second (reuse existing)
- Playoff extraction: < 1 second (reuse existing)
- Championship calculation: < 1 second (reuse existing)
- Formatting: < 2 seconds per format
- Total: < 30 seconds for worst case (3 divisions, all formats)

**Monitoring**:
- Add timing logs during development
- Measure actual performance during integration testing
- Optimize if targets not met (unlikely)

---

## Security Considerations

**No new security concerns introduced.**

Season recap uses:
- Same ESPN API authentication as existing scripts
- Same environment variable handling (ESPN_S2, SWID)
- No user input beyond league IDs (already validated)
- No external network calls beyond ESPN API
- No file system operations beyond --output-dir (user-controlled)

**Existing Security Practices Maintained**:
- Private league credentials via environment variables only
- No credentials in command-line arguments (visible in process list)
- No credentials in output files
- Fail-fast on authentication errors with clear guidance

---

## Complexity Tracking

> This section documents any deviations from the constitution.

**No constitutional violations in this implementation.**

System maintains all constitutional principles:
- ✅ Article I: 100% type coverage, zero `Any` types
- ✅ Article II: Immutable models with `__post_init__` validation
- ✅ Article III: Fail-fast error handling with clear messages
- ✅ Article IV: Clean layer separation (Models → Services → Display)
- ✅ Article V: Efficient API usage, reuse connections
- ✅ Article VI: All formatters receive identical data
- ✅ Article VII: Self-documenting code with types and names
- ✅ Article VIII: Behavior defined by specifications
- ✅ Article IX: CLI follows established conventions
- ✅ Article X: Performance requirements met

**Design Notes**:
- Separate script maintains single responsibility (Article IV)
- Reuses existing services maximizes code reuse (Article V)
- Dynamic season detection avoids hardcoded assumptions (Article VIII)
- Force flag enables testing without compromising normal behavior (Article III)

---

## Open Technical Questions

**All questions resolved during spec approval.**

Resolved decisions documented in [DECISIONS.md](./DECISIONS.md):
1. ✅ Season structure detection: Fully dynamic from ESPN API
2. ✅ Incomplete data handling: Flexible with --force flag
3. ✅ Division names: Hybrid approach (ESPN or fallback)
4. ✅ Historical persistence: Multi-output mode saves JSON
5. ✅ Season awards: Not in v1 (focus on core facts)

**No remaining technical uncertainties.**

---

## Related Documentation

- **Feature Spec**: [spec.md](./spec.md) - Complete functional specification
- **Design Decisions**: [DECISIONS.md](./DECISIONS.md) - Architectural decisions explained
- **Quick Reference**: [README.md](./README.md) - Overview and key features
- **User Guide**: [quickstart.md](./quickstart.md) - Usage examples and troubleshooting
- **Project Constitution**: [../../memory/constitution.md](../../memory/constitution.md) - Development principles

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-12-29 | Modern Architect | Initial implementation plan with all phases and architectural decisions |
