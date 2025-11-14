# Implementation Plan: Multi-League Support

> **Spec ID**: 004
> **Status**: Implemented
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Technology Choices

### Primary Stack
- **Language**: Python 3.9+
- **Key Libraries**: espn-api for each league connection
- **Pattern**: Iterative league loading with aggregation

### Rationale
Each league requires separate ESPN API connection. Iterative loading with fail-fast ensures all-or-nothing data availability. Simple list aggregation for cross-league analysis.

**Constitutional Compliance**:
- Article III: Fail-fast if any league fails
- Article V: Efficient API usage (one call per league)

---

## Architecture Pattern

**Pattern**: Multi-Connection Service Layer

**Justification**: ESPNService manages multiple league connections, extracting data from each and aggregating into DivisionData list. Calculators remain unchanged (receive list of divisions).

**Constitutional Compliance**:
- Article IV: Services handle multiple API connections
- Article V: Context manager per league connection

---

## Component Breakdown

### Component 1: Configuration Multi-League Parsing

**Purpose**: Parse and validate multiple league IDs from CLI or environment

**Responsibilities**:
- Parse comma-separated league IDs from CLI argument
- Load LEAGUE_IDS from environment if --env flag
- Validate all IDs are integers
- Detect duplicates
- Validate authentication for private leagues

**Interface**:
```python
def parse_league_ids_from_arg(league_id_arg: str) -> list[int]:
    """Parse comma-separated league IDs from CLI argument."""

def create_config(
    league_ids: list[int] | None = None,
    use_env: bool = False,
    year: int | None = None,
    private: bool = False
) -> Config:
    """Create configuration for single or multiple leagues."""
```

### Component 2: ESPNService Multi-League Loading

**Purpose**: Load data from multiple leagues

**Responsibilities**:
- Connect to each league sequentially
- Extract teams, games, weekly data per league
- Create DivisionData for each league
- Fail immediately if any league fails
- Return list of DivisionData

**Interface**:
```python
class ESPNService:
    def load_all_divisions(self) -> list[DivisionData]:
        """Load all configured leagues as divisions."""

    def _load_single_division(self, league_id: int) -> DivisionData:
        """Load one league as division."""
```

### Component 3: DivisionData Model

**Purpose**: Represent single league/division data

**Structure**:
```python
@dataclass(frozen=True)
class DivisionData:
    division_name: str
    teams: list[TeamStats]
    games: list[GameResult]
    weekly_games: list[WeeklyGameResult]
    weekly_players: list[WeeklyPlayerStats]
```

---

## Data Flow

```
CLI: ff-tracker 123,456,789 --private
    ↓
Parse league IDs: [123, 456, 789]
    ↓
Validate: all integers, no duplicates, auth provided
    ↓
For each league ID:
    ├─> Connect to ESPN API
    ├─> Load league data
    ├─> Extract teams, games, weekly data
    ├─> Create DivisionData
    └─> If any fails → raise ESPNAPIError (fail-fast)
    ↓
Return list[DivisionData] (3 divisions)
    ↓
ChallengeCalculator.calculate_all_challenges(divisions)
    ├─> Combines all teams from all divisions
    ├─> Combines all games from all divisions
    └─> Returns aggregated challenge results
    ↓
Formatters receive divisions + challenges
    ├─> Show per-division standings
    └─> Show overall challenge results
```

---

## Implementation Phases

### Phase 1: Configuration Enhancement

**Goal**: Support multiple league IDs in config

**Tasks**:
- [ ] Implement parse_league_ids_from_arg
- [ ] Update create_config to accept list[int]
- [ ] Add duplicate detection
- [ ] Test with various input formats

**Deliverable**: Config handles multiple leagues

**Dependencies**: None

### Phase 2: ESPNService Multi-Connection

**Goal**: Load multiple leagues sequentially

**Tasks**:
- [ ] Implement load_all_divisions
- [ ] Implement _load_single_division
- [ ] Add fail-fast error handling
- [ ] Extract division name from league

**Deliverable**: ESPNService loads multiple leagues

**Dependencies**: Phase 1 complete

### Phase 3: Calculator Aggregation

**Goal**: Ensure calculators handle multiple divisions

**Tasks**:
- [ ] Verify ChallengeCalculator aggregates divisions
- [ ] Verify WeeklyChallengeCalculator aggregates divisions
- [ ] Test cross-division challenge identification
- [ ] Validate performance with multiple divisions

**Deliverable**: Calculators work with multiple divisions

**Dependencies**: Phase 2 complete

### Phase 4: Formatter Division Display

**Goal**: Show per-division and overall data

**Tasks**:
- [ ] Update formatters to show division headers
- [ ] Separate per-division standings
- [ ] Show overall challenge context (division field)
- [ ] Test readability with multiple divisions

**Deliverable**: Formatters display multi-division data clearly

**Dependencies**: Phase 3 complete

---

## Performance Considerations

**Expected Load**: 4 leagues, 10 teams each, 18 weeks
**Performance Target**: < 10 seconds total
**API Calls**: 4 (one per league)

**Optimization**: Sequential loading acceptable, parallel would be premature optimization

---

## Complexity Tracking

> No constitutional deviations.

Potential concern: Loading leagues sequentially could be seen as inefficient.
**Justification**: Premature optimization. Sequential is simple, meets performance targets.
**Future**: Could parallelize if needed, but current approach sufficient.

---

## Related Documentation

- **Feature Spec**: [spec.md](./spec.md)
- **Configuration Contract**: [config.md](./contracts/config.md)
- **ESPN Service Contract**: [espn-service.md](./contracts/espn-service.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial multi-league plan |
