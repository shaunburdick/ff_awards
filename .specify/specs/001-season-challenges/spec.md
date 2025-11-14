# Feature: Season-Long Challenge Tracking

> **Spec ID**: 001
> **Status**: Active
> **Created**: 2025-11-14
> **Last Updated**: 2025-11-14

## Overview

Track 5 season-long fantasy football challenges across regular season games to award prizes at end of season. Challenges identify exceptional performances in both winning and losing scenarios.

---

## User Stories

### Story 1: Most Points Overall Champion

**As a** fantasy football league manager
**I want** to identify the team that scored the most total points during the regular season
**So that** I can award a prize for overall offensive excellence

**Acceptance Criteria:**
- [ ] System calculates total points_for across all teams
- [ ] Winner is team with highest points_for
- [ ] Ties result in multiple winners with equal recognition
- [ ] Display shows team name, owner name, and total points
- [ ] Works correctly across multiple leagues (divisions)

### Story 2: Single Game Scoring Record

**As a** fantasy football league manager
**I want** to identify the highest score achieved in any single game
**So that** I can award a prize for the best single week performance

**Acceptance Criteria:**
- [ ] System examines all individual game scores
- [ ] Winner is team with highest single game score
- [ ] Display shows team name, owner, score, opponent, and week number
- [ ] First to achieve the score wins ties
- [ ] Works across all games in all divisions

### Story 3: Highest Scoring Loss

**As a** fantasy football league manager
**I want** to identify the team that scored the most points in a losing effort
**So that** I can provide consolation for "bad luck" losses

**Acceptance Criteria:**
- [ ] System identifies all games where team lost
- [ ] Winner is team with highest score among losses
- [ ] Display shows team name, owner, score, opponent score, and week
- [ ] First to achieve wins ties
- [ ] Only considers completed games with winner/loser

### Story 4: Lowest Scoring Win

**As a** fantasy football league manager
**I want** to identify the team that won with the lowest score
**So that** I can award a prize for "lucky" wins

**Acceptance Criteria:**
- [ ] System identifies all games where team won
- [ ] Winner is team with lowest score among wins
- [ ] Display shows team name, owner, score, opponent score, and week
- [ ] First to achieve wins ties
- [ ] Only considers completed games with winner/loser

### Story 5: Closest Victory

**As a** fantasy football league manager
**I want** to identify the closest victory (smallest winning margin)
**So that** I can recognize the most exciting close game

**Acceptance Criteria:**
- [ ] System calculates margin for all wins (winner_score - loser_score)
- [ ] Winner is game with smallest positive margin
- [ ] Display shows both team names, owners, scores, margin, and week
- [ ] First to achieve wins ties
- [ ] Margin must be positive (ties are not victories)

---

## Business Rules

1. **Regular Season Only**: Challenges only apply to regular season games, playoff games are excluded
2. **First-to-Achieve Wins Ties**: If multiple teams tie for a challenge, the first team chronologically to achieve that result wins (by week number, then by team ID)
3. **Multiple Winners Allowed**: In rare cases where teams achieve identical results in the same week, both can be declared co-winners
4. **Division Aggregation**: When multiple leagues are tracked as divisions, challenges are calculated across ALL divisions (not per-division)
5. **Complete Games Only**: Only consider games that have final scores (both teams played, no byes or missing data)

---

## Edge Cases and Error Scenarios

### Edge Case 1: Perfect Tie Scores

**Situation**: Two teams achieve identical scores in the same week
**Expected Behavior**: Compare by secondary criteria (team ID, alphabetical) or declare co-winners
**Rationale**: Extremely rare but possible, need deterministic tiebreaker

### Edge Case 2: No Games Played Yet

**Situation**: Season hasn't started, no game data available
**Expected Behavior**: Return placeholder results or empty challenge list with clear message
**Rationale**: Early season runs should not crash, just show no data available

### Edge Case 3: Incomplete Game Data

**Situation**: Some games missing scores (API failure, data corruption)
**Expected Behavior**: Raise `InsufficientDataError` with details about missing data
**Rationale**: Incomplete data leads to incorrect results; fail clearly rather than produce misleading output

### Error Scenario 1: No Division Data

**Trigger**: API returns empty division list or all divisions fail to load
**Error Handling**: Raise `InsufficientDataError` with actionable message
**User Experience**: "No division data available. Check league IDs and ESPN API access."

### Error Scenario 2: Data Validation Failure

**Trigger**: Game data has negative scores, missing teams, or invalid structures
**Error Handling**: Raise `DataValidationError` with specific field that failed
**User Experience**: "Invalid game data: points_for cannot be negative (-10.5)"

---

## Non-Functional Requirements

### Performance
- Calculate all 5 challenges for maximum 18 weeks of games in under 5 seconds
- Memory usage should be O(n) where n is number of games (bounded by season length)

### Accuracy
- Calculations must be mathematically correct (no rounding errors affecting winners)
- Tie-breaking must be deterministic and consistent
- Week numbers must accurately reflect when achievement occurred

### Reliability
- Fail fast on any missing or invalid data
- Validate all input data before processing
- Clear error messages for all failure modes

### Usability
- Challenge results easy to understand (clear names, full context)
- Display format works across all output formatters (console, email, JSON, etc.)

---

## Data Requirements

### Input Data
- **Data Source**: DivisionData objects from ESPN API service
- **Required Fields**:
  - Teams: name, owner, points_for, points_against, wins, losses, division
  - Games: team1_name, team1_score, team2_name, team2_score, week, division
- **Data Validation**:
  - All scores must be >= 0
  - Team names must be non-empty
  - Week numbers must be positive integers
  - Division names must be non-empty

### Output Data
- **Output Format**: List of ChallengeResult objects
- **ChallengeResult Structure**:
  - challenge_name: str (e.g., "Most Points Overall")
  - team_name: str
  - owner: Owner object
  - score: float (the achievement value)
  - additional_info: dict[str, str | float | int] (context like opponent, week, margin)
- **Output Validation**:
  - Exactly 5 results (one per challenge)
  - All required fields populated
  - additional_info contains appropriate context for challenge type

---

## Constraints

### Technical Constraints
- Must work with espn-api Python library data structures
- Cannot make additional API calls (work with loaded data only)
- Must follow immutable data model pattern (frozen dataclasses)

### Business Constraints
- Cannot change challenge definitions (historically consistent definitions)
- Must support both single league and multi-league (division) operation

### External Dependencies
- ESPN API data must be loaded first via ESPNService
- Depends on TeamStats and GameResult models being properly constructed

---

## Out of Scope

Explicitly list what this feature does **not** include:

- Playoff games or championship calculations
- Historical multi-season tracking (single season only)
- Player-level achievements (handled by Weekly Challenges feature)
- Custom or user-defined challenges (fixed to these 5)
- Automated prize distribution or notifications
- Challenge leaderboards showing top N (just winners)

---

## Success Metrics

How will we know this feature is successful?

- **Accuracy**: 100% correct winner identification validated against manual calculation
- **Performance**: All 5 challenges calculated in under 5 seconds for maximum season length (18 weeks)
- **Reliability**: Zero crashes on valid ESPN data, fail fast on any incomplete data
- **Usability**: Users can immediately understand results without additional explanation

---

## Related Specifications

- **002: Weekly Highlights**: Similar calculation pattern but for current week only
- **003: Output Format System**: Challenge results are rendered by all formatters
- **ESPN Service Contract**: Defines the DivisionData structure used as input

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-14 | AI Agent | Initial specification based on working implementation |
