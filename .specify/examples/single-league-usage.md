# Example: Single League Analysis

This example demonstrates using FF-Awards to analyze a single ESPN Fantasy Football league.

## Scenario

You manage a 10-team fantasy football league (League ID: 123456) and want to see season challenge winners and current week highlights.

---

## Command Line Usage

### Basic Usage (Public League)

```bash
# Console output (default)
uv run ff-tracker 123456

# Specific year
uv run ff-tracker 123456 --year 2024

# Different output format
uv run ff-tracker 123456 --format json
```

### Private League

If your league requires authentication:

```bash
# Create .env file with credentials
cat > .env << EOF
ESPN_S2=your_espn_s2_cookie_here
SWID=your_swid_cookie_here
EOF

# Run with --private flag
uv run ff-tracker 123456 --private --format email
```

### Multi-Output Mode

Generate all formats at once:

```bash
uv run ff-tracker 123456 --output-dir ./reports

# Creates:
# - reports/standings.txt (console format)
# - reports/standings.tsv (sheets format)
# - reports/standings.html (email format)
# - reports/standings.json (json format)
# - reports/standings.md (markdown format)
```

### With Format Arguments

Add a note or customize output:

```bash
# Add a note for all formats
uv run ff-tracker 123456 --format-arg note="Playoffs start next week!"

# Customize email appearance
uv run ff-tracker 123456 --format email \
  --format-arg email.accent_color="#ff0000" \
  --format-arg email.max_teams=5

# Pretty JSON output
uv run ff-tracker 123456 --format json \
  --format-arg json.pretty=true
```

---

## Expected Output Structure

### Console Format

```
Fantasy Football Challenge Tracker - 2024 Season

══════════════════════════════════════════════════════════════════════════
                        SEASON CHALLENGES
══════════════════════════════════════════════════════════════════════════

Challenge: Most Points Overall
Winner: Team Phoenix (Sarah Johnson)
Score: 1,456.78 points
Division: Main League

Challenge: Most Points in One Game
Winner: Team Thunder (Mike Davis)
Score: 178.92 points
Week 7 vs Team Lightning
Division: Main League

[... more challenges ...]

══════════════════════════════════════════════════════════════════════════
                    WEEKLY HIGHLIGHTS - WEEK 12
══════════════════════════════════════════════════════════════════════════

TEAM CHALLENGES
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Challenge             ┃ Winner             ┃ Score    ┃ Details     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Highest Score         │ Team Phoenix       │ 156.78   │             │
│                       │ (Sarah Johnson)    │          │             │
├───────────────────────┼────────────────────┼──────────┼─────────────┤
│ Biggest Win           │ Team Thunder       │          │ 148.92 -    │
│                       │ (Mike Davis)       │          │ 89.45       │
│                       │                    │          │ (Δ59.47)    │
[... more challenges ...]
└───────────────────────┴────────────────────┴──────────┴─────────────┘

PLAYER HIGHLIGHTS
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Position          ┃ Player              ┃ Points ┃ Team           ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ Top Scorer        │ Patrick Mahomes     │ 38.5   │ Team Phoenix   │
├───────────────────┼─────────────────────┼────────┼────────────────┤
│ Best QB           │ Patrick Mahomes     │ 38.5   │ Team Phoenix   │
[... more highlights ...]
└───────────────────┴─────────────────────┴────────┴────────────────┘

══════════════════════════════════════════════════════════════════════════
                        LEAGUE STANDINGS
══════════════════════════════════════════════════════════════════════════

Division: Main League

Team Name               Owner           W-L      Points For    Points Against
─────────────────────────────────────────────────────────────────────────────
* Team Phoenix          Sarah Johnson   10-2     1,456.78      1,234.56
* Team Thunder          Mike Davis      9-3      1,398.45      1,289.90
[... more teams ...]

* = In playoff position (Top 4)
```

### JSON Format

```json
{
  "metadata": {
    "year": 2024,
    "generated_at": "2024-11-14T14:00:00Z",
    "current_week": 12,
    "note": "Playoffs start next week!"
  },
  "divisions": [
    {
      "name": "Main League",
      "teams": [
        {
          "name": "Team Phoenix",
          "owner": {
            "name": "Sarah Johnson",
            "id": "user123"
          },
          "wins": 10,
          "losses": 2,
          "points_for": 1456.78,
          "points_against": 1234.56,
          "in_playoff_position": true
        }
      ]
    }
  ],
  "season_challenges": [
    {
      "challenge_name": "Most Points Overall",
      "team_name": "Team Phoenix",
      "owner": {
        "name": "Sarah Johnson",
        "id": "user123"
      },
      "score": 1456.78,
      "additional_info": {
        "division": "Main League"
      }
    }
  ],
  "weekly_challenges": [
    {
      "challenge_name": "Highest Score This Week",
      "challenge_type": "team",
      "team_name": "Team Phoenix",
      "owner": {
        "name": "Sarah Johnson",
        "id": "user123"
      },
      "score": 156.78,
      "additional_info": {
        "week": 12
      }
    }
  ]
}
```

---

## Common Use Cases

### 1. Quick Check During Season

```bash
# Fast console output to see current standings
uv run ff-tracker 123456
```

### 2. Weekly Email Report

```bash
# Generate HTML for email
uv run ff-tracker 123456 --private --format email > weekly-report.html

# Or save to file
uv run ff-tracker 123456 --private --output-dir ./reports
# Email reports/standings.html
```

### 3. Data Export for Analysis

```bash
# JSON for further processing
uv run ff-tracker 123456 --format json > league-data.json

# Process with jq
uv run ff-tracker 123456 --format json | jq '.season_challenges'
```

### 4. Share on Slack/Discord

```bash
# Markdown format for chat platforms
uv run ff-tracker 123456 --format markdown > league-update.md
# Copy and paste into Slack/Discord
```

---

## Troubleshooting

### "No league data found"
- Verify league ID is correct
- If private league, ensure you're using `--private` flag
- Check ESPN_S2 and SWID in .env file

### "Current week data unavailable"
- This is normal if week hasn't started yet
- Season challenges still work, weekly highlights will be empty

### "Rate limit exceeded"
- Wait a few minutes and try again
- ESPN API has rate limits; don't run too frequently

---

## Performance Notes

For a single 10-team league:
- **Execution Time**: < 2 seconds
- **API Calls**: 1 (all data fetched in single request)
- **Memory Usage**: < 50MB

---

## Next Steps

- See [multi-league-usage.md](./multi-league-usage.md) for handling multiple leagues
- See [format-arguments.md](./format-arguments.md) for customization options
- Check [expected-outputs/](./expected-outputs/) for sample outputs
