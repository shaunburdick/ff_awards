# Fantasy Football Challenge Tracker - Agent Summary

## Project Overview
A CLI tool to track 13 weekly highlights and 5 season-long fantasy football challenges across multiple ESPN leagues for end-of-season awards. Originally built as a single 1000+ line script, it has been completely refactored into a modern Python package demonstrating best practices.

## Current Architecture

### Package Structure
```
ff_tracker/
├── __init__.py              # Package exports
├── __main__.py              # Module entry point
├── main.py                  # CLI implementation
├── config.py                # Configuration management
├── exceptions.py            # Custom exception hierarchy
├── models/
│   ├── __init__.py          # Type-safe data models
│   ├── base.py              # Base model classes
│   ├── challenge.py         # ChallengeResult model
│   ├── division.py          # DivisionData model
│   ├── game.py              # GameResult model
│   ├── owner.py             # Owner model
│   ├── team.py              # TeamStats model
│   ├── week.py              # WeeklyGameResult model
│   ├── player.py            # WeeklyPlayerStats model
│   └── weekly_challenge.py  # WeeklyChallenge model
├── services/
│   ├── __init__.py          # Service exports
│   ├── espn_service.py      # ESPN API integration
│   ├── challenge_service.py # Season challenge calculation
│   └── weekly_challenge_service.py  # Weekly challenge calculation
└── display/
    ├── __init__.py          # Formatter exports
    ├── base.py              # Base formatter protocol
    ├── console.py           # Console table output
    ├── sheets.py            # TSV for Google Sheets
    ├── email.py             # Mobile-friendly HTML
    ├── json.py              # Structured JSON output
    └── markdown.py          # Markdown for GitHub/Slack/Discord
```

### Core Functionality
- **Input**: Single league ID, multiple leagues via comma-separated CLI argument, or `LEAGUE_IDS` environment variable
- **Output**: Five formats (console tables, TSV for sheets, HTML for email, JSON for APIs, Markdown for GitHub/Slack/Discord)
- **Multi-Output Mode**: Generate all formats at once with `--output-dir` (single API call)
- **Format Arguments**: Generic `--format-arg` system for passing formatter-specific parameters (v2.3)
- **Data Source**: ESPN Fantasy Football API (via espn-api Python library)
- **Multi-League Support**: Handles 3-4 leagues typically, tested with 30+ teams
- **Playoff Positioning**: Shows current playoff qualification status (top 4 by record, points-for tiebreaker)
- **Weekly Highlights**: Tracks current week's top team and player performances (13 total challenges)
- **True Projection Tracking**: Uses pre-game starter projections for accurate boom/bust analysis (v2.2)

### The 13 Weekly Highlights ✅ All Working (v2.2)
**Team Challenges (6):**
1. **Highest Score This Week** - Team with most points this week
2. **Lowest Score This Week** - Team with fewest points this week
3. **Biggest Win This Week** - Largest margin of victory (displays: "148.78 - 49.00 (Δ99.78)")
4. **Closest Game This Week** - Smallest margin (displays: "107.00 - 98.92 (Δ8.08)")
5. **Overachiever** - Team that most exceeded pre-game starter projections (NEW v2.2)
6. **Below Expectations** - Team that most underperformed pre-game starter projections (NEW v2.2)

**Player Highlights (7):**
7. **Top Scorer (Player)** - Highest scoring player across all positions
8. **Best QB** - Top quarterback performance
9. **Best RB** - Top running back performance
10. **Best WR** - Top wide receiver performance
11. **Best TE** - Top tight end performance
12. **Best K** - Top kicker performance
13. **Best D/ST** - Top defense/special teams performance

### The 5 Season Challenges ✅ All Working
1. **Most Points Overall** - Team with most total regular season points
2. **Most Points in One Game** - Highest single week score
3. **Most Points in a Loss** - Highest score in a losing effort
4. **Least Points in a Win** - Lowest score that still won the game
5. **Closest Victory** - Smallest winning margin

## Technical Implementation

### Modern Python Features Used
- **Type Safety**: 100% type coverage with Python 3.9+ syntax (`str | None`)
- **Future Annotations**: `from __future__ import annotations` throughout
- **Data Classes**: Properly validated with `__post_init__` methods
- **Protocol Pattern**: For extensible formatter interfaces
- **Context Managers**: Proper resource management
- **Custom Exceptions**: Hierarchical error handling

### CLI Interface
```bash
# Single league
uv run ff-tracker 123456 --format console
uv run ff-tracker 123456 --year 2024 --private

# Multiple leagues via CLI (comma-separated)
uv run ff-tracker 123456789,987654321,678998765
uv run ff-tracker 123456789,987654321 --private --format email

# Multiple leagues from environment
uv run ff-tracker --env --format email
uv run ff-tracker --env --private --format sheets

# Multi-output mode (generates all formats in one execution)
uv run ff-tracker --env --private --output-dir ./reports
uv run ff-tracker 123456789,987654321 --output-dir ./reports
# Creates: standings.txt, standings.tsv, standings.html, standings.json, standings.md

# Format arguments (v2.3 - NEW)
--format-arg note="Playoffs start next week!"  # Global argument (all formats)
--format-arg email.accent_color="#007bff"      # Formatter-specific argument
--format-arg markdown.include_toc=true         # Enable table of contents
--format-arg json.pretty=true                  # Pretty-print JSON
--format-arg email.max_teams=5                 # Limit top teams display

# Output formats
--format console   # Human-readable tables (default)
--format sheets    # TSV for Google Sheets
--format email     # Mobile-friendly HTML
--format json      # Structured JSON for APIs
--format markdown  # Markdown for GitHub/Slack/Discord
--output-dir DIR   # Generate all formats to directory (single API call)
```

### Environment Configuration
```bash
# Required for multi-league operation
LEAGUE_IDS=123456789,987654321,555444333

# Required for private leagues
ESPN_S2=your_espn_s2_cookie
SWID=your_swid_cookie
```

## Key Components

### 1. Data Models (`ff_tracker/models/__init__.py`)
- **GameResult**: Individual game data with validation
- **WeeklyGameResult**: Single week matchup data (team scores, margins, projections)
- **WeeklyPlayerStats**: Individual player weekly performance (points, position, team)
- **TeamStats**: Season statistics with computed properties and playoff positioning
- **ChallengeResult**: Season challenge winners with details
- **WeeklyChallenge**: Weekly challenge winners with flexible additional_info
- **DivisionData**: Complete league information including weekly data
- All models use modern typing and validation

### 2. ESPN Service (`ff_tracker/services/espn_service.py`)
- **Connection Management**: Handles public/private league authentication
- **Data Extraction**: Teams, games, owner names with error handling
- **Weekly Data**: Extracts current week game results and player stats via BoxScore API
- **Playoff Calculation**: Determines top 4 teams by record with points_for tiebreaker
- **Context Manager**: Proper resource cleanup
- **Fail-Fast Strategy**: Clear errors on API failures

### 3. Challenge Calculators
**Season Challenges** (`ff_tracker/services/challenge_service.py`)
- **Business Logic**: Implements all 5 season challenge calculations
- **Game Analysis**: Processes individual game results for accuracy
- **Tie Handling**: First-to-achieve wins, with split support
- **Data Validation**: Ensures complete game data before calculation

**Weekly Challenges** (`ff_tracker/services/weekly_challenge_service.py`)
- **Team Challenges**: Highest/lowest scores, biggest win, closest game, overachiever, below expectations
- **Player Highlights**: Top scorer overall and by position (QB/RB/WR/TE/K/D/ST)
- **Starter Filtering**: Only includes players in starting lineups (excludes bench)
- **Detailed Scoring**: Shows both team scores and margins for context
- **Projection Tracking**: Overachiever/Below Expectations use true pre-game starter projections (v2.2)

### 4. Display System (`ff_tracker/display/`)
- **Extensible Architecture**: Protocol-based formatter pattern with format arguments support (v2.3)
- **Format Arguments**: All formatters inherit from `BaseFormatter` with `format_args` parameter
- **Separated Weekly Tables**: Team challenges and player highlights in distinct tables
- **Console Output**: Beautiful tables with emojis and playoff indicators (*), optional note display
- **Sheets Export**: Clean TSV format with separate sections for team/player challenges, optional note row
- **Email Format**: Mobile-friendly HTML with responsive design, optional note alert box, customizable colors
- **JSON Export**: Structured data with challenge_type field ("team" or "player"), weekly_games array (v2.2), optional metadata note
- **Markdown Format**: GitHub/Slack/Discord-ready tables with bold subheadings, optional note blockquote, optional TOC

### 5. Configuration (`ff_tracker/config.py`)
- **Environment Loading**: Automatic .env file detection
- **Credential Management**: ESPN authentication handling
- **Validation**: Comprehensive input validation with clear errors
- **Multi-League Support**: Parse comma-separated league IDs

### 6. Error Handling (`ff_tracker/exceptions.py`)
- **Custom Hierarchy**: `FFTrackerError` → `ESPNAPIError`, `ConfigurationError`
- **Fail-Fast Strategy**: No retry logic, clear error messages
- **User Guidance**: Actionable error messages for common issues

## Testing & Verification

### Functionality Verified ✅
- **Single League**: 10 teams, 60 games processed
- **Multi-League**: 3 divisions, 30 teams, 180+ games processed
- **All Challenges**: Accurate calculations across all game data (13 weekly + 5 season)
- **Weekly Highlights**: Team challenges and player highlights working correctly
- **True Projections**: Starter-based projections calculated for all teams (v2.2)
- **Output Formats**: Console, TSV, HTML, JSON, and Markdown all working perfectly
- **Playoff Positioning**: Accurate top 4 calculation with proper tiebreaking
- **Private Leagues**: Authentication and data extraction working
- **Error Handling**: Proper validation and user-friendly messages

### Performance Metrics
- **Game Processing**: Successfully handles 180+ individual game results
- **Weekly Data**: Processes current week's BoxScore data for all teams
- **Player Stats**: Filters and ranks starters across all positions
- **Projection Calculation**: Sums starter projections for 30+ teams per week (v2.2)
- **Team Rankings**: Accurate sorting across divisions and overall
- **Challenge Accuracy**: All 13 weekly + 5 season challenges calculated from real game data
- **Memory Usage**: Efficient processing with minimal memory footprint

## GitHub Actions Integration

### Weekly Automation (`weekly-report.yml`)
```yaml
# Generate all reports in one execution (v2.1 - NEW)
uv run ff-tracker --env --private --output-dir ./reports

# With format arguments (v2.3 - NEW)
uv run ff-tracker --env --private --output-dir ./reports \
  --format-arg note="Playoffs start next week!"

# Old approach (deprecated - kept for reference)
# uv run ff-tracker --env --private --format sheets > weekly-report.tsv
# uv run ff-tracker --env --private --format email > email_content.html
```

- **Multi-Output Mode (v2.1)**: Single execution generates all 5 formats with one API call
- **Efficiency Improvement**: Reduced from 3 API calls to 1 (~66% faster)
- **Output Files**: `standings.txt`, `standings.tsv`, `standings.html`, `standings.json`, `standings.md`
- **Format Arguments (v2.3)**: Optional `weekly_note` workflow input passed via `--format-arg note="..."`
- **Environment Integration**: Loads leagues from `LEAGUE_IDS` secret
- **Email Reports**: Mobile-friendly HTML with comprehensive league data
- **Artifacts**: All formats saved for 30 days in GitHub Actions

## Development Setup

### Prerequisites
- Python 3.9+ (for modern typing features)
- uv package manager (recommended) or pip
- ESPN league access (public or private with credentials)

### Installation
```bash
git clone <repository>
cd ff_awards
uv sync                    # Install dependencies
uv run ruff check .        # Lint code
uv run ff-tracker --help  # Test CLI
```

### Code Style
- **Linting**: Ruff with comprehensive rule set
- **Type Checking**: 100% coverage, no suppressions
- **Import Organization**: isort-compatible with modern practices
- **Documentation**: Comprehensive docstrings throughout

## Key Learnings & Architectural Decisions

### 1. ESPN API Data Access ✅ SOLVED
- **Challenge**: Original script struggled with game-by-game data extraction
- **Solution**: Improved ESPN service with proper error handling and data parsing
- **Result**: Successfully processes 180+ games across multiple leagues

### 2. Code Organization ✅ DRAMATICALLY IMPROVED
- **Before**: 1000+ line monolithic script
- **After**: ~20 focused files with single responsibilities
- **Benefit**: Much easier to maintain, test, and extend

### 3. Type Safety ✅ COMPLETE
- **Achievement**: Zero `Any` types or `# type: ignore` suppressions
- **Modern Syntax**: Uses Python 3.9+ features throughout
- **Educational Value**: Excellent example of Pythonic typing patterns

### 4. Error Handling ✅ ROBUST
- **Strategy**: Fail-fast with clear, actionable error messages
- **Implementation**: Custom exception hierarchy with context
- **User Experience**: Clear guidance on what went wrong and how to fix

### 5. Extensibility ✅ FUTURE-READY
- **Output Formats**: Easy to add new formatters via Protocol pattern
- **Challenge Types**: Simple to add new challenges to calculator
- **League Support**: Can handle additional leagues without code changes

### 6. Multi-Output Efficiency ✅ OPTIMIZED (v2.1)
- **Challenge**: GitHub Actions workflow made 3 separate API calls for different formats
- **Solution**: Added `--output-dir` flag to generate all formats in single execution
- **Result**: 66% reduction in API calls and execution time, more reliable workflows
- **Architecture**: Leverages existing modular formatter system with minimal changes

### 7. Weekly Highlights Feature ✅ IMPLEMENTED (v2.1)
- **Need**: Real-time weekly performance tracking alongside season-long challenges
- **Solution**: Added 11 weekly challenges (4 team + 7 player) with separate data models and calculator
- **Challenges Removed**: 4 projection-based challenges due to ESPN real-time projection updates
- **Display Innovation**: Separated team and player tables for clarity, shows detailed margins (Δ) for wins/losses
- **Result**: Comprehensive weekly insights with clean, intuitive presentation across all 5 output formats

### 8. True Projection Tracking ✅ IMPLEMENTED (v2.2)
- **Problem**: ESPN updates team projections in real-time as games progress, making post-game boom/bust analysis unreliable
- **Discovery**: Team that scored 108.24 showed ESPN projection of 121.34 (diff: -13.10), but true pre-game projection was 142.57 (diff: -34.33)
  - ESPN had adjusted projections DOWN by 21 points during games, hiding true underperformance
- **Solution**: Calculate "true" pre-game projections by summing individual starter projected points before games begin
- **Implementation**:
  - Added `_calculate_starter_projections()` method to sum starter projections (excludes bench)
  - Added `starter_projected_score` and `true_projection_diff` fields to `WeeklyGameResult`
  - Maintains both ESPN's real-time projection AND true pre-game projection for comparison
- **New Challenges**: Overachiever (most above) and Below Expectations (most below) using true projections
- **Data Export**: JSON format includes `weekly_games` array with both projection types for analysis
- **Result**: Accurate boom/bust tracking based on actual pre-game expectations vs real-time adjusted values

### 9. Format Arguments System ✅ IMPLEMENTED (v2.3)
- **Need**: Ability to customize formatter output (e.g., add weekly notes, customize colors, control display options)
- **Solution**: Generic `--format-arg` CLI system supporting both global and formatter-specific arguments
- **Architecture**:
  - Added `format_args` parameter to `BaseFormatter.__init__()`
  - Created helper methods: `_get_arg()`, `_get_arg_bool()`, `_get_arg_int()`
  - Added `parse_format_args()` and `get_formatter_args()` for argument parsing and merging
  - Each formatter declares supported arguments via `get_supported_args()` classmethod
- **Syntax**:
  - Global: `--format-arg note="Important message"` (applies to all formats)
  - Specific: `--format-arg email.accent_color="#007bff"` (applies only to email formatter)
- **Implementation**:
  - **Note Feature**: All formatters support optional note display at top of output
    - Console: Fancy Unicode table using tabulate with `fancy_grid` format
    - Email: Styled alert box with warning icon and customizable accent color
    - Markdown: Blockquote with warning emoji
    - JSON: Metadata section in JSON structure
    - Sheets: First row in TSV output
  - **Formatter-Specific Args**:
    - `email.accent_color`, `email.max_teams`
    - `markdown.include_toc`
    - `json.pretty`
- **GitHub Actions**: Added `weekly_note` workflow input for automated report customization
- **Unicode Handling**: Leveraged tabulate library for proper emoji width calculation
- **Result**: Flexible, extensible system for output customization without hardcoding formatter-specific logic

## Future Enhancement Opportunities

### Potential Improvements
1. **Owner Name Extraction**: Some challenge results show "Unknown Owner"
2. **Current Week Detection**: Could auto-detect fantasy football week
3. **Caching**: Add optional caching for faster repeated runs
4. **Historical Tracking**: Store weekly results for season-long trends
5. **Web Interface**: Could add simple web UI using current modular design

### Extension Points
- **New Output Formats**: Add PDF, Slack, Discord formatters
- **Additional Data Sources**: Framework supports other fantasy platforms
- **Enhanced Analytics**: More sophisticated challenge calculations (e.g., consistency metrics)
- **Database Storage**: Optional persistence layer for historical tracking

## How to Work With This Project

### For Bug Fixes
1. **Identify Component**: Use modular structure to locate relevant code
2. **Check Types**: Leverage comprehensive type hints for guidance
3. **Error Handling**: Follow established exception patterns
4. **Testing**: Test with real ESPN league data

### For New Features
1. **Follow Patterns**: Use existing service/model/display patterns
2. **Maintain Types**: Keep 100% type coverage
3. **Error Strategy**: Maintain fail-fast approach with clear messages
4. **Documentation**: Update docstrings and README

### For Troubleshooting
1. **Check Configuration**: Verify .env file and league IDs
2. **ESPN API Issues**: Look for ESPNAPIError with specific guidance
3. **Data Problems**: Examine individual game/team data extraction
4. **Output Issues**: Test different format options for debugging

### For Documentation Maintenance

#### Table of Contents (TOC) Generation
The README.md Table of Contents should only show H2 (##) level headers for clean navigation

## Success Criteria ✅ ALL MET
- ✅ Tool connects to ESPN leagues successfully (single and multiple)
- ✅ Displays comprehensive league standings and challenge results
- ✅ Weekly highlights feature tracking current week's top performances (v2.1)
- ✅ True projection tracking for accurate boom/bust analysis (v2.2)
- ✅ Clean, maintainable codebase (modular, well-organized)
- ✅ Proper typing without suppressions (100% type coverage)
- ✅ Clear error messages for all failure modes
- ✅ Educational value demonstrating Pythonic patterns
- ✅ Preserved all original functionality while improving architecture
- ✅ Efficient multi-output mode for automated workflows (v2.1)

**Current Status**: Production-ready, fully functional with 13 weekly highlights and 5 season challenges, serving as excellent example of modern Python development practices.