# Season Recap Script (Spec 008)

## Overview

A **standalone script** (`ff-season-recap`) that generates comprehensive end-of-season summaries, bringing together regular season results, season challenges, playoff brackets, and championship week into one complete report.

## Why This Script?

After Week 17 completes, commissioners need a **single comprehensive summary** that tells the complete season story. Currently, this information is scattered across:
- Multiple weekly `ff-tracker` reports (regular season)
- Playoff bracket reports from Weeks 15-16
- Championship report from Week 17

This script consolidates everything into one polished, shareable season recap.

## Key Features

### 1. Regular Season Summary
- Division champions (best record per division)
- Final standings for all divisions
- Season date range (Weeks 1-14)

### 2. Season Challenge Winners
All 5 season challenges with complete details:
1. Most Points Overall
2. Most Points in One Game
3. Most Points in a Loss
4. Least Points in a Win
5. Closest Victory

### 3. Playoff Results
- Week 15 Semifinals (all matchups, all divisions)
- Week 16 Finals (division champions crowned)
- Seeds, scores, and winners clearly indicated

### 4. Championship Summary
- Week 17 results (all division winners)
- Final ranking of division winners
- Overall champion clearly marked
- Margin of victory

### 5. Multiple Output Formats
- Console (human-readable tables)
- Sheets (TSV for Google Sheets)
- Email (mobile-friendly HTML)
- JSON (structured data for archival)
- Markdown (GitHub/Slack/Discord ready)

## Architecture

```
ff_tracker/
├── season_recap.py          # NEW: Season recap CLI
├── models/
│   ├── season_summary.py    # NEW: Recap data models
│   └── [existing models]    # SHARED: Team, Challenge, Playoff, Championship
├── services/
│   ├── season_recap_service.py  # NEW: Orchestration logic
│   └── [existing services]  # SHARED: ESPN, Challenge, Championship
└── display/                 # SHARED: All 5 formatters (extended)
```

**Philosophy**: Separate script with single responsibility, reuses existing infrastructure

## Usage

```bash
# Generate season recap for current season
uv run ff-season-recap --env --private

# Specific year
uv run ff-season-recap --env --year 2024

# All formats at once
uv run ff-season-recap --env --output-dir ./season-recap

# With custom note
uv run ff-season-recap --env --format email \
  --format-arg note="Thanks for a great season! 🏆"

# Specific format
uv run ff-season-recap --env --format markdown
```

## Implementation Phases

1. **Foundation** (2-3h) - Data models for season summary
2. **Service Layer** (3-4h) - Logic to extract and organize all season data
3. **CLI Entry Point** (1-2h) - Command-line interface
4. **Display Formatters** (2-3h) - Extend all 5 formats for recap
5. **Testing** (2-3h) - Integration tests with real season data
6. **Documentation** (1h) - README updates, quickstart
7. **GitHub Actions** (1h) - Automated workflow (manual trigger)

**Total Time**: 12-17 hours

## Success Criteria

✅ Shows regular season division champions and final standings  
✅ Shows all 5 season challenge winners with complete details  
✅ Shows playoff results (semifinals and finals) for all divisions  
✅ Shows championship week results with overall champion  
✅ All 5 output formats work correctly  
✅ Data matches existing scripts exactly (accuracy verification)  
✅ Clear error messages for incomplete seasons  
✅ CLI interface matches existing script patterns  

## Future Enhancements (Phase 2)

### Season Awards
- Most Consistent (lowest score variance)
- Boom or Bust (highest score variance)
- Best Playoff Run (seed improvement)
- Heartbreaker (most close losses)
- Lucky Winner (most close wins)
- Benchwarmer (most bench points)

### Historical Tracking
- Year-over-year comparisons
- Multi-season trends
- All-time records
- Repeat winners

### Enhanced Visualizations
- Charts/graphs in email format
- Scoring trends over season
- Head-to-head records matrix

## Key Design Decisions ✅

All design questions have been resolved:

1. **Season Structure Detection**: Fully dynamic from ESPN API
   - Uses `league.settings.reg_season_count`, `league.finalScoringPeriod`
   - Championship week = `finalScoringPeriod + 1`
   - No hardcoded weeks or playoff lengths

2. **Incomplete Data Handling**: Flexible with `--force` flag
   - Normal: Validates championship week complete
   - `--force`: Generates partial recap with warnings

3. **Division Names**: Hybrid approach
   - Uses `league.settings.name` or falls back to "Division N"

4. **Historical Persistence**: Multi-output mode saves JSON
   - Single format: outputs to stdout
   - `--output-dir`: creates all 5 files including JSON
   - No year-over-year comparisons (players change annually)

5. **Season Awards**: Not in v1
   - Focus on core facts (standings, challenges, playoffs, championship)
   - Awards can be Phase 2 enhancement if desired

## Timeline

- **Spec Review**: Dec 29, 2024
- **Implementation**: 12-17 hours (spread over multiple days)
- **Testing**: With complete 2024 season data
- **Production Ready**: Early January 2025

## Status

**Status**: ✅ **Approved** (Dec 29, 2024) - Ready for implementation

**Next Steps**:
1. Hand off to modern-architect-engineer agent for implementation
2. Follow 7-phase plan (12-17 hours estimated)
3. Test with real season data after championship week
4. Deploy for 2024 season recap

See [spec.md](./spec.md) for full technical specification.
