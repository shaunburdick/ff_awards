# Season Recap Script - Design Decisions

**Status**: ✅ Approved (Dec 29, 2024)  
**Spec Version**: 1.0

## Decision Summary

All open questions have been resolved through collaboration with the user. This document captures the key architectural decisions for the season recap script.

---

## 1. Season Structure Detection ✅

**Decision**: Fully dynamic detection from ESPN API (no hardcoded values)

**Implementation**:
```python
reg_season_end = league.settings.reg_season_count  # e.g., 14
playoff_start = reg_season_end + 1  # e.g., 15
playoff_end = league.finalScoringPeriod  # e.g., 16 (ESPN's last week)
championship_week = playoff_end + 1  # e.g., 17 (custom cross-division)
playoff_weeks = playoff_end - playoff_start + 1
playoff_rounds = playoff_weeks // league.settings.playoff_matchup_period_length
```

**Rationale**:
- Existing `ff-tracker` has battle-tested playoff detection logic
- Supports any league configuration (different playoff lengths, team counts)
- No assumptions about season structure
- Championship week is custom cross-division competition (not in ESPN)

**Key Properties**:
- ✅ No hardcoded week numbers
- ✅ No hardcoded playoff lengths
- ✅ Works with any ESPN league configuration
- ✅ Reuses proven detection logic

---

## 2. Incomplete Season Handling ✅

**Decision**: Flexible with `--force` flag for testing

**Normal Mode**:
```bash
uv run ff-season-recap --env
# Validates: Championship week has occurred and has game data
# Error: "Season incomplete: Championship week has not occurred yet. Use --force to generate partial recap."
```

**Force Mode**:
```bash
uv run ff-season-recap --env --force
# Generates: Whatever sections are available
# Output: Clear warnings about missing data sections
```

**Validation Logic**:
```python
available_sections = {
    "regular_season": current_week > reg_season_end,
    "playoffs": current_week > playoff_end,
    "championship": current_week > championship_week
}
```

**Rationale**:
- Need to test script before season ends (Dec 29, 2024)
- Useful for generating partial recaps if needed
- Clear warnings prevent confusion
- Normal mode protects against accidental incomplete reports

---

## 3. Division Names ✅

**Decision**: Hybrid approach - ESPN names with sensible fallback

**Implementation**:
```python
def get_division_name(league: League, index: int) -> str:
    """Use ESPN league name or fallback to positional naming."""
    return league.settings.name or f"Division {index + 1}"
```

**Examples**:
- ESPN has name: "Rough Street League" ✅
- ESPN no name: "Division 1" ✅
- Consistent across all three divisions

**Rationale**:
- Uses meaningful names when available
- Sensible defaults when ESPN data missing
- No additional configuration required
- Consistent with "detect what we can, sensible defaults" philosophy

---

## 4. Historical Persistence ✅

**Decision**: Multi-output mode saves files including JSON (no automatic archival)

**Single Format Mode** (outputs to stdout):
```bash
uv run ff-season-recap --env --format console
uv run ff-season-recap --env --format json > archive.json
```

**Multi-Output Mode** (creates files):
```bash
uv run ff-season-recap --env --output-dir ./season-recap
# Creates: season-recap.txt, .tsv, .html, .json, .md
```

**JSON for Archival**:
- User controls file creation via `--output-dir`
- JSON preserves complete season data
- No automatic directory creation or management
- Consistent with `ff-tracker` and `ff-championship` behavior

**Important Note**: No year-over-year comparisons planned
- Players change divisions/leagues annually
- Historical comparisons not meaningful
- JSON useful for record-keeping only

**Rationale**:
- Consistent with existing script patterns
- User has explicit control
- JSON naturally preserved when needed
- Simple and predictable

---

## 5. Season Awards ✅

**Decision**: Not included in v1 (focus on core facts)

**v1 Scope** (what's included):
- ✅ Regular season standings & division champions
- ✅ All 5 season challenge winners
- ✅ Playoff results (all rounds, all divisions)
- ✅ Championship results (overall winner)

**Out of Scope for v1**:
- ❌ Most Consistent (stddev calculations)
- ❌ Boom or Bust (stddev calculations)
- ❌ Best Playoff Run
- ❌ Heartbreaker / Lucky Winner
- ❌ Benchwarmer (bench points)

**Phase 2 Consideration**:
- Can add awards as enhancement if desired
- Would require additional calculations
- Not essential for season story

**Rationale**:
- Keep v1 focused and deliverable
- Core facts are most important
- Awards are nice-to-have, not essential
- Can iterate based on feedback
- Ship early, add features later

---

## Implementation Impact

These decisions affect the implementation in the following ways:

### Data Models
- `SeasonSummary` includes dynamic week ranges (not hardcoded)
- `SeasonStructure` helper class to encapsulate week calculations
- No award-related models in v1

### Service Layer
- `SeasonRecapService.calculate_season_structure()` - new method
- `SeasonRecapService.validate_season_complete()` - with force flag
- `SeasonRecapService.get_division_name()` - hybrid naming logic
- Reuses existing challenge/playoff/championship services

### CLI Interface
- `--force` flag for incomplete season testing
- `--output-dir` for multi-format output
- No `--save` or `--archive` flags
- No `--include-awards` flag

### Output Formats
- All show dynamic season structure (not "Weeks 1-14")
- Division names from hybrid logic
- JSON includes season structure metadata
- Warnings displayed for missing sections (with --force)

---

## Testing Implications

### Before Season Ends
```bash
# Test with --force flag
uv run ff-season-recap --env --force
# Should show regular season and playoffs (no championship)
```

### After Championship Week
```bash
# Normal operation (no --force needed)
uv run ff-season-recap --env --output-dir ./2024-recap
# Should generate complete recap with all sections
```

### Different League Configurations
- Test with league that has different playoff structure
- Verify dynamic detection works correctly
- Confirm no hardcoded assumptions break

---

## Success Criteria

The implementation will be considered successful if:

1. ✅ Season structure detected dynamically (verified with test leagues)
2. ✅ `--force` flag allows testing before season ends
3. ✅ Division names use ESPN or fallback correctly
4. ✅ Multi-output mode creates all 5 files including JSON
5. ✅ No season awards in output (keeping focused)
6. ✅ All data matches existing scripts exactly (accuracy check)
7. ✅ Clear warnings for missing data sections
8. ✅ Works with any ESPN league configuration

---

## Related Documents

- **Full Specification**: [spec.md](./spec.md)
- **Quick Reference**: [README.md](./README.md)
- **User Guide**: [quickstart.md](./quickstart.md)

---

**Approved By**: Shaun (User)  
**Date**: December 29, 2024  
**Ready for**: Implementation (Phase 1-7, estimated 12-17 hours)
