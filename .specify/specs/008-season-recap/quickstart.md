# Season Recap Script - Quickstart Guide

## What is this?

The **Season Recap Script** generates a comprehensive end-of-season summary that brings together:
- Regular season results (best teams, final standings)
- All 5 season challenge winners
- Playoff results (semifinals and finals)
- Championship week results (overall champion)

## When to use this

**After Week 17 completes** - This is your season capstone report. Run it once after the championship week to generate a polished summary you can share with league members.

## Quick Start

### 1. Basic Usage (Current Season)

```bash
# Generate console output for current season
uv run ff-season-recap --env --private
```

This will:
- Auto-detect the current season year
- Fetch all data from ESPN API
- Generate a formatted console report

### 2. Generate All Formats

```bash
# Create all 5 formats at once
uv run ff-season-recap --env --private --output-dir ./season-recap
```

This creates:
- `season-recap.txt` - Console format
- `season-recap.tsv` - Sheets format
- `season-recap.html` - Email format
- `season-recap.json` - JSON format
- `season-recap.md` - Markdown format

### 3. Email Format with Custom Note

```bash
# Generate mobile-friendly HTML with a note
uv run ff-season-recap --env --private --format email \
  --format-arg note="Thanks for an amazing 2024 season! See you next year! 🏈"
```

### 4. Previous Season

```bash
# Generate recap for 2023 season
uv run ff-season-recap --env --private --year 2023 --output-dir ./2023-recap
```

### 5. Testing with Incomplete Season

```bash
# Force generation even if Week 17 hasn't completed
uv run ff-season-recap --env --private --force
```

⚠️ **Note**: This will show warnings about missing data but still generate what it can.

## Common Use Cases

### Share via Email
```bash
# Generate HTML and send to league members
uv run ff-season-recap --env --private --format email \
  --format-arg note="Congratulations to our 2024 champion!" \
  > season-recap.html

# Then email the HTML file or copy/paste into email client
```

### Post to Slack/Discord
```bash
# Generate Markdown format
uv run ff-season-recap --env --private --format markdown > season-recap.md

# Copy contents and paste into Slack/Discord channel
```

### Archive for Records
```bash
# Generate JSON for data preservation
uv run ff-season-recap --env --private --year 2024 --format json \
  > archives/2024-season-recap.json

# Keep these JSON files year over year for historical analysis
```

### Import to Google Sheets
```bash
# Generate TSV format
uv run ff-season-recap --env --private --format sheets > season-recap.tsv

# Open Google Sheets, File → Import → Upload tab
# Select the TSV file and import
```

## Command-Line Arguments

### Required
- `--env` - Load league IDs from environment variable
- `--private` - Use ESPN authentication for private leagues

### Optional
- `--year YYYY` - Specify season year (default: current year)
- `--format FORMAT` - Output format: console, sheets, email, json, markdown
- `--output-dir PATH` - Generate all formats to directory
- `--format-arg KEY=VALUE` - Pass arguments to formatters
  - `note="Message"` - Add custom note to all formats
  - `email.accent_color="#007bff"` - Customize email color
  - `markdown.include_toc=true` - Add table of contents
  - `json.pretty=true` - Pretty-print JSON
- `--force` - Generate recap even if season incomplete (testing)

## Configuration

Set environment variables in `.env` file:

```bash
# Required: Your league IDs (comma-separated)
LEAGUE_IDS=123456789,987654321,555444333

# Required for private leagues:
ESPN_S2=your_espn_s2_cookie_here
SWID=your_swid_cookie_here
```

## Output Examples

### Console Format Preview
```
================================================================================
                        🏆 2024 SEASON RECAP 🏆
================================================================================

📅 REGULAR SEASON (Weeks 1-14)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Division Champions (Best Record)
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Division           ┃ Team             ┃ Owner  ┃ Record      ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━┩
│ Rough Street       │ Ja'marr Wars     │ Brian  │ 10-4 (🏆#1) │
│ Block Party        │ Miller Time 🍻   │ Mike   │ 9-5 (🏆#1)  │
│ Road Reptiles      │ Billieve Champ   │ Eric   │ 11-3 (🏆#1) │
└────────────────────┴──────────────────┴────────┴─────────────┘

🏅 SEASON CHALLENGE WINNERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Most Points Overall
   Winner: Ja'marr Wars (Brian Fox) - Rough Street
   Total: 1,842.52 points

[... more challenges ...]

🏈 PLAYOFFS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Week 15 - Semifinals
[... playoff brackets ...]

Week 16 - Finals
[... finals results ...]

🥇 CHAMPIONSHIP WEEK (Week 17)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 OVERALL CHAMPION: Billieve the Champ Is Back (eric barnum)
   Road Reptiles League Division Winner
   Championship Score: 162.06 points
   Margin of Victory: 3.66 points
```

### JSON Format Preview
```json
{
  "version": "1.0",
  "year": 2024,
  "generated_at": "2024-12-29T18:30:00Z",
  "metadata": {
    "divisions": ["Rough Street", "Block Party", "Road Reptiles"],
    "total_teams": 30
  },
  "regular_season": {
    "weeks": [1, 14],
    "division_champions": [...]
  },
  "season_challenges": [...],
  "playoffs": {
    "semifinals": [...],
    "finals": [...]
  },
  "championship": {
    "champion": {...},
    "margin": 3.66
  }
}
```

## Troubleshooting

### "Season incomplete" Error
**Problem**: Week 17 hasn't happened yet or data is missing

**Solution**: 
- Wait for Week 17 to complete
- OR use `--force` flag for testing: `uv run ff-season-recap --env --force`

### "League not found" Error
**Problem**: LEAGUE_IDS not set or incorrect

**Solution**:
```bash
# Check your .env file
cat .env | grep LEAGUE_IDS

# Should show:
# LEAGUE_IDS=123456789,987654321,555444333
```

### "Authentication failed" Error
**Problem**: Private league credentials invalid or missing

**Solution**:
```bash
# Check your ESPN cookies are set
cat .env | grep ESPN_S2
cat .env | grep SWID

# Get fresh cookies from ESPN website if needed
```

### Data Doesn't Match Other Reports
**Problem**: Recap shows different numbers than weekly/championship reports

**Solution**:
- This should NEVER happen - it's a bug
- Recap reuses the same calculation services as other scripts
- Please report with specifics (which numbers differ)

## Tips & Best Practices

### 1. Archive Every Year
```bash
# Create yearly archives
mkdir -p archives/2024
uv run ff-season-recap --env --private --year 2024 \
  --output-dir archives/2024
```

### 2. Share via Email
- Use `--format email` for mobile-friendly HTML
- Add a personalized note with `--format-arg note="..."`
- Email HTML works great in Gmail, Outlook, Apple Mail

### 3. Post to Slack/Discord
- Use `--format markdown` for clean, formatted text
- Markdown renders beautifully in both platforms
- Can also use `--format console` and wrap in code blocks

### 4. Import to Sheets for Analysis
- Use `--format sheets` for TSV output
- Import to Google Sheets for further analysis
- Add your own charts, calculations, notes

### 5. Keep JSON for Historical Tracking
- JSON format preserves ALL data
- Future versions may support year-over-year comparisons
- Great for building your own analytics

## Next Steps

1. **Run it!** - Generate your first season recap after Week 17
2. **Share it** - Send to league members via email or Slack
3. **Archive it** - Save the JSON for future reference
4. **Feedback** - Let us know what features you'd like in Phase 2!

## Getting Help

- **Spec Documentation**: See `spec.md` for full technical details
- **GitHub Issues**: Report bugs or request features
- **Constitution**: Check project principles in `.specify/memory/constitution.md`

---

**Ready to recap your season? Run your first report!** 🏆
