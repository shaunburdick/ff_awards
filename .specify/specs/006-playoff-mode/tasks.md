# Implementation Tasks: Playoff Mode

> **Spec ID**: 006
> **Status**: Ready for Implementation
> **Created**: 2025-12-09
> **Last Updated**: 2025-12-09

This document breaks down the playoff mode implementation into concrete, ordered tasks. Tasks marked with `[P]` can be executed in parallel once their dependencies are met.

---

## Task Execution Guidelines

- Complete tasks in order within each phase
- Mark tasks with ✅ when complete
- Tasks marked `[P]` can run in parallel with other `[P]` tasks in the same group
- Test after each phase before moving to the next
- Document any deviations or issues encountered

---

## Phase 1: Data Models & Foundation

**Goal**: Create immutable playoff data structures

### Task 1.1: Create Playoff Models File
- [ ] Create `ff_tracker/models/playoff.py`
- [ ] Add file header with module docstring
- [ ] Add `from __future__ import annotations` import
- [ ] Add necessary imports: `dataclasses`, `DataValidationError`

**Validation**: File imports without errors

---

### Task 1.2: Implement PlayoffMatchup Model
- [ ] Define `PlayoffMatchup` dataclass with `@dataclass(frozen=True)`
- [ ] Add all 13 fields with proper types (see data-model.md)
- [ ] Implement `__post_init__` validation:
  - [ ] Validate seeds > 0
  - [ ] Validate scores >= 0 if present
  - [ ] Validate winner_name matches team1 or team2 if present
  - [ ] Validate winner_seed matches seed1 or seed2 if present
  - [ ] Validate all required strings are non-empty
- [ ] Add comprehensive docstring with field descriptions

**Validation**: Can create valid matchup, invalid data raises `DataValidationError`

---

### Task 1.3: Implement PlayoffBracket Model
- [ ] Define `PlayoffBracket` dataclass with `@dataclass(frozen=True)`
- [ ] Add fields: `round: str`, `week: int`, `matchups: list[PlayoffMatchup]`
- [ ] Implement `__post_init__` validation:
  - [ ] Validate round is "Semifinals" or "Finals"
  - [ ] Validate week > 0
  - [ ] Validate at least 1 matchup
  - [ ] Validate Semifinals has exactly 2 matchups
  - [ ] Validate Finals has exactly 1 matchup
- [ ] Add comprehensive docstring

**Validation**: Can create valid brackets, invalid data raises errors

---

### Task 1.4: Implement ChampionshipEntry Model
- [ ] Define `ChampionshipEntry` dataclass with `@dataclass(frozen=True)`
- [ ] Add all 6 fields with proper types
- [ ] Implement `__post_init__` validation:
  - [ ] Validate rank > 0
  - [ ] Validate score >= 0
  - [ ] Validate is_champion=True only when rank=1
  - [ ] Validate all required strings are non-empty
- [ ] Add comprehensive docstring

**Validation**: Can create valid entries, invalid data raises errors

---

### Task 1.5: Implement ChampionshipLeaderboard Model
- [ ] Define `ChampionshipLeaderboard` dataclass with `@dataclass(frozen=True)`
- [ ] Add fields: `week: int`, `entries: list[ChampionshipEntry]`
- [ ] Implement `__post_init__` validation:
  - [ ] Validate week > 0
  - [ ] Validate at least 1 entry
  - [ ] Validate entries ranked sequentially (1, 2, 3, ...)
  - [ ] Validate exactly one champion
  - [ ] Validate champion is first entry (rank=1)
- [ ] Add `champion` property that returns the champion entry
- [ ] Add comprehensive docstring

**Validation**: Can create valid leaderboard, invalid data raises errors

---

### Task 1.6: Update Models Package
- [ ] Update `ff_tracker/models/__init__.py` to import new playoff models
- [ ] Add to `__all__` list: `PlayoffMatchup`, `PlayoffBracket`, `ChampionshipEntry`, `ChampionshipLeaderboard`

**Validation**: Can import playoff models from `ff_tracker.models`

---

### Task 1.7: Extend DivisionData Model
- [ ] Open `ff_tracker/models/division.py`
- [ ] Add `playoff_bracket: PlayoffBracket | None = None` field to `DivisionData`
- [ ] Add `is_playoff_mode` property that returns `playoff_bracket is not None`
- [ ] Update docstring to document playoff field

**Validation**: Can create DivisionData with and without playoff_bracket

---

### Task 1.8: Add DivisionSyncError Exception
- [ ] Open `ff_tracker/exceptions.py`
- [ ] Add `DivisionSyncError` class that extends `FFTrackerError`
- [ ] Add `division_states: dict[str, str]` attribute
- [ ] Add custom `__init__` to store division states
- [ ] Add docstring explaining when this error is raised

**Validation**: Can import and raise `DivisionSyncError`

---

### Task 1.9: Test Phase 1 (Data Models)
- [ ] Write test script or use Python REPL to test:
  - [ ] Create valid PlayoffMatchup instances
  - [ ] Verify validation catches invalid seeds
  - [ ] Verify validation catches invalid scores
  - [ ] Create valid PlayoffBracket for Semifinals (2 matchups)
  - [ ] Create valid PlayoffBracket for Finals (1 matchup)
  - [ ] Verify bracket validation catches wrong matchup counts
  - [ ] Create valid ChampionshipEntry instances
  - [ ] Create valid ChampionshipLeaderboard
  - [ ] Verify leaderboard validation catches duplicate ranks
  - [ ] Create DivisionData with playoff_bracket
  - [ ] Verify is_playoff_mode property works

**Validation**: All models work as expected, validation catches all error cases

---

## Phase 2: Playoff Detection Logic

**Goal**: Add playoff detection methods to ESPNService

### Task 2.1: Add Playoff Detection Method
- [ ] Open `ff_tracker/services/espn_service.py`
- [ ] Add `is_in_playoffs(self, league: League) -> bool` method
- [ ] Implement: `return league.current_week > league.settings.reg_season_count`
- [ ] Add comprehensive docstring with examples

**Validation**: Method returns True for Week 15+, False for Week 14-

---

### Task 2.2: Add Playoff Round Detection Method
- [ ] Add `get_playoff_round(self, league: League) -> str` method
- [ ] Check if in playoffs, raise `ESPNAPIError` if not
- [ ] Calculate `playoff_week = current_week - reg_season_count`
- [ ] Return "Semifinals" for playoff_week==1
- [ ] Return "Finals" for playoff_week==2
- [ ] Return "Championship Week" for playoff_week==3
- [ ] Raise `ESPNAPIError` for unexpected playoff weeks
- [ ] Add comprehensive docstring

**Validation**: Returns correct round for Weeks 15, 16, 17

---

### Task 2.3: Add Division Sync Check Method
- [ ] Add `check_division_sync(self, leagues: list[League]) -> tuple[bool, str]` method
- [ ] Check if all leagues have same `current_week`
- [ ] Check if all leagues have same playoff state (in playoffs or not)
- [ ] If in playoffs, check all have same playoff round
- [ ] Build detailed error message if out of sync
- [ ] Return `(True, "")` if synced, `(False, error_message)` if not
- [ ] Add comprehensive docstring

**Validation**: Detects mismatched weeks and playoff states correctly

---

### Task 2.4: Test Phase 2 (Detection Logic)
- [ ] Test with real ESPN data (Week 15):
  - [ ] Verify `is_in_playoffs()` returns True
  - [ ] Verify `get_playoff_round()` returns "Semifinals"
- [ ] Test sync checking with mock leagues:
  - [ ] All in Week 15 → synced
  - [ ] Mix of Week 14 and 15 → out of sync
  - [ ] All in Week 15 but one in Week 16 → out of sync

**Validation**: All detection logic works correctly

---

## Phase 3: Playoff Data Extraction (Semifinals & Finals)

**Goal**: Extract bracket matchups from ESPN API

### Task 3.1: Add Matchup Extraction Method
- [ ] Add `extract_playoff_matchups(self, league: League, division_name: str) -> list[PlayoffMatchup]` method
- [ ] Get box_scores for current week: `league.box_scores(league.current_week)`
- [ ] Filter to winners bracket: `bs.is_playoff and bs.matchup_type == "WINNERS_BRACKET"`
- [ ] For each box_score:
  - [ ] Extract home/away teams
  - [ ] Get seeds from `team.standing`
  - [ ] Get team names from `team.team_name`
  - [ ] Get owner names using existing helper
  - [ ] Get scores from `bs.home_score`, `bs.away_score`
  - [ ] Determine winner (higher score wins, None if 0-0)
  - [ ] Create `PlayoffMatchup` instance
- [ ] Return list of matchups
- [ ] Add comprehensive docstring

**Validation**: Extracts 2 matchups for Semifinals, 1 for Finals

---

### Task 3.2: Add Bracket Builder Method
- [ ] Add `build_playoff_bracket(self, league: League, division_name: str) -> PlayoffBracket` method
- [ ] Get playoff round using `get_playoff_round()`
- [ ] Extract matchups using `extract_playoff_matchups()`
- [ ] Create `PlayoffBracket` with round, week, matchups
- [ ] Return bracket
- [ ] Add comprehensive docstring

**Validation**: Builds valid PlayoffBracket for given league

---

### Task 3.3: Integrate into load_all_divisions
- [ ] Locate `load_all_divisions()` method in `ESPNService`
- [ ] After loading each league, check if in playoffs
- [ ] If in playoffs:
  - [ ] Build playoff bracket using `build_playoff_bracket()`
  - [ ] Pass to `DivisionData` constructor as `playoff_bracket=bracket`
- [ ] If not in playoffs:
  - [ ] Pass `playoff_bracket=None` (default)
- [ ] Update method signature if needed

**Validation**: DivisionData includes playoff bracket when in playoffs

---

### Task 3.4: Add Division Sync Validation to load_all_divisions
- [ ] After loading all leagues, check division sync
- [ ] Call `check_division_sync(leagues)`
- [ ] If out of sync, raise `DivisionSyncError` with detailed message
- [ ] Include division names and states in error

**Validation**: Out-of-sync divisions cause immediate failure with clear error

---

### Task 3.5: Test Phase 3 (Data Extraction)
- [ ] Test with real ESPN data (Week 15):
  - [ ] Verify 2 matchups extracted per division
  - [ ] Verify seeds are #1 vs #4, #2 vs #3
  - [ ] Verify team names and owners extracted
  - [ ] Verify scores extracted (may be 0.0 if games not started)
  - [ ] Verify bracket structure is valid
  - [ ] Verify DivisionData.is_playoff_mode == True
- [ ] Test sync validation:
  - [ ] Mock leagues out of sync → DivisionSyncError raised
  - [ ] Error message is clear and actionable

**Validation**: Playoff data extraction works end-to-end

---

## Phase 4: Championship Week Data Extraction

**Goal**: Extract championship leaderboard from division winners

### Task 4.1: Add Championship Entry Extraction Method
- [ ] Add `extract_championship_entry(self, league: League, division_name: str, championship_week: int) -> ChampionshipEntry` method
- [ ] Find division winner:
  - [ ] Get previous week's box_scores (Finals)
  - [ ] Find winners bracket Finals matchup
  - [ ] Determine winner from scores
- [ ] Get winner's championship week score:
  - [ ] Get box_scores for championship_week
  - [ ] Find team in matchups or get score directly
- [ ] Create `ChampionshipEntry` (rank will be set later)
- [ ] Add comprehensive docstring

**Validation**: Extracts correct division winner and score

**Note**: This task may need adjustment after Week 17 testing

---

### Task 4.2: Add Championship Leaderboard Builder Method
- [ ] Add `build_championship_leaderboard(self, leagues: list[League], division_names: list[str], championship_week: int) -> ChampionshipLeaderboard` method
- [ ] Extract championship entry for each league/division
- [ ] Sort entries by score (highest first)
- [ ] Assign ranks (1, 2, 3, ...)
- [ ] Set is_champion=True for rank 1
- [ ] Create `ChampionshipLeaderboard` with entries
- [ ] Return leaderboard
- [ ] Add comprehensive docstring

**Validation**: Builds valid leaderboard with correct ranking

**Note**: This task may need adjustment after Week 17 testing

---

### Task 4.3: Integrate Championship Week into Main Flow
- [ ] Update main CLI flow in `ff_tracker/main.py`
- [ ] After loading divisions, check if Championship Week:
  - [ ] Check if playoff_week == 3
- [ ] If Championship Week:
  - [ ] Build championship leaderboard using service
  - [ ] Pass to formatters as `championship` parameter
- [ ] If not Championship Week:
  - [ ] Pass `championship=None`

**Validation**: Championship leaderboard passed to formatters when appropriate

**Note**: This task may need adjustment after Week 17 testing

---

### Task 4.4: Test Phase 4 (Championship Week)
- [ ] Create mock data for testing (Week 17 not available yet):
  - [ ] Mock 3 division winners with scores
  - [ ] Build championship leaderboard manually
  - [ ] Verify ranking is correct (highest → lowest)
  - [ ] Verify champion is marked correctly
- [ ] Plan to re-test with real Week 17 data on Dec 24

**Validation**: Championship logic works with mock data

**Note**: Must re-test with real data Week 17 (Dec 24)

---

## Phase 5: Console Formatter Extensions

**Goal**: Render playoff brackets in console output

### Task 5.1: Add Playoff Bracket Formatting Method
- [ ] Open `ff_tracker/display/console.py`
- [ ] Add `_format_playoff_bracket(self, divisions: list[DivisionData]) -> str` method
- [ ] For each division with playoff_bracket:
  - [ ] Add division header with round name
  - [ ] Create table using tabulate with `fancy_grid` style
  - [ ] Columns: Matchup | Team (Owner) | Seed | Score | Result
  - [ ] For each matchup:
    - [ ] Row 1: Matchup name, Team1 (Owner1), #seed1, score1, ✓ if winner
    - [ ] Row 2: Empty, Team2 (Owner2), #seed2, score2, ✓ if winner
  - [ ] Handle in-progress games (0.0 scores)
- [ ] Return formatted string
- [ ] Add comprehensive docstring

**Validation**: Outputs match example in `examples/01-semifinals-console.txt`

---

### Task 5.2: Add Championship Leaderboard Formatting Method
- [ ] Add `_format_championship_leaderboard(self, championship: ChampionshipLeaderboard) -> str` method
- [ ] Add large trophy banner at top
- [ ] Add champion announcement with name, owner, division, score
- [ ] Create leaderboard table using tabulate
- [ ] Columns: Rank | Team (Owner) | Division | Score | Status
- [ ] Add medal emojis for top 3 (🥇🥈🥉)
- [ ] Mark champion row with "CHAMPION!" status
- [ ] Return formatted string
- [ ] Add comprehensive docstring

**Validation**: Outputs match example in `examples/03-championship-console.txt`

---

### Task 5.3: Adapt Weekly Challenges Display for Playoffs
- [ ] Add `_filter_playoff_challenges(self, weekly_challenges: list[WeeklyChallenge], is_playoff_mode: bool) -> list[WeeklyChallenge]` method
- [ ] If playoff mode (not championship):
  - [ ] Filter to only player highlights (challenge_type=="player")
  - [ ] Exclude team challenges (challenge_type=="team")
- [ ] If not playoff mode or championship week:
  - [ ] Return all challenges unchanged
- [ ] Return filtered list
- [ ] Add comprehensive docstring

**Validation**: Returns 7 player challenges during playoffs, all 13 otherwise

---

### Task 5.4: Add Historical Note to Season Challenges
- [ ] Update `_format_season_challenges()` method
- [ ] Add parameter: `is_playoff_mode: bool`
- [ ] If playoff mode:
  - [ ] Add section header: "📊 REGULAR SEASON FINAL RESULTS (Historical) 📊"
  - [ ] Add note: "These challenges reflect final regular season results"
- [ ] If not playoff mode:
  - [ ] Keep existing header
- [ ] Add comprehensive docstring update

**Validation**: Shows historical note during playoffs

---

### Task 5.5: Update Main format_output Method
- [ ] Update `format_output()` method signature to add `championship` parameter
- [ ] At start of method, detect playoff mode:
  - [ ] `is_playoff = any(d.is_playoff_mode for d in divisions)`
  - [ ] `is_championship = championship is not None`
- [ ] Build output in new order:
  - [ ] If championship week: Championship leaderboard FIRST
  - [ ] If playoff mode: Playoff brackets FIRST
  - [ ] Filter weekly challenges based on mode
  - [ ] Format season challenges with historical note
  - [ ] If playoff mode (not championship): Regular season standings LAST
  - [ ] If championship mode: Skip regular season standings
- [ ] Return formatted output

**Validation**: Output structure matches examples

---

### Task 5.6: Test Phase 5 (Console Formatter)
- [ ] Test with mock playoff data:
  - [ ] Semifinals output matches `examples/01-semifinals-console.txt`
  - [ ] Finals output matches `examples/02-finals-console.txt`
  - [ ] Championship output matches `examples/03-championship-console.txt`
- [ ] Test weekly challenge filtering:
  - [ ] Playoffs show 7 player highlights only
  - [ ] Regular season shows all 13 challenges
- [ ] Test historical note appears during playoffs

**Validation**: Console output is beautiful and correct

---

## Phase 6: Other Formatter Extensions

**Goal**: Extend sheets, email, markdown, JSON formatters

### Task 6.1: [P] Extend Sheets Formatter
- [ ] Open `ff_tracker/display/sheets.py`
- [ ] Add `_format_playoff_bracket()` method:
  - [ ] Header row: "PLAYOFF BRACKET - [ROUND]"
  - [ ] Columns: Division | Matchup | Seed1 | Team1 | Owner1 | Score1 | Seed2 | Team2 | Owner2 | Score2 | Winner
  - [ ] One row per matchup
- [ ] Add `_format_championship()` method:
  - [ ] Header row: "CHAMPIONSHIP WEEK"
  - [ ] Columns: Rank | Team | Owner | Division | Score | Champion
  - [ ] One row per entry
- [ ] Update `format_output()` following same pattern as console
- [ ] Test output is valid TSV

**Validation**: TSV imports cleanly into Google Sheets

---

### Task 6.2: [P] Extend Email Formatter
- [ ] Open `ff_tracker/display/email.py`
- [ ] Add `_format_playoff_bracket()` method:
  - [ ] Purple gradient header for playoff excitement
  - [ ] HTML table with responsive styling
  - [ ] Winner rows highlighted in green with left border
  - [ ] Handle mobile display
- [ ] Add `_format_championship()` method:
  - [ ] Gold-themed styling
  - [ ] Large trophy banner with gradient background
  - [ ] Champion row prominently highlighted
  - [ ] Medal emojis (🥇🥈🥉)
- [ ] Update `format_output()` following same pattern as console
- [ ] Test HTML renders correctly in browser

**Validation**: HTML matches `examples/08-semifinals-email.html`, `examples/09-championship-email.html`

---

### Task 6.3: [P] Extend Markdown Formatter
- [ ] Open `ff_tracker/display/markdown.py`
- [ ] Add `_format_playoff_bracket()` method:
  - [ ] Markdown table format
  - [ ] Bold subheadings for divisions
  - [ ] Seeds shown as **#1**, **#2**, etc.
  - [ ] Winner marked with ✓
- [ ] Add `_format_championship()` method:
  - [ ] Championship heading with trophy emoji
  - [ ] Medal emojis (🥇🥈🥉) in table
  - [ ] Champion clearly indicated
- [ ] Update `format_output()` following same pattern as console
- [ ] Test markdown renders correctly in GitHub/Slack

**Validation**: Markdown matches `examples/04-semifinals-markdown.md`, `examples/05-championship-markdown.md`

---

### Task 6.4: [P] Extend JSON Formatter
- [ ] Open `ff_tracker/display/json.py`
- [ ] Update `format_output()` to detect playoff mode
- [ ] If playoff mode:
  - [ ] Add `report_type` field: "playoff_semifinals", "playoff_finals", or "championship_week"
  - [ ] Add top-level `playoff_bracket` object with structure:
    - [ ] `round`: string
    - [ ] `divisions`: array of division bracket objects
    - [ ] Each division has `division_name` and `matchups` array
    - [ ] Matchups follow contract structure
- [ ] If championship mode:
  - [ ] Add top-level `championship` object:
    - [ ] `week`: int
    - [ ] `leaderboard`: array of entries
    - [ ] `overall_champion`: champion object
- [ ] Ensure all playoff data serializes correctly

**Validation**: JSON matches `examples/06-semifinals-json.json`, `examples/07-championship-json.json`

---

### Task 6.5: Test Phase 6 (All Formatters)
- [ ] Test each formatter with mock playoff data:
  - [ ] Sheets: Valid TSV output
  - [ ] Email: Valid HTML that renders correctly
  - [ ] Markdown: Valid MD that renders correctly
  - [ ] JSON: Valid JSON that parses correctly
- [ ] Test all formatters with championship data
- [ ] Verify challenge filtering works in all formats
- [ ] Verify historical notes appear in all formats

**Validation**: All 5 formatters support playoff mode correctly

---

## Phase 7: Integration Testing & Validation

**Goal**: End-to-end testing with real ESPN data

### Task 7.1: Test with Week 15 Data (Semifinals)
- [ ] Run with real leagues in Semifinals:
  ```bash
  uv run ff-tracker --env --format console
  uv run ff-tracker --env --output-dir ./test_output
  ```
- [ ] Verify all acceptance criteria from spec:
  - [ ] Automatic playoff detection works
  - [ ] Playoff brackets display correctly
  - [ ] Only 7 player highlights shown
  - [ ] Season challenges show "Historical" note
  - [ ] All 5 formats render correctly
- [ ] Compare output to examples directory
- [ ] Document any differences or issues

**Validation**: Week 15 works perfectly

---

### Task 7.2: Test Division Sync Error Scenarios
- [ ] Mock leagues out of sync (Week 14 and Week 15)
- [ ] Run tool and verify:
  - [ ] Clear error message displayed
  - [ ] Shows exact week/state for each division
  - [ ] Tool exits with error code 1
  - [ ] No partial output generated
- [ ] Verify error message is actionable

**Validation**: Sync errors fail gracefully with clear guidance

---

### Task 7.3: Test with Week 16 Data (Finals)
**Test Date**: December 17, 2025

- [ ] Run with real leagues in Finals:
  ```bash
  uv run ff-tracker --env --format console
  uv run ff-tracker --env --output-dir ./test_output
  ```
- [ ] Verify:
  - [ ] Round detected as "Finals"
  - [ ] 1 matchup per division
  - [ ] Division winners correctly identified
  - [ ] All formats render correctly
- [ ] Compare to `examples/02-finals-console.txt`
- [ ] Document any adjustments needed

**Validation**: Week 16 works correctly

**Note**: Adjust implementation if Finals structure differs from assumptions

---

### Task 7.4: Test with Week 17 Data (Championship Week)
**Test Date**: December 24, 2025

- [ ] Run with real leagues in Championship Week:
  ```bash
  uv run ff-tracker --env --format console
  uv run ff-tracker --env --output-dir ./test_output
  ```
- [ ] Verify:
  - [ ] Round detected as "Championship Week"
  - [ ] Championship leaderboard displays
  - [ ] All division winners present
  - [ ] Ranked correctly by score
  - [ ] Overall champion declared
  - [ ] Player highlights include ALL teams
  - [ ] All formats render correctly
- [ ] Compare to `examples/03-championship-console.txt`
- [ ] Document any adjustments needed

**Validation**: Week 17 works correctly

**Note**: Adjust implementation if Championship Week structure differs from assumptions

---

### Task 7.5: Test Regular Season (Regression Testing)
- [ ] Test with leagues in regular season (Week 14 or earlier)
- [ ] Verify output is IDENTICAL to pre-playoff-mode version:
  - [ ] All 13 weekly challenges displayed
  - [ ] Season challenges shown (not historical)
  - [ ] Playoff indicators (*) show top 4 teams
  - [ ] No playoff brackets displayed
- [ ] Test all 5 output formats

**Validation**: Regular season output unchanged

---

### Task 7.6: Performance Testing
- [ ] Measure execution time with regular season data
- [ ] Measure execution time with playoff data
- [ ] Verify performance impact < 5%
- [ ] If performance issue, profile and optimize

**Validation**: Performance meets requirements

---

### Task 7.7: Final Documentation Updates
- [ ] Update README.md with playoff mode examples
- [ ] Update CHANGELOG.md with v3.0 entry
- [ ] Update AGENTS.md if needed
- [ ] Add any lessons learned to spec documentation

**Validation**: Documentation is complete and accurate

---

## Success Criteria Checklist

Before considering implementation complete, verify:

- [ ] All 18 acceptance criteria from spec verified
- [ ] All 5 output formats support playoff mode
- [ ] Automatic detection works (no manual flags)
- [ ] Division sync errors fail gracefully
- [ ] Semifinals tested with real data (Week 15)
- [ ] Finals tested with real data (Week 16)
- [ ] Championship Week tested with real data (Week 17)
- [ ] Regular season output unchanged (regression test)
- [ ] Performance impact < 5%
- [ ] All code passes linting (100% clean)
- [ ] All code has 100% type coverage
- [ ] Zero constitutional violations
- [ ] Documentation complete and accurate

---

## Notes & Adjustments

### Week 16 Testing Notes (Dec 17)
*To be filled in after testing*

### Week 17 Testing Notes (Dec 24)
*To be filled in after testing*

### Implementation Deviations
*Document any deviations from the plan*

### Lessons Learned
*Document insights gained during implementation*

---

## Estimated Effort

- **Phase 1** (Data Models): 2-3 hours
- **Phase 2** (Detection Logic): 1-2 hours
- **Phase 3** (Data Extraction): 2-3 hours
- **Phase 4** (Championship Week): 2-3 hours (may need adjustment after testing)
- **Phase 5** (Console Formatter): 2-3 hours
- **Phase 6** (Other Formatters): 3-4 hours (parallel work possible)
- **Phase 7** (Testing & Validation): 2-3 hours (spread over 3 weeks)

**Total Estimated Time**: 14-21 hours of active development + 3 weeks of real-data testing

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-09 | AI Agent | Initial task breakdown |
