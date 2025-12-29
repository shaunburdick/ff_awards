# Spec: Season Recap Script

**Status**: Approved ✅  
**Version**: 1.0  
**Created**: 2024-12-29  
**Last Updated**: 2024-12-29  
**Epic**: End-of-Season Reporting  
**Related Issues**: Need comprehensive season summary after championship week completes

---

## Problem Statement

After the fantasy football season ends (Week 17 championship complete), commissioners need a **comprehensive season summary** that ties together:
1. Regular season results (best teams, final standings)
2. All 5 season challenge winners
3. Playoff results (semifinals, finals)
4. Championship week results (overall champion)

Currently, this information exists across multiple scripts and weekly reports:
- `ff-tracker` shows regular season standings and challenges (Weeks 1-14)
- `ff-tracker` shows playoff brackets (Weeks 15-16)
- `ff-championship` shows championship results (Week 17)

There is **no single place** to see the complete season story. Commissioners must manually piece together data from different reports.

---

## User Stories

### US-1: View Complete Season Summary
**As a** league commissioner  
**I want to** see a comprehensive end-of-season report  
**So that** I can review the entire season (regular season, playoffs, championship) in one place

**Acceptance Criteria**:
- Shows regular season division champions (highest ranked teams by record)
- Shows all 5 season challenge winners with details
- Shows playoff results for all divisions (semifinals and finals)
- Shows championship week results with overall champion
- Available in all 5 output formats (console, sheets, email, json, markdown)
- Clearly structured with distinct sections for each phase

### US-2: Share Season Recap with League Members
**As a** league commissioner  
**I want to** generate a shareable season recap report  
**So that** I can send a final summary to all league members

**Acceptance Criteria**:
- Email format optimized for mobile viewing
- Markdown format ready for Slack/Discord posting
- JSON format for archival/analysis
- Console format for quick viewing
- Sheets format for manual manipulation

### US-3: Archive Season Results
**As a** league commissioner  
**I want to** save a complete season summary  
**So that** I can reference it in future seasons

**Acceptance Criteria**:
- All formats include year/season identifier
- JSON format includes all raw data for analysis
- File naming includes season year for easy archival
- Can run for previous seasons (not just current)

### US-4: Historical Comparison (Future Enhancement)
**As a** league commissioner  
**I want to** compare current season to previous seasons  
**So that** I can identify trends and records

**Status**: ⭕ **Out of Scope for v1** (Phase 2 enhancement)

**Acceptance Criteria** (future):
- Shows year-over-year champion comparisons
- Identifies season records across multiple years
- Tracks repeat winners and streaks
- Compares scoring trends

---

## Solution Overview

Create a new **standalone script** (`ff-season-recap`) that:

1. **Fetches Data via ESPN API**: Makes fresh API calls to ensure accuracy
2. **Analyzes Full Season**: Processes all weeks (1-17) to extract season story
3. **Structures Output**: Organizes data into clear sections (regular season → playoffs → championship)
4. **Leverages Existing Infrastructure**: Reuses models, services, and formatters from `ff-tracker` and `ff-championship`
5. **Generates Multiple Formats**: Supports all 5 output formats for flexibility

### Architecture: Separate Script

```
ff_tracker/
├── season_recap.py          # NEW: Season recap CLI entry point
├── models/
│   ├── season_summary.py    # NEW: Season summary data models
│   ├── team.py              # EXISTING: TeamStats model
│   ├── playoff.py           # EXISTING: Playoff models
│   └── championship.py      # EXISTING: Championship models
├── services/
│   ├── espn_service.py      # SHARED: ESPN API integration
│   ├── challenge_service.py # SHARED: Season challenge calculation
│   ├── season_recap_service.py  # NEW: Season recap logic
│   └── championship_service.py  # SHARED: Championship data
└── display/                 # SHARED: All 5 formatters (extended for recap)
```

### Why Separate Script?

**Benefits**:
- **Focused**: Single responsibility (end-of-season summary only)
- **Independent**: Can run without running other scripts first
- **Simple**: No complex conditionals for "recap mode" in existing scripts
- **Flexible**: Can enhance with historical features without affecting weekly/championship scripts

**Shared Code**:
- All existing models (Team, Game, Challenge, Playoff, Championship)
- All existing services (ESPN API, challenge calculation)
- All existing formatters (console, sheets, email, json, markdown)

**New Code**:
- `season_recap.py`: CLI entry point
- `services/season_recap_service.py`: Orchestration logic to build complete summary
- `models/season_summary.py`: Data model for complete season summary

---

## Functional Requirements

### FR-001: Regular Season Summary
**Description**: Display regular season results and division champions

**Requirements**:
- FR-001a: Identify highest ranked team per division at end of regular season
  - Regular season end detected dynamically from `league.settings.reg_season_count`
  - Ranking by: wins-losses record, then points_for tiebreaker
- FR-001b: Show final regular season standings for each division
  - Include: rank, team name, owner, record, points_for, points_against
  - Division names: Use `league.settings.name` or fallback to "Division N"
- FR-001c: Include season date range dynamically (Week 1 - Week {reg_season_count})

**Data Source**: ESPN API, same logic as `ff-tracker` regular season analysis

### FR-002: Season Challenge Winners
**Description**: Display all 5 season challenge winners with complete details

**Requirements**:
- FR-002a: Show all 5 challenge winners:
  1. Most Points Overall (team name, total points)
  2. Most Points in One Game (team name, points, week number)
  3. Most Points in a Loss (team name, points, week number, opponent)
  4. Least Points in a Win (team name, points, week number, opponent)
  5. Closest Victory (team name, margin, week number, opponent)
- FR-002b: Include owner names for all winning teams
- FR-002c: Include division names for context
- FR-002d: Mark ties if multiple teams achieved same result

**Data Source**: Reuse existing `ChallengeCalculator` from `challenge_service.py`

### FR-003: Playoff Results Summary
**Description**: Display playoff bracket results for all divisions

**Requirements**:
- FR-003a: Dynamically detect playoff weeks from ESPN API
  - Playoff start: `league.settings.reg_season_count + 1`
  - Playoff end: `league.finalScoringPeriod`
  - Number of rounds: `playoff_weeks // playoff_matchup_period_length`
- FR-003b: Show all playoff rounds dynamically (typically Semifinals and Finals)
  - First playoff week: Semifinals (seed matchups: #1 vs #4, #2 vs #3)
  - Second playoff week: Finals (winners from semifinals)
  - Additional rounds if league configured differently
- FR-003c: Display all matchups with seed ranks, team names, and scores
- FR-003d: Winners clearly indicated
- FR-003e: Group by division for clarity
- FR-003f: Division names from `league.settings.name` or "Division N"

**Data Source**: ESPN API, same playoff detection logic from `ff-tracker` v3.0

### FR-004: Championship Results
**Description**: Display championship week results (week after playoff finals)

**Requirements**:
- FR-004a: Championship week is dynamically calculated as `league.finalScoringPeriod + 1`
  - This is a custom cross-division competition (not official ESPN playoff)
- FR-004b: Show all division winners and their championship week scores
- FR-004c: Rank division winners by championship week performance
- FR-004d: Clearly mark overall champion (highest score)
- FR-004e: Show runner-up and third place (or all participants if more/less than 3)
- FR-004f: Include margin between champion and runner-up
- FR-004g: Handle case where championship week hasn't occurred (with --force flag)

**Data Source**: Reuse logic from `ff-championship` script's championship service

### FR-005: Multiple Output Formats
**Description**: Support all 5 existing output formats

**Requirements**:
- FR-005a: Console format with clear section headers and tables
- FR-005b: Email format (HTML) optimized for mobile viewing
- FR-005c: Sheets format (TSV) for easy copying to Google Sheets
- FR-005d: JSON format with complete structured data (for archival)
- FR-005e: Markdown format for GitHub/Slack/Discord
- FR-005f: Multi-output mode (--output-dir) to generate all formats at once
  - Creates files: season-recap.txt, season-recap.tsv, season-recap.html, season-recap.json, season-recap.md
  - JSON format preserved for historical record-keeping
  - Single format mode outputs to stdout (no files created)
- FR-005g: No automatic archival or year-over-year comparison features in v1

**Data Source**: Extend existing formatters in `display/` directory

### FR-006: CLI Interface
**Description**: Command-line interface for running season recap

**Requirements**:
- FR-006a: Accept league IDs via CLI args or environment variable (same as existing scripts)
- FR-006b: Support private league authentication (--private flag)
- FR-006c: Support year specification (--year YYYY)
- FR-006d: Support format selection (--format console|sheets|email|json|markdown)
- FR-006e: Support multi-output mode (--output-dir PATH)
- FR-006f: Support format arguments (--format-arg key=value)
- FR-006g: Default to current season if no year specified

**Example Commands**:
```bash
# Generate season recap for current season
uv run ff-season-recap --env --private

# Specific year
uv run ff-season-recap --env --year 2024

# All formats
uv run ff-season-recap --env --output-dir ./season-recap

# With custom note
uv run ff-season-recap --env --format email --format-arg note="Thanks for a great season!"

# Specific format
uv run ff-season-recap --env --format markdown
```

### FR-007: Data Validation
**Description**: Validate that season is complete before generating recap

**Requirements**:
- FR-007a: Dynamically detect season structure from ESPN API:
  - Regular season: weeks 1 through `league.settings.reg_season_count`
  - Division playoffs: `reg_season_count + 1` through `league.finalScoringPeriod`
  - Championship: `league.finalScoringPeriod + 1` (custom cross-division)
- FR-007b: Check that championship week has occurred (games played)
- FR-007c: Check that all divisions have playoff data available
- FR-007d: Provide clear error message if season incomplete
- FR-007e: Allow override flag (--force) for testing with incomplete seasons
- FR-007f: Warn if championship week data is missing but allow regular season + playoffs recap
- FR-007g: Calculate playoff rounds dynamically: `playoff_weeks // playoff_matchup_period_length`

**Error Messages**:
- "Season incomplete: Championship week has not occurred yet. Use --force to generate partial recap."
- "Warning: Championship data unavailable. Recap will include regular season and playoffs only."
- "Season structure: Regular season (weeks 1-{reg_season_count}), Playoffs (weeks {playoff_start}-{playoff_end}), Championship (week {championship_week})"

### FR-008: Extensibility for Future Features
**Description**: Design to support future enhancements without major refactoring

**Requirements**:
- FR-008a: Data model supports adding "awards" section (most consistent, boom/bust, etc.)
- FR-008b: JSON format includes version field for future compatibility
- FR-008c: Service layer separates data fetching from summary generation
- FR-008d: Formatters can easily add new sections to output

---

## Non-Functional Requirements

### NFR-001: Performance
- Complete season recap generated in under 30 seconds for 3 divisions
- API calls optimized (reuse league connections, batch requests where possible)

### NFR-002: Accuracy
- All data must match source ESPN API exactly (no calculations drift)
- Challenge calculations must match `ff-tracker` results exactly
- Playoff/championship data must match `ff-tracker`/`ff-championship` results exactly

### NFR-003: Reliability
- Fail-fast with clear error messages if API unavailable
- Graceful handling of missing data (partial seasons)
- No silent failures or incorrect data

### NFR-004: Usability
- Clear, intuitive output structure across all formats
- Mobile-friendly email format
- Copy-paste friendly console/markdown formats
- Easy archival with year in filename

### NFR-005: Maintainability
- Reuse existing code wherever possible
- Follow established patterns from other scripts
- Comprehensive type hints (100% coverage)
- Clear separation of concerns

---

## Data Models

### New: SeasonSummary
```python
@dataclass(frozen=True)
class SeasonSummary:
    """Complete summary of a fantasy football season."""
    year: int
    regular_season: RegularSeasonSummary
    season_challenges: list[ChallengeResult]
    playoffs: PlayoffSummary
    championship: ChampionshipSummary
    generated_at: str  # ISO timestamp
```

### New: RegularSeasonSummary
```python
@dataclass(frozen=True)
class RegularSeasonSummary:
    """Summary of regular season results."""
    weeks: tuple[int, int]  # (start_week, end_week) e.g., (1, 14)
    division_champions: list[DivisionChampion]
    final_standings: list[DivisionData]  # Reuse existing model
```

### New: DivisionChampion
```python
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
    rank: int  # Final rank in division (should be 1)
```

### New: PlayoffSummary
```python
@dataclass(frozen=True)
class PlayoffSummary:
    """Summary of playoff results."""
    semifinals: list[PlayoffRound]  # Week 15
    finals: list[PlayoffRound]  # Week 16
```

### New: PlayoffRound
```python
@dataclass(frozen=True)
class PlayoffRound:
    """Results for one playoff round in one division."""
    division_name: str
    week: int
    matchups: list[PlayoffMatchup]
```

### New: PlayoffMatchup
```python
@dataclass(frozen=True)
class PlayoffMatchup:
    """Single playoff matchup result."""
    home_team: str
    home_owner: str
    home_seed: int
    home_score: float
    away_team: str
    away_owner: str
    away_seed: int
    away_score: float
    winner: str  # team name
```

### Reuse: ChampionshipSummary
```python
# Already exists in models/championship.py, may add:
@dataclass(frozen=True)
class ChampionshipSummary:
    """Week 17 championship results."""
    week: int
    entries: list[ChampionshipEntry]  # All 3 division winners
    champion: ChampionshipEntry
    runner_up: ChampionshipEntry
    third_place: ChampionshipEntry
    margin: float  # Points between champion and runner-up
```

---

## API Design

### New Service: SeasonRecapService

```python
class SeasonRecapService:
    """Service for generating complete season recap."""
    
    def __init__(
        self,
        espn_service: ESPNService,
        challenge_service: ChallengeCalculator,
        championship_service: ChampionshipService
    ):
        self.espn = espn_service
        self.challenges = challenge_service
        self.championships = championship_service
    
    def generate_season_summary(
        self,
        leagues: list[League],
        division_names: list[str],
        year: int
    ) -> SeasonSummary:
        """
        Generate complete season summary.
        
        Args:
            leagues: ESPN league objects for all divisions
            division_names: Names for each division
            year: Season year
            
        Returns:
            Complete SeasonSummary object
            
        Raises:
            InsufficientDataError: If season data incomplete
        """
        pass
    
    def get_regular_season_summary(
        self,
        leagues: list[League],
        division_names: list[str]
    ) -> RegularSeasonSummary:
        """
        Extract regular season results (Weeks 1-14).
        
        Returns:
            Regular season summary with champions and standings
        """
        pass
    
    def get_playoff_summary(
        self,
        leagues: list[League],
        division_names: list[str]
    ) -> PlayoffSummary:
        """
        Extract playoff results (Weeks 15-16).
        
        Returns:
            Playoff summary with semifinals and finals results
        """
        pass
    
    def get_championship_summary(
        self,
        leagues: list[League],
        division_names: list[str]
    ) -> ChampionshipSummary:
        """
        Extract championship week results (Week 17).
        
        Returns:
            Championship summary with rankings and overall winner
        """
        pass
    
    def calculate_season_structure(
        self,
        league: League
    ) -> dict[str, Any]:
        """
        Calculate season structure dynamically from ESPN API.
        
        Returns dict with:
            - regular_season: (start_week, end_week)
            - playoff_start: int
            - playoff_end: int
            - championship_week: int
            - playoff_rounds: int
            - playoff_round_length: int
        
        Example:
            {
                "regular_season": (1, 14),
                "playoff_start": 15,
                "playoff_end": 16,
                "championship_week": 17,
                "playoff_rounds": 2,
                "playoff_round_length": 1
            }
        """
        pass
    
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
        """
        pass
    
    def get_division_name(
        self,
        league: League,
        index: int
    ) -> str:
        """
        Get division name from ESPN or fallback to positional naming.
        
        Args:
            league: ESPN League object
            index: Zero-based position in LEAGUE_IDS list
            
        Returns:
            Division name (e.g., "Rough Street" or "Division 1")
        """
        pass
```

---

## Output Format Examples

### Console Format

```
================================================================================
                        🏆 2024 SEASON RECAP 🏆
================================================================================

📅 REGULAR SEASON (Weeks 1-14)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Division Champions (Best Record)
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Division           ┃ Team             ┃ Owner  ┃ Record      ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━┩
│ Rough Street       │ Ja'marr Wars     │ Brian  │ 10-4 (🏆#1) │
│ Block Party        │ Miller Time 🍻   │ Mike   │ 9-5 (🏆#1)  │
│ Road Reptiles      │ Billieve Champ   │ Eric   │ 11-3 (🏆#1) │
└────────────────────┴──────────────────┴────────┴─────────────┘

🏅 SEASON CHALLENGE WINNERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Most Points Overall
   Winner: Ja'marr Wars (Brian Fox) - Rough Street
   Total: 1,842.52 points

2. Most Points in One Game
   Winner: Miller Time 🍻 (Mike Rowland) - Block Party
   Score: 187.34 points (Week 7)

3. Most Points in a Loss
   Winner: Dynasty Decaf (Sean Flynn) - Road Reptiles
   Score: 156.82 points (Week 3)
   Lost to: Billieve Champ (161.24)

4. Least Points in a Win
   Winner: Clipboard Jesus (Mark Stevens) - Rough Street
   Score: 87.18 points (Week 11)
   Beat: Lucky Charms (84.32)

5. Closest Victory
   Winner: Ja'marr Wars (Brian Fox) - Rough Street
   Margin: 0.42 points (Week 9)
   Final: 112.86 - 112.44

🏈 PLAYOFFS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Week 15 - Semifinals

Rough Street League
  🏆 #1 Ja'marr Wars (128.54) def. #4 Team Name (102.38)
  🏆 #2 Miller Time (145.23) def. #3 Team Name (138.72)

Block Party League
  🏆 #1 Team Name (132.45) def. #4 Team Name (98.23)
  🏆 #2 Team Name (119.88) def. #3 Team Name (115.67)

Road Reptiles League
  🏆 #1 Billieve Champ (149.32) def. #4 Team Name (108.44)
  🏆 #2 Team Name (126.78) def. #3 Team Name (122.11)

Week 16 - Finals

Rough Street League
  🏆 CHAMPION: Ja'marr Wars (152.34) def. Miller Time (141.28)

Block Party League
  🏆 CHAMPION: Miller Time 🍻 (148.92) def. Team Name (136.45)

Road Reptiles League
  🏆 CHAMPION: Billieve Champ (162.88) def. Team Name (149.23)

🥇 CHAMPIONSHIP WEEK (Week 17)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Final Rankings - Division Winners
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━┓
┃ Place  ┃ Team               ┃ Owner            ┃ Division   ┃ Score   ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━┩
│ 🥇 1st │ Billieve Champ     │ eric barnum      │ Road Rep   │ 162.06  │
│ 🥈 2nd │ Ja'marr Wars       │ Brian Fox        │ Rough St   │ 158.40  │
│ 🥉 3rd │ Miller Time 🍻     │ Michael Rowland  │ Block Pa   │ 147.25  │
└────────┴────────────────────┴──────────────────┴────────────┴─────────┘

🎉 OVERALL CHAMPION: Billieve the Champ Is Back (eric barnum)
   Road Reptiles League Division Winner
   Championship Score: 162.06 points
   Margin of Victory: 3.66 points

================================================================================
```

### Email Format Structure

- Responsive HTML with mobile-first design
- Clear section headers with emoji icons
- Collapsible sections for each phase (regular season, playoffs, championship)
- Summary stats at top (overall champion, season point leader, closest game)
- Color-coded sections (blue=regular season, orange=playoffs, gold=championship)
- Optional note section at top (via --format-arg note="...")
- Footer with generation timestamp and download link

### JSON Format Structure

```json
{
  "version": "1.0",
  "year": 2024,
  "generated_at": "2024-12-29T18:30:00Z",
  "metadata": {
    "note": "Thanks for a great season!",
    "divisions": ["Rough Street", "Block Party", "Road Reptiles"],
    "total_teams": 30
  },
  "regular_season": {
    "weeks": [1, 14],
    "division_champions": [
      {
        "division": "Rough Street",
        "team": "Ja'marr Wars",
        "owner": "Brian Fox",
        "record": {"wins": 10, "losses": 4},
        "points_for": 1842.52,
        "points_against": 1523.44
      }
    ],
    "standings": [...]
  },
  "season_challenges": [
    {
      "challenge": "Most Points Overall",
      "winner": "Ja'marr Wars",
      "owner": "Brian Fox",
      "division": "Rough Street",
      "value": 1842.52,
      "details": {}
    }
  ],
  "playoffs": {
    "semifinals": [...],
    "finals": [...]
  },
  "championship": {
    "week": 17,
    "entries": [...],
    "champion": {...},
    "runner_up": {...},
    "third_place": {...},
    "margin": 3.66
  }
}
```

---

## Implementation Plan

### Phase 1: Foundation (2-3 hours)
- [P] Create new data models in `models/season_summary.py`
- [P] Define all dataclasses with type hints and validation
- [P] Add unit tests for model validation

### Phase 2: Service Layer (3-4 hours)
- [P] Create `services/season_recap_service.py`
- [P] Implement `get_regular_season_summary()` (reuse existing ESPN service methods)
- [P] Implement `get_playoff_summary()` (reuse playoff detection logic)
- [P] Implement `get_championship_summary()` (reuse championship service)
- [P] Implement `validate_season_complete()`
- [P] Implement `generate_season_summary()` (orchestrate all pieces)
- [P] Add comprehensive unit tests

### Phase 3: CLI Entry Point (1-2 hours)
- [P] Create `season_recap.py` with argparse
- [P] Implement all CLI arguments (--env, --private, --year, --format, etc.)
- [P] Add validation and error handling
- [P] Add --force flag for testing incomplete seasons

### Phase 4: Display Formatters (2-3 hours)
- [P] Extend console formatter for season recap layout
- [P] Extend email formatter with new sections
- [P] Extend sheets formatter with recap structure
- [P] Extend JSON formatter with nested recap data
- [P] Extend markdown formatter with clean section headers
- [P] Test all 5 formats with sample data

### Phase 5: Integration & Testing (2-3 hours)
- [P] Test with real 2024 season data (post-Week 17)
- [P] Verify data accuracy against existing reports
- [P] Test all output formats
- [P] Test edge cases (incomplete seasons, missing data)
- [P] Performance testing with 3 divisions

### Phase 6: Documentation (1 hour)
- [P] Update README with season recap usage
- [P] Add to pyproject.toml scripts section
- [P] Create quickstart guide in spec directory
- [P] Document known limitations

### Phase 7: GitHub Actions Integration (1 hour)
- [P] Create `season-recap.yml` workflow (manual trigger only)
- [P] Support all 5 output formats
- [P] Upload artifacts with 365-day retention
- [P] Optional email sending (like championship workflow)

**Total Estimated Time**: 12-17 hours

---

## Testing Strategy

### Unit Tests
- Test all data model validation
- Test service methods independently with mock data
- Test data extraction logic
- Test summary generation

### Integration Tests
- Test with real ESPN API using 2024 season data
- Verify regular season data extraction
- Verify playoff data extraction
- Verify championship data extraction
- Test all output formats

### Edge Case Tests
- Season not yet complete (Week 17 hasn't happened)
- Missing playoff data (league ended early)
- Missing championship data (not all finals played)
- Tied records/scores
- Empty divisions

---

## Open Questions - RESOLVED ✅

All design questions have been answered and decisions documented below.

### 1. **Regular Season Week Range** ✅ RESOLVED
   - **Decision**: Detect dynamically from ESPN API (Option B)
   - **Implementation**: Use `league.settings.reg_season_count` for regular season end
   - **Rationale**: Existing `ff-tracker` has battle-tested playoff detection logic; reuse it for flexibility

### 2. **Season Structure Detection** ✅ RESOLVED
   - **Decision**: Fully dynamic detection from ESPN API (no hardcoded weeks or playoff lengths)
   - **Implementation**:
     ```python
     reg_season_end = league.settings.reg_season_count  # e.g., 14
     playoff_start = reg_season_end + 1  # e.g., 15
     playoff_end = league.finalScoringPeriod  # e.g., 16 (ESPN's last week)
     championship_week = playoff_end + 1  # e.g., 17 (custom cross-division)
     playoff_weeks = playoff_end - playoff_start + 1
     playoff_rounds = playoff_weeks // league.settings.playoff_matchup_period_length
     ```
   - **Rationale**: ESPN API provides all necessary settings; no assumptions about league structure

### 3. **Incomplete Data Handling** ✅ RESOLVED
   - **Decision**: Flexible with `--force` flag (Option B)
   - **Implementation**:
     - Normal mode: Validates championship week is complete (has game data)
     - `--force` mode: Generates what's available with clear warnings
     - Warnings indicate which sections are missing (e.g., "Championship week data unavailable")
   - **Rationale**: Need to test before season ends; useful for partial recaps if needed
   
### 4. **Historical Persistence** ✅ RESOLVED
   - **Decision**: Multi-output mode saves files including JSON (Option D)
   - **Implementation**:
     - Single format mode: Outputs to stdout (no files created)
     - `--output-dir` mode: Creates all 5 formats including JSON for archival
     - No automatic archival or special handling
   - **Phase 2 Note**: No year-over-year comparisons planned (players/divisions change annually)
   - **Rationale**: Consistent with existing scripts; user controls file creation explicitly
   
### 5. **Division Names** ✅ RESOLVED
   - **Decision**: Hybrid approach - ESPN names with fallback (Option D)
   - **Implementation**: 
     ```python
     division_name = league.settings.name or f"Division {index + 1}"
     ```
   - **Rationale**: Uses meaningful ESPN names when available; sensible defaults otherwise

### 6. **Season Awards** ✅ RESOLVED
   - **Decision**: Not included in v1 (Option A)
   - **v1 Scope**: Focus on core facts (standings, challenges, playoffs, championship)
   - **Phase 2**: Can add awards later (Most Consistent, Boom/Bust, etc.)
   - **Rationale**: Keep v1 focused and deliverable; iterate based on feedback

---

## Future Enhancements (Out of Scope for v1)

### Phase 2: Season Awards (Optional)
- **Most Consistent**: Lowest standard deviation in weekly scores
- **Boom or Bust**: Highest standard deviation
- **Best Playoff Run**: Biggest improvement from regular season seed
- **Heartbreaker**: Most losses by <5 points
- **Lucky Winner**: Most wins by <5 points
- **Benchwarmer**: Most points left on bench
- **Injury Bug**: Team most affected by injuries
- **Comeback Kid**: Biggest single-week point improvement

**Note**: Awards are optional enhancements that can be added if there's interest after v1 feedback.

### Phase 3: Enhanced Visualizations
- Charts/graphs in email format
- Scoring trends over season
- Head-to-head records matrix
- Position strength analysis

### Phase 4: Export Options
- PDF generation
- Interactive HTML dashboard
- CSV exports for Excel analysis

### Explicitly NOT Planned
- ❌ **Year-over-year comparisons**: Players and divisions change annually, making historical comparisons not meaningful
- ❌ **Automatic archival system**: User controls file creation via `--output-dir`
- ❌ **Database persistence**: JSON files sufficient for record-keeping

---

## Risk Assessment

### High Risk
- **Data Accuracy**: Must perfectly match existing scripts' calculations
  - *Mitigation*: Reuse existing services, comprehensive testing against known results
- **API Reliability**: ESPN API must be available for all season weeks
  - *Mitigation*: Clear error messages, retry logic for transient failures

### Medium Risk
- **Performance**: Processing full season (17 weeks × 3 divisions) could be slow
  - *Mitigation*: Optimize API calls, implement caching where appropriate
- **Complexity**: Coordinating data from regular season + playoffs + championship
  - *Mitigation*: Clear service layer separation, thorough testing

### Low Risk
- **Output Formatting**: Should reuse existing formatters with minor extensions
  - *Mitigation*: Follow established patterns, test incrementally

---

## Dependencies

- Existing `ff-tracker` codebase (v3.0+)
- ESPN API access (same as existing scripts)
- Python 3.9+ with type hints
- Complete season data (Weeks 1-17)
- Existing models, services, formatters

---

## Success Criteria

### Must Have (v1)
- ✅ Shows regular season division champions and final standings
- ✅ Shows all 5 season challenge winners with complete details
- ✅ Shows playoff results (semifinals and finals) for all divisions
- ✅ Shows championship week results with overall champion
- ✅ All 5 output formats work correctly
- ✅ Data matches existing scripts exactly (accuracy verification)
- ✅ Clear error messages for incomplete seasons
- ✅ CLI interface matches existing script patterns

### Should Have
- ✅ Multi-output mode (--output-dir) for all formats at once
- ✅ Format arguments support for customization
- ✅ GitHub Actions workflow for automated recap generation
- ✅ Comprehensive documentation and examples

### Nice to Have (Phase 2)
- ⭕ Historical tracking and year-over-year comparisons
- ⭕ Season awards (most consistent, boom/bust, etc.)
- ⭕ Enhanced visualizations (charts, graphs)
- ⭕ PDF export option

---

## Approval & Sign-off

**Stakeholders**:
- [x] User (Shaun) - ✅ Approved (Dec 29, 2024)

**Key Decisions Made**:
1. ✅ Dynamic season detection from ESPN API (no hardcoded weeks)
2. ✅ Flexible validation with --force flag for testing
3. ✅ Hybrid division naming (ESPN name or "Division N")
4. ✅ Multi-output mode saves JSON for archival (no auto-archival)
5. ✅ No season awards in v1 (focus on facts)
6. ✅ No year-over-year comparisons (players change annually)

**Next Steps**:
1. ✅ Spec approved and ready for implementation
2. Hand off to implementation team (modern-architect-engineer agent)
3. Begin Phase 1 (Foundation - data models)
4. Follow 7-phase implementation plan (12-17 hours estimated)

**Timeline Estimate**:
- Spec Complete: ✅ Dec 29, 2024
- Implementation: 12-17 hours (can be spread over multiple days)
- Testing: After championship week completes (with real 2024 data)
- Production Ready: Early January 2025

---

## Notes

- This is designed as the **final season capstone** - run once after Week 17
- Unlike weekly/championship scripts, this is meant for **archival and sharing**
- Design emphasizes **clarity and completeness** over real-time updates
- v1 focuses on **accuracy and usability**, Phase 2 can add analytics/awards
- Architecture allows easy enhancement without breaking existing functionality

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2024-12-29 | Spec-Driven Architect | Initial draft |
| 1.0 | 2024-12-29 | Spec-Driven Architect | Resolved all open questions with user input; spec approved for implementation |
