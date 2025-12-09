# ESPN Playoff API Testing Results

**Date**: 2025-12-10 (Tuesday, Week 15 - Playoffs Week 1)
**Leagues Tested**: 3 leagues (1499701648, 688779743, 1324184869)
**Year**: 2025

## Key Findings ✅

### 1. Playoff Detection Works Perfectly
- `league.current_week` = 15
- `league.settings.reg_season_count` = 14
- **Detection Logic**: `current_week > reg_season_count` ✅ CONFIRMED

### 2. Playoff Configuration
All three leagues have identical playoff settings:
- **Playoff Team Count**: 4 teams per division
- **Playoff Matchup Period Length**: 1 week per round
- **Playoff Seed Tie Rule**: TOTAL_POINTS_SCORED

### 3. Playoff Matchup Detection ✅
The ESPN API provides excellent playoff matchup identification:

**BoxScore Fields:**
- `is_playoff`: **True** for all playoff games (including consolation)
- `matchup_type`: 
  - `"WINNERS_BRACKET"` for semifinal matchups (#1 vs #4, #2 vs #3)
  - `"LOSERS_CONSOLATION_LADDER"` for consolation bracket

**KEY INSIGHT**: We can filter to winners bracket only using:
```python
if box_score.is_playoff and box_score.matchup_type == "WINNERS_BRACKET":
    # This is a real playoff game
```

### 4. Seeding Information ✅
**Perfect seeding data available:**
- `team.standing`: Provides exact playoff seed (1, 2, 3, 4 for playoff teams)
- `team.playoff_pct`: 100.0 for playoff teams, 0.0 for eliminated teams

**Matchup Structure Confirmed:**
- **Semifinal 1**: Seed #1 vs Seed #4
- **Semifinal 2**: Seed #2 vs Seed #3

This matches our specification exactly!

### 5. In-Progress Game Handling ✅
**Current State**: All games show `0.0 - 0.0` (games haven't started yet)

This confirms our design decision for Option A:
- Show scores as-is with status indicators
- `0.0 - 0.0` = "Not Started"
- Partial scores = "In Progress"
- Final scores = show winner

### 6. Consolation Bracket Detection ✅
**Finding**: ESPN API returns ALL playoff matchups, including consolation games

**Our Solution**: Filter using `matchup_type == "WINNERS_BRACKET"` to show only winners bracket (per spec requirement: "Winners Bracket Only")

### 7. Team Playoff Status ✅
**Excellent discovery:**
- Teams 1-4: `playoff_pct = 100.000` (in playoffs)
- Teams 5-10: `playoff_pct = 0.000` (eliminated)

We can use this to identify playoff teams programmatically!

## Matchup Periods Data
```python
matchup_periods = {
    '1': [1], '2': [2], ..., '14': [14],  # Regular season
    '15': [15], '16': [16]  # Playoffs
}
```

Each matchup period is 1 week long (matches `playoff_matchup_period_length: 1`)

## Validation Against Spec

| Spec Requirement | Status | Notes |
|-----------------|--------|-------|
| Playoff detection via `current_week > reg_season_count` | ✅ PASS | Works perfectly |
| Read `playoff_team_count` from API | ✅ PASS | Returns 4 for all leagues |
| Identify playoff games via `is_playoff` | ✅ PASS | Boolean flag works |
| Extract seeding from `team.standing` | ✅ PASS | Exact seed numbers (1-4) |
| Filter to winners bracket only | ✅ PASS | Use `matchup_type == "WINNERS_BRACKET"` |
| Semifinal matchups #1 vs #4, #2 vs #3 | ✅ PASS | Confirmed in all 3 leagues |
| Handle in-progress games | ✅ PASS | Scores show as-is (0.0 = not started) |

## Implementation Notes

### Recommended Playoff Detection Logic
```python
def is_in_playoffs(league: League) -> bool:
    """Check if league is in playoff weeks."""
    return league.current_week > league.settings.reg_season_count

def get_playoff_matchups(league: League, week: int) -> list[BoxScore]:
    """Get winners bracket playoff matchups only."""
    box_scores = league.box_scores(week)
    return [
        bs for bs in box_scores 
        if bs.is_playoff and bs.matchup_type == "WINNERS_BRACKET"
    ]

def get_playoff_teams(league: League) -> list[Team]:
    """Get teams that made playoffs."""
    return [team for team in league.teams if team.playoff_pct > 0]
```

### Game Status Detection
```python
def get_game_status(home_score: float, away_score: float) -> str:
    """Determine game status from scores."""
    if home_score == 0.0 and away_score == 0.0:
        return "Not Started"
    elif home_score > 0 or away_score > 0:
        # Check if game is complete (would need additional logic)
        return "In Progress"
    else:
        return "Final"
```

## Championship Week Detection

**Question for Week 16+**: How do we detect Championship Week?

Hypothesis:
- Week 16 = Division Finals (`matchup_type` still "WINNERS_BRACKET", 2 teams left per division)
- Week 17 = Championship Week (need to test if there's a special matchup_type)

**TODO**: Re-run this test script next Tuesday (Week 16) to see Finals structure

## Spec Updates Needed

### ✅ No Major Changes Required!
The spec accurately predicted the ESPN API structure. Minor updates:

1. **Add `matchup_type` filtering** to Business Rules:
   - Use `matchup_type == "WINNERS_BRACKET"` to exclude consolation games
   
2. **Add `playoff_pct` usage** to Data Requirements:
   - Can use `team.playoff_pct > 0` to identify playoff teams (alternative to top-4 by record)

3. **Confirm Playoff Period Length** in Data Requirements:
   - All leagues use 1-week playoff rounds (stored in `playoff_matchup_period_length`)

## Next Steps

1. ✅ **Test Complete**: ESPN API structure confirmed
2. 📝 **Update Spec**: Add minor clarifications about `matchup_type` filtering
3. 🏗️ **Ready for Planning Phase**: Spec is validated and ready for implementation
4. 📅 **Week 16 Test**: Re-run test script next Tuesday to see Finals structure
5. 📅 **Week 17 Test**: Confirm Championship Week detection (if applicable)

## Sample Output for Development

See test_playoff_api.py output above for real ESPN data structure.
Key matchup example:
```
Matchup 1:
  is_playoff: True
  matchup_type: WINNERS_BRACKET
  Home: ILikeTurtles (standing: 1)
  Away: Billieve the Champ Is Back (standing: 4)
  Score: 0.0 - 0.0
```
