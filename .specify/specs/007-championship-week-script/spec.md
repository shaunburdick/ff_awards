# Spec: Championship Week Management Script

**Status**: Draft  
**Created**: 2024-12-23  
**Epic**: Championship Week Support  
**Related Issues**: Week 17 manual championship tracking

---

## Problem Statement

Week 17 (Championship Week) requires special handling because:
1. **No Official ESPN Matchups**: Division winners compete but ESPN shows no matchup (leagues are marked complete)
2. **Manual Score Calculation**: Must calculate scores from individual player performances, not team matchups
3. **Roster Management**: Need to track and validate that champions have set legal rosters before games start
4. **Different Workflow**: This week's requirements are fundamentally different from regular/playoff weeks

The existing `ff-tracker` tool was designed for weeks with ESPN matchups. Rather than complicate that tool with Championship Week edge cases, we need a **separate script** focused on Championship Week management.

---

## User Stories

### US-1: View Championship Leaderboard
**As a** league commissioner  
**I want to** see a ranked leaderboard of all division winners with their Week 17 scores  
**So that** I can determine the overall champion

**Acceptance Criteria**:
- Shows all 3 division winners (from Week 16 Finals)
- Displays Week 17 scores calculated from individual player performances
- Ranks champions by score (highest to lowest)
- Clearly marks the overall champion (#1)
- Available in all 5 output formats (console, sheets, email, json, markdown)

### US-2: Track Roster Status
**As a** league commissioner  
**I want to** see which division winners have set their rosters  
**So that** I can remind anyone who hasn't set their lineup

**Acceptance Criteria**:
- Lists each division winner
- Shows roster status: "Complete" or "Incomplete"
- Identifies empty roster slots (position, e.g., "RB2 empty")
- Shows last roster modification time (if available from ESPN)
- Can check before games start (proactive reminders)

### US-3: Validate Rosters
**As a** league commissioner  
**I want to** validate that all rosters are legal  
**So that** I can ensure fair competition

**Acceptance Criteria**:
- Checks all required positions are filled (no empty slots)
- Identifies players on bye weeks
- Identifies injured/out players in starting lineup
- Flags players whose games have already started
- Provides clear warnings for each issue found

### US-4: Live Score Updates ❌ NOT IMPLEMENTED
**As a** league commissioner  
**I want to** see live score updates during Championship Week  
**So that** I can track who's winning in real-time

**Status**: ❌ **Removed** - ESPN API limitation

**Reason**: ESPN does not provide live scoring for post-season consolation weeks (Week 17+). The API returns static scores once leagues officially end at Week 16 Finals. True live updates would require external NFL APIs which adds significant complexity.

**Alternative**: Run the leaderboard mode multiple times to see updated scores as ESPN refreshes them (though updates are infrequent for consolation weeks).

**Original Acceptance Criteria** (not met):
- Shows current scores for all division winners ✅ (scores shown, but not "live")
- Updates as games progress (can be run multiple times) ⚠️ (can run multiple times, but ESPN doesn't update frequently)
- Indicates which players have finished (completed games) ✅ (projection-based detection)
- Shows projected final scores (if available) ✅ (projections shown)
- Clearly marks current leader ✅ (champion marked with 🥇)

---

## Technical Design

### Architecture: Separate Script

Create a new **standalone script** that shares common infrastructure with `ff-tracker`:

```
ff_tracker/
├── championship.py          # NEW: Championship Week CLI entry point
├── models/
│   ├── championship.py      # NEW: Championship-specific models
│   └── playoff.py           # EXISTING: ChampionshipEntry, ChampionshipLeaderboard
├── services/
│   ├── espn_service.py      # SHARED: ESPN API connection, player data extraction
│   ├── championship_service.py  # NEW: Championship-specific logic
│   └── roster_validator.py  # NEW: Roster validation logic
└── display/                 # SHARED: All 5 formatters (reuse with new data)
```

### Why Separate Script?

**Benefits**:
- **Focused**: Each script handles one workflow (regular season vs championship)
- **Simpler**: No complex conditionals for championship edge cases in `ff-tracker`
- **Testable**: Can test championship logic independently
- **Maintainable**: Changes to one script don't risk breaking the other

**Shared Code**:
- `models/`: Data structures (Owner, Team, Player, etc.)
- `services/espn_service.py`: ESPN API connection and player extraction methods
- `display/`: All output formatters (they already handle generic data)
- `config.py`, `exceptions.py`: Configuration and error handling

**Championship-Specific Code**:
- `championship.py`: CLI entry point with championship-specific arguments
- `services/championship_service.py`: Score calculation from players, roster validation
- New models if needed (e.g., `RosterStatus`, `ChampionshipProgress`)

---

## Data Models

### New: ChampionshipTeam
```python
@dataclass(frozen=True)
class ChampionshipTeam:
    """A division winner competing in Championship Week."""
    team_name: str
    owner_name: str
    division_name: str
    team_id: int  # ESPN team ID for API calls
    seed: int  # What seed they were (1-4)
```

### New: RosterSlot
```python
@dataclass(frozen=True)
class RosterSlot:
    """A single roster slot with player info."""
    position: str  # "QB", "RB", "WR", "TE", "FLEX", "K", "D/ST"
    player_name: str | None  # None if empty slot
    player_team: str | None  # NFL team (e.g., "KC", "DAL")
    projected_points: float
    actual_points: float
    game_status: str  # "not_started", "in_progress", "final"
    injury_status: str | None  # "OUT", "DOUBTFUL", "QUESTIONABLE", None
    is_bye: bool
```

### New: ChampionshipRoster
```python
@dataclass(frozen=True)
class ChampionshipRoster:
    """Complete roster for a championship team."""
    team: ChampionshipTeam
    starters: list[RosterSlot]
    bench: list[RosterSlot]
    total_score: float
    projected_score: float
    is_complete: bool  # All slots filled?
    empty_slots: list[str]  # ["RB2", "FLEX"] if any empty
    warnings: list[str]  # ["QB on bye", "WR is OUT"]
    last_modified: str | None  # Timestamp if available
```

### Extend: ChampionshipLeaderboard
```python
# Already exists in models/playoff.py, may need to add:
progress: str  # "not_started", "in_progress", "final"
last_updated: str  # Timestamp of last data fetch
```

---

## API Design

### New Service: ChampionshipService

```python
class ChampionshipService:
    """Service for Championship Week management."""
    
    def __init__(self, espn_service: ESPNService):
        self.espn = espn_service
    
    def get_division_winners(
        self, 
        leagues: list[League], 
        division_names: list[str]
    ) -> list[ChampionshipTeam]:
        """
        Find the winner of each division's Finals (Week 16).
        
        Returns list of ChampionshipTeam objects.
        """
        pass
    
    def get_roster(
        self, 
        league: League, 
        team: ChampionshipTeam, 
        week: int
    ) -> ChampionshipRoster:
        """
        Get complete roster for a championship team in Week 17.
        
        Includes:
        - All starter and bench players
        - Current scores and projections
        - Game status (not started, in progress, final)
        - Validation warnings
        """
        pass
    
    def calculate_score(
        self, 
        roster: ChampionshipRoster
    ) -> float:
        """
        Calculate total score from starter performances.
        
        Sums actual_points for all starters (excludes bench).
        """
        pass
    
    def build_leaderboard(
        self, 
        rosters: list[ChampionshipRoster]
    ) -> ChampionshipLeaderboard:
        """
        Create ranked championship leaderboard.
        
        Sorts by total_score (descending), marks champion.
        """
        pass
```

### New Service: RosterValidator

```python
class RosterValidator:
    """Validates fantasy football rosters."""
    
    def validate_roster(
        self, 
        roster: ChampionshipRoster
    ) -> list[str]:
        """
        Validate a roster and return list of warnings.
        
        Checks:
        - Empty slots
        - Bye week players
        - Injured/OUT players
        - Players in started games (locked)
        
        Returns empty list if no issues.
        """
        pass
    
    def is_complete(self, roster: ChampionshipRoster) -> bool:
        """Check if all required slots are filled."""
        pass
    
    def has_warnings(self, roster: ChampionshipRoster) -> bool:
        """Check if roster has any validation warnings."""
        pass
```

---

## CLI Interface

### New Command: `ff-championship`

```bash
# View championship leaderboard (default action)
uv run ff-championship --env --private

# Check roster status (before games start)
uv run ff-championship --env --private --check-rosters

# Validate rosters (detailed warnings)
uv run ff-championship --env --private --validate

# Live updates during games
uv run ff-championship --env --private --live

# Output formats (same as ff-tracker)
uv run ff-championship --env --format email
uv run ff-championship --env --format sheets
uv run ff-championship --env --output-dir ./reports

# Testing with specific week (future weeks allowed)
uv run ff-championship --env --week 17 --dry-run
```

### CLI Arguments

```python
parser.add_argument(
    "--check-rosters",
    action="store_true",
    help="Check if division winners have set their rosters"
)

parser.add_argument(
    "--validate",
    action="store_true",
    help="Validate rosters for issues (bye weeks, injuries, empty slots)"
)

parser.add_argument(
    "--live",
    action="store_true",
    help="Show live scores with game progress (updates as games play)"
)

parser.add_argument(
    "--dry-run",
    action="store_true",
    help="Test mode: allows future weeks, shows what would happen"
)
```

---

## Output Formats

### Console Format

```
================================================================================
                       🏆 CHAMPIONSHIP WEEK - WEEK 17 🏆
================================================================================
📅 Status: In Progress (12 of 15 games complete)
🕐 Last Updated: Sunday, Dec 29, 2024 at 7:45 PM ET

┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Rank ┃ Team                 ┃ Owner            ┃ Division ┃ Score     ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ 🥇 1 │ Ja'marr Wars         │ Brian Fox        │ Rough St │ 158.40 🏆 │
├──────┼──────────────────────┼──────────────────┼──────────┼───────────┤
│ 🥈 2 │ Miller Time 🍻       │ Michael Rowland  │ Block Pa │ 147.25    │
├──────┼──────────────────────┼──────────────────┼──────────┼───────────┤
│ 🥉 3 │ Billieve the Champ   │ eric barnum      │ Road Rep │ 132.80    │
└──────┴──────────────────────┴──────────────────┴──────────┴───────────┘

🎉 CHAMPION: Ja'marr Wars (Brian Fox) - Rough Street League
   Final Score: 158.40 points

═══════════════════════════════════════════════════════════════════════════════
                              DETAILED ROSTERS
═══════════════════════════════════════════════════════════════════════════════

┌── Ja'marr Wars (Brian Fox) - 158.40 points ──────────────────────────────────┐
│ Pos    Player                Team   Status      Points   Projected            │
├───────────────────────────────────────────────────────────────────────────────┤
│ QB     Lamar Jackson         BAL    ✓ Final     28.50    22.3                 │
│ RB     Derrick Henry          BAL    ✓ Final     24.10    18.7                 │
│ RB     Saquon Barkley         PHI    ✓ Final     32.80    21.4                 │
│ WR     Ja'Marr Chase          CIN    ⏱ Progress  18.20    19.8                 │
│ WR     CeeDee Lamb            DAL    ✓ Final     22.40    17.6                 │
│ TE     George Kittle          SF     ✓ Final     15.60    12.1                 │
│ FLEX   Kenneth Walker III     SEA    ✓ Final      8.90    14.3                 │
│ K      Justin Tucker          BAL    ✓ Final      9.00     8.5                 │
│ D/ST   Ravens D/ST            BAL    ✓ Final     -1.00     7.2                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Roster Check Output

```bash
uv run ff-championship --env --check-rosters
```

```
================================================================================
                        🏈 CHAMPIONSHIP ROSTER STATUS 🏈
================================================================================
📅 Championship Week: Week 17
🕐 Checked: Thursday, Dec 26, 2024 at 10:00 AM ET
⚠️  Roster Deadline: Thursday 8:15 PM ET (TNF kickoff)

┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Team                ┃ Owner            ┃ Status   ┃ Issues              ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ Ja'marr Wars        │ Brian Fox        │ ✅ Ready │ None                │
├─────────────────────┼──────────────────┼──────────┼─────────────────────┤
│ Miller Time 🍻      │ Michael Rowland  │ ✅ Ready │ None                │
├─────────────────────┼──────────────────┼──────────┼─────────────────────┤
│ Billieve the Champ  │ eric barnum      │ ⚠️  Warn │ RB2 empty           │
│                     │                  │          │ FLEX: D.Adams (Q)   │
└─────────────────────┴──────────────────┴──────────┴─────────────────────┘

⚠️  ACTION REQUIRED:
• eric barnum: Set RB2 and check Davante Adams injury status
```

---

## Implementation Plan

### Phase 1: Extract Shared Code (1-2 hours)
- [P] Review `espn_service.py` for methods that need to be shared
- [P] Extract player roster fetching logic if not already available
- [P] Ensure `display/` formatters can handle championship data
- [P] Add any missing ESPN API methods for roster/player data

### Phase 2: Championship Models (1 hour)
- [P] Create `models/championship.py`
- [P] Define `ChampionshipTeam`, `RosterSlot`, `ChampionshipRoster`
- [P] Extend `ChampionshipLeaderboard` if needed
- [P] Add validation and tests

### Phase 3: Championship Service (2-3 hours)
- [P] Create `services/championship_service.py`
- [P] Implement `get_division_winners()` (from Week 16 Finals)
- [P] Implement `get_roster()` (fetch player data from ESPN)
- [P] Implement `calculate_score()` (sum starter points)
- [P] Implement `build_leaderboard()` (rank by score)
- [P] Add comprehensive tests

### Phase 4: Roster Validator (1-2 hours)
- [P] Create `services/roster_validator.py`
- [P] Implement empty slot detection
- [P] Implement bye week detection
- [P] Implement injury status detection
- [P] Implement game start detection
- [P] Add tests for all validation rules

### Phase 5: CLI Entry Point (1-2 hours)
- [P] Create `championship.py` with argparse
- [P] Implement `--check-rosters` mode
- [P] Implement `--validate` mode
- [P] Implement default leaderboard mode
- [P] Implement `--live` mode
- [P] Add `--dry-run` for testing

### Phase 6: Output Formatters (1-2 hours)
- [P] Extend console formatter for championship display
- [P] Extend email formatter for championship HTML
- [P] Extend sheets/json/markdown formatters
- [P] Add roster detail display
- [P] Test all 5 formats

### Phase 7: Integration & Testing (2-3 hours)
- [P] Test with `--dry-run` against current leagues
- [P] Test roster validation logic
- [P] Test score calculation
- [P] Test all output formats
- [P] **Wait for Week 17 real data** to validate
- [P] Iterate based on real ESPN data structure

### Phase 8: Documentation (1 hour)
- [P] Update README with championship script usage
- [P] Add to pyproject.toml scripts
- [P] Create quickstart guide
- [P] Document known limitations

**Total Estimated Time**: 10-16 hours

---

## Testing Strategy

### Unit Tests
- Test each service method independently
- Mock ESPN API responses
- Test all validation rules
- Test score calculations

### Integration Tests
- Test with `--dry-run` against real leagues (Week 16 data)
- Verify division winner detection from Finals
- Verify roster data extraction
- Test all output formats

### Live Testing (Week 17)
- **Before games**: Test roster checking/validation
- **During games**: Test live score updates
- **After games**: Test final leaderboard
- **Iterate**: Fix any issues with real ESPN data structure

---

## Open Questions

1. **ESPN API Behavior**:
   - Q: Can we access Week 17 player scores even without official matchups?
   - A: Need to test - likely yes via `league.box_scores(17)` or individual team rosters

2. **Roster Timestamps**:
   - Q: Does ESPN provide "last modified" timestamps for rosters?
   - A: Need to investigate ESPN API - may not be available

3. **Player Game Status**:
   - Q: Can we detect which players' games have started (locked)?
   - A: Need to check ESPN API - likely available via player object

4. **Projections**:
   - Q: Are Week 17 projections available in ESPN?
   - A: Likely yes - same as other weeks

5. **Bye Weeks**:
   - Q: Are there bye weeks in Week 17?
   - A: No - all teams play in Week 18 (regular season finale)

---

## Future Enhancements

- **Email Notifications**: Auto-send reminder emails to champions who haven't set rosters
- **Slack/Discord Integration**: Post live updates to team chat
- **Historical Tracking**: Store championship results across years
- **Tiebreakers**: Handle tied scores (bench points, specific positions, etc.)
- **Multi-Year Support**: Compare current championship to past years

---

## Success Criteria

### Must Have (Week 17 2024-2025)
- ✅ Shows championship leaderboard with correct scores
- ✅ Calculates scores from individual player performances
- ✅ Identifies division winners from Week 16 Finals
- ✅ Validates rosters (empty slots, bye weeks, injuries)
- ✅ All 5 output formats work correctly

### Should Have
- ✅ Live score updates during games
- ✅ Roster status checking before games
- ✅ Clear error messages for ESPN API issues

### Nice to Have
- ⭕ Email notifications for incomplete rosters
- ⭕ Historical comparison to past championships
- ⭕ Projected final scores during games

---

## Risk Assessment

### High Risk
- **ESPN API Changes**: Week 17 data structure may be different than expected
  - *Mitigation*: Build with `--dry-run` testing, iterate on real data
- **No Official Matchups**: Unclear if player scores are accessible
  - *Mitigation*: Test early, have fallback plan (manual entry?)

### Medium Risk
- **Time Constraint**: Week 17 is Dec 28-29, 2024 (days away!)
  - *Mitigation*: Focus on MVP features first, enhancements later
- **Testing Limited**: Can't fully test until Week 17 arrives
  - *Mitigation*: Thorough `--dry-run` testing, plan for quick fixes

### Low Risk
- **Code Sharing**: Risk of breaking existing `ff-tracker`
  - *Mitigation*: Separate script minimizes coupling
- **Output Formats**: Should reuse existing formatters easily
  - *Mitigation*: Formatters are already modular

---

## Dependencies

- Existing `ff-tracker` codebase (v3.1.0)
- ESPN API access (same as current tool)
- Python 3.9+ with type hints
- Week 16 Finals data (available now)
- Week 17 live data (available Dec 28-29)

---

## Approval & Sign-off

**Stakeholders**:
- [x] User (Shaun) - Confirmed requirements

**Next Steps**:
1. Review and approve this spec
2. Begin Phase 1 (Extract shared code)
3. Implement through Phase 7
4. Test with `--dry-run`
5. Deploy before Week 17 (Dec 28)
6. Iterate based on live data

**Timeline**:
- Spec Approval: Dec 23, 2024
- Implementation: Dec 23-26, 2024
- Testing: Dec 26-27, 2024
- Week 17 Live: Dec 28-29, 2024

---

## Notes

- This is the **first Championship Week** for this tool
- Expect to iterate based on real Week 17 ESPN data
- Keep the script simple and focused for v1
- Can enhance with notifications/integrations in future seasons
