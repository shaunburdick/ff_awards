# Feature: Multi-League Support (Divisions)

> **Spec ID**: 004
> **Status**: Active
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Overview

Support multiple ESPN leagues analyzed as divisions with aggregated challenges and overall rankings. Enables commissioner-level view across entire multi-league organization while maintaining per-division standings.

---

## User Stories

### Story 1: Multi-League Configuration

**As a** commissioner managing multiple leagues
**I want** to provide multiple league IDs via CLI or environment
**So that** I can analyze all leagues together

**Acceptance Criteria:**
- [ ] Support comma-separated league IDs in CLI: `ff-tracker 123,456,789`
- [ ] Support LEAGUE_IDS environment variable
- [ ] Support --env flag to load from environment
- [ ] Validate all league IDs are valid integers
- [ ] Clear error message if any league fails to load

### Story 2: Division-Based Organization

**As a** commissioner viewing multi-league results
**I want** each league treated as a named division
**So that** I can see both divisional and overall standings

**Acceptance Criteria:**
- [ ] Each league becomes a named division
- [ ] Division name extracted from ESPN league settings
- [ ] Standings shown per-division with dividers
- [ ] Overall rankings aggregate all teams
- [ ] Playoff positions calculated per-division (top 4)

### Story 3: Cross-Division Challenges

**As a** commissioner tracking achievements
**I want** challenges calculated across all divisions
**So that** the best performances are recognized organization-wide

**Acceptance Criteria:**
- [ ] Season challenges aggregate all division games
- [ ] Weekly challenges aggregate all division data
- [ ] Winners can come from any division
- [ ] Division shown in challenge result context
- [ ] No per-division challenge calculation (overall only)

---

## Business Rules

1. **Single API Call Per League**: Each league fetched once, data cached for all operations
2. **Fail If Any League Fails**: All leagues must load successfully (no partial data)
3. **Division Names from ESPN**: Use league name from ESPN as division identifier
4. **Overall Aggregation**: Challenges always calculated across ALL divisions
5. **Per-Division Playoffs**: Top 4 determined within each division, not overall

---

## Edge Cases and Error Scenarios

### Edge Case 1: Single League as Division

**Situation**: User provides single league ID
**Expected Behavior**: Treat as one division, works identically to single-league mode
**Rationale**: No special case logic needed

### Edge Case 2: Many Leagues (10+)

**Situation**: User provides 10 or more league IDs
**Expected Behavior**: Process all successfully if data available, may take longer
**Rationale**: No artificial limit on league count

### Edge Case 3: Duplicate League IDs

**Situation**: User provides same league ID multiple times
**Expected Behavior**: Raise ConfigurationError about duplicate IDs
**Rationale**: Likely user error, prevent confusing results

### Error Scenario 1: League Load Failure

**Trigger**: One league ID invalid or API fails for that league
**Error Handling**: Raise ESPNAPIError with specific league ID that failed
**User Experience**: "Failed to load league 123456: League not found or private"

### Error Scenario 2: Mixed Public/Private Leagues

**Trigger**: Some leagues public, some private, missing credentials
**Error Handling**: Raise ConfigurationError about authentication
**User Experience**: "Private leagues detected but ESPN_S2/SWID not provided. Use --private flag."

---

## Non-Functional Requirements

### Performance
- Load and process 4 leagues in < 10 seconds
- Linear scaling O(n) where n is number of leagues
- Maximum 18 weeks per league (bounded)

### Reliability
- All leagues must load successfully (fail-fast on any failure)
- Consistent ordering of divisions in output
- Deterministic results across runs

### Usability
- Clear indication which data is per-division vs overall
- Division names prominent in output
- Easy to identify which division a team belongs to

---

## Data Requirements

### Input Data
- **CLI**: Comma-separated league IDs or --env flag
- **Environment**: LEAGUE_IDS variable with comma-separated values
- **Authentication**: ESPN_S2 and SWID if --private flag used
- **Validation**: All IDs must be valid integers

### Output Data
- **DivisionData List**: One per league
- **Each Division Contains**:
  - division_name: str (from ESPN league settings)
  - teams: list[TeamStats]
  - games: list[GameResult]
  - weekly_games: list[WeeklyGameResult]
  - weekly_players: list[WeeklyPlayerStats]

---

## Constraints

### Technical Constraints
- espn-api library rate limits (respect them)
- Each league requires separate API connection
- League data must be from same year

### Business Constraints
- All leagues must use same scoring settings (for fair comparison)
- League names must be distinct (or add suffix if duplicate)

### External Dependencies
- ESPN API must be accessible for all leagues
- All leagues must be accessible to provided credentials

---

## Out of Scope

- Per-division challenge calculations (overall only)
- Cross-league trades or roster management
- Historical multi-season tracking
- Custom division naming (use ESPN names)
- Merging leagues with different scoring systems

---

## Success Metrics

- **Correctness**: Challenges aggregate all divisions correctly
- **Performance**: 4 leagues load and process in < 10 seconds
- **Reliability**: Zero partial data scenarios
- **Usability**: Clear division vs overall distinction

---

## Related Specifications

- **001: Season Challenges**: Aggregates across divisions
- **002: Weekly Highlights**: Aggregates across divisions
- **ESPN Service Contract**: Handles multiple league connections

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial multi-league specification |
