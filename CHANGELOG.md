# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
