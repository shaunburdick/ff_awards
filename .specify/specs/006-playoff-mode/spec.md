# Feature: Playoff Mode

> **Spec ID**: 006
> **Status**: Ready for Planning
> **Created**: 2025-12-08
> **Last Updated**: 2025-12-08
> **Version**: 1.0

## Overview

Automatically detect and display playoff brackets when leagues transition from regular season to playoffs, culminating in a Championship Week where division winners compete for highest score. This feature provides visual bracket displays, tracks playoff progression, and adapts the output to focus on playoff-relevant data while maintaining historical regular season statistics.

---

## User Stories

### Story 1: Automatic Playoff Detection

**As a** fantasy football league commissioner
**I want** the tool to automatically detect when playoffs start
**So that** I don't need to manually configure playoff mode each week

**Acceptance Criteria:**
- [ ] When `current_week > reg_season_count` for all divisions, playoff mode activates automatically
- [ ] No manual `--playoffs` flag needed (auto-detection only)
- [ ] Tool reads `playoff_team_count` from ESPN API to determine bracket size
- [ ] Tool identifies playoff games using `is_playoff: bool` field from `BoxScore`
- [ ] If divisions are out of sync (some in playoffs, some not), show error and stay in regular season mode

### Story 2: Playoff Bracket Display

**As a** league member
**I want** to see playoff matchups with seeds, teams, owners, and scores
**So that** I can follow playoff progression across all divisions

**Acceptance Criteria:**
- [ ] Playoff bracket section appears at TOP of all output formats
- [ ] Regular season standings appear BELOW playoff bracket for context
- [ ] Each matchup shows: seed numbers, team names, owner names, scores (if available), winner indicator
- [ ] Bracket displays current playoff round (Semifinals, Finals, etc.)
- [ ] All 5 output formats (console, sheets, email, markdown, JSON) display playoff brackets appropriately
- [ ] JSON format includes new `playoff_bracket` section with structured matchup data

### Story 3: Adapted Challenge Display During Playoffs

**As a** league member viewing playoff reports
**I want** to see only relevant challenges during playoffs
**So that** I'm not distracted by irrelevant team statistics from limited matchups

**Acceptance Criteria:**
- [ ] During playoff weeks (before Championship Week): Show 7 player highlights only
- [ ] Hide all 6 team challenges (Highest/Lowest Score, Biggest Win, Closest Game, Overachiever, Below Expectations)
- [ ] Continue showing 5 season challenges with "Regular Season" label indicating they're final/historical
- [ ] Player highlights include all players across all teams (not just playoff teams)

### Story 4: Championship Week Free-For-All

**As a** multi-league commissioner
**I want** division winners to compete in a final "highest score wins" week
**So that** we crown an overall champion across all divisions

**Acceptance Criteria:**
- [ ] After each division crowns a champion (finals complete), Championship Week activates
- [ ] Championship Week displays ONE team per division (the winner)
- [ ] Leaderboard shows: rank, team name, division name (e.g., "Division 1 Champion"), owner name, score
- [ ] Highest scoring division winner is declared overall champion
- [ ] Championship Week shows: championship leaderboard + 7 player highlights + 5 historical season challenges
- [ ] All divisions must reach Championship Week simultaneously or show error

### Story 5: Playoff Data in All Formats

**As a** user of different output formats
**I want** playoff data formatted appropriately for each output type
**So that** I can consume playoff information in my preferred format

**Acceptance Criteria:**
- [ ] Console: Visual bracket using tables with emojis and indicators
- [ ] Sheets (TSV): Structured rows with matchup data (round, seed1, team1, owner1, score1, seed2, team2, owner2, score2, winner)
- [ ] Email (HTML): Styled bracket layout with responsive design
- [ ] Markdown: Text-based bracket with proper formatting for GitHub/Slack/Discord
- [ ] JSON: New `playoff_bracket` array with matchup objects including all matchup details

---

## Business Rules

1. **Playoff Detection Rule**: Playoff mode activates when `current_week > reg_season_count` for ALL configured divisions. If any division is still in regular season, stay in regular season mode and show warning.

2. **Division Synchronization Rule**: All divisions must be in the same playoff stage (all in semifinals, all in finals, all in championship week). Out-of-sync divisions trigger an error message.

3. **Championship Week Eligibility**: Only division winners (one team per division) compete in Championship Week. Winner is determined by highest score in that single week.

4. **Bracket Size Rule**: Number of playoff teams is read from `league.settings.playoff_team_count` (not hardcoded to 4).

5. **Winners Bracket Only**: Only display winners bracket matchups. Consolation brackets are ignored.

6. **Trust ESPN Data**: Display playoff matchups exactly as ESPN API provides them via `league.box_scores(week)` where `is_playoff: True`. No validation of seeding rules.

7. **Winners Bracket Filtering**: Only display matchups where `matchup_type == "WINNERS_BRACKET"`. Ignore `"LOSERS_CONSOLATION_LADDER"` matchups.

8. **Historical Season Challenges**: The 5 season challenges (Most Points Overall, Most Points in One Game, etc.) are finalized at end of regular season and displayed as historical/final during playoffs.

9. **Player Highlights Scope**: During playoffs, player highlights include ALL players across ALL teams (not just playoff teams), filtered to starters only as usual.

---

## Edge Cases and Error Scenarios

### Edge Case 1: Divisions Out of Sync (Playoff Detection)

**Situation**: Division 1 is in week 15 (playoffs), Division 2 is in week 14 (regular season)
**Expected Behavior**: Display error message: "Divisions are out of sync. Division 1: Week 15 (Playoffs), Division 2: Week 14 (Regular Season). All divisions must be in playoffs to activate playoff mode."
**Rationale**: Prevents confusing mixed-mode displays and encourages synchronized league management

### Edge Case 2: Divisions Out of Sync (Championship Week)

**Situation**: Division 1 has crowned champion, Division 2 still in semifinals
**Expected Behavior**: Display error message: "Divisions are out of sync for Championship Week. Division 1: Championship Week, Division 2: Semifinals. All divisions must reach Championship Week simultaneously."
**Rationale**: Championship Week requires all division winners to compete together

### Edge Case 3: Missing Playoff Data

**Situation**: Tool detects playoffs (`current_week > reg_season_count`) but `league.box_scores(week)` returns no games with `is_playoff: True`
**Expected Behavior**: Display warning: "Playoff week detected but no playoff games found. Showing regular season view." Fall back to regular season display.
**Rationale**: Graceful degradation when API data is incomplete

### Edge Case 4: Incomplete Playoff Games

**Situation**: Playoff week in progress, some matchups have scores, others show 0-0
**Expected Behavior**: Display bracket with available scores. Show "In Progress" or blank for games not yet played.
**Rationale**: Users want to see partial playoff results as games complete

### Error Scenario 1: Unable to Determine Playoff Team Count

**Trigger**: `league.settings.playoff_team_count` is missing or invalid
**Error Handling**: Log warning, fall back to calculating top 4 teams by record (existing logic)
**User Experience**: Bracket displays with best-effort team selection, warning in logs

### Error Scenario 2: ESPN API Returns Unexpected Playoff Matchups

**Trigger**: Playoff matchups don't follow expected seeding (e.g., #1 vs #2 in semifinals)
**Error Handling**: Display matchups as-is (trust ESPN data per Business Rule #6)
**User Experience**: Bracket shows actual matchups, no validation errors

---

## Non-Functional Requirements

### Performance
- Playoff detection adds no significant overhead (reads fields already fetched: `current_week`, `reg_season_count`)
- Bracket display should render in under 1 second for typical multi-league setups (3-4 divisions)

### Accuracy
- Playoff team identification must match ESPN's official playoff bracket
- Championship Week winner determined by exact score comparison (no rounding)
- Seed numbers must match `team.standing` from ESPN API

### Reliability
- If playoff data unavailable, gracefully fall back to regular season display
- Synchronization checks prevent invalid multi-league states
- All playoff detection logic is deterministic (no random behavior)

### Usability
- Playoff brackets are visually distinct from regular season standings
- Clear labels indicate playoff round (Semifinals, Finals, Championship Week)
- Error messages for out-of-sync divisions are actionable and specific

---

## Data Requirements

### Input Data

**Data Source**: ESPN Fantasy Football API via `espn_api.football.League`

**Required Fields**:
- `league.current_week` (int): Current week number from ESPN
- `league.settings.reg_season_count` (int): Number of regular season weeks
- `league.settings.playoff_team_count` (int): Number of teams in playoff bracket
- `league.settings.playoff_matchup_period_length` (int): Weeks per playoff round (typically 1)
- `league.box_scores(week)` → `BoxScore.is_playoff` (bool): Identifies playoff games
- `league.box_scores(week)` → `BoxScore.matchup_type` (str): "WINNERS_BRACKET" or "LOSERS_CONSOLATION_LADDER"
- `team.standing` (int): Playoff seed number (1-4 for playoff teams)
- `team.playoff_pct` (float): 100.0 for playoff teams, 0.0 for eliminated
- `team.team_name` (str): Team name
- `team.owners` (list): Owner information

**Data Validation**:
- `current_week` must be positive integer
- `reg_season_count` must be positive integer (typically 14)
- `playoff_team_count` must be even number (typically 4 or 6)
- All divisions must have same `reg_season_count` and `playoff_team_count`

### Output Data

**Playoff Bracket Structure** (for all formats):
```python
playoff_bracket = {
    "round": str,  # "Semifinals", "Finals", "Championship Week"
    "week": int,
    "matchups": [
        {
            "matchup_id": str,
            "seed1": int,
            "team1": str,
            "owner1": str,
            "score1": float | None,
            "seed2": int,
            "team2": str,
            "owner2": str,
            "score2": float | None,
            "winner": str | None,  # team name of winner
            "division": str
        }
    ]
}
```

**Championship Week Leaderboard**:
```python
championship_leaderboard = [
    {
        "rank": int,
        "team_name": str,
        "owner_name": str,
        "division": str,
        "score": float
    }
]
```

---

## Constraints

### Technical Constraints
- Must use existing `ESPNService` architecture (no new API client)
- Must preserve all existing output formats (console, sheets, email, markdown, JSON)
- Type safety: 100% type coverage required per constitution
- Immutable data models: Use `@dataclass(frozen=True)` pattern

### Business Constraints
- Cannot show consolation brackets (winners bracket only)
- Cannot create new playoff-specific challenges beyond existing 7 player highlights
- Must maintain regular season standings display during playoffs (for context)

### External Dependencies
- ESPN API must provide `is_playoff` field on `BoxScore` objects
- ESPN API must provide `playoff_team_count` in `league.settings`
- **[TESTING REQUIRED]** Need to verify ESPN API behavior with live playoff data (week 15+) to confirm bracket structure

---

## Out of Scope

Explicitly list what this feature does **not** include:
- Consolation bracket display (only winners bracket)
- New playoff-specific challenges (e.g., "Biggest Upset", "Playoff MVP")
- Historical playoff data from previous years
- Playoff predictions or projections
- Manual `--playoffs` flag (auto-detection only)
- Editing or modifying playoff brackets
- Support for divisions in different playoff stages (must be synchronized)
- Single-elimination tournaments with more than 2 rounds (assumes 2-round playoffs + championship)

---

## Open Questions

**[RESOLVED]** ESPN API Playoff Data Structure ✅
- ✅ Tested with live playoff data (Week 15, 2025-12-10)
- ✅ Confirmed: `current_week > reg_season_count` detects playoffs perfectly
- ✅ Confirmed: `team.standing` provides exact seed numbers (1-4)
- ✅ Confirmed: `playoff_matchup_period_length = 1` (1 week per round)
- ✅ Confirmed: Semifinal matchups are #1 vs #4, #2 vs #3
- ✅ Confirmed: `matchup_type` field distinguishes winners vs consolation brackets
- 📝 See ESPN_API_TESTING.md for full test results

**[TESTING REQUIRED]** Championship Week Detection:
- Need to test Week 16 (Finals) and Week 17 (Championship Week) to confirm:
  - How finals matchups are structured (2 teams remaining)
  - Whether Championship Week uses a special `matchup_type`
  - How to detect when all divisions have crowned champions
- **Action**: Re-run test_playoff_api.py on Week 16 and Week 17

## Design Decisions (From Iteration)

The following design decisions were confirmed through example iteration:

1. **Bracket Layout**: Table format (not ASCII art brackets)
2. **Champion Emphasis**: Dramatic styling with large trophy banner and gold theme
3. **Sheets Format**: Simple TSV rows (straightforward, no examples needed)
4. **Email Format**: Full HTML examples created (see examples/08-semifinals-email.html, examples/09-championship-email.html)
5. **In-Progress Games**: Show partial scores with status indicators ("In Progress", "Not Started", "Live")
6. **Division Titles**: "Division 2" format in championship leaderboard (current format retained)
7. **Regular Season Standings**: Show ALL teams during playoffs for full context (Option A)

---

## Success Metrics

How will we know this feature is successful?

- **Automatic Detection**: 100% of playoff transitions detected without manual intervention
- **Data Accuracy**: Playoff brackets match ESPN's official brackets exactly (verified by manual inspection)
- **Format Consistency**: All 5 output formats render playoff data correctly
- **Error Handling**: Out-of-sync divisions display clear error messages (verified by testing mismatched leagues)
- **Performance**: No measurable performance degradation (< 5% increase in execution time)

---

## Related Specifications

- **001-season-challenges**: Season challenges become "historical" during playoffs
- **002-weekly-highlights**: Weekly challenges adapted (player highlights only during playoffs)
- **003-output-formatters**: All formatters extended to support playoff bracket display
- **004-multi-league-support**: Multi-league synchronization rules for playoff detection

---

## Revision History

| Version | Date       | Author           | Changes                                      |
|---------|------------|------------------|----------------------------------------------|
| 0.1     | 2025-12-08 | Spec Planner     | Initial draft based on clarification session |
| 1.0     | 2025-12-08 | Spec Planner     | Finalized with examples and design decisions |
| 1.1     | 2025-12-10 | Spec Planner     | Updated with ESPN API test results (Week 15) |
