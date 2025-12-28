# Championship Week Management Script (Spec 007)

## Overview

A **separate script** (`ff-championship`) for managing Week 17 Championship Week, where division winners compete for the overall championship without official ESPN matchups.

## Why Separate Script?

Week 17 is fundamentally different:
- ❌ No official ESPN matchups (leagues marked complete)
- ✅ Must calculate scores from individual player performances
- ✅ Different workflow (roster validation, live updates)
- ✅ Keeping separate prevents complicating `ff-tracker`

## Key Features

### 1. Championship Leaderboard
Shows all division winners ranked by Week 17 score:
```bash
uv run ff-championship --env --private
```

### 2. Roster Status Checking
Tracks which champions have set their rosters:
```bash
uv run ff-championship --env --mode check-rosters
```

### 3. Roster Validation
Validates rosters for issues (empty slots, bye weeks, injuries):
```bash
uv run ff-championship --env --mode validate
```

## Architecture

```
ff_tracker/
├── championship.py          # NEW: Championship CLI
├── models/
│   ├── championship.py      # NEW: Championship models
│   └── playoff.py           # EXISTING: Shared models
├── services/
│   ├── espn_service.py      # SHARED: ESPN API
│   ├── championship_service.py  # NEW: Championship logic
│   └── roster_validator.py  # NEW: Roster validation
└── display/                 # SHARED: All 5 formatters
```

**Shared Code**: ESPN service, models, display formatters
**New Code**: Championship-specific logic, roster validation

## Implementation Phases

1. **Extract Shared Code** (1-2h) - Ensure ESPN service can fetch player rosters
2. **Championship Models** (1h) - Data structures for teams, rosters, slots
3. **Championship Service** (2-3h) - Score calculation, winner detection
4. **Roster Validator** (1-2h) - Empty slots, bye weeks, injury detection
5. **CLI Entry Point** (1-2h) - Command-line interface with modes
6. **Output Formatters** (1-2h) - Extend all 5 formats for championship data
7. **Testing** (2-3h) - Dry-run testing, iterate on real Week 17 data
8. **Documentation** (1h) - Update README, add quickstart

**Total Time**: 10-16 hours

## Timeline

- **Dec 23-26**: Implementation & testing
- **Dec 26-27**: Dry-run testing with `--week 17`
- **Dec 28-29**: Week 17 live (iterate on real data)

## Success Criteria

✅ Shows championship leaderboard with correct scores
✅ Calculates scores from individual player performances
✅ Validates rosters (empty slots, injuries, bye weeks)
✅ All 5 output formats work correctly
✅ Projection-based game status detection (see [GAME_STATUS_DETECTION.md](./GAME_STATUS_DETECTION.md))

## Implementation Status

**Status**: ✅ **COMPLETE** (Dec 28, 2025)

All core features implemented and tested with real Week 17 data:
- ✅ Championship leaderboard mode
- ✅ Roster status checking mode
- ✅ Roster validation mode
- ❌ Live score updates mode (removed - ESPN API limitation)
- ✅ All 5 output formats tested and working
- ✅ Documented ESPN API limitations and workarounds

### Key Files Created
- `ff_tracker/championship.py` (498 lines) - CLI implementation
- `ff_tracker/services/championship_service.py` (405 lines) - Business logic
- `ff_tracker/services/roster_validator.py` (204 lines) - Roster validation
- `ff_tracker/models/championship.py` (197 lines) - Data models
- `GAME_STATUS_DETECTION.md` - Technical documentation

### Real Data Testing (Dec 28, 2025)
- 3 division winners identified correctly
- All rosters validated successfully
- Scores calculated from 30 individual starter performances
- Progress tracking: 98/100 games detected as completed (accurate!)
- Overall champion: "Billieve the Champ Is Back" (162.06 pts)

## Important Notes

### ESPN API Limitation
ESPN does **not** provide true "live" scoring for post-season consolation weeks (Week 17+). The API returns static scores once the league officially ends (Week 16 Finals).

**Our Solution**: Use projected points as a proxy to infer game status:
- `projected=0, points=0` → Player ruled out (final)
- `projected>0, points=0` → Game not started
- `points>0` → Game started/complete (final)

This approach is **sufficient for roster validation** (the primary goal) but cannot provide true real-time score updates. See [GAME_STATUS_DETECTION.md](./GAME_STATUS_DETECTION.md) for full technical details.

## GitHub Actions Workflow

A dedicated workflow is available for automated championship reporting:

**File**: `.github/workflows/championship-report.yml`

### Features
- ✅ Manual trigger only (no cron schedule)
- ✅ Generates all 5 output formats
- ✅ Sends email report to league members
- ✅ Uploads artifacts for 90 days (longer retention than weekly reports)
- ✅ Supports optional championship note in email

### Usage
```bash
# Trigger from GitHub Actions UI with default settings
# Or use GitHub CLI:
gh workflow run championship-report.yml

# With custom note:
gh workflow run championship-report.yml \
  -f championship_note="Congratulations to all champions! 🏆"

# Test without sending email:
gh workflow run championship-report.yml -f skip_email=true
```

### Configuration Required
Set these secrets in your GitHub repository:
- `LEAGUE_IDS` - Comma-separated ESPN league IDs
- `ESPN_SWID` - ESPN authentication cookie
- `ESPN_S2` - ESPN authentication cookie
- `SMTP_SERVER` - Email server address
- `SMTP_PORT` - Email server port
- `SMTP_USERNAME` - SMTP username
- `SMTP_PASSWORD` - SMTP password
- `EMAIL_FROM` - Sender email address
- `EMAIL_RECIPIENTS` - Comma-separated recipient list (BCC)

## Next Steps

1. ✅ Complete implementation
2. ✅ Test with real Week 17 data
3. ✅ Create GitHub Actions workflow
4. ⏳ Commit and merge to main
5. 📊 Run during Week 17 games (Dec 28-29)

See [spec.md](./spec.md) for full technical details.
