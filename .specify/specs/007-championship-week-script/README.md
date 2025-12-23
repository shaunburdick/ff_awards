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
uv run ff-championship --env --check-rosters
```

### 3. Roster Validation
Validates rosters for issues (empty slots, bye weeks, injuries):
```bash
uv run ff-championship --env --validate
```

### 4. Live Score Updates
Shows real-time scores during Championship Week:
```bash
uv run ff-championship --env --live
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
✅ Live score updates during games

## Next Steps

1. Review & approve spec
2. Begin implementation
3. Test with `--dry-run`
4. Deploy before Week 17 (Dec 28)

See [spec.md](./spec.md) for full technical details.
