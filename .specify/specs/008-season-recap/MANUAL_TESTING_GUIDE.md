# Manual Testing Guide for Season Recap Feature

## Prerequisites

1. **Navigate to project directory:**
   ```bash
   cd /Users/shaun.burdick/github/shaunburdick/ff-awards
   ```

2. **Ensure you're on the correct branch:**
   ```bash
   git branch --show-current
   # Should show: 008-season-recap
   ```

3. **Verify environment is set up:**
   ```bash
   # Check if LEAGUE_IDS is set
   echo $LEAGUE_IDS
   # Should show: 1499701648,688779743,1324184869 (or your league IDs)
   ```

---

## Quick Start: Basic Tests

### Test 1: Simple Console Output

**What it does:** Generates a text-based season recap in your terminal

```bash
uv run ff-season-recap --env --force --format console
```

**What to look for:**
- Beautiful ASCII tables with borders
- Championship week section (if available)
- Playoff brackets (Semifinals and Finals)
- Division champions table
- Season-long challenges
- Final standings for each division
- Emojis (🏆, ✅) in output

**Sample output you should see:**
```
╒═══════════════════════════════════════════════════════════════════╕
│                   🏆 2025 SEASON RECAP                            │
╘═══════════════════════════════════════════════════════════════════╛

Divisions: 3
Regular Season: Weeks 1-14
Playoffs: Weeks 15-16
...
```

---

### Test 2: Generate All Formats at Once

**What it does:** Creates 5 different format files in one command

```bash
# Clean slate - remove old test directory
rm -rf ./my-season-recap

# Generate all 5 formats
uv run ff-season-recap --env --force --output-dir ./my-season-recap
```

**What to look for:**
```
📁 Multi-output mode: Writing all formats to my-season-recap
   ✅ Generated console: my-season-recap/season-recap.txt
   ✅ Generated json: my-season-recap/season-recap.json
   ✅ Generated sheets: my-season-recap/season-recap.tsv
   ✅ Generated markdown: my-season-recap/season-recap.md
   ✅ Generated email: my-season-recap/season-recap.html
```

**Verify files were created:**
```bash
ls -lh ./my-season-recap/
```

**Expected output:**
```
-rw-r--r--  season-recap.html   (~22 KB)
-rw-r--r--  season-recap.json   (~18 KB)
-rw-r--r--  season-recap.md     (~5 KB)
-rw-r--r--  season-recap.tsv    (~4 KB)
-rw-r--r--  season-recap.txt    (~7 KB)
```

---

## Detailed Format Testing

### Test 3: View Each Format Individually

#### 3a. Console Format (Terminal)
```bash
uv run ff-season-recap --env --force --format console | less
```
- Press `SPACE` to scroll down
- Press `q` to quit
- Look for table borders, emojis, clean alignment

#### 3b. JSON Format (Structured Data)
```bash
uv run ff-season-recap --env --force --format json | head -30
```
**What to look for:**
```json
{
  "year": 2025,
  "is_complete": false,
  "total_divisions": 3,
  "season_structure": {
    "regular_season_start": 1,
    "regular_season_end": 14,
    "playoff_start": 15,
    "playoff_end": 16,
    "championship_week": 17
  },
  ...
}
```

#### 3c. Markdown Format (GitHub/Slack)
```bash
uv run ff-season-recap --env --force --format markdown | head -30
```
**What to look for:**
```markdown
# 🏆 2025 Season Recap

**Divisions:** 3
**Regular Season:** Weeks 1-14
**Playoffs:** Weeks 15-16

## Playoff Results

### Semifinals - Week 15
...
```

#### 3d. Sheets/TSV Format (Google Sheets)
```bash
uv run ff-season-recap --env --force --format sheets | head -20
```
**What to look for:**
```
SEASON RECAP	2025
Divisions	3
Regular Season	Weeks 1-14
Playoffs	Weeks 15-16

SEMIFINALS	Week 15
Division	MM 2025 - Road Repo Division
...
```

#### 3e. Email/HTML Format (Email Preview)
```bash
# Save to file
uv run ff-season-recap --env --force --format email > my-recap.html

# Open in browser (macOS)
open my-recap.html

# Or on Linux
xdg-open my-recap.html
```
**What to look for in browser:**
- Mobile-friendly responsive design
- Championship box with gradient background (pink/purple)
- Playoff brackets with green highlighting for winners
- Tables with alternating row colors
- Proper spacing and fonts

---

## Testing Format Arguments

### Test 4: Add a Custom Note

**Console with note:**
```bash
uv run ff-season-recap --env --force --format console \
  --format-arg note="This is the official 2025 season recap!"
```
**Look for:** A fancy table at the top with your note

**Email with note:**
```bash
uv run ff-season-recap --env --force --format email \
  --format-arg note="Final season standings!" > recap-with-note.html

open recap-with-note.html
```
**Look for:** A purple gradient box at the top with your note

**Markdown with note:**
```bash
uv run ff-season-recap --env --force --format markdown \
  --format-arg note="Season complete!" | head -10
```
**Look for:** A blockquote (>) with your note

---

### Test 5: Customize Email Colors

```bash
uv run ff-season-recap --env --force --format email \
  --format-arg note="Custom styled recap" \
  --format-arg email.accent_color="#ff0000" > red-recap.html

open red-recap.html
```
**Look for:** 
- Red border on the left side of season highlight sections
- Note box at top
- Championship box (if available)

**Try different colors:**
```bash
# Blue accent
--format-arg email.accent_color="#0066cc"

# Green accent
--format-arg email.accent_color="#28a745"

# Gold accent (default)
--format-arg email.accent_color="#ffc107"
```

---

### Test 6: Markdown Table of Contents

```bash
uv run ff-season-recap --env --force --format markdown \
  --format-arg markdown.include_toc=true | head -40
```
**Look for:**
```markdown
# 🏆 2025 Season Recap

**Divisions:** 3
...

## Table of Contents

- [Playoff Results](#playoff-results)
- [Regular Season Results](#regular-season-results)
  - [Division Champions](#division-champions)
  - [Season-Long Challenges](#season-long-challenges)
  - [Final Standings](#final-standings)
```

---

### Test 7: JSON Minified vs Pretty

**Pretty (default):**
```bash
uv run ff-season-recap --env --force --format json | head -10
```
You'll see indented JSON:
```json
{
  "year": 2025,
  "is_complete": false,
  ...
}
```

**Minified:**
```bash
uv run ff-season-recap --env --force --format json \
  --format-arg json.pretty=false | head -1
```
You'll see one long line:
```json
{"year": 2025, "is_complete": false, "total_divisions": 3, ...
```

---

## Error Handling Tests

### Test 8: Missing --force Flag (Should Fail)

```bash
uv run ff-season-recap --env --format console
```
**Expected output:**
```
❌ Season incomplete: Currently in Finals (week 16). 
   Championship week is 17. Use --force to generate partial recap.
   Current week: 16, Championship week: 17
   Use --force to generate partial recap.
```
**Status:** This is CORRECT behavior - season isn't complete yet

---

### Test 9: Invalid League ID (Should Fail)

```bash
uv run ff-season-recap 999999999 --force --format console
```
**Expected output:**
```
❌ Error: Failed to generate season summary: 
   Failed to connect to league 999999999: League 999999999 does not exist
```
**Status:** This is CORRECT error handling

---

### Test 10: Missing Required Argument (Should Fail)

```bash
uv run ff-season-recap
```
**Expected output:**
```
error: Either provide league_ids or use --env flag
```
**Status:** Helpful error message ✅

---

## Content Verification Tests

### Test 11: Verify Playoff Data

```bash
uv run ff-season-recap --env --force --format console | grep -A 20 "SEMIFINALS"
```
**What to look for:**
- Week 15 header
- Division names
- Team matchups with seeds (#1, #2, #3, #4)
- Scores for each team
- Winner indicators (✅ checkmark)

**Sample output:**
```
SEMIFINALS - Week 15

MM 2025 - Road Repo Division
┌────────────────────────────────────┬─────────────┐
│ Team                               │ Score       │
├────────────────────────────────────┼─────────────┤
│ #1 ILikeTurtles                    │ 95.80       │
│ ✅ #4 Billieve the Champ Is Back   │ 153.26      │
...
```

---

### Test 12: Verify Division Champions

```bash
uv run ff-season-recap --env --force --format console | grep -A 10 "DIVISION CHAMPIONS"
```
**What to look for:**
- Table with Division, Team, Owner, Record, Points For
- Multiple divisions listed
- Win-Loss records (e.g., 10-4, 12-2)
- Points totals

---

### Test 13: Verify Season Challenges

```bash
uv run ff-season-recap --env --force --format console | grep -A 10 "SEASON-LONG CHALLENGES"
```
**What to look for:**
- 5 challenges listed:
  1. Most Points Overall
  2. Most Points in One Game
  3. Most Points in a Loss
  4. Least Points in a Win
  5. Closest Victory
- Winner names
- Division names
- Values/scores

---

## File Content Verification

### Test 14: Compare File Sizes

```bash
# Generate all formats
uv run ff-season-recap --env --force --output-dir ./test-verify

# Check sizes
ls -lh ./test-verify/

# Show file sizes in a nice format
du -h ./test-verify/*
```

**Expected ranges:**
- TSV: 3-4 KB (most compact)
- Markdown: 4-5 KB
- Console: 7-8 KB
- JSON: 18-20 KB
- HTML: 20-25 KB (largest, includes styling)

---

### Test 15: Open HTML in Browser and Check Features

```bash
# Generate HTML
uv run ff-season-recap --env --force --format email \
  --format-arg note="Browser Test" \
  --format-arg email.accent_color="#007bff" > browser-test.html

# Open in browser
open browser-test.html
```

**Checklist when viewing in browser:**
- [ ] Title shows "Season Recap 2025"
- [ ] Blue note box at top with "Browser Test"
- [ ] Playoff sections have light blue background
- [ ] Winner rows have green background
- [ ] Tables are readable with alternating row colors
- [ ] Mobile responsive (resize browser window to check)
- [ ] All text is readable (proper font sizes)
- [ ] No broken formatting or overlapping text

---

### Test 16: Import TSV into Google Sheets

```bash
# Generate TSV
uv run ff-season-recap --env --force --format sheets > season-recap.tsv

# View the raw TSV
cat season-recap.tsv | head -30
```

**To test in Google Sheets:**
1. Open Google Sheets in browser
2. Create new spreadsheet
3. File → Import → Upload
4. Select `season-recap.tsv`
5. Choose "Tab" as separator
6. Import

**Verify in Google Sheets:**
- Each section is clearly separated
- Columns align properly
- No data in wrong columns
- All emojis display correctly

---

### Test 17: Preview Markdown on GitHub

```bash
# Generate Markdown with TOC
uv run ff-season-recap --env --force --format markdown \
  --format-arg markdown.include_toc=true > SEASON-RECAP.md

# View in terminal
cat SEASON-RECAP.md
```

**To preview on GitHub:**
1. Copy contents of SEASON-RECAP.md
2. Go to any GitHub repo (or create gist)
3. Create new file or edit existing .md file
4. Paste content
5. Click "Preview" tab

**Verify on GitHub:**
- Table of contents has working anchor links
- Tables render correctly
- Emojis display
- Hierarchy is clear (H1, H2, H3)

---

## Performance Testing

### Test 18: Measure Execution Time

```bash
time uv run ff-season-recap --env --force --format console > /dev/null
```

**Expected time:** 20-40 seconds (includes ESPN API calls)

**Breakdown:**
- API calls: ~15-30 seconds (network dependent)
- Processing: ~2-5 seconds
- Formatting: <1 second

---

### Test 19: Test Multi-Output Efficiency

```bash
# Single format (3 separate calls)
time uv run ff-season-recap --env --force --format console > test1.txt
time uv run ff-season-recap --env --force --format json > test2.json
time uv run ff-season-recap --env --force --format sheets > test3.tsv

# Multi-output (1 call)
time uv run ff-season-recap --env --force --output-dir ./test-multi
```

**Expected:** Multi-output should be ~3x faster than running 3 separate commands

---

## Real-World Usage Scenarios

### Test 20: End of Season Workflow

**Scenario:** Championship week just finished, generate final recap

```bash
# Step 1: Try without --force (should work if week 17 is complete)
uv run ff-season-recap --env --format console

# Step 2: Generate all formats for distribution
uv run ff-season-recap --env --output-dir ./final-2025-season

# Step 3: Generate custom email for league members
uv run ff-season-recap --env --format email \
  --format-arg note="Congratulations on a great season! See you next year!" \
  --format-arg email.accent_color="#ffd700" > season-finale-email.html

# Step 4: Open email to review before sending
open season-finale-email.html
```

---

### Test 21: Mid-Season Preview

**Scenario:** Playoffs have started, want to see current standings

```bash
# Generate partial recap during playoffs
uv run ff-season-recap --env --force --format markdown \
  --format-arg note="Mid-season update: Playoffs in progress!" \
  --format-arg markdown.include_toc=true > playoff-update.md

# View in terminal
cat playoff-update.md
```

---

### Test 22: Archival/Record Keeping

**Scenario:** Keep JSON record for historical analysis

```bash
# Generate compact JSON for archival
uv run ff-season-recap --env --force --format json \
  --format-arg json.pretty=false > archives/season-2025.json

# Verify it's valid JSON
cat archives/season-2025.json | jq '.year'
# Should output: 2025
```

---

## Troubleshooting Common Issues

### Issue 1: "Command not found: ff-season-recap"

**Fix:**
```bash
# Make sure you're in the project directory
cd /Users/shaun.burdick/github/shaunburdick/ff-awards

# Use uv run prefix
uv run ff-season-recap --help
```

---

### Issue 2: "LEAGUE_IDS not set"

**Fix:**
```bash
# Check if variable is set
echo $LEAGUE_IDS

# If empty, set it
export LEAGUE_IDS=1499701648,688779743,1324184869

# Or use explicit league IDs
uv run ff-season-recap 1499701648,688779743,1324184869 --force --format console
```

---

### Issue 3: "ESPN API connection failed"

**Possible causes:**
- Network connection issues
- Invalid league ID
- League is private (need --private flag)

**Fix for private leagues:**
```bash
# Make sure ESPN_S2 and SWID are set
echo $ESPN_S2
echo $SWID

# Add --private flag
uv run ff-season-recap --env --private --force --format console
```

---

### Issue 4: Output looks weird in terminal

**Fix:**
```bash
# Make sure terminal supports UTF-8
echo $LANG
# Should include UTF-8

# If using less, use -R flag for color
uv run ff-season-recap --env --force --format console | less -R

# Or redirect to file and view with proper editor
uv run ff-season-recap --env --force --format console > recap.txt
cat recap.txt
```

---

## Quick Command Reference

```bash
# Basic usage
uv run ff-season-recap --env --force --format console

# All formats at once
uv run ff-season-recap --env --force --output-dir ./output

# With custom note
uv run ff-season-recap --env --force --format email \
  --format-arg note="Your message here"

# Custom email colors
uv run ff-season-recap --env --force --format email \
  --format-arg email.accent_color="#ff0000"

# Markdown with TOC
uv run ff-season-recap --env --force --format markdown \
  --format-arg markdown.include_toc=true

# Minified JSON
uv run ff-season-recap --env --force --format json \
  --format-arg json.pretty=false

# Specific year
uv run ff-season-recap --env --force --year 2024 --format console

# Help
uv run ff-season-recap --help
```

---

## Expected Behavior Summary

✅ **With --force flag:** Generates partial recap (current state)
❌ **Without --force flag:** Fails with helpful error (season incomplete)
✅ **Multi-output mode:** Creates 5 files in one run
✅ **Format arguments:** Customize output per formatter
✅ **Error messages:** Clear guidance on what went wrong
✅ **All formats:** Produce professional, well-formatted output

---

## Next Steps After Manual Testing

Once you've verified everything works:

1. **Generate final test outputs for review:**
   ```bash
   uv run ff-season-recap --env --force --output-dir ./final-test
   ```

2. **Check all 5 files look good:**
   ```bash
   ls -lh ./final-test/
   cat ./final-test/season-recap.txt
   open ./final-test/season-recap.html
   ```

3. **Ready to proceed to Phase 7 (Documentation)**

---

**Questions while testing?**
- Check `--help` for available options
- Review error messages carefully
- Compare your output to the examples above
- All test commands should work exactly as shown
