# Feature: Weekly Performance Highlights

> **Spec ID**: 002
> **Status**: Active
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Overview

Track 13 current-week performance highlights (6 team challenges + 7 player highlights) to identify exceptional weekly performances across all leagues. Provides real-time weekly awards complementing season-long challenges.

---

## User Stories

### Story 1: Weekly Team Performance Awards

**As a** fantasy football league manager
**I want** to identify the best and worst team performances this week
**So that** I can recognize standout weekly achievements

**Acceptance Criteria:**
- [ ] System calculates 6 team challenges for current week only
- [ ] Highest and lowest scores identified
- [ ] Biggest win and closest game calculated with margins
- [ ] Overachiever and below expectations based on true projections
- [ ] All results show current week number
- [ ] Works across multiple divisions

### Story 2: Weekly Player Spotlight

**As a** fantasy football league manager
**I want** to identify the top scoring players by position this week
**So that** I can celebrate individual player performances

**Acceptance Criteria:**
- [ ] System calculates 7 player highlights for current week
- [ ] Top scorer overall identified
- [ ] Best player by position (QB, RB, WR, TE, K, D/ST)
- [ ] Only starting lineup players included (bench excluded)
- [ ] Shows player name, points, team, and position
- [ ] Works across all divisions

### Story 3: True Projection Analysis

**As a** fantasy football league manager
**I want** projection analysis based on pre-game starter projections
**So that** boom/bust awards reflect actual pre-game expectations

**Acceptance Criteria:**
- [ ] System calculates true projections by summing starter projected points
- [ ] Overachiever = team most above true projection
- [ ] Below Expectations = team most below true projection
- [ ] Ignores ESPN's real-time adjusted projections
- [ ] Shows both true projection and actual score with difference

---

## Business Rules

1. **Current Week Only**: Challenges apply only to current/most recent week, not historical weeks
2. **Starter-Only Analysis**: Player highlights only consider players in starting lineups (bench players excluded)
3. **True Projections Required**: Pre-game starter projections must be available for projection-based challenges
4. **Division Aggregation**: Challenges calculated across ALL divisions (not per-division)
5. **First-to-Achieve Wins**: For ties, first occurrence in data order wins

---

## Edge Cases and Error Scenarios

### Edge Case 1: Week Hasn't Started

**Situation**: Current week games not yet played
**Expected Behavior**: Raise `InsufficientDataError` - no weekly data available
**Rationale**: Cannot calculate weekly highlights without game data

### Edge Case 2: Projections Unavailable

**Situation**: ESPN API doesn't provide starter projections
**Expected Behavior**: Skip projection-based challenges, calculate other 11 challenges
**Rationale**: Projection data sometimes unavailable, but other challenges still valuable

### Edge Case 3: No Starters Identified

**Situation**: BoxScore data doesn't indicate starting lineup
**Expected Behavior**: Raise `InsufficientDataError` - cannot filter to starters
**Rationale**: Including bench players would produce incorrect results

### Error Scenario 1: No Weekly Game Data

**Trigger**: ESPN API returns no BoxScore data for current week
**Error Handling**: Raise `InsufficientDataError` with week number
**User Experience**: "No game data available for week 12. Games may not have started yet."

### Error Scenario 2: Incomplete Player Data

**Trigger**: Player stats missing position, points, or team
**Error Handling**: Raise `DataValidationError` with missing field
**User Experience**: "Invalid player data: position field missing for player ID 12345"

---

## Non-Functional Requirements

### Performance
- Calculate all 13 challenges for current week in under 3 seconds
- Memory usage O(n) where n is number of players in current week

### Accuracy
- True projections must match sum of individual starter projections
- Player position classification must match ESPN designations
- Score calculations accurate to 2 decimal places

### Reliability
- Fail fast on any incomplete weekly data
- Clear distinction between unavailable data and calculation errors
- Graceful handling when projections unavailable (skip those challenges)

### Usability
- Challenge names clearly indicate weekly vs season scope
- Results include enough context (week number, opponent, margin)
- Player highlights show team context for relatability

---

## Data Requirements

### Input Data
- **Data Source**: BoxScore API from ESPN for current week
- **Required Fields (Games)**:
  - team_name, opponent, score, projected_score, starter_projected_score
  - week number, division
- **Required Fields (Players)**:
  - name, position, points, team_name
  - is_starter flag (true for starting lineup)
- **Data Validation**:
  - All scores >= 0
  - Week number matches expected current week
  - Position is valid (QB, RB, WR, TE, K, D/ST)
  - Starter flag present and valid

### Output Data
- **Output Format**: List of WeeklyChallenge objects
- **WeeklyChallenge Structure**:
  - challenge_name: str
  - challenge_type: str ("team" or "player")
  - team_name: str (or player name for player challenges)
  - owner: Owner object
  - score: float
  - additional_info: dict[str, str | float | int]
- **Output Validation**:
  - Up to 13 results (fewer if projections unavailable)
  - All required fields populated
  - challenge_type correctly set
  - Week number included in additional_info

---

## Constraints

### Technical Constraints
- Must use ESPN BoxScore API for weekly data
- Cannot reprocess historical weeks (current week only)
- Depends on espn-api library's BoxScore implementation

### Business Constraints
- Cannot change challenge definitions mid-season (consistency)
- Starter/bench distinction critical for fairness
- Projection methodology must be transparent and consistent

### External Dependencies
- ESPN BoxScore API must provide current week data
- ESPN must indicate which players are starters vs bench
- Starter projections must be accessible before games complete

---

## Out of Scope

Explicitly list what this feature does **not** include:

- Historical weekly tracking (single week only)
- Custom or user-defined weekly challenges
- Playoff week analysis (regular season only)
- Individual game-level analysis (aggregated week level)
- Bench player performance tracking
- Mid-week partial results (full week only)

---

## Success Metrics

How will we know this feature is successful?

- **Accuracy**: 100% correct identification of weekly winners
- **Performance**: All 13 challenges calculated in under 3 seconds
- **Reliability**: Handles missing projection data gracefully
- **Usability**: Users immediately understand weekly vs season context

---

## Related Specifications

- **001: Season Challenges**: Similar calculation pattern but season scope
- **003: Output Format System**: Weekly results rendered by all formatters
- **ESPN Service Contract**: Defines BoxScore data extraction

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial specification for weekly highlights |
