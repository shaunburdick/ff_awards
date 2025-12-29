# Season Recap - Data Model Specification

> **Spec ID**: 008
> **Created**: 2024-12-29
> **Status**: Ready for Implementation

## Overview

This document defines all data models for the season recap feature. All models follow the project constitution: immutable (`frozen=True`), fully typed, with `__post_init__` validation.

---

## Model Architecture

### Model Categories

**New Models** (season-specific aggregations):
1. `SeasonStructure` - Dynamic season boundary information
2. `DivisionChampion` - Regular season champion data
3. `RegularSeasonSummary` - Complete regular season results
4. `PlayoffSummary` - All playoff rounds
5. `PlayoffRound` - Single round across divisions
6. `SeasonSummary` - Top-level container

**Reused Models** (existing, proven):
1. `DivisionData` - Final standings (from spec 004)
2. `ChallengeResult` - Season challenge winners (from spec 001)
3. `PlayoffBracket`, `PlayoffMatchup` - Playoff data (from spec 006)
4. `ChampionshipLeaderboard`, `ChampionshipEntry` - Championship data (from spec 007)

---

## New Model Definitions

### SeasonStructure

**Purpose**: Dynamic season boundary information calculated from ESPN API

**Fields**:
- `regular_season_start: int` - First week of regular season (typically 1)
- `regular_season_end: int` - Last week of regular season (from `league.settings.reg_season_count`)
- `playoff_start: int` - First playoff week (typically `regular_season_end + 1`)
- `playoff_end: int` - Last playoff week (from `league.finalScoringPeriod`)
- `championship_week: int` - Championship week (custom, typically `playoff_end + 1`)
- `playoff_rounds: int` - Number of playoff rounds
- `playoff_round_length: int` - Weeks per round (from `league.settings.playoff_matchup_period_length`)

**Validation Rules**:
- `regular_season_start >= 1`
- `regular_season_end >= regular_season_start`
- `playoff_start == regular_season_end + 1` (playoffs immediately after regular season)
- `playoff_end >= playoff_start`
- `championship_week == playoff_end + 1` (championship immediately after playoffs)
- `playoff_rounds >= 1`
- `playoff_round_length >= 1`

**Example**:
```python
SeasonStructure(
    regular_season_start=1,
    regular_season_end=14,
    playoff_start=15,
    playoff_end=16,
    championship_week=17,
    playoff_rounds=2,  # Semifinals + Finals
    playoff_round_length=1  # 1 week per round
)
```

**Source Calculation**:
```python
def calculate_season_structure(league: League) -> SeasonStructure:
    reg_end = league.settings.reg_season_count
    playoff_end = league.finalScoringPeriod
    round_length = league.settings.playoff_matchup_period_length
    
    playoff_weeks = playoff_end - reg_end
    rounds = playoff_weeks // round_length
    
    return SeasonStructure(
        regular_season_start=1,
        regular_season_end=reg_end,
        playoff_start=reg_end + 1,
        playoff_end=playoff_end,
        championship_week=playoff_end + 1,
        playoff_rounds=rounds,
        playoff_round_length=round_length
    )
```

---

### DivisionChampion

**Purpose**: Regular season division champion information

**Fields**:
- `division_name: str` - Name of division (from ESPN or "Division N")
- `team_name: str` - Team name
- `owner_name: str` - Owner name
- `wins: int` - Regular season wins
- `losses: int` - Regular season losses
- `points_for: float` - Total points scored
- `points_against: float` - Total points allowed
- `final_rank: int` - Final rank in division (should be 1 for champion)

**Validation Rules**:
- `team_name` not empty after stripping whitespace
- `division_name` not empty after stripping whitespace
- `wins >= 0`
- `losses >= 0`
- `points_for >= 0`
- `points_against >= 0`
- `final_rank >= 1`

**Example**:
```python
DivisionChampion(
    division_name="Rough Street",
    team_name="Ja'marr Wars",
    owner_name="Brian Fox",
    wins=10,
    losses=4,
    points_for=1842.52,
    points_against=1523.44,
    final_rank=1
)
```

**Source Extraction**:
```python
def get_division_champion(league: League, division_name: str) -> DivisionChampion:
    # Sort teams by record: wins (desc), then points_for (desc)
    teams_sorted = sorted(
        league.teams,
        key=lambda t: (t.wins, t.points_for),
        reverse=True
    )
    champion = teams_sorted[0]
    
    return DivisionChampion(
        division_name=division_name,
        team_name=champion.team_name,
        owner_name=champion.owner or "Unknown Owner",
        wins=champion.wins,
        losses=champion.losses,
        points_for=champion.points_for,
        points_against=champion.points_against,
        final_rank=1
    )
```

---

### RegularSeasonSummary

**Purpose**: Complete regular season results across all divisions

**Fields**:
- `structure: SeasonStructure` - Season boundary information
- `division_champions: tuple[DivisionChampion, ...]` - One champion per division
- `final_standings: tuple[DivisionData, ...]` - Complete standings (all teams, all divisions)

**Validation Rules**:
- `len(division_champions) == len(final_standings)` (one champion per division)
- `division_champions` not empty
- `final_standings` not empty

**Computed Properties**:
```python
@property
def total_teams(self) -> int:
    """Total number of teams across all divisions."""
    return sum(len(div.teams) for div in self.final_standings)

@property
def division_count(self) -> int:
    """Number of divisions."""
    return len(self.division_champions)

@property
def regular_season_weeks(self) -> tuple[int, int]:
    """Regular season week range (start, end)."""
    return (self.structure.regular_season_start, self.structure.regular_season_end)
```

**Example**:
```python
RegularSeasonSummary(
    structure=SeasonStructure(...),
    division_champions=(
        DivisionChampion(division_name="Rough Street", ...),
        DivisionChampion(division_name="Block Party", ...),
        DivisionChampion(division_name="Road Reptiles", ...)
    ),
    final_standings=(
        DivisionData(name="Rough Street", teams=[...], ...),
        DivisionData(name="Block Party", teams=[...], ...),
        DivisionData(name="Road Reptiles", teams=[...], ...)
    )
)
```

---

### PlayoffRound

**Purpose**: Results for one playoff round across all divisions

**Fields**:
- `round_name: str` - Name of round ("Semifinals", "Finals", "Round 1", etc.)
- `week: int` - Week number for this round
- `division_brackets: tuple[PlayoffBracket, ...]` - One bracket per division

**Validation Rules**:
- `round_name` not empty after stripping whitespace
- `week >= 1`
- `division_brackets` not empty (at least one division)

**Example**:
```python
PlayoffRound(
    round_name="Semifinals",
    week=15,
    division_brackets=(
        PlayoffBracket(round="Semifinals", week=15, matchups=[...]),  # Rough Street
        PlayoffBracket(round="Semifinals", week=15, matchups=[...]),  # Block Party
        PlayoffBracket(round="Semifinals", week=15, matchups=[...])   # Road Reptiles
    )
)
```

**Round Naming Logic**:
```python
def get_round_name(round_number: int, total_rounds: int) -> str:
    """Determine round name based on position."""
    if round_number == 1:
        return "Semifinals"
    elif round_number == total_rounds:
        return "Finals"
    else:
        return f"Round {round_number}"
```

---

### PlayoffSummary

**Purpose**: Complete playoff results for all rounds

**Fields**:
- `structure: SeasonStructure` - Season boundary information
- `rounds: tuple[PlayoffRound, ...]` - All playoff rounds (typically 2: Semifinals + Finals)

**Validation Rules**:
- `rounds` not empty (at least one playoff round)
- Round weeks sequential and within playoff boundaries

**Computed Properties**:
```python
@property
def semifinals(self) -> PlayoffRound | None:
    """Get semifinals round if it exists."""
    return next((r for r in self.rounds if "Semifinal" in r.round_name), None)

@property
def finals(self) -> PlayoffRound | None:
    """Get finals round if it exists."""
    return next((r for r in self.rounds if "Final" in r.round_name), None)

@property
def playoff_weeks(self) -> tuple[int, int]:
    """Playoff week range (start, end)."""
    return (self.structure.playoff_start, self.structure.playoff_end)
```

**Example**:
```python
PlayoffSummary(
    structure=SeasonStructure(...),
    rounds=(
        PlayoffRound(round_name="Semifinals", week=15, ...),
        PlayoffRound(round_name="Finals", week=16, ...)
    )
)
```

---

### SeasonSummary

**Purpose**: Top-level container for complete season recap

**Fields**:
- `year: int` - Season year (e.g., 2024)
- `generated_at: str` - ISO 8601 timestamp of generation (UTC)
- `structure: SeasonStructure` - Season boundary information
- `regular_season: RegularSeasonSummary` - Complete regular season results
- `season_challenges: tuple[ChallengeResult, ...]` - All 5 season challenge winners
- `playoffs: PlayoffSummary` - Complete playoff results
- `championship: ChampionshipLeaderboard | None` - Championship results (None if unavailable)

**Validation Rules**:
- `year >= 2000 and year <= 2100` (sanity check)
- `generated_at` valid ISO 8601 format
- `len(season_challenges) == 5` (exactly 5 season challenges)
- `regular_season` not None
- `playoffs` not None
- `championship` optional (can be None with --force flag)

**Computed Properties**:
```python
@property
def is_complete(self) -> bool:
    """Check if season summary includes championship."""
    return self.championship is not None

@property
def total_divisions(self) -> int:
    """Total number of divisions."""
    return len(self.regular_season.division_champions)

@property
def overall_champion(self) -> ChampionshipEntry | None:
    """Get overall champion if championship complete."""
    if self.championship:
        return self.championship.champion
    return None
```

**Example**:
```python
SeasonSummary(
    year=2024,
    generated_at="2024-12-29T18:30:00Z",
    structure=SeasonStructure(...),
    regular_season=RegularSeasonSummary(...),
    season_challenges=(
        ChallengeResult(challenge_name="Most Points Overall", ...),
        ChallengeResult(challenge_name="Most Points in One Game", ...),
        ChallengeResult(challenge_name="Most Points in a Loss", ...),
        ChallengeResult(challenge_name="Least Points in a Win", ...),
        ChallengeResult(challenge_name="Closest Victory", ...)
    ),
    playoffs=PlayoffSummary(...),
    championship=ChampionshipLeaderboard(...)  # or None
)
```

---

## Reused Model Summary

These models are used as-is from existing specs:

### DivisionData (Spec 004)

**Source**: `ff_tracker/models/division.py`

**Used For**: Final regular season standings

**Fields**:
- `name: str` - Division name
- `teams: tuple[TeamStats, ...]` - All teams in division
- `games: tuple[GameResult, ...]` - All games in regular season
- `weekly_games: tuple[WeeklyGameResult, ...]` - Current week games
- `weekly_player_stats: tuple[WeeklyPlayerStats, ...]` - Current week player stats
- `playoff_bracket: PlayoffBracket | None` - Playoff bracket (if in playoffs)

**Why Reuse**: Contains complete team data and standings in proper format

---

### ChallengeResult (Spec 001)

**Source**: `ff_tracker/models/challenge.py`

**Used For**: Season challenge winners

**Fields**:
- `challenge_name: str` - Name of challenge
- `team_name: str` - Winning team
- `owner_name: str` - Owner name
- `division: str` - Division name
- `value: float | str` - Challenge value (points or margin)
- `additional_info: dict[str, str | float | int]` - Extra details (week, opponent, etc.)

**Why Reuse**: Perfect fit for season challenge representation

---

### PlayoffBracket, PlayoffMatchup (Spec 006)

**Source**: `ff_tracker/models/playoff.py`

**Used For**: Playoff bracket results

**PlayoffBracket Fields**:
- `round: str` - Round name
- `week: int` - Week number
- `matchups: tuple[PlayoffMatchup, ...]` - All matchups in round

**PlayoffMatchup Fields**:
- `matchup_id: str` - Unique identifier
- `round_name: str` - Round name
- `seed1, team1_name, owner1_name, score1` - First team
- `seed2, team2_name, owner2_name, score2` - Second team
- `winner_name, winner_seed` - Winner information
- `division_name: str` - Division name

**Why Reuse**: Proven playoff bracket representation from spec 006

---

### ChampionshipLeaderboard, ChampionshipEntry (Spec 007)

**Source**: `ff_tracker/models/championship.py`

**Used For**: Championship week results

**ChampionshipLeaderboard Fields**:
- `week: int` - Championship week number
- `entries: tuple[ChampionshipEntry, ...]` - All entries ranked

**ChampionshipEntry Fields**:
- `rank: int` - Final rank (1 = champion)
- `team_name: str` - Team name
- `owner_name: str` - Owner name
- `division_name: str` - Division name
- `score: float` - Championship week score
- `is_champion: bool` - True for overall winner

**Why Reuse**: Perfect fit for championship representation from spec 007

---

## Data Relationships

```
SeasonSummary (top-level)
│
├─ SeasonStructure (season boundaries)
│
├─ RegularSeasonSummary
│   ├─ SeasonStructure (reference)
│   ├─ division_champions: tuple[DivisionChampion, ...]
│   └─ final_standings: tuple[DivisionData, ...]  [REUSED]
│       └─ teams: tuple[TeamStats, ...]  [REUSED]
│
├─ season_challenges: tuple[ChallengeResult, ...]  [REUSED]
│
├─ PlayoffSummary
│   ├─ SeasonStructure (reference)
│   └─ rounds: tuple[PlayoffRound, ...]
│       └─ division_brackets: tuple[PlayoffBracket, ...]  [REUSED]
│           └─ matchups: tuple[PlayoffMatchup, ...]  [REUSED]
│
└─ championship: ChampionshipLeaderboard | None  [REUSED]
    └─ entries: tuple[ChampionshipEntry, ...]  [REUSED]
```

---

## Model File Organization

### New File: `ff_tracker/models/season_summary.py`

Contains:
- `SeasonStructure`
- `DivisionChampion`
- `RegularSeasonSummary`
- `PlayoffSummary`
- `PlayoffRound`
- `SeasonSummary`

All models:
- Import `from __future__ import annotations`
- Use `@dataclass(frozen=True)`
- Include `__post_init__` validation
- Have complete docstrings
- Export via `__all__`

### Update: `ff_tracker/models/__init__.py`

Add exports:
```python
from ff_tracker.models.season_summary import (
    DivisionChampion,
    PlayoffRound,
    PlayoffSummary,
    RegularSeasonSummary,
    SeasonStructure,
    SeasonSummary,
)

__all__ = [
    # ... existing exports ...
    "DivisionChampion",
    "PlayoffRound",
    "PlayoffSummary",
    "RegularSeasonSummary",
    "SeasonStructure",
    "SeasonSummary",
]
```

---

## Validation Examples

### Valid SeasonSummary
```python
summary = SeasonSummary(
    year=2024,
    generated_at="2024-12-29T18:30:00Z",
    structure=SeasonStructure(
        regular_season_start=1,
        regular_season_end=14,
        playoff_start=15,
        playoff_end=16,
        championship_week=17,
        playoff_rounds=2,
        playoff_round_length=1
    ),
    regular_season=RegularSeasonSummary(...),
    season_challenges=(c1, c2, c3, c4, c5),
    playoffs=PlayoffSummary(...),
    championship=ChampionshipLeaderboard(...)
)
# ✅ Valid - all fields correct
```

### Invalid Examples

```python
# ❌ Invalid year
SeasonSummary(year=1999, ...)
# Raises: DataValidationError("Invalid year: 1999")

# ❌ Wrong number of challenges
SeasonSummary(season_challenges=(c1, c2, c3), ...)
# Raises: DataValidationError("Must have exactly 5 season challenges, got 3")

# ❌ Empty team name
DivisionChampion(team_name="", ...)
# Raises: DataValidationError("Team name cannot be empty")

# ❌ Negative points
DivisionChampion(points_for=-100.0, ...)
# Raises: DataValidationError("Points for cannot be negative: -100.0")

# ❌ Playoff start not immediately after regular season
SeasonStructure(
    regular_season_end=14,
    playoff_start=16,  # Should be 15
    ...
)
# Raises: DataValidationError("Playoffs must start immediately after regular season")
```

---

## Type Safety Examples

All models maintain 100% type coverage:

```python
# ✅ Proper typing
def process_summary(summary: SeasonSummary) -> str:
    """Process season summary with full type safety."""
    year: int = summary.year
    champions: tuple[DivisionChampion, ...] = summary.regular_season.division_champions
    
    for champion in champions:
        team: str = champion.team_name
        wins: int = champion.wins
        points: float = champion.points_for
    
    return f"Season {year} complete"

# ❌ Type errors caught
def bad_example(summary: SeasonSummary) -> None:
    # Error: SeasonSummary is immutable
    summary.year = 2025  # ❌ Can't assign to frozen dataclass
    
    # Error: Wrong type
    year: str = summary.year  # ❌ year is int, not str
    
    # Error: Can't use Any
    data: Any = summary  # ❌ Zero Any types permitted
```

---

## Testing Checklist

### Data Model Tests
- [ ] All models instantiate with valid data
- [ ] Invalid data raises `DataValidationError`
- [ ] Immutability enforced (can't modify fields)
- [ ] Computed properties work correctly
- [ ] Type hints correct (mypy passes)

### Validation Tests
- [ ] SeasonStructure validates week boundaries
- [ ] DivisionChampion validates non-negative values
- [ ] RegularSeasonSummary validates champion count matches divisions
- [ ] PlayoffRound validates non-empty brackets
- [ ] SeasonSummary validates year range and challenge count

### Integration Tests
- [ ] Models work with real ESPN data
- [ ] Reused models integrate seamlessly
- [ ] JSON serialization works (for JSON formatter)
- [ ] All relationships properly typed

---

## Constitutional Compliance

**Article I: Type Safety First** ✅
- 100% type coverage with Python 3.9+ syntax
- Zero `Any` types
- All fields fully typed
- Computed properties typed

**Article II: Data Immutability and Validation** ✅
- All models use `@dataclass(frozen=True)`
- All models have `__post_init__` validation
- Clear `DataValidationError` messages
- No business logic in models

**Article VII: Documentation as Code** ✅
- Descriptive field names
- Type hints serve as documentation
- Comprehensive docstrings
- Examples provided

---

**Data Model Status**: ✅ Ready for Implementation

**Next Step**: Phase 1 Implementation (Create models in `ff_tracker/models/season_summary.py`)
