# Implementation Plan: Playoff Mode

> **Spec ID**: 006
> **Status**: Active
> **Created**: 2025-12-09
> **Last Updated**: 2025-12-09

## Technology Choices

### Primary Stack
- **Language**: Python 3.9+ (using modern type syntax)
- **ESPN API Library**: espn-api (existing dependency)
- **Key Libraries**: 
  - `dataclasses` (frozen=True for immutable playoff models)
  - `tabulate` (existing - for console bracket tables)
  - No new dependencies required

### Rationale
All functionality can be implemented using existing stack and dependencies. ESPN API testing (Week 15, 2025-12-10) confirmed all required fields are available: `is_playoff`, `matchup_type`, `team.standing`, `playoff_pct`, `reg_season_count`.

**Constitutional Compliance**:
- Article I: 100% type coverage with Python 3.9+ syntax (`str | None`)
- Article II: Immutable data models using `@dataclass(frozen=True)`
- Article V: Efficient API usage - single call per week, no additional ESPN requests

---

## Architecture Pattern

**Pattern**: Extended Service Layer with New Data Models

**Justification**: 
- Playoff detection logic belongs in `ESPNService` (already handles league data extraction)
- New playoff-specific models (`PlayoffMatchup`, `PlayoffBracket`, `ChampionshipEntry`) keep data immutable
- Existing `DivisionData` extended with optional `playoff_bracket` field
- Formatters detect playoff mode by checking for playoff data presence

**Constitutional Compliance**:
- Article III: Fail-fast with clear errors for out-of-sync divisions
- Article IV: Clean layer separation (Models → Services → Display)
- Article VI: All formatters receive identical playoff data

---

## Key Architectural Decisions

### Decision 1: Playoff Round Detection
**Approach**: Calculate by weeks since playoffs started
```python
playoff_week = current_week - reg_season_count
# 1 = Semifinals, 2 = Finals, 3 = Championship Week
```

**Rationale**: Simple arithmetic, matches ESPN's `playoff_matchup_period_length=1`. Confirmed via API testing.

### Decision 2: Championship Week Data Access
**Approach**: Pull individual team scores directly (not from matchups)

**Rationale**: Championship Week is a leaderboard format, not bracket matchups. Identify division winner from Finals, then get their Week 17 score.

### Decision 3: Division Synchronization
**Approach**: Fail completely with clear error when divisions out of sync

**Rationale**: Mixed playoff/regular season state is confusing and error-prone. Force user to fix synchronization issue.

### Decision 4: Model Architecture
**Approach**: Create new playoff models + extend `DivisionData`

**Structure**:
- New models: `PlayoffMatchup`, `PlayoffBracket`, `ChampionshipEntry`
- Extend `DivisionData` with: `playoff_bracket: PlayoffBracket | None`
- Extend output with: `championship: ChampionshipLeaderboard | None`

### Decision 5: Formatter Integration
**Approach**: Pass playoff data through existing `format_output()` method

**Rationale**: Formatters check if `playoff_bracket` is present in divisions. No protocol changes needed.

### Decision 6: Testing Strategy
**Approach**: Build full implementation with reasonable assumptions, adjust after testing

**Plan**: Implement all three rounds (Semifinals/Finals/Championship) based on API testing results and reasonable predictions. Test with real data on Week 16 (Dec 17) and Week 17 (Dec 24).

---

## Component Breakdown

### Component 1: Playoff Data Models

**Purpose**: Type-safe, immutable containers for playoff information

**Responsibilities**:
- Store playoff matchup data (seeds, teams, scores, winners)
- Store playoff bracket structure per division
- Store championship leaderboard entries
- Validate data at construction time

**Interface**:
```python
@dataclass(frozen=True)
class PlayoffMatchup:
    """Single playoff matchup between two teams."""
    matchup_id: str
    round_name: str  # "Semifinal 1", "Semifinal 2", "Finals"
    seed1: int
    team1_name: str
    owner1_name: str
    score1: float | None
    seed2: int
    team2_name: str
    owner2_name: str
    score2: float | None
    winner_name: str | None
    winner_seed: int | None
    division_name: str
    
    def __post_init__(self) -> None:
        """Validate matchup data."""
        # Validate seeds are positive
        # Validate scores are non-negative if present
        # Validate winner matches one of the teams if present

@dataclass(frozen=True)
class PlayoffBracket:
    """Playoff bracket for a division."""
    round: str  # "Semifinals", "Finals", "Championship Week"
    week: int
    matchups: list[PlayoffMatchup]
    
    def __post_init__(self) -> None:
        """Validate bracket has at least one matchup."""

@dataclass(frozen=True)
class ChampionshipEntry:
    """Single entry in championship leaderboard."""
    rank: int
    team_name: str
    owner_name: str
    division_name: str
    score: float
    is_champion: bool
    
    def __post_init__(self) -> None:
        """Validate rank is positive, score is non-negative."""

@dataclass(frozen=True)
class ChampionshipLeaderboard:
    """Championship Week leaderboard."""
    week: int
    entries: list[ChampionshipEntry]
    
    @property
    def champion(self) -> ChampionshipEntry:
        """Get the overall champion (highest scorer)."""
        return next(e for e in self.entries if e.is_champion)
```

**Dependencies**: 
- Standard library `dataclasses`
- Existing `DataValidationError` from `exceptions.py`

**Constraints**:
- Immutable (`frozen=True`)
- Full validation in `__post_init__`
- No business logic (data only)

### Component 2: Playoff Detection Service

**Purpose**: Detect playoff mode and extract playoff data from ESPN API

**Responsibilities**:
- Detect if league is in playoffs (`current_week > reg_season_count`)
- Determine playoff round (Semifinals/Finals/Championship)
- Check division synchronization across multiple leagues
- Extract playoff matchups from `BoxScore` data
- Build `PlayoffBracket` and `ChampionshipLeaderboard` structures

**Interface**:
```python
class ESPNService:
    # Existing methods remain unchanged
    
    def is_in_playoffs(self, league: League) -> bool:
        """Check if league is currently in playoff weeks."""
        return league.current_week > league.settings.reg_season_count
    
    def get_playoff_round(self, league: League) -> str:
        """
        Determine current playoff round.
        
        Returns: "Semifinals", "Finals", or "Championship Week"
        Raises: ESPNAPIError if not in playoffs
        """
        if not self.is_in_playoffs(league):
            raise ESPNAPIError("League is not in playoffs")
        
        playoff_week = league.current_week - league.settings.reg_season_count
        if playoff_week == 1:
            return "Semifinals"
        elif playoff_week == 2:
            return "Finals"
        elif playoff_week == 3:
            return "Championship Week"
        else:
            raise ESPNAPIError(f"Unexpected playoff week: {playoff_week}")
    
    def check_division_sync(self, leagues: list[League]) -> tuple[bool, str]:
        """
        Check if all divisions are in same playoff state.
        
        Returns: (is_synced, error_message)
        """
        # Check if all in playoffs or all in regular season
        # Check if all in same playoff round
        # Return detailed error message if out of sync
    
    def extract_playoff_matchups(
        self, 
        league: League, 
        division_name: str
    ) -> list[PlayoffMatchup]:
        """
        Extract playoff matchups from ESPN API for winners bracket.
        
        Filters to matchups where:
        - is_playoff == True
        - matchup_type == "WINNERS_BRACKET"
        """
        # Get box_scores for current week
        # Filter to playoff winners bracket matchups
        # Extract seeds from team.standing
        # Build PlayoffMatchup objects
    
    def build_playoff_bracket(
        self,
        league: League,
        division_name: str
    ) -> PlayoffBracket:
        """Build complete playoff bracket for division."""
        # Get playoff round
        # Extract matchups
        # Return PlayoffBracket
    
    def extract_championship_entry(
        self,
        league: League,
        division_name: str,
        championship_week: int
    ) -> ChampionshipEntry:
        """
        Extract championship week score for division winner.
        
        Finds division winner from Finals, gets their Week 17 score.
        """
        # Find winner from previous week's Finals
        # Get their score for championship_week
        # Return ChampionshipEntry
```

**Dependencies**:
- ESPN API `League`, `BoxScore`, `Team` objects
- New playoff models
- Existing `ESPNAPIError`, `DivisionSyncError` (new)

**Data Structures**:
- Uses existing ESPN API objects
- Produces new playoff model instances

**Constraints**:
- Must preserve existing single-API-call efficiency
- Must fail-fast on sync errors
- No retry logic (fail clearly)

### Component 3: Extended DivisionData Model

**Purpose**: Container that holds both regular season AND playoff data

**Responsibilities**:
- Store optional playoff bracket
- Maintain backward compatibility with regular season only
- Provide property to check if in playoffs

**Interface**:
```python
@dataclass(frozen=True)
class DivisionData:
    """Extended with playoff support."""
    name: str
    teams: list[TeamStats]
    games: list[GameResult]
    weekly_games: list[WeeklyGameResult]
    weekly_player_stats: list[WeeklyPlayerStats]
    playoff_bracket: PlayoffBracket | None = None  # NEW
    
    @property
    def is_playoff_mode(self) -> bool:
        """Check if this division is in playoff mode."""
        return self.playoff_bracket is not None
```

**Dependencies**: New `PlayoffBracket` model

**Constraints**:
- Maintain immutability
- Backward compatible (playoff_bracket optional)

### Component 4: Formatter Playoff Extensions

**Purpose**: Render playoff brackets in all output formats

**Responsibilities**:
- Detect playoff mode (check for playoff_bracket presence)
- Render playoff brackets at top of output
- Adapt challenge display (hide team challenges during playoffs)
- Show "historical" label on season challenges
- Display championship leaderboard

**Implementation** (per formatter):

**Console Formatter**:
- Use tabulate with `fancy_grid` style for brackets
- Show seeds as "#1", "#2", etc.
- Winner indicator: ✓ checkmark
- Championship: Large trophy banner, gold styling

**Sheets (TSV) Formatter**:
- Header row: "PLAYOFF BRACKET - [ROUND]"
- Columns: Division | Matchup | Seed1 | Team1 | Owner1 | Score1 | Seed2 | Team2 | Owner2 | Score2 | Winner
- Championship: Rank | Team | Owner | Division | Score | Champion

**Email (HTML) Formatter**:
- Purple gradient header for playoff excitement
- Winner rows highlighted in green with left border
- Responsive tables for mobile
- Championship: Gold theme, trophy banner

**Markdown Formatter**:
- Table format with bold subheadings
- Seeds shown as **#1**, **#2**, etc.
- Winner marked with ✓
- Championship: Medal emojis (🥇🥈🥉)

**JSON Formatter**:
- New top-level `playoff_bracket` object
- Structure matches data models exactly
- `report_type` field: "playoff_semifinals", "playoff_finals", "championship_week"

**Interface Changes**: None - all use existing `format_output()` method

**Constraints**:
- Must check for playoff data before rendering
- Must maintain regular season format when no playoff data
- Must handle in-progress games (0-0 scores)

---

## Data Flow

### High-Level Flow

```
1. CLI invoked → Parse args → Load config
2. For each league_id:
   a. Connect to ESPN league
   b. Check if in playoffs (current_week > reg_season_count)
   c. If in playoffs:
      - Determine round (Semifinals/Finals/Championship)
      - Extract playoff matchups OR championship scores
      - Build playoff bracket OR championship leaderboard
3. Check division synchronization across all leagues
   - If out of sync → Raise DivisionSyncError with details
4. Extract regular season data (teams, games, challenges)
5. Extract weekly data (highlights, player stats)
6. Build DivisionData objects with optional playoff_bracket
7. Pass to formatter with playoff data
8. Formatter detects playoff mode and renders appropriately
```

### Detailed Flow with Decision Points

```
Input: League IDs
    ↓
Load leagues via ESPNService
    ↓
For each league:
    ↓
Check: current_week > reg_season_count?
    ├─ No → Regular season mode
    │        Extract teams, games, challenges
    │        playoff_bracket = None
    │
    └─ Yes → Playoff mode
             ↓
        Calculate: playoff_week = current_week - reg_season_count
             ↓
        playoff_week == 1? → Semifinals
             ├─ Extract matchups where:
             │    is_playoff=True AND matchup_type="WINNERS_BRACKET"
             ├─ Build PlayoffMatchup objects (2 per division)
             └─ Create PlayoffBracket(round="Semifinals", ...)
             
        playoff_week == 2? → Finals
             ├─ Extract matchups where:
             │    is_playoff=True AND matchup_type="WINNERS_BRACKET"
             ├─ Build PlayoffMatchup objects (1 per division)
             └─ Create PlayoffBracket(round="Finals", ...)
             
        playoff_week == 3? → Championship Week
             ├─ Find division winners from Week 16 Finals
             ├─ Get each winner's Week 17 score
             ├─ Rank by score (highest wins)
             └─ Create ChampionshipLeaderboard
             
        playoff_week > 3? → Error: Unexpected playoff week
    ↓
Check Division Sync:
    All divisions same mode? ──No──> DivisionSyncError
    All divisions same round? ──No──> DivisionSyncError
    ↓ Yes
Build DivisionData with playoff_bracket
    ↓
Pass to formatter
    ↓
Formatter checks: division.playoff_bracket is not None?
    ├─ Yes → Playoff mode rendering
    │         1. Render playoff bracket (top)
    │         2. Render 7 player highlights (middle)
    │         3. Render 5 season challenges with "Historical" note (bottom)
    │         4. Render regular season standings (context)
    │
    └─ No → Regular season rendering (unchanged)
```

### Error Paths

- **DivisionSyncError**: Divisions out of sync (some in playoffs, some not OR different rounds)
  - **Handling**: Display detailed error message, exit with error code 1
  - **Message**: "Divisions are out of sync. Division 1: Week 15 (Semifinals), Division 2: Week 14 (Regular Season). All divisions must be in the same state."

- **ESPNAPIError**: Missing playoff data when expected
  - **Handling**: Log warning, fall back to showing error message
  - **Message**: "Playoff week detected but no playoff games found. ESPN API may not have updated yet."

- **DataValidationError**: Invalid playoff matchup data
  - **Handling**: Fail fast with details about which field failed validation
  - **Message**: "Invalid playoff matchup: seed must be positive, got -1"

---

## Implementation Phases

### Phase 1: Data Models

**Goal**: Create immutable playoff data structures

**Tasks**:
- [ ] Create `ff_tracker/models/playoff.py` with PlayoffMatchup, PlayoffBracket, ChampionshipEntry, ChampionshipLeaderboard
- [ ] Add full validation in `__post_init__` methods
- [ ] Update `ff_tracker/models/__init__.py` to export new models
- [ ] Extend `DivisionData` in `ff_tracker/models/division.py` with `playoff_bracket` field
- [ ] Add new exception `DivisionSyncError` to `ff_tracker/exceptions.py`

**Deliverable**: All playoff models defined with 100% type coverage

**Validation**: Models can be imported and instantiated with valid data

**Dependencies**: None

### Phase 2: Playoff Detection Logic

**Goal**: Add playoff detection and data extraction to ESPNService

**Tasks**:
- [ ] Implement `is_in_playoffs()` method
- [ ] Implement `get_playoff_round()` method
- [ ] Implement `check_division_sync()` method
- [ ] Add unit logic for sync checking across multiple leagues
- [ ] Handle edge cases (no playoff data, unexpected rounds)

**Deliverable**: Service can detect playoff state reliably

**Validation**: Test with real ESPN data from Week 15

**Dependencies**: Phase 1 complete

### Phase 3: Playoff Data Extraction (Semifinals & Finals)

**Goal**: Extract bracket matchups from ESPN API

**Tasks**:
- [ ] Implement `extract_playoff_matchups()` method
- [ ] Filter to `is_playoff=True` and `matchup_type="WINNERS_BRACKET"`
- [ ] Extract seed numbers from `team.standing`
- [ ] Extract team names and owner names
- [ ] Handle in-progress games (scores may be 0-0)
- [ ] Implement `build_playoff_bracket()` to construct PlayoffBracket
- [ ] Integrate into `load_all_divisions()` flow

**Deliverable**: Service extracts playoff brackets for Semifinals and Finals

**Validation**: Test with live Week 15 data, verify 2 matchups per division

**Dependencies**: Phase 2 complete

### Phase 4: Championship Week Data Extraction

**Goal**: Extract championship leaderboard from division winners

**Tasks**:
- [ ] Implement `extract_championship_entry()` method
- [ ] Find division winner from Finals matchup
- [ ] Get winner's Week 17 score from ESPN API
- [ ] Implement `build_championship_leaderboard()` to rank all winners
- [ ] Determine overall champion (highest score)
- [ ] Pass championship leaderboard to formatters

**Deliverable**: Service builds championship leaderboard

**Validation**: Test with mock data (real data not available until Dec 24)

**Dependencies**: Phase 3 complete

### Phase 5: Console Formatter Extensions

**Goal**: Render playoff brackets in console output

**Tasks**:
- [ ] Add `_format_playoff_bracket()` private method
- [ ] Use tabulate with fancy_grid style
- [ ] Show seeds, teams, owners, scores, winner indicators
- [ ] Add `_format_championship_leaderboard()` method
- [ ] Trophy banner with emojis
- [ ] Update `format_output()` to check for playoff mode
- [ ] Adapt weekly challenges display (hide team challenges during playoffs)
- [ ] Add "Historical" label to season challenges section

**Deliverable**: Console output shows playoff brackets beautifully

**Validation**: Compare output to examples/01-semifinals-console.txt

**Dependencies**: Phase 3 complete

### Phase 6: Other Formatter Extensions

**Goal**: Extend sheets, email, markdown, JSON formatters

**Tasks**:
- [ ] Sheets: Add bracket rows in TSV format
- [ ] Email: Add HTML bracket tables with styling
- [ ] Markdown: Add bracket tables with proper formatting
- [ ] JSON: Add `playoff_bracket` and `championship` top-level objects
- [ ] All formatters: Adapt challenge display for playoffs
- [ ] All formatters: Handle championship week rendering

**Deliverable**: All 5 formatters support playoff mode

**Validation**: Compare outputs to examples directory files

**Dependencies**: Phase 5 complete

### Phase 7: Integration Testing

**Goal**: End-to-end testing with real ESPN data

**Tasks**:
- [ ] Test with Week 15 Semifinals data (available now)
- [ ] Test division sync error scenarios (mock mismatched leagues)
- [ ] Test missing playoff data graceful degradation
- [ ] Test all output formats generate correctly
- [ ] Test Week 16 Finals when available (Dec 17)
- [ ] Test Week 17 Championship when available (Dec 24)
- [ ] Document any adjustments needed after real data testing

**Deliverable**: Fully tested playoff mode feature

**Validation**: All acceptance criteria from spec verified

**Dependencies**: Phase 6 complete

---

## Risk Assessment

### Risk 1: ESPN API Finals/Championship Structure Differs from Assumptions

**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Built implementation based on confirmed Semifinals structure and reasonable predictions. Prepared to adjust quickly.
**Fallback**: If Finals or Championship structure is drastically different, implement phase-specific logic rather than unified handling.

### Risk 2: Division Synchronization is Common Issue

**Likelihood**: Low (most commissioners keep leagues synced)
**Impact**: Low (clear error message guides user to fix)
**Mitigation**: Detailed error message explains exactly which divisions are out of sync and how to fix it.
**Fallback**: None needed - this is expected behavior per spec.

### Risk 3: Formatter Changes Break Existing Regular Season Output

**Likelihood**: Low
**Impact**: High
**Mitigation**: Playoff detection is explicit (check for playoff_bracket presence). Regular season code path unchanged.
**Fallback**: Thorough testing with regular season data before merging.

### Risk 4: Performance Degradation from Additional Data Extraction

**Likelihood**: Low
**Impact**: Low
**Mitigation**: Playoff data comes from same ESPN API call (box_scores), no additional requests.
**Fallback**: Profile if performance issues arise, optimize data extraction.

---

## Testing Strategy

### Unit Testing
- Playoff model validation (valid/invalid data)
- Playoff detection logic (various week numbers)
- Division sync checking (all combinations)
- Round name calculation
- Matchup extraction and filtering

### Integration Testing
- Full data flow from ESPN API to formatted output
- Test with real Week 15 Semifinals data
- Test division sync errors with mock leagues
- Test all 5 output formatters

### Validation Against Spec
- [ ] Story 1: Automatic playoff detection works without --playoffs flag
- [ ] Story 2: Playoff brackets display in all formats with correct data
- [ ] Story 3: Weekly challenges adapt (7 player highlights only, no team challenges)
- [ ] Story 4: Championship Week shows leaderboard and declares winner
- [ ] Story 5: All output formats render playoff data appropriately
- [ ] Edge Case 1: Out-of-sync divisions show error
- [ ] Edge Case 2: Out-of-sync championship week shows error
- [ ] Edge Case 3: Missing playoff data shows warning and falls back
- [ ] Edge Case 4: In-progress games show partial scores correctly

---

## Performance Considerations

**Expected Load**: Same as regular season (3-4 leagues, 180 games)
**Performance Target**: No measurable degradation (< 5% increase)
**Optimization Strategy**: 
- Playoff data extracted from existing box_scores call
- No additional ESPN API requests
- Efficient filtering using list comprehensions
- Models are immutable (no defensive copying needed)

**Current Performance**: Regular season processes in ~3-5 seconds
**Expected with Playoffs**: ~3-6 seconds (minimal increase)

---

## Security Considerations

No new security concerns. Playoff feature uses same ESPN API authentication as existing features. No user input beyond league IDs (already validated).

---

## Complexity Tracking

> This section documents any deviations from the constitution.

### Potential Deviation 1: Championship Week Data Access Pattern

**Constitutional Principle**: Article V (consistent API patterns)
**Details**: Championship Week pulls individual team scores rather than matchups, which is different from Semifinals/Finals.
**Justification**: Championship Week is fundamentally different (leaderboard vs bracket), so different data access makes sense.
**Mitigation**: Document clearly in code comments. Consider refactoring if pattern proves problematic.
**Approval**: Decision 2 from planning session - approved

### No Other Deviations

System maintains:
- 100% type coverage (Article I)
- Immutable models with validation (Article II)
- Fail-fast error handling (Article III)
- Clean layer separation (Article IV)
- Efficient API usage (Article V)
- Format equality (Article VI)

---

## Open Technical Questions

- [NEEDS TESTING - Week 16] How are Finals matchups structured in ESPN API? (Expected: 1 matchup per division, winners bracket)
- [NEEDS TESTING - Week 17] Does Championship Week have matchups or just individual scores? (Assumption: No matchups, pull scores directly)
- [NEEDS TESTING - Week 17] How to identify division winners programmatically? (Assumption: Check Finals winner from Week 16)

**Resolution Plan**: Test with live data on Week 16 (Dec 17) and Week 17 (Dec 24). Adjust implementation as needed.

---

## Related Documentation

- **Feature Spec**: [spec.md](./spec.md)
- **ESPN API Testing**: [ESPN_API_TESTING.md](./ESPN_API_TESTING.md)
- **Example Outputs**: [examples/](./examples/)
- **Data Models**: [data-model.md](./data-model.md) (to be created)
- **API Contracts**: [contracts/](./contracts/) (to be created)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-09 | AI Agent | Initial plan with all architectural decisions |
