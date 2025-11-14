# Component Contract: ChallengeCalculator

> **Component Type**: Service
> **Layer**: Business Logic
> **Status**: Active

## Purpose

Calculates all 5 season-long fantasy football challenges from ESPN league data aggregated across multiple divisions.

---

## Public Interface

### Class: ChallengeCalculator

```python
from collections.abc import Sequence
from ..models import ChallengeResult, DivisionData

class ChallengeCalculator:
    """
    Service for calculating fantasy football season challenges.

    Implements the business logic for the 5 tracked challenges:
    1. Most Points Overall
    2. Most Points in One Game
    3. Most Points in a Loss
    4. Least Points in a Win
    5. Closest Victory
    """

    def __init__(self) -> None:
        """Initialize the challenge calculator."""
        pass

    def calculate_all_challenges(
        self,
        divisions: Sequence[DivisionData]
    ) -> list[ChallengeResult]:
        """
        Calculate all 5 challenges across multiple divisions.

        Args:
            divisions: List of division data to analyze

        Returns:
            List of 5 challenge results, one per challenge

        Raises:
            InsufficientDataError: If there's not enough data to calculate challenges
        """
        pass
```

---

## Input Contract

### Required Input: `divisions: Sequence[DivisionData]`

**Structure**:
```python
DivisionData(
    division_name: str,
    teams: list[TeamStats],
    games: list[GameResult],
    weekly_games: list[WeeklyGameResult],  # Not used by this calculator
    weekly_players: list[WeeklyPlayerStats]  # Not used by this calculator
)
```

**Requirements**:
- `divisions` must not be empty
- Each `DivisionData` must have non-empty `division_name`
- `teams` list must contain at least one team
- `games` list must have complete data for all game-based challenges

**Validation**:
- Raises `InsufficientDataError` if `divisions` is empty
- Raises `InsufficientDataError` if no teams exist across all divisions
- Raises `InsufficientDataError` if no games available for game-based challenges

---

## Output Contract

### Return Value: `list[ChallengeResult]`

**Structure**:
```python
[
    ChallengeResult(
        challenge_name: str,
        team_name: str,
        owner: Owner,
        score: float,
        additional_info: dict[str, str | float | int]
    ),
    # ... 5 total results
]
```

**Guarantees**:
- Always returns exactly 5 results (one per challenge)
- Results ordered consistently: Most Points Overall, Most Points One Game, Most Points in Loss, Least Points in Win, Closest Victory
- Each result has all required fields populated
- `additional_info` contains context appropriate to challenge type

**Additional Info Contents**:

| Challenge | additional_info Keys |
|-----------|---------------------|
| Most Points Overall | `division` |
| Most Points One Game | `week`, `opponent`, `division` |
| Most Points in Loss | `week`, `opponent`, `opponent_score`, `margin`, `division` |
| Least Points in Win | `week`, `opponent`, `opponent_score`, `margin`, `division` |
| Closest Victory | `week`, `opponent`, `opponent_score`, `margin`, `division` |

---

## Behavior Specification

### Challenge 1: Most Points Overall

**Logic**:
```python
winner = max(all_teams, key=lambda t: t.points_for)
```

**Tie Handling**: First team in list with max value (deterministic by team order)

**Edge Cases**:
- Single team: That team wins
- All teams have 0 points: First team wins with 0

### Challenge 2: Most Points in One Game

**Logic**:
1. Iterate through all games
2. Track highest score seen
3. Record team, week, opponent

**Tie Handling**: First occurrence chronologically (earliest week wins)

**Edge Cases**:
- No games: Raise `InsufficientDataError`
- Single game: That game's highest score wins

### Challenge 3: Most Points in a Loss

**Logic**:
1. Filter games to losses only (team scored less than opponent)
2. Find maximum score among losing teams
3. Record context (opponent, margin)

**Tie Handling**: First occurrence chronologically

**Edge Cases**:
- No losses: Raise `InsufficientDataError` (indicates data problem)
- All games are ties: Raise `InsufficientDataError` (no valid losses)

### Challenge 4: Least Points in a Win

**Logic**:
1. Filter games to wins only (team scored more than opponent)
2. Find minimum score among winning teams
3. Record context (opponent, margin)

**Tie Handling**: First occurrence chronologically

**Edge Cases**:
- No wins: Raise `InsufficientDataError` (indicates data problem)
- All games are ties: Raise `InsufficientDataError` (no valid wins)

### Challenge 5: Closest Victory

**Logic**:
1. Calculate margin for all games (winner_score - loser_score)
2. Find minimum positive margin
3. Record both teams and context

**Tie Handling**: First occurrence chronologically

**Edge Cases**:
- No games: Raise `InsufficientDataError`
- All games are blowouts: Still reports smallest margin (all margins valid)
- Negative margins impossible (would be losses, not victories)

---

## Error Handling

### InsufficientDataError

**When Raised**:
- `divisions` parameter is empty list
- All divisions have empty teams lists
- Any other "not enough data to calculate" scenario

**Error Message Format**:
```
"No division data provided"
"No team data found across all divisions"
```

**User Action**: Check league IDs, verify ESPN API access, ensure data loaded correctly

---

## Performance Contract

**Expected Performance**:
- Full 18 week season, any number of leagues: < 5 seconds
- Typical 3-4 leagues, 10 teams each: < 1 second

**Complexity**:
- Time: O(n) where n = number of games (bounded by 18 weeks maximum)
- Space: O(n) for combined teams/games lists

**No Side Effects**: Pure calculation, no I/O, no state mutation

---

## Dependencies

### Required Models
- `DivisionData`: Input container
- `TeamStats`: Team information
- `GameResult`: Individual game data
- `ChallengeResult`: Output container
- `Owner`: Owner information

### Required Exceptions
- `InsufficientDataError`: From `ff_tracker.exceptions`

### No External Dependencies
- Uses only Python standard library
- No database, no file I/O, no network calls

---

## Usage Examples

### Example 1: Basic Usage

```python
from ff_tracker.services import ChallengeCalculator
from ff_tracker.models import DivisionData

calculator = ChallengeCalculator()

# divisions loaded from ESPNService
divisions: list[DivisionData] = [...]

# Calculate all challenges
results = calculator.calculate_all_challenges(divisions)

# results[0] = Most Points Overall
# results[1] = Most Points One Game
# results[2] = Most Points in Loss
# results[3] = Least Points in Win
# results[4] = Closest Victory

for result in results:
    print(f"{result.challenge_name}: {result.team_name} ({result.owner.name}) - {result.score}")
```

### Example 2: Error Handling

```python
from ff_tracker.services import ChallengeCalculator
from ff_tracker.exceptions import InsufficientDataError

calculator = ChallengeCalculator()

try:
    results = calculator.calculate_all_challenges([])
except InsufficientDataError as e:
    print(f"Cannot calculate challenges: {e}")
    # Output: "Cannot calculate challenges: No division data provided"
```

### Example 3: Multi-Division Aggregation

```python
# Three divisions worth of data
divisions = [
    DivisionData(division_name="East", teams=[...], games=[...]),
    DivisionData(division_name="West", teams=[...], games=[...]),
    DivisionData(division_name="Central", teams=[...], games=[...]),
]

calculator = ChallengeCalculator()
results = calculator.calculate_all_challenges(divisions)

# Results aggregate across all three divisions
# Winner could come from any division
```

---

## Testing Requirements

### Unit Tests Required
- [ ] Empty divisions list raises InsufficientDataError
- [ ] Single team/game scenarios work correctly
- [ ] Tie scenarios handled deterministically
- [ ] Each challenge calculated correctly with known data
- [ ] additional_info populated correctly for each challenge
- [ ] No crashes on edge cases (no wins, no losses, etc.)

### Integration Tests Required
- [ ] Works with real ESPN data structure
- [ ] Multi-division aggregation correct
- [ ] Performance meets targets (< 5s for 18 week season)
- [ ] Results render correctly in all output formatters
- [ ] Fails appropriately on incomplete data

---

## Change History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2025-11-14 | Initial contract documentation |
