# Game Status Detection for Championship Week

## ESPN API Limitation Discovered

When fantasy leagues officially end (typically Week 16 Finals), ESPN treats subsequent weeks differently:

### Original Problem (Discovered Dec 28, 2025)

When calling `league.box_scores(17)` for leagues that ended at Week 16:
- **Returns Week 16 data** instead of Week 17
- All player stats show Week 16 scores and dates
- `player.stats` dictionary only contains `{16: {...}}` 
- Week 17 games appear as Week 16 Finals matchups

**Example:**
```python
# Calling league.box_scores(17) for ended league
box_scores = league.box_scores(17)  # Returns Week 16 data!
player = box_scores[0].home_lineup[0]

player.name  # "Dak Prescott"
player.points  # 19.16 (Week 16 score from Dec 21)
player.game_date  # 2025-12-21 (Week 16 game date)
player.stats  # {16: {'points': 19.16, ...}}  # Only Week 16!
```

### The Solution: Use team.roster for Week 17+

ESPN **does** track Week 17 data, but it's stored in the team roster, not box scores:

```python
# Access Week 17 data from team roster
team = league.teams[0]
for player in team.roster:
    if 17 in player.stats:
        week_17_data = player.stats[17]
        points = week_17_data['points']  # Live Week 17 scores!
        projected = week_17_data['projected_points']
```

**Confirmed Working (Dec 28, 2025 - Live Week 17 Games):**
- Dak Prescott: 22.68 pts (played early game)
- Lions D/ST: 10.0 pts (played early game)  
- Ja'Marr Chase: 0.0 pts (game not started yet)
- Progress: 8/30 games completed

## Our Solution: Dual-Mode Data Fetching

The championship service now uses two different methods:

### Mode 1: Box Scores (Week 16 and earlier)

For weeks where the league was active, use standard box_scores API:

```python
def _get_roster_from_box_score(league, team, week):
    box_scores = league.box_scores(week)
    # Find team's box score and extract lineup
    # Works perfectly for active league weeks
```

### Mode 2: Team Roster (Week 17+)

For post-season weeks, fetch data from team.roster:

```python
def _get_roster_from_team_roster(league, team, week):
    espn_team = find_team_by_id(league.teams, team.team_id)
    
    for player in espn_team.roster:
        if week in player.stats:
            week_data = player.stats[week]
            points = week_data['points']  # Live scores!
            projected = week_data['projected_points']
```

### Game Status Detection

For Week 17+ data from roster, we use simple logic:

```python
def _get_game_status_from_week_data(week_data, projected):
    points = week_data['points']
    
    # Player ruled out/inactive
    if projected == 0.0 and points == 0.0:
        return "final"
    
    # Game not started yet
    if points == 0.0 and projected > 0.0:
        return "not_started"
    
    # Game started/completed
    return "final"
```

## Results

**Tested Dec 28, 2025 during live Week 17 games:**

✅ **Accurate Score Tracking**
- Players who played: Show actual Week 17 scores
- Players not yet played: Show 0.00 with projections
- Real-time progress: 8/30 games completed

✅ **Game Status Detection**
- `⏳ not_started` - Games happening later today
- `✓ final` - Early games already completed

✅ **Live Leaderboard**
- Miller Time: 47.1 pts (leading)
- Billieve the Champ: 32.68 pts
- Ja'marr Wars: 27.4 pts

## Technical Implementation

The fix was implemented in `championship_service.py`:

1. **Main router** (`get_roster`): Detects week and routes to appropriate method
2. **Box score method** (`_get_roster_from_box_score`): For Week ≤ 16
3. **Roster method** (`_get_roster_from_team_roster`): For Week ≥ 17
4. **Status helper** (`_get_game_status_from_week_data`): Analyzes week data dictionary

This ensures accurate Week 17 tracking while maintaining backward compatibility with playoff weeks.

## Known Limitations

1. **Cannot distinguish "in_progress" from "final"**: Once a player scores points, we mark as "final"
2. **Backup players with 0 points**: If a player plays but gets 0 points, marked as "not_started" (rare)
3. **No live updates during games**: ESPN updates scores periodically, not in real-time

## Testing Verification

### Real Data Test (Dec 28, 2025)

**Before Fix:**
- All players showing Week 16 data (Dec 20-21 game dates)
- Dak Prescott: 19.16 pts (Week 16 score)
- Total: 162.06 pts (Week 16 Finals total)

**After Fix:**
- Players showing live Week 17 data
- Dak Prescott: 22.68 pts (Week 17 actual)
- Mixed status: 8/30 games completed
- Live leaderboard updating as games finish

### Edge Cases Tested

1. ✅ **Player who played**: Dak Prescott (22.68 pts) → status="final"
2. ✅ **Player not started**: Ja'Marr Chase (0 pts, proj 20.63) → status="not_started"
3. ✅ **Defense**: Lions D/ST (10.0 pts) → status="final"
4. ✅ **Progress tracking**: 8/30 games → status="in_progress"

## Conclusion

The dual-mode approach provides:
- ✅ Accurate Week 17 live scoring
- ✅ Backward compatibility with playoff weeks (15-16)
- ✅ Real-time game status detection
- ✅ No external API dependencies
- ✅ Works entirely with ESPN Fantasy API
