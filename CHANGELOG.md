# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.3.0] - 2025-12-29 (Season Recap Feature)

### Added - Season Recap 📊
- **New Command**: `ff-season-recap` - Generate comprehensive end-of-season summaries
  - Combines regular season results, playoffs, and championship into one cohesive report
  - Available in all 5 output formats (console, sheets, email, json, markdown)
  - Multi-output mode support (`--output-dir`) for generating all formats at once
  - Format arguments support (`--format-arg`) for customization

- **Complete Season Coverage**:
  - **Regular Season**: Division champions, final standings, and all 5 season challenge winners
  - **Playoff Brackets**: Semifinals (Week 15) and Finals (Week 16) with all matchups and winners
  - **Championship**: Week 17 leaderboard ranking all division winners, crowns overall champion

- **New Data Models** (`ff_tracker/models/season_summary.py`):
  - `SeasonSummary`: Top-level container for entire season
  - `RegularSeasonSummary`: Regular season standings and challenges
  - `PlayoffSummary`: Complete playoff bracket data
  - `PlayoffRound`: Individual round (Semifinals or Finals) with matchups
  - `DivisionChampion`: Week 17 championship participant data
  - `SeasonStructure`: Season configuration (weeks, playoff detection)

- **New Service Layer** (`ff_tracker/services/season_recap_service.py`):
  - `SeasonRecapService`: Orchestrates data collection across all ESPN leagues
  - Dynamic season structure detection from ESPN API (no hardcoded weeks)
  - Intelligent season status detection (regular_season, semifinals, finals, championship, complete)
  - `--force` flag support for generating partial recaps during playoffs (testing/progress tracking)

- **New Display Formatters**:
  - `SeasonRecapConsoleFormatter`: Human-readable tables with emojis and visual hierarchy
  - `SeasonRecapSheetsFormatter`: TSV format optimized for Google Sheets import
  - `SeasonRecapEmailFormatter`: Mobile-friendly HTML with responsive design
  - `SeasonRecapJsonFormatter`: Structured JSON for archival and analysis
  - `SeasonRecapMarkdownFormatter`: GitHub/Slack/Discord-compatible with optional TOC

- **CLI Features**:
  - Same league input options as `ff-tracker` (CLI args, `--env`, single/multiple leagues)
  - `--year` support for historical season recaps
  - `--private` flag for private league authentication
  - `--force` flag to generate partial recaps (with clear warnings)
  - `--format` to choose output format
  - `--output-dir` to generate all formats at once
  - `--format-arg` for customization (notes, colors, TOC, etc.)
  - `-v`/`--verbose` and `--debug` for logging control

- **GitHub Actions Integration**:
  - New workflow: `season-recap.yml` for automated season recap generation
  - Manual trigger only (`workflow_dispatch`) - run after season completes
  - Workflow inputs: `season_year`, `email_recipients`, `email_from`, `skip_email`, `recap_note`, `force_generation`
  - Generates all 5 output formats in single execution
  - Optional email delivery with mobile-friendly HTML
  - Artifacts uploaded with 365-day retention for historical records

### Changed
- **Display Order**: Season recap now shows results in reverse chronological order for better narrative flow
  - Order: Championship → Finals → Semifinals → Regular Season
  - Tells the story from climax backwards, showing the journey that led to the final result
  - Applied consistently across all 5 output formats (console, sheets, email, json, markdown)

### Fixed
- **Championship Data Fetching**: Fixed season recap not showing Week 17 championship results during Finals week
  - ESPN reports `current_week=16` during Finals, but Week 17 roster data is available via `team.roster` API
  - Changed championship fetch logic to attempt extraction whenever playoffs have started (not just when current_week >= 17)
  - Matches behavior of `ff-championship` script which successfully pulls Week 17 data
  - Championship leaderboard now displays correctly in all 5 output formats during Finals week
- **Logging Configuration**: Fixed `season_recap.py` passing logging level constants instead of verbosity integers
  - Changed from `setup_logging(logging.DEBUG)` to `setup_logging(2)` 
  - Aligns with `main.py` and `championship.py` implementations
  - Clean output without DEBUG logs unless `--debug` flag used
  - Added `urllib3` logger suppression to `cli_utils.py`

### Documentation
- **README.md**: Added comprehensive Season Recap section with usage examples
- **MANUAL_TESTING_GUIDE.md**: Step-by-step testing procedures for all scenarios
- **PHASE6_TESTING.md**: Complete integration test results documentation
- **Spec 008**: Full specification, planning, and implementation documentation

### Technical Details
- **Zero Breaking Changes**: Existing `ff-tracker` functionality unchanged
- **Shared Infrastructure**: Reuses ESPNService, models, and display factory
- **Type Safety**: 100% type coverage with modern Python 3.9+ syntax
- **Modular Architecture**: Clean separation of concerns (models → service → CLI → formatters)
- **Performance**: Efficient multi-league data collection with single ESPN API session
- **Error Handling**: Clear error messages with actionable guidance

## [3.1.0] - 2024-12-23 (Week 16 - Finals Fix)

### Fixed
- **Playoff Week Detection**: Fixed bug where tool showed Week 15 data on Tuesday after Week 16 Monday Night Football finished
  - Changed `_determine_max_week()` to check current week first in playoffs, then fall back to previous week if incomplete
  - Previously checked `current_week - 1` which missed completed playoff weeks
  - Now correctly shows Week 16 Finals data on Tuesday Dec 23 instead of Week 15 Semifinals
  - Handles both scenarios: Tuesday after MNF (shows just-completed week) and Tuesday before TNF (falls back)
  - Updated tests to properly validate week-specific behavior

### Changed
- **GitHub Actions Workflow**: Disabled scheduled cron runs for end of 2024-2025 season
  - Automatic Tuesday morning emails paused (can be re-enabled by uncommenting schedule)
  - Manual `workflow_dispatch` trigger still available for testing and historical reports
  - Updated hardcoded note for final week messaging

## [3.0.0] - 2025-12-09 (Week 15 - Playoffs Begin)

### Added - Playoff Mode 🏆
- **Automatic Playoff Detection**: Tool now automatically detects and displays playoff brackets when `current_week > reg_season_count`
  - No manual flags required - seamless transition from regular season to playoffs
  - Validates all divisions are in sync (same week and playoff state)
  - Raises clear `DivisionSyncError` if divisions are out of sync

- **Playoff Bracket Display** (Weeks 15-16):
  - **Semifinals (Week 15)**: Shows 2 matchups per division (#1 vs #4, #2 vs #3)
  - **Finals (Week 16)**: Shows 1 matchup per division (winners of semifinals)
  - Displays seeds, team names, owners, scores, and winner indicators
  - Handles in-progress games (shows scores as-is, "TBD" before games start)
  - Winners bracket only (consolation games excluded per spec)

- **Championship Week Display** (Week 17):
  - Championship leaderboard ranking all division winners by score
  - Trophy banner and medal emojis (🥇🥈🥉) for top 3 finishers
  - Overall champion prominently highlighted
  - Player highlights include ALL teams (not just division winners)

- **Playoff-Adapted Weekly Highlights**:
  - **Regular Season**: Shows all 13 challenges (6 team + 7 player)
  - **Semifinals/Finals**: Shows only 7 player highlights (team challenges excluded - playoff brackets provide context)
  - **Championship Week**: Shows all 7 player highlights across entire league

- **Historical Context Labels**:
  - Season challenges marked as "REGULAR SEASON FINAL RESULTS (Historical)" during playoffs
  - Standings shown as "FINAL REGULAR SEASON STANDINGS" to clarify data is frozen
  - Regular season stats preserved for end-of-season awards

- **New Data Models**:
  - `PlayoffMatchup`: Immutable playoff game data with validation
  - `PlayoffBracket`: Container for round matchups (Semifinals/Finals)
  - `ChampionshipEntry`: Division winner with championship week score
  - `ChampionshipLeaderboard`: Ranked list of all division winners
  - `DivisionData.is_playoff_mode`: Property to check playoff state

- **All 5 Output Formats Support Playoffs**:
  - **Console**: Beautiful Unicode tables with playoff brackets
  - **Sheets (TSV)**: Structured playoff data for Google Sheets import
  - **Email (HTML)**: Responsive mobile-friendly playoff brackets with styling
  - **JSON**: Structured playoff data with `report_type` field
  - **Markdown**: GitHub/Slack/Discord-ready playoff tables

### Changed
- **Display Order During Playoffs**:
  - **Semifinals/Finals**: Brackets → Player Highlights → Season Challenges (Historical) → Final Standings
  - **Championship Week**: Championship Leaderboard → Player Highlights → Season Challenges (Historical)
  - Regular season standings moved to end and marked as "final"

- **Weekly Challenge Filtering**:
  - Team challenges (Highest/Lowest Score, Biggest Win, Closest Game, Overachiever, Below Expectations) hidden during playoffs
  - Reasoning: Playoff brackets provide comprehensive team performance context
  - Player highlights remain visible to celebrate individual performances

- **DivisionData Model**: Added optional `playoff_bracket` field (defaults to None for regular season)

### Technical Details
- **Playoff Detection Logic**: `league.current_week > league.settings.reg_season_count`
- **Playoff Rounds**:
  - Week 15 (playoff_week=1): Semifinals
  - Week 16 (playoff_week=2): Finals
  - Week 17 (playoff_week=3): Championship Week
- **Division Sync Validation**: Ensures all leagues are in same week and playoff state
- **ESPN API Filtering**: Uses `is_playoff=True` and `matchup_type=="WINNERS_BRACKET"` to identify playoff games
- **Seeding**: Extracted from `team.standing` (1-4 for playoff teams)
- **Architectural Design**: All playoff features are additive - zero modifications to existing regular season code paths
- **Code Quality**: 100% type coverage, all linting rules passing, zero suppressions

### Testing
- ✅ **Week 15 (Semifinals)**: Fully tested with real ESPN data (December 9, 2025)
  - All 5 formatters working perfectly
  - 3 divisions × 2 semifinals = 6 matchups displayed correctly
  - Playoff brackets, filtered challenges, and historical labels all verified
- ⏳ **Week 16 (Finals)**: Scheduled for testing on December 17, 2025
- ⏳ **Week 17 (Championship)**: Scheduled for testing on December 24, 2025
- ✅ **Regular Season Regression**: Code review confirms zero impact on regular season functionality
  - All playoff code gated behind `is_playoff_mode` checks
  - Challenge services unchanged (git diff shows zero modifications)
  - DivisionData changes are purely additive (optional field + property)

### Performance
- Execution time: ~25-27 seconds for 3 leagues (playoff mode)
- Playoff overhead minimal: just additional box_scores queries for matchups
- No performance degradation compared to regular season operation

### Breaking Changes
- None - playoff mode activates automatically based on league week
- Regular season functionality completely preserved
- All existing CLI arguments and output formats unchanged

## [2.3.0] - 2025-11-13

### Added
- **Format Arguments System**: Generic `--format-arg` CLI option for passing formatter-specific parameters
  - Supports both global arguments (e.g., `--format-arg note="Important message"`)
  - Supports formatter-specific arguments (e.g., `--format-arg email.accent_color="#007bff"`)
  - Can be specified multiple times to pass multiple arguments
  - Each formatter declares supported arguments via `get_supported_args()` classmethod

- **Note Feature Across All Formats**:
  - **Console**: Displays note in fancy Unicode table at the top of output
  - **Email**: Shows note in styled alert box with warning icon
  - **Markdown**: Renders note as blockquote with warning emoji
  - **JSON**: Includes note in metadata section of JSON output
  - **Sheets**: Includes note as first row in TSV output

- **Formatter-Specific Arguments**:
  - **Email Formatter**: `note`, `accent_color` (customize border colors), `max_teams` (limit top teams display)
  - **Markdown Formatter**: `note`, `include_toc` (generate table of contents)
  - **Console Formatter**: `note` (displayed with tabulate fancy_grid)
  - **JSON Formatter**: `note`, `pretty` (enable indented JSON output)
  - **Sheets Formatter**: `note` (included as first row)

- **GitHub Actions Integration**: Added `weekly_note` input to workflow_dispatch for manual report customization

### Changed
- **Base Formatter Architecture**: All formatters now inherit format arguments support
  - Added `format_args` parameter to `BaseFormatter.__init__()`
  - Added helper methods: `_get_arg()`, `_get_arg_bool()`, `_get_arg_int()`
  - Formatters automatically receive merged global and formatter-specific arguments

- **CLI Interface**: Enhanced argument parsing for format-arg syntax
  - Added `parse_format_args()` function to parse key=value pairs
  - Added `get_formatter_args()` function to merge global and formatter-specific args
  - Updated `create_formatter()` to accept and pass format_args_dict

### Technical Details
- Format arguments use nested dictionary structure: `{"_global": {...}, "formatter_name": {...}}`
- Argument merging prioritizes formatter-specific values over global values
- Unicode width handling in console formatter uses tabulate library for proper emoji/character display
- All formatters maintain backward compatibility when no format args are provided

## [2.2.1] - 2025-11-10

### Fixed
- **Email Formatter**: Added spacing between Team Challenges and Player Highlights tables in weekly highlights section
  - Tables now have 15px margin separation for improved readability
  - Last table in section no longer has bottom margin to maintain consistent container padding

## [2.2.0] - 2025-11-03

### Added
- **True Projection Tracking**: New starter-based projection system that calculates pre-game projections by summing individual player projections
  - Added `starter_projected_score` field to `WeeklyGameResult` model
  - Added `true_projection_diff` field for accurate boom/bust analysis
  - Implemented `_calculate_starter_projections()` method in `ESPNService`
  - Projections are calculated from starters only (excludes bench players)

- **Two New Weekly Challenges**:
  - **Overachiever**: Team that most exceeded their pre-game starter projections
  - **Below Expectations**: Team that most underperformed their pre-game starter projections
  - Both challenges use `true_projection_diff` for accurate pre-game vs actual comparison

- **Enhanced JSON Output**:
  - Added `weekly_games` array to JSON export containing all weekly game data
  - Includes both ESPN's real-time projections and true starter projections
  - Fields: `score`, `projected_score`, `starter_projected_score`, `projection_diff`, `true_projection_diff`

### Changed
- Updated weekly challenge count from 11 to 13 (4→6 team challenges, 7 player challenges unchanged)
- Weekly challenge calculator now conditionally calculates projection-based challenges only when data is available

### Technical Details
- ESPN updates team projections in real-time during games, making post-game comparisons unreliable
- New system sums pre-game player projections for more accurate boom/bust tracking
- Example: Team scored 108.24 with ESPN showing 121.34 projected, but true starter projection was 142.57
  - ESPN diff: -13.10 (misleading - projection was adjusted down 21 points during games)
  - True diff: -34.33 (accurate - actual underperformance vs pre-game expectations)

## [2.1.0] - 2025-11-02

### Added
- **11 Weekly Highlights Feature**: Real-time weekly performance tracking
  - 4 team challenges: Highest/Lowest Score, Biggest Win, Closest Game
  - 7 player highlights: Top scorer overall and by position (QB/RB/WR/TE/K/D/ST)
  - Separated display tables for team and player challenges
  - Only includes starting lineup players (bench excluded)

- **Multi-Output Mode**: Generate all formats in single execution
  - New `--output-dir` flag generates all 5 formats with one API call
  - 66% reduction in API calls for automated workflows
  - Output files: `standings.txt`, `standings.tsv`, `standings.html`, `standings.json`, `standings.md`

### Changed
- Removed 4 projection-based challenges due to ESPN's real-time projection updates
- Updated documentation to reflect new challenge counts
- Improved GitHub Actions workflow efficiency

### Fixed
- Enhanced weekly data extraction with proper BoxScore API usage
- Improved margin calculations for wins/losses

## [2.0.0] - 2025-10-XX

### Added
- Complete refactor from 1000+ line script to modular architecture
- Type-safe data models with comprehensive validation
- Multiple output formatters: Console, Sheets, Email, JSON, Markdown
- Playoff positioning indicators
- Multi-league support via CLI or environment variables
- Extensive error handling with custom exception hierarchy

### Changed
- Migrated to modern Python package structure
- Implemented Protocol-based formatter pattern
- Enhanced configuration management with dataclasses

### Technical
- 100% type coverage with Python 3.9+ syntax
- Zero `Any` types or `# type: ignore` suppressions
- Comprehensive docstrings throughout
- Modular service/model/display architecture

## [1.0.0] - Initial Release

### Added
- Basic ESPN league analysis
- 5 season challenges tracking
- Single league support
- Console output only
