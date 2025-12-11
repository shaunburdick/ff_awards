# Quickstart: Playoff Mode Testing & Validation

> **Spec ID**: 006
> **Created**: 2025-12-09
> **Last Updated**: 2025-12-09

This guide provides quick validation scenarios for testing the Playoff Mode feature.

---

## Prerequisites

```bash
# Ensure project is set up
cd ff_awards
uv sync

# Set up test environment (if using private leagues)
export ESPN_S2="your_espn_s2_cookie"
export SWID="your_swid_cookie"
export LEAGUE_IDS="123456789,987654321,555444333"
```

---

## Quick Test Scenarios

### Scenario 1: Semifinals Detection (Week 15)

**Test Date**: Available NOW (Dec 9-15, 2025)

**Command**:
```bash
uv run ff-tracker --env --format console
```

**Expected Output**:
```
================================================================================
                        🏈 PLAYOFF SEMIFINALS - WEEK 15 🏈
================================================================================

╔══════════════════════════════════════════════════════════════════════════════╗
║                            DIVISION 1 - SEMIFINALS                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────┬──────────────────────────┬────────────────┬────────┬──────────┐
│   Matchup   │      Team (Owner)        │      Seed      │ Score  │  Result  │
├─────────────┼──────────────────────────┼────────────────┼────────┼──────────┤
│ Semifinal 1 │ Thunder Cats (John)      │       #1       │ 145.67 │    ✓     │
│             │ Dream Team (Sarah)       │       #4       │  98.23 │          │
├─────────────┼──────────────────────────┼────────────────┼────────┼──────────┤
│ Semifinal 2 │ Grid Iron Giants (Mike)  │       #2       │ 132.45 │    ✓     │
│             │ The Replacements (Lisa)  │       #3       │ 128.90 │          │
└─────────────┴──────────────────────────┴────────────────┴────────┴──────────┘

... (continues with player highlights and historical season challenges)
```

**Validation Checklist**:
- [ ] Playoff brackets appear at TOP of output
- [ ] Each division shows 2 semifinal matchups
- [ ] Seeds display as #1, #2, #3, #4
- [ ] Scores show correctly (or 0.0 if not started)
- [ ] Winner indicator (✓) shows for higher scorer
- [ ] Only 7 player highlights (no team challenges)
- [ ] Season challenges show "Historical" note
- [ ] Regular season standings appear at BOTTOM

---

### Scenario 2: Finals Detection (Week 16)

**Test Date**: December 17, 2025 (Tuesday)

**Command**:
```bash
uv run ff-tracker --env --format console
```

**Expected Output**:
```
================================================================================
                          🏈 PLAYOFF FINALS - WEEK 16 🏈
================================================================================

╔══════════════════════════════════════════════════════════════════════════════╗
║                              DIVISION 1 - FINALS                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────┬──────────────────────────┬────────────────┬────────┬──────────┐
│   Matchup   │      Team (Owner)        │      Seed      │ Score  │  Result  │
├─────────────┼──────────────────────────┼────────────────┼────────┼──────────┤
│    Finals   │ Thunder Cats (John)      │       #1       │ 152.34 │    ✓     │
│             │ Grid Iron Giants (Mike)  │       #2       │ 148.90 │          │
└─────────────┴──────────────────────────┴────────────────┴────────┴──────────┘

... (continues)
```

**Validation Checklist**:
- [ ] Each division shows 1 finals matchup
- [ ] Seeds reflect semifinals winners
- [ ] Winner declared for each division
- [ ] Display structure same as semifinals

---

### Scenario 3: Championship Week (Week 17)

**Test Date**: December 24, 2025 (Christmas Eve)

**Command**:
```bash
uv run ff-tracker --env --format console
```

**Expected Output**:
```
================================================================================
                    🏆 CHAMPIONSHIP WEEK - WEEK 17 🏆
================================================================================

                         🥇 OVERALL CHAMPION 🥇
                           Pineapple Express
                                 Tom
                              Division 2
                          Score: 163.45 pts

╔══════════════════════════════════════════════════════════════════════════════╗
║                          CHAMPIONSHIP LEADERBOARD                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────┬─────────────────────────┬───────────────┬────────────┬───────────────┐
│ Rank │      Team (Owner)       │   Division    │   Score    │    Status     │
├──────┼─────────────────────────┼───────────────┼────────────┼───────────────┤
│  🥇  │ Pineapple Express (Tom) │  Division 2   │  163.45    │  CHAMPION!    │
│  🥈  │ Thunder Cats (John)     │  Division 1   │  156.78    │               │
│  🥉  │ End Zone Warriors (Pat) │  Division 3   │  148.92    │               │
└──────┴─────────────────────────┴───────────────┴────────────┴───────────────┘

... (continues with player highlights from ALL teams)
```

**Validation Checklist**:
- [ ] Championship banner appears at top
- [ ] Leaderboard shows all division winners
- [ ] Ranked by score (highest to lowest)
- [ ] Medal emojis for top 3
- [ ] Champion clearly indicated
- [ ] Player highlights include ALL teams (not just champions)
- [ ] NO regular season standings (championship is finale)

---

### Scenario 4: Division Sync Error

**Test Date**: Anytime

**Setup**: Use leagues in different weeks (one in Week 15, one in Week 14)

**Expected Output**:
```
ERROR: Divisions are out of sync

Division Status:
  - Division 1: Week 15 (Semifinals)
  - Division 2: Week 14 (Regular Season)
  - Division 3: Week 15 (Semifinals)

All divisions must be in the same state. Please wait for all leagues 
to advance to the same week before running playoff reports.
```

**Validation Checklist**:
- [ ] Clear error message displayed
- [ ] Shows exact week/state for each division
- [ ] Tool exits with error code 1
- [ ] No partial output generated

---

### Scenario 5: Regular Season (Unchanged)

**Test Date**: Anytime before Week 15

**Command**:
```bash
uv run ff-tracker --env --format console
```

**Expected Output**: Regular season output (unchanged from v2.2)

**Validation Checklist**:
- [ ] NO playoff brackets shown
- [ ] All 13 weekly challenges displayed (6 team + 7 player)
- [ ] Season challenges shown (current, not historical)
- [ ] Playoff indicators (*) show top 4 teams
- [ ] Output identical to pre-playoff-mode version

---

## Multi-Format Testing

### Test All Formats

```bash
# Generate all formats at once
uv run ff-tracker --env --output-dir ./playoff_test

# Individual formats
uv run ff-tracker --env --format console
uv run ff-tracker --env --format sheets > playoffs.tsv
uv run ff-tracker --env --format json > playoffs.json
uv run ff-tracker --env --format markdown > playoffs.md
uv run ff-tracker --env --format email > playoffs.html
```

**Validation**:
- [ ] All formats contain playoff bracket data
- [ ] Console: Fancy tables with Unicode borders
- [ ] Sheets: Clean TSV rows suitable for import
- [ ] JSON: Structured playoff_bracket object
- [ ] Markdown: GitHub/Slack compatible tables
- [ ] Email: Responsive HTML with styling

---

## Performance Testing

### Measure Performance Impact

```bash
# Regular season baseline
time uv run ff-tracker --env --format console

# Playoff mode (should be < 5% slower)
time uv run ff-tracker --env --format console
```

**Expected**:
- Regular season: ~3-5 seconds
- Playoff mode: ~3-6 seconds (< 20% increase)

**If slower**, profile to identify bottleneck:
```bash
python -m cProfile -o playoff_profile.stats ff_tracker/__main__.py --env
python -m pstats playoff_profile.stats
```

---

## Data Validation Testing

### Test with Mock Data

Create a test script to validate model behavior:

```python
from ff_tracker.models.playoff import PlayoffMatchup, PlayoffBracket

# Test valid matchup
matchup = PlayoffMatchup(
    matchup_id="test_sf1",
    round_name="Semifinal 1",
    seed1=1, team1_name="Team A", owner1_name="Owner A", score1=145.67,
    seed2=4, team2_name="Team B", owner2_name="Owner B", score2=98.23,
    winner_name="Team A", winner_seed=1,
    division_name="Test Division"
)
print(f"Valid matchup created: {matchup}")

# Test invalid matchup (should raise DataValidationError)
try:
    bad_matchup = PlayoffMatchup(
        matchup_id="", # Empty ID - should fail
        round_name="Semifinal 1",
        seed1=1, team1_name="Team A", owner1_name="Owner A", score1=145.67,
        seed2=4, team2_name="Team B", owner2_name="Owner B", score2=98.23,
        winner_name="Team A", winner_seed=1,
        division_name="Test Division"
    )
except DataValidationError as e:
    print(f"✓ Validation correctly rejected: {e}")
```

**Validation Checklist**:
- [ ] Valid data creates models successfully
- [ ] Invalid seeds raise DataValidationError
- [ ] Negative scores raise DataValidationError
- [ ] Empty strings raise DataValidationError
- [ ] Mismatched winner/seed raise DataValidationError

---

## ESPN API Testing

### Test Playoff Data Extraction

```bash
# Run existing test script
python test_playoff_api.py
```

**Expected Output**:
```
Testing ESPN Playoff API (Week 15)

League 1499701648:
  Current Week: 15
  Regular Season Count: 14
  In Playoffs: True
  Playoff Round: Semifinals
  
  Winners Bracket Matchups: 2
  Matchup 1:
    Seed #1 (Thunder Cats) vs Seed #4 (Dream Team)
    Score: 145.67 - 98.23
    Winner: Thunder Cats
  
  Matchup 2:
    Seed #2 (Grid Iron Giants) vs Seed #3 (The Replacements)
    Score: 132.45 - 128.90
    Winner: Grid Iron Giants
```

**Validation Checklist**:
- [ ] Playoff detection works (current_week > reg_season_count)
- [ ] Round detection accurate (Semifinals = week 1)
- [ ] Matchup extraction filters correctly (winners bracket only)
- [ ] Seeding accurate (1 vs 4, 2 vs 3)
- [ ] Scores extracted correctly
- [ ] Winner determination correct

---

## Acceptance Criteria Verification

### Story 1: Automatic Playoff Detection
- [ ] No `--playoffs` flag needed
- [ ] Detects when `current_week > reg_season_count`
- [ ] Reads `playoff_team_count` from ESPN API
- [ ] Identifies playoff games via `is_playoff` field
- [ ] Shows error if divisions out of sync

### Story 2: Playoff Bracket Display
- [ ] Brackets at TOP of all formats
- [ ] Regular standings at BOTTOM (context)
- [ ] Shows seeds, teams, owners, scores, winners
- [ ] Displays current round name
- [ ] All 5 formats render correctly

### Story 3: Adapted Challenge Display
- [ ] During playoffs: Show only 7 player highlights
- [ ] Hide 6 team challenges during playoffs
- [ ] Season challenges show "Historical" label
- [ ] Player highlights include ALL players (not just playoff teams)

### Story 4: Championship Week
- [ ] Shows ONE team per division (winners)
- [ ] Leaderboard format (rank, team, division, score)
- [ ] Highest scorer declared champion
- [ ] Shows player highlights + historical challenges
- [ ] All divisions must be in Championship Week

### Story 5: Playoff Data in All Formats
- [ ] Console: Visual brackets with emojis
- [ ] Sheets: TSV rows with matchup data
- [ ] Email: Styled HTML brackets
- [ ] Markdown: GitHub/Slack compatible
- [ ] JSON: Structured playoff_bracket object

---

## Common Issues & Troubleshooting

### Issue: "Playoff week detected but no playoff games found"

**Cause**: ESPN API hasn't updated yet for the current week

**Solution**: Wait a few hours and try again. ESPN typically updates early Tuesday morning.

---

### Issue: "Divisions are out of sync"

**Cause**: Commissioners advanced leagues at different times

**Solution**: Wait for all leagues to reach the same week. This is expected behavior.

---

### Issue: Scores show 0.0 - 0.0

**Cause**: Games haven't started yet

**Solution**: This is normal. Formatters will show "Not Started" status. Check back after games begin.

---

### Issue: Wrong seed numbers

**Cause**: ESPN API data inconsistency

**Solution**: We trust ESPN data per Business Rule #6. If seeds look wrong, verify in ESPN's actual bracket UI.

---

## Manual Verification Steps

After implementing playoff mode:

1. **Week 15 Testing** (Dec 9-15):
   - Run with real leagues in Semifinals
   - Verify 2 matchups per division
   - Check seed accuracy (#1 vs #4, #2 vs #3)
   - Validate all 5 output formats

2. **Week 16 Testing** (Dec 17):
   - Run with real leagues in Finals
   - Verify 1 matchup per division
   - Check winner determination
   - Validate division champions identified

3. **Week 17 Testing** (Dec 24):
   - Run with real leagues in Championship Week
   - Verify leaderboard ranking
   - Check overall champion declaration
   - Validate all formats handle championship mode

4. **Compare to Examples**:
   - Console output matches `examples/01-semifinals-console.txt`
   - JSON output matches `examples/06-semifinals-json.json`
   - Email HTML matches `examples/08-semifinals-email.html`

---

## Success Criteria

Playoff Mode is considered complete when:

- ✅ All 5 output formats render playoff brackets
- ✅ Automatic detection works (no manual flags)
- ✅ Division sync errors fail gracefully
- ✅ Semifinals, Finals, and Championship Week all work
- ✅ Performance impact < 5%
- ✅ All acceptance criteria verified
- ✅ Real ESPN data tested (Weeks 15, 16, 17)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-09 | AI Agent | Initial quickstart guide |
