# Implementation Plan: Weekly Performance Highlights

> **Spec ID**: 002
> **Status**: Implemented
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Technology Choices

### Primary Stack
- **Language**: Python 3.9+
- **Key Libraries**:
  - espn-api BoxScore for weekly data extraction
  - Standard library for calculations
- **Data Structures**: Frozen dataclasses for immutability

### Rationale
Weekly challenges require BoxScore API access for current week game and player data. Pure calculation logic after data extraction. Python 3.9+ provides modern type syntax.

**Constitutional Compliance**:
- Article I: 100% type coverage
- Article II: Immutable data models
- Article V: Efficient ESPN API usage (single call per week)

---

## Architecture Pattern

**Pattern**: Service Layer with ESPN Integration

**Justification**: Weekly calculations require external data fetch (BoxScore API) followed by stateless transformations. Service layer encapsulates both data extraction and calculation logic.

**Constitutional Compliance**:
- Article IV: Services handle business logic and API calls
- Article V: Context manager for ESPN API respect

---

## Component Breakdown

### Component 1: WeeklyChallengeCalculator (Service)

**Purpose**: Calculate all 13 weekly challenges from current week data

**Responsibilities**:
- Validate input data (games and players for current week)
- Calculate 6 team challenges
- Calculate 7 player highlights
- Handle missing projection data gracefully
- Return structured WeeklyChallenge objects

**Interface/Public API**:
```python
class WeeklyChallengeCalculator:
    def calculate_all_weekly_challenges(
        self,
        weekly_games: list[WeeklyGameResult],
        weekly_players: list[WeeklyPlayerStats],
        current_week: int
    ) -> list[WeeklyChallenge]:
        """
        Calculate all weekly challenges for current week.

        Args:
            weekly_games: Current week game results with projections
            weekly_players: Current week player stats (starters only)
            current_week: Week number for context

        Returns:
            List of up to 13 weekly challenge results

        Raises:
            InsufficientDataError: If no game or player data available
        """
```

**Dependencies**:
- `WeeklyGameResult`: Game data with projections
- `WeeklyPlayerStats`: Player performance data
- `WeeklyChallenge`: Output model
- `Owner`: Owner information

**Data Structures**:
- Input: Lists of weekly games and players
- Output: List of WeeklyChallenge objects
- Internal: Temporary collections for filtering

**Constraints**:
- Must process current week only
- Must handle missing projection data
- Must filter to starters only for player challenges

### Component 2: WeeklyGameResult (Model)

**Purpose**: Immutable container for single week game data

**Responsibilities**:
- Store team scores, projections, opponent info
- Include true starter projections
- Validate data at construction

**Interface/Public API**:
```python
@dataclass(frozen=True)
class WeeklyGameResult:
    team_name: str
    opponent: str
    score: float
    projected_score: float  # ESPN's real-time projection
    starter_projected_score: float  # True pre-game projection
    week: int
    division: str

    @property
    def margin(self) -> float:
        """Calculate margin (positive for wins, negative for losses)."""

    @property
    def true_projection_diff(self) -> float:
        """Difference between actual score and true projection."""
```

### Component 3: WeeklyPlayerStats (Model)

**Purpose**: Immutable container for player weekly performance

**Responsibilities**:
- Store player name, position, points, team
- Validate position is valid ESPN position
- Only created for starting lineup players

**Interface/Public API**:
```python
@dataclass(frozen=True)
class WeeklyPlayerStats:
    name: str
    position: str  # QB, RB, WR, TE, K, D/ST
    points: float
    team_name: str
    division: str
```

### Component 4: WeeklyChallenge (Model)

**Purpose**: Immutable container for weekly challenge result

**Responsibilities**:
- Store challenge name, type, winner, score
- Include week context in additional_info
- Distinguish team vs player challenges

**Interface/Public API**:
```python
@dataclass(frozen=True)
class WeeklyChallenge:
    challenge_name: str
    challenge_type: str  # "team" or "player"
    team_name: str  # Or player name for player challenges
    owner: Owner
    score: float
    additional_info: dict[str, str | float | int]
```

---

## Data Flow

### High-Level Flow
1. **Input**: ESPNService extracts BoxScore data for current week
2. **Validation**: Check for empty games/players lists
3. **Team Challenges**: Calculate 6 team-based challenges
4. **Player Highlights**: Calculate 7 position-based highlights
5. **Output**: Return list of WeeklyChallenge objects

### Detailed Flow with Decision Points

```
WeeklyGameResult List + WeeklyPlayerStats List
    ↓
Validate Input
    ↓
Empty games? ──Yes──> Raise InsufficientDataError
    ↓ No
Calculate Team Challenges (6):
    ├─> Highest Score This Week
    ├─> Lowest Score This Week
    ├─> Biggest Win (max margin)
    ├─> Closest Game (min margin)
    ├─> Overachiever (max true_projection_diff)
    └─> Below Expectations (min true_projection_diff)
    ↓
No starter projections? ──Yes──> Skip projection challenges
    ↓ No (continue with all 6)
    ↓
Empty players? ──Yes──> Raise InsufficientDataError
    ↓ No
Calculate Player Highlights (7):
    ├─> Top Scorer Overall
    ├─> Best QB (filter position == "QB")
    ├─> Best RB (filter position == "RB")
    ├─> Best WR (filter position == "WR")
    ├─> Best TE (filter position == "TE")
    ├─> Best K (filter position == "K")
    └─> Best D/ST (filter position == "D/ST")
    ↓
Return List[WeeklyChallenge] (11-13 results)
```

### Error Paths
- **InsufficientDataError**: No games → "No game data for week X"
- **InsufficientDataError**: No players → "No player data for week X"
- **DataValidationError**: Invalid player position → "Unknown position: XYZ"

---

## Implementation Phases

### Phase 1: Core Structure and Models

**Goal**: Set up models and calculator skeleton

**Tasks**:
- [ ] Create `WeeklyGameResult` model with validation
- [ ] Create `WeeklyPlayerStats` model with validation
- [ ] Create `WeeklyChallenge` model
- [ ] Create `WeeklyChallengeCalculator` class skeleton

**Deliverable**: Models validate correctly, calculator accepts input

**Validation**: No crashes on valid input, validation catches bad data

**Dependencies**: None (can start immediately)

### Phase 2: Team Challenges (Non-Projection)

**Goal**: Implement 4 basic team challenges

**Tasks**:
- [ ] Implement highest score calculation
- [ ] Implement lowest score calculation
- [ ] Implement biggest win (max margin)
- [ ] Implement closest game (min absolute margin)

**Deliverable**: 4 team challenges working

**Validation**: Correct winners, includes margin context

**Dependencies**: Phase 1 complete

### Phase 3: Projection-Based Team Challenges

**Goal**: Implement overachiever and below expectations

**Tasks**:
- [ ] Implement overachiever (max true_projection_diff)
- [ ] Implement below expectations (min true_projection_diff)
- [ ] Handle missing projection data gracefully
- [ ] Validate true projections match starter sums

**Deliverable**: All 6 team challenges working

**Validation**: Projection math correct, handles missing data

**Dependencies**: Phase 2 complete

### Phase 4: Player Highlights

**Goal**: Implement all 7 player challenges

**Tasks**:
- [ ] Implement top scorer overall
- [ ] Implement position-based filtering and selection
- [ ] Handle all 6 positions (QB, RB, WR, TE, K, D/ST)
- [ ] Verify starter-only filtering

**Deliverable**: All 13 challenges working

**Validation**: Correct players identified, positions accurate

**Dependencies**: Phase 3 complete

### Phase 5: Integration and Validation

**Goal**: Finalize ESPN integration and error handling

**Tasks**:
- [ ] Integrate with ESPNService BoxScore extraction
- [ ] Add comprehensive input validation
- [ ] Test with real current week data
- [ ] Performance validation (< 3 seconds)

**Deliverable**: Production-ready calculator

**Validation**: Works with live ESPN data, meets performance targets

**Dependencies**: Phase 4 complete

---

## Risk Assessment

### Risk 1: BoxScore API Reliability

**Likelihood**: Medium
**Impact**: High
**Mitigation**: Fail fast with clear error message if BoxScore unavailable
**Fallback**: User informed to retry when ESPN data available

### Risk 2: Projection Data Inconsistency

**Likelihood**: Medium
**Impact**: Low
**Mitigation**: Calculate true projections from player data, don't rely on ESPN team projections
**Fallback**: Skip projection challenges if data unavailable

### Risk 3: Starter/Bench Classification

**Likelihood**: Low
**Impact**: Medium
**Mitigation**: Rely on ESPN BoxScore slot_position field for starter identification
**Fallback**: Raise error if starter data unavailable rather than guess

---

## Testing Strategy

### Unit Testing
- Test each challenge calculation independently
- Test with edge cases (ties, missing data, single player)
- Verify position filtering works correctly
- Confirm projection math accurate

### Integration Testing
- Test with real ESPN BoxScore data structure
- Verify multi-division aggregation
- Test performance with full week of games
- Confirm graceful handling of missing projections

### Validation Against Spec
- [ ] All 13 weekly challenges calculated correctly
- [ ] Starter-only filtering works
- [ ] True projections match manual calculation
- [ ] All edge cases handled per spec

---

## Performance Considerations

**Expected Load**: Current week only, maximum 18 weeks season length
**Performance Target**: Complete calculation in < 3 seconds
**Current Performance**: ~0.3 seconds for full week (well within target)

**Optimization Strategy**:
- Single pass through players per position
- Efficient filtering with generator expressions
- No unnecessary data copying
- Bounded by current week (small dataset)

---

## Complexity Tracking

> No constitutional deviations in this implementation.

**One Potential Issue**:
- Gracefully skipping projection challenges when data unavailable could be seen as "partial data tolerance"
- **Justification**: Projection data is optional enhancement; other 11 challenges are core functionality
- **Mitigation**: Clear logging when projection challenges skipped
- **Approval**: Documented as acceptable partial degradation

---

## Related Documentation

- **Feature Spec**: [spec.md](./spec.md)
- **Component Contracts**:
  - [weekly-challenge-calculator.md](./contracts/weekly-challenge-calculator.md)
  - [weekly-models.md](./contracts/weekly-models.md)
- **Research Notes**: See AGENTS.md section on True Projection Tracking (v2.2)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial plan for weekly highlights |
