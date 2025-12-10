# Data Model: Playoff Mode

> **Spec ID**: 006
> **Created**: 2025-12-09
> **Last Updated**: 2025-12-09

This document defines all data entities and their relationships for the Playoff Mode feature.

---

## Entity Overview

The playoff mode introduces 4 new entities and extends 1 existing entity:

1. **PlayoffMatchup** - Single playoff game between two teams
2. **PlayoffBracket** - Collection of matchups for a division's playoff round
3. **ChampionshipEntry** - Single team's championship week performance
4. **ChampionshipLeaderboard** - Ranked list of division winners
5. **DivisionData** (Extended) - Adds optional playoff bracket field

---

## Entity: PlayoffMatchup

**Purpose**: Represents a single playoff game between two teams in a winners bracket.

**Source**: ESPN API `BoxScore` objects where `is_playoff=True` and `matchup_type="WINNERS_BRACKET"`

### Fields

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `matchup_id` | `str` | Yes | Non-empty | Unique identifier (e.g., "div1_sf1", "div2_finals") |
| `round_name` | `str` | Yes | Non-empty | Human-readable round name ("Semifinal 1", "Semifinal 2", "Finals") |
| `seed1` | `int` | Yes | > 0 | Playoff seed of first team (1-4) |
| `team1_name` | `str` | Yes | Non-empty | Name of first team |
| `owner1_name` | `str` | Yes | Non-empty | Owner name of first team |
| `score1` | `float \| None` | No | >= 0 if present | First team's score (None if game not started) |
| `seed2` | `int` | Yes | > 0 | Playoff seed of second team (1-4) |
| `team2_name` | `str` | Yes | Non-empty | Name of second team |
| `owner2_name` | `str` | Yes | Non-empty | Owner name of second team |
| `score2` | `float \| None` | No | >= 0 if present | Second team's score (None if game not started) |
| `winner_name` | `str \| None` | No | Must match team1 or team2 if present | Name of winning team (None if game incomplete) |
| `winner_seed` | `int \| None` | No | Must match seed1 or seed2 if present | Seed of winning team (None if game incomplete) |
| `division_name` | `str` | Yes | Non-empty | Division this matchup belongs to |

### Validation Rules

```python
def __post_init__(self) -> None:
    # Validate seeds are positive
    if self.seed1 <= 0 or self.seed2 <= 0:
        raise DataValidationError(f"Seeds must be positive: seed1={self.seed1}, seed2={self.seed2}")
    
    # Validate scores are non-negative if present
    if self.score1 is not None and self.score1 < 0:
        raise DataValidationError(f"Score1 cannot be negative: {self.score1}")
    if self.score2 is not None and self.score2 < 0:
        raise DataValidationError(f"Score2 cannot be negative: {self.score2}")
    
    # Validate winner matches one of the teams
    if self.winner_name is not None:
        if self.winner_name not in (self.team1_name, self.team2_name):
            raise DataValidationError(
                f"Winner must be one of the teams: {self.winner_name} not in "
                f"[{self.team1_name}, {self.team2_name}]"
            )
    
    # Validate winner seed matches
    if self.winner_seed is not None:
        if self.winner_seed not in (self.seed1, self.seed2):
            raise DataValidationError(
                f"Winner seed must match one of the seeds: {self.winner_seed} not in "
                f"[{self.seed1}, {self.seed2}]"
            )
    
    # Validate strings are non-empty
    if not self.matchup_id.strip():
        raise DataValidationError("matchup_id cannot be empty")
    if not self.round_name.strip():
        raise DataValidationError("round_name cannot be empty")
    if not self.team1_name.strip() or not self.team2_name.strip():
        raise DataValidationError("Team names cannot be empty")
    if not self.owner1_name.strip() or not self.owner2_name.strip():
        raise DataValidationError("Owner names cannot be empty")
    if not self.division_name.strip():
        raise DataValidationError("division_name cannot be empty")
```

### Example Instances

**Semifinal Matchup (Complete)**:
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

**Finals Matchup (In Progress)**:
```python
PlayoffMatchup(
    matchup_id="div2_finals",
    round_name="Finals",
    seed1=1,
    team1_name="Pineapple Express",
    owner1_name="Tom",
    score1=0.0,
    seed2=3,
    team2_name="Touchdown Titans",
    owner2_name="Chris",
    score2=0.0,
    winner_name=None,
    winner_seed=None,
    division_name="Division 2"
)
```

---

## Entity: PlayoffBracket

**Purpose**: Contains all playoff matchups for a single division in a specific round.

**Source**: Constructed by `ESPNService.build_playoff_bracket()` from ESPN API data

### Fields

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `round` | `str` | Yes | Must be "Semifinals" or "Finals" | Current playoff round name |
| `week` | `int` | Yes | > 0 | ESPN week number (15, 16, etc.) |
| `matchups` | `list[PlayoffMatchup]` | Yes | Length >= 1 | List of playoff matchups in this round |

### Validation Rules

```python
def __post_init__(self) -> None:
    # Validate round name
    if self.round not in ("Semifinals", "Finals"):
        raise DataValidationError(
            f"Round must be 'Semifinals' or 'Finals', got '{self.round}'"
        )
    
    # Validate week is positive
    if self.week <= 0:
        raise DataValidationError(f"Week must be positive: {self.week}")
    
    # Validate at least one matchup
    if not self.matchups:
        raise DataValidationError("PlayoffBracket must have at least one matchup")
    
    # Validate matchup count matches round
    if self.round == "Semifinals" and len(self.matchups) != 2:
        raise DataValidationError(
            f"Semifinals must have exactly 2 matchups, got {len(self.matchups)}"
        )
    if self.round == "Finals" and len(self.matchups) != 1:
        raise DataValidationError(
            f"Finals must have exactly 1 matchup, got {len(self.matchups)}"
        )
```

### Computed Properties

None - this is a simple container.

### Example Instances

**Semifinals Bracket**:
```python
PlayoffBracket(
    round="Semifinals",
    week=15,
    matchups=[
        PlayoffMatchup(...),  # Seed 1 vs Seed 4
        PlayoffMatchup(...)   # Seed 2 vs Seed 3
    ]
)
```

**Finals Bracket**:
```python
PlayoffBracket(
    round="Finals",
    week=16,
    matchups=[
        PlayoffMatchup(...)  # Winner 1 vs Winner 2
    ]
)
```

---

## Entity: ChampionshipEntry

**Purpose**: Represents a single division winner's performance in Championship Week.

**Source**: Constructed by `ESPNService.extract_championship_entry()` from division winner's Week 17 score

### Fields

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `rank` | `int` | Yes | > 0 | Rank in championship (1 = champion, 2 = runner-up, etc.) |
| `team_name` | `str` | Yes | Non-empty | Name of team |
| `owner_name` | `str` | Yes | Non-empty | Owner name |
| `division_name` | `str` | Yes | Non-empty | Division this team won |
| `score` | `float` | Yes | >= 0 | Team's score in Championship Week |
| `is_champion` | `bool` | Yes | - | True if this is the overall champion (rank=1) |

### Validation Rules

```python
def __post_init__(self) -> None:
    # Validate rank is positive
    if self.rank <= 0:
        raise DataValidationError(f"Rank must be positive: {self.rank}")
    
    # Validate score is non-negative
    if self.score < 0:
        raise DataValidationError(f"Score cannot be negative: {self.score}")
    
    # Validate strings are non-empty
    if not self.team_name.strip():
        raise DataValidationError("team_name cannot be empty")
    if not self.owner_name.strip():
        raise DataValidationError("owner_name cannot be empty")
    if not self.division_name.strip():
        raise DataValidationError("division_name cannot be empty")
    
    # Validate is_champion matches rank
    if self.is_champion and self.rank != 1:
        raise DataValidationError(
            f"Champion flag set but rank is {self.rank}, must be 1"
        )
    if not self.is_champion and self.rank == 1:
        raise DataValidationError(
            "Rank is 1 but champion flag not set"
        )
```

### Example Instances

**Champion (Rank 1)**:
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

**Runner-up (Rank 2)**:
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

---

## Entity: ChampionshipLeaderboard

**Purpose**: Contains ranked list of all division winners competing in Championship Week.

**Source**: Constructed by `ESPNService.build_championship_leaderboard()` after collecting all championship entries

### Fields

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `week` | `int` | Yes | > 0 | Championship week number (typically 17) |
| `entries` | `list[ChampionshipEntry]` | Yes | Length >= 1, ordered by rank | Ranked division winners |

### Validation Rules

```python
def __post_init__(self) -> None:
    # Validate week is positive
    if self.week <= 0:
        raise DataValidationError(f"Week must be positive: {self.week}")
    
    # Validate at least one entry
    if not self.entries:
        raise DataValidationError("ChampionshipLeaderboard must have at least one entry")
    
    # Validate entries are properly ranked (1, 2, 3, ...)
    expected_ranks = list(range(1, len(self.entries) + 1))
    actual_ranks = [entry.rank for entry in self.entries]
    if actual_ranks != expected_ranks:
        raise DataValidationError(
            f"Entries must be ranked sequentially starting at 1. "
            f"Expected {expected_ranks}, got {actual_ranks}"
        )
    
    # Validate exactly one champion
    champions = [e for e in self.entries if e.is_champion]
    if len(champions) != 1:
        raise DataValidationError(
            f"Must have exactly one champion, found {len(champions)}"
        )
    
    # Validate champion is rank 1
    if self.entries[0].rank != 1 or not self.entries[0].is_champion:
        raise DataValidationError("First entry must be rank 1 and champion")
```

### Computed Properties

```python
@property
def champion(self) -> ChampionshipEntry:
    """Get the overall champion (highest scorer)."""
    return next(e for e in self.entries if e.is_champion)
```

### Example Instance

```python
ChampionshipLeaderboard(
    week=17,
    entries=[
        ChampionshipEntry(rank=1, team_name="Pineapple Express", ..., is_champion=True),
        ChampionshipEntry(rank=2, team_name="Thunder Cats", ..., is_champion=False),
        ChampionshipEntry(rank=3, team_name="End Zone Warriors", ..., is_champion=False)
    ]
)
```

---

## Entity: DivisionData (Extended)

**Purpose**: Main container for all division data, now including optional playoff information.

**Changes**: Added one optional field for playoff bracket.

### New Field

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `playoff_bracket` | `PlayoffBracket \| None` | No | - | Playoff bracket if division is in playoffs, None during regular season |

### Computed Properties (New)

```python
@property
def is_playoff_mode(self) -> bool:
    """Check if this division is in playoff mode."""
    return self.playoff_bracket is not None
```

### Validation Rules

No additional validation beyond existing DivisionData rules. The `playoff_bracket` field is optional and validated by its own class.

### Example Instances

**Regular Season (Unchanged)**:
```python
DivisionData(
    name="Division 1",
    teams=[...],
    games=[...],
    weekly_games=[...],
    weekly_player_stats=[...],
    playoff_bracket=None  # No playoffs yet
)
```

**Playoff Mode**:
```python
DivisionData(
    name="Division 1",
    teams=[...],  # Still includes all 10 teams for standings context
    games=[...],  # All regular season games (historical)
    weekly_games=[...],  # Current playoff week games
    weekly_player_stats=[...],  # Current week player stats (all starters, not just playoff teams)
    playoff_bracket=PlayoffBracket(...)  # NEW - playoff matchups
)
```

---

## Relationships Between Entities

```
ChampionshipLeaderboard
    │
    ├─── ChampionshipEntry (rank 1, champion)
    ├─── ChampionshipEntry (rank 2)
    └─── ChampionshipEntry (rank 3)

DivisionData
    │
    ├─── teams: list[TeamStats]  (existing)
    ├─── games: list[GameResult]  (existing)
    ├─── weekly_games: list[WeeklyGameResult]  (existing)
    ├─── weekly_player_stats: list[WeeklyPlayerStats]  (existing)
    └─── playoff_bracket: PlayoffBracket | None  (NEW)
             │
             ├─── round: str
             ├─── week: int
             └─── matchups: list[PlayoffMatchup]
                      │
                      ├─── seed1, team1, owner1, score1
                      ├─── seed2, team2, owner2, score2
                      └─── winner_name, winner_seed

Multi-Division Output
    │
    ├─── divisions: list[DivisionData]
    │         └─── Each with optional playoff_bracket
    │
    └─── championship: ChampionshipLeaderboard | None  (NEW, only during Championship Week)
```

---

## Data Flow Diagram

```
ESPN API (BoxScore)
    │
    │ is_playoff=True, matchup_type="WINNERS_BRACKET"
    ↓
PlayoffMatchup objects
    │
    │ Grouped by division
    ↓
PlayoffBracket (per division)
    │
    │ Added to DivisionData
    ↓
DivisionData.playoff_bracket
    │
    │ Passed to formatters
    ↓
Formatter detects playoff mode
    │
    ├─── Console: fancy_grid tables
    ├─── Sheets: TSV rows
    ├─── Email: HTML tables
    ├─── Markdown: MD tables
    └─── JSON: playoff_bracket object


ESPN API (Week 16 Finals) + ESPN API (Week 17 Scores)
    │
    │ Find division winners, get their Week 17 scores
    ↓
ChampionshipEntry objects
    │
    │ Ranked by score
    ↓
ChampionshipLeaderboard
    │
    │ Passed to formatters alongside divisions
    ↓
Formatters render championship leaderboard
```

---

## Immutability Guarantees

All playoff entities use `@dataclass(frozen=True)`:

- **PlayoffMatchup**: Frozen, cannot modify seeds/scores after creation
- **PlayoffBracket**: Frozen, matchups list is immutable reference
- **ChampionshipEntry**: Frozen, rank/score cannot change
- **ChampionshipLeaderboard**: Frozen, entries list is immutable reference
- **DivisionData**: Frozen, playoff_bracket is immutable reference

This maintains constitutional requirement (Article II) for immutable data models.

---

## Type Safety

All entities maintain 100% type coverage:

- Union types use modern syntax: `float | None` not `Optional[float]`
- Collections fully typed: `list[PlayoffMatchup]` not `list`
- No `Any` types anywhere
- All fields explicitly typed
- All validation methods fully typed

This maintains constitutional requirement (Article I) for complete type safety.

---

## Validation Strategy

Each entity validates itself at construction time via `__post_init__`:

1. **Range checks**: Seeds > 0, scores >= 0, ranks > 0
2. **String validation**: Non-empty for required strings
3. **Relationship validation**: Winners match teams, ranks sequential
4. **Business rules**: Semifinals have 2 matchups, Finals have 1, exactly one champion

All validation raises `DataValidationError` with specific, actionable messages.

This maintains constitutional requirement (Article II) for construction-time validation.

---

## Future Extensions

Potential additions if scope expands:

1. **ConsolationMatchup**: Track consolation bracket (currently out of scope)
2. **PlayoffTeamStats**: Aggregate stats across playoff rounds
3. **HistoricalPlayoffData**: Archive past playoff results
4. **PlayoffPredictions**: Pre-game projections for matchups

All would follow same patterns: frozen dataclasses, full typing, construction-time validation.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-09 | AI Agent | Initial data model documentation |
