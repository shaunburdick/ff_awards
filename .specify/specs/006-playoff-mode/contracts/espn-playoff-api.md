# API Contract: ESPN Playoff Data

This document defines the contract between our system and the ESPN Fantasy Football API for playoff data extraction.

## Source: ESPN API BoxScore Object

### Playoff Matchup Fields

When `league.box_scores(week)` is called during playoff weeks, each `BoxScore` object contains:

```python
{
    "is_playoff": bool,              # True for ALL playoff games (including consolation)
    "matchup_type": str,             # "WINNERS_BRACKET" | "LOSERS_CONSOLATION_LADDER"
    "home_team": Team,               # Home team object
    "away_team": Team,               # Away team object
    "home_score": float,             # Home team's score (0.0 if not started)
    "away_score": float,             # Away team's score (0.0 if not started)
    "matchup_period": int            # Week number
}
```

### Team Playoff Fields

Each `Team` object contains playoff-related information:

```python
{
    "team_id": int,                  # Unique team ID
    "team_name": str,                # Team name
    "owners": list[dict],            # Owner information
    "standing": int,                 # Playoff seed (1-4 for playoff teams, 5-10 for eliminated)
    "playoff_pct": float,            # 100.0 for playoff teams, 0.0 for eliminated teams
    "wins": int,                     # Season wins
    "losses": int,                   # Season losses
    "points_for": float              # Total season points
}
```

### League Playoff Settings

The `League` object provides playoff configuration:

```python
{
    "current_week": int,                    # Current week number (15, 16, 17, ...)
    "settings": {
        "reg_season_count": int,            # Number of regular season weeks (typically 14)
        "playoff_team_count": int,          # Number of playoff teams per division (typically 4)
        "playoff_matchup_period_length": int # Weeks per playoff round (typically 1)
    }
}
```

## Filter Logic

### Extract Winners Bracket Only

```python
def get_playoff_matchups(league: League, week: int) -> list[BoxScore]:
    """Extract playoff matchups for winners bracket only."""
    box_scores = league.box_scores(week)
    
    return [
        bs for bs in box_scores
        if bs.is_playoff and bs.matchup_type == "WINNERS_BRACKET"
    ]
```

**Rationale**: Per spec requirement, we only display winners bracket. Consolation games have `matchup_type="LOSERS_CONSOLATION_LADDER"`.

### Detect Playoff State

```python
def is_in_playoffs(league: League) -> bool:
    """Check if league is currently in playoff weeks."""
    return league.current_week > league.settings.reg_season_count
```

**Example**:
- Regular season: weeks 1-14, `current_week <= 14` → `False`
- Semifinals: week 15, `current_week = 15 > 14` → `True`
- Finals: week 16, `current_week = 16 > 14` → `True`
- Championship: week 17, `current_week = 17 > 14` → `True`

### Determine Playoff Round

```python
def get_playoff_round(league: League) -> str:
    """Determine current playoff round based on weeks since reg season ended."""
    if not is_in_playoffs(league):
        raise ValueError("Not in playoffs")
    
    playoff_week = league.current_week - league.settings.reg_season_count
    
    if playoff_week == 1:
        return "Semifinals"
    elif playoff_week == 2:
        return "Finals"
    elif playoff_week == 3:
        return "Championship Week"
    else:
        raise ValueError(f"Unexpected playoff week: {playoff_week}")
```

## Expected Matchup Counts by Round

### Semifinals (Playoff Week 1)
- **Matchups per division**: 2
- **Teams per division**: 4 (seeds 1-4)
- **Structure**:
  - Matchup 1: Seed #1 vs Seed #4
  - Matchup 2: Seed #2 vs Seed #3

### Finals (Playoff Week 2)
- **Matchups per division**: 1
- **Teams per division**: 2 (winners from semifinals)
- **Structure**:
  - Matchup 1: Winner of (1 vs 4) vs Winner of (2 vs 3)

### Championship Week (Playoff Week 3)
- **Matchups per division**: 0 (leaderboard format, not bracket)
- **Teams per division**: 1 (division champion)
- **Structure**: No matchups, pull individual scores directly

## Data Validation Rules

### Matchup Validation

```python
# Semifinals must have exactly 2 matchups
if round == "Semifinals" and len(matchups) != 2:
    raise ValidationError(f"Expected 2 matchups, found {len(matchups)}")

# Finals must have exactly 1 matchup
if round == "Finals" and len(matchups) != 1:
    raise ValidationError(f"Expected 1 matchup, found {len(matchups)}")
```

### Score Validation

```python
# Scores must be non-negative
if score < 0:
    raise ValidationError(f"Score cannot be negative: {score}")

# 0.0 scores are valid (game not started)
if score == 0.0:
    # Acceptable - game hasn't started yet
    pass
```

### Seed Validation

```python
# Seeds must be positive and within playoff_team_count range
if not (1 <= seed <= league.settings.playoff_team_count):
    raise ValidationError(f"Invalid seed {seed}, must be 1-{playoff_team_count}")

# Semifinals must have seeds 1-4
if round == "Semifinals":
    all_seeds = [m.seed1, m.seed2 for m in matchups]
    expected_seeds = {1, 2, 3, 4}
    if set(all_seeds) != expected_seeds:
        raise ValidationError(f"Semifinals must include all seeds 1-4, found {all_seeds}")
```

## Edge Cases

### In-Progress Games

```python
# Before games start
home_score = 0.0
away_score = 0.0
# Display as "Not Started"

# During games (partial scoring)
home_score = 45.6
away_score = 0.0
# Display as "In Progress"

# After games complete
home_score = 145.67
away_score = 98.23
# Display winner indicator
```

### Missing Playoff Data

```python
# If no playoff games found when expected
matchups = get_playoff_matchups(league, 15)
if not matchups and is_in_playoffs(league):
    # ESPN API may not have updated yet
    # Show warning and fall back gracefully
    log.warning("Playoff week detected but no playoff games found")
```

### Out-of-Sync Divisions

```python
# Check all divisions are in same state
playoff_states = [(div, is_in_playoffs(league)) for div, league in divisions]
if not all_equal([state for _, state in playoff_states]):
    # Some divisions in playoffs, some in regular season
    raise DivisionSyncError("Divisions out of sync", details=playoff_states)
```

## Testing Checklist

- [ ] Semifinals data extraction (Week 15) - ✅ Verified 2025-12-10
- [ ] Finals data extraction (Week 16) - ⏳ Test on 2025-12-17
- [ ] Championship Week handling (Week 17) - ⏳ Test on 2025-12-24
- [ ] Consolation bracket filtering - ✅ Verified matchup_type works
- [ ] Seed extraction from team.standing - ✅ Verified
- [ ] In-progress game scores - ✅ Verified (0.0 before games)
- [ ] Owner name extraction - ✅ Existing code works

## Version History

| Version | Date | ESPN API Version | Changes |
|---------|------|------------------|---------|
| 1.0 | 2025-12-09 | 2025 Season | Initial contract based on Week 15 testing |
