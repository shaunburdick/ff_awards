# Data Contract: Playoff Output Structures

This document defines the data structures passed between services and formatters for playoff mode.

## PlayoffMatchup Structure

Single playoff game between two teams.

```python
@dataclass(frozen=True)
class PlayoffMatchup:
    matchup_id: str               # e.g., "div1_sf1", "div2_finals"
    round_name: str              # "Semifinal 1", "Semifinal 2", "Finals"
    seed1: int                   # 1-4
    team1_name: str
    owner1_name: str
    score1: float | None         # None if not started, 0.0+ if playing/complete
    seed2: int                   # 1-4
    team2_name: str
    owner2_name: str
    score2: float | None         # None if not started, 0.0+ if playing/complete
    winner_name: str | None      # Team name of winner (None if incomplete)
    winner_seed: int | None      # Seed of winner (None if incomplete)
    division_name: str           # "Division 1", "Division 2", etc.
```

**Example (Complete Game)**:
```python
PlayoffMatchup(
    matchup_id="div1_sf1",
    round_name="Semifinal 1",
    seed1=1,
    team1_name="Thunder Cats",
    owner1_name="John",
    score1=145.67,
    seed2=4,
    team2_name="Dream Team",
    owner2_name="Sarah",
    score2=98.23,
    winner_name="Thunder Cats",
    winner_seed=1,
    division_name="Division 1"
)
```

**Example (Not Started)**:
```python
PlayoffMatchup(
    matchup_id="div2_finals",
    round_name="Finals",
    seed1=1,
    team1_name="Pineapple Express",
    owner1_name="Tom",
    score1=None,
    seed2=3,
    team2_name="Touchdown Titans",
    owner2_name="Chris",
    score2=None,
    winner_name=None,
    winner_seed=None,
    division_name="Division 2"
)
```

## PlayoffBracket Structure

Collection of playoff matchups for a division.

```python
@dataclass(frozen=True)
class PlayoffBracket:
    round: str                   # "Semifinals" | "Finals"
    week: int                    # ESPN week number (15, 16, ...)
    matchups: list[PlayoffMatchup]
```

**Example (Semifinals)**:
```python
PlayoffBracket(
    round="Semifinals",
    week=15,
    matchups=[
        PlayoffMatchup(...),  # Seed 1 vs 4
        PlayoffMatchup(...)   # Seed 2 vs 3
    ]
)
```

**Example (Finals)**:
```python
PlayoffBracket(
    round="Finals",
    week=16,
    matchups=[
        PlayoffMatchup(...)  # Winner 1 vs Winner 2
    ]
)
```

## ChampionshipEntry Structure

Single division winner's championship week performance.

```python
@dataclass(frozen=True)
class ChampionshipEntry:
    rank: int                    # 1 = champion, 2 = runner-up, 3 = third, ...
    team_name: str
    owner_name: str
    division_name: str
    score: float                 # Championship week score
    is_champion: bool            # True only for rank=1
```

**Example (Champion)**:
```python
ChampionshipEntry(
    rank=1,
    team_name="Pineapple Express",
    owner_name="Tom",
    division_name="Division 2",
    score=163.45,
    is_champion=True
)
```

**Example (Runner-up)**:
```python
ChampionshipEntry(
    rank=2,
    team_name="Thunder Cats",
    owner_name="John",
    division_name="Division 1",
    score=156.78,
    is_champion=False
)
```

## ChampionshipLeaderboard Structure

Ranked list of all division winners.

```python
@dataclass(frozen=True)
class ChampionshipLeaderboard:
    week: int                    # Championship week number (typically 17)
    entries: list[ChampionshipEntry]  # Ordered by rank (1, 2, 3, ...)
```

**Example**:
```python
ChampionshipLeaderboard(
    week=17,
    entries=[
        ChampionshipEntry(rank=1, ..., is_champion=True),
        ChampionshipEntry(rank=2, ..., is_champion=False),
        ChampionshipEntry(rank=3, ..., is_champion=False)
    ]
)
```

## DivisionData Extension

Extended to include optional playoff bracket.

```python
@dataclass(frozen=True)
class DivisionData:
    # Existing fields
    name: str
    teams: list[TeamStats]
    games: list[GameResult]
    weekly_games: list[WeeklyGameResult]
    weekly_player_stats: list[WeeklyPlayerStats]
    
    # NEW field
    playoff_bracket: PlayoffBracket | None = None
```

**Property**:
```python
@property
def is_playoff_mode(self) -> bool:
    return self.playoff_bracket is not None
```

## Formatter Input Contract

Formatters receive:

```python
def format_output(
    self,
    divisions: list[DivisionData],          # May include playoff_bracket
    challenges: list[ChallengeResult],      # Season challenges (historical during playoffs)
    weekly_challenges: list[WeeklyChallenge], # Adapted during playoffs (player highlights only)
    format_args: dict[str, str],            # Format-specific arguments
    championship: ChampionshipLeaderboard | None = None  # NEW parameter
) -> str:
    """
    Format output for display.
    
    Playoff mode detection:
    - Check if any division has playoff_bracket
    - Check if championship is not None
    - Adapt display accordingly
    """
```

### Playoff Mode Display Rules

**During Semifinals/Finals** (championship=None):
1. Render playoff brackets at TOP
2. Render 7 player highlights only (hide 6 team challenges)
3. Render 5 season challenges with "Historical" note
4. Render regular season standings at BOTTOM (context)

**During Championship Week** (championship not None):
1. Render championship leaderboard at TOP
2. Render 7 player highlights (all teams)
3. Render 5 season challenges with "Historical" note
4. NO regular season standings (championship is the finale)

## JSON Output Contract

During playoff mode, JSON output includes new top-level fields:

```json
{
  "report_type": "playoff_semifinals" | "playoff_finals" | "championship_week",
  "week": 15,
  "generated_at": "2025-12-15T10:30:00Z",
  
  "playoff_bracket": {
    "round": "Semifinals",
    "divisions": [
      {
        "division_name": "Division 1",
        "matchups": [
          {
            "matchup_id": "div1_sf1",
            "round": "Semifinal 1",
            "seed1": 1,
            "team1": "Thunder Cats",
            "owner1": "John",
            "score1": 145.67,
            "seed2": 4,
            "team2": "Dream Team",
            "owner2": "Sarah",
            "score2": 98.23,
            "winner": "Thunder Cats",
            "winner_seed": 1,
            "division": "Division 1"
          }
        ]
      }
    ]
  },
  
  "championship": {
    "week": 17,
    "leaderboard": [
      {
        "rank": 1,
        "team": "Pineapple Express",
        "owner": "Tom",
        "division": "Division 2",
        "score": 163.45,
        "is_champion": true
      }
    ],
    "overall_champion": {
      "team": "Pineapple Express",
      "owner": "Tom",
      "division": "Division 2",
      "score": 163.45
    }
  },
  
  "weekly_player_highlights": [...],
  "season_challenges": [...],
  "standings": [...]
}
```

## Error Contracts

### DivisionSyncError

Raised when divisions are not synchronized.

```python
class DivisionSyncError(FFTrackerError):
    """Divisions are in different playoff states."""
    
    def __init__(self, message: str, division_states: dict[str, str]):
        self.division_states = division_states
        super().__init__(message)
```

**Example**:
```python
raise DivisionSyncError(
    "Divisions are out of sync",
    division_states={
        "Division 1": "Week 15 (Semifinals)",
        "Division 2": "Week 14 (Regular Season)"
    }
)
```

**Error Message Format**:
```
Divisions are out of sync:
  - Division 1: Week 15 (Semifinals)
  - Division 2: Week 14 (Regular Season)

All divisions must be in the same state. Please wait for all leagues to advance to the same week.
```

## Validation Contracts

All playoff models validate at construction:

```python
# PlayoffMatchup validation
- Seeds must be > 0
- Scores must be >= 0 if present
- Winner must match one of the teams if present
- All required strings must be non-empty

# PlayoffBracket validation
- Round must be "Semifinals" or "Finals"
- Week must be > 0
- Must have at least 1 matchup
- Semifinals must have exactly 2 matchups
- Finals must have exactly 1 matchup

# ChampionshipEntry validation
- Rank must be > 0
- Score must be >= 0
- is_champion must be True only when rank=1
- All required strings must be non-empty

# ChampionshipLeaderboard validation
- Week must be > 0
- Must have at least 1 entry
- Entries must be ranked sequentially (1, 2, 3, ...)
- Must have exactly 1 champion
- Champion must be first entry (rank=1)
```

All validation errors raise `DataValidationError` with specific, actionable messages.

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-09 | Initial playoff data contracts |
