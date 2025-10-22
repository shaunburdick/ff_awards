# Fantasy Football Challenge Tracker

A modern, type-safe command-line tool to analyze ESPN Fantasy Football leagues and track 5 specific season challenges across single leagues or multiple divisions.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Configuration](#configuration)
- [Sample Output](#sample-output)
- [The 5 Season Challenges](#the-5-season-challenges)
- [Automated Weekly Reports (GitHub Actions)](#automated-weekly-reports-github-actions)
- [Contributing](#contributing)
- [License](#license)

## Features

- **5 Season Challenges**: Track Most Points Overall, Most Points in One Game, Most Points in a Loss, Least Points in a Win, and Closest Victory
- **Playoff Positioning**: Shows current playoff qualification (top 4 by record, points-for tiebreaker) with visual indicators
- **Multi-Division Support**: Analyze multiple leagues as divisions with overall rankings
- **Flexible League Input**: Pass league IDs via CLI (comma-separated), environment variable, or .env file
- **Private League Support**: Works with both public and private ESPN leagues
- **Multiple Output Formats**: Console tables, Google Sheets TSV, mobile-friendly HTML email, and JSON
- **Multi-Output Mode**: Generate all formats in one execution with `--output-dir`
- **Type Safety**: Comprehensive type annotations with modern Python syntax
- **Fast Error Handling**: Fail-fast approach with clear error messages
- **Modular Architecture**: Clean separation of concerns for easy maintenance and extension
- **Mobile-Friendly**: HTML email format optimized for mobile devices

## Installation

### Quick Start with uv

1. **Install uv**
   ```bash
   # macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Alternative: via pip/pipx (if you have them)
   pip install uv
   ```

2. **Clone and setup the project**
   ```bash
   git clone <repository-url>
   cd ff-awards

   # Install dependencies (creates virtual environment automatically)
   uv sync
   ```

3. **Run the new tracker**
   ```bash
   # Single league analysis
   uv run ff-tracker 123456

   # With specific year and format
   uv run ff-tracker 123456 --year 2024 --format email

   # Private league with HTML email output
   uv run ff-tracker 123456 --private --format email
   ```

### Authentication Setup

**For private leagues only**: Set up ESPN authentication
```bash
cp .env.example .env
# Edit .env with your ESPN credentials (see Configuration section below)
```

## Usage

### Basic Usage

```bash
# Single league (public)
uv run ff-tracker <league_id>

# Multiple leagues via CLI (comma-separated)
uv run ff-tracker <league_id1>,<league_id2>,<league_id3>

# Single private league
uv run ff-tracker <league_id> --private

# Specific year
uv run ff-tracker <league_id> --year 2023

# Different output format
uv run ff-tracker <league_id> --format sheets
```

### Output Formats

The script supports multiple output formats:

- **`console`** (default): Human-readable tables for terminal display
- **`sheets`**: Tab-separated values for easy import into Google Sheets
- **`email`**: Mobile-friendly HTML format perfect for email reports
- **`json`**: Structured JSON data for further processing

```bash
# Console output (default)
uv run ff-tracker 123456

# Google Sheets format
uv run ff-tracker 123456 --format sheets > results.tsv

# HTML email format
uv run ff-tracker 123456 --format email > report.html

# JSON data export
uv run ff-tracker 123456 --format json > data.json
```

### Multi-Output Mode

Generate all formats in a single execution with `--output-dir`:

```bash
# Generate all 4 formats at once (single ESPN API call)
uv run ff-tracker --env --output-dir ./reports

# Creates:
#   ./reports/standings.txt   (console format)
#   ./reports/standings.tsv   (sheets format)
#   ./reports/standings.html  (email format)
#   ./reports/standings.json  (json format)
```

## Examples

```bash
# Basic single league analysis
uv run ff-tracker 123456

# Multiple leagues via CLI (comma-separated)
uv run ff-tracker 123456789,987654321,678998765

# Multiple leagues with spaces (also supported)
uv run ff-tracker "123456, 789012, 345678"

# Private league with specific year
uv run ff-tracker 123456 --private --year 2024

# Multiple private leagues via CLI
uv run ff-tracker 123456789,987654321 --private --format email

# Generate Google Sheets compatible output
uv run ff-tracker 123456 --format sheets > weekly_report.tsv

# Create HTML email report
uv run ff-tracker 123456 --format email > email_report.html

# Generate all formats at once (recommended for automation)
uv run ff-tracker --env --private --output-dir ./reports

# Multiple leagues from environment variable (alternative to CLI)
uv run ff-tracker --env --format console
```

## Configuration

### Multiple League Input Options

There are three ways to provide league IDs:

1. **CLI Comma-Separated** (Quick and easy):
   ```bash
   uv run ff-tracker 123456789,987654321,678998765
   ```

2. **Environment Variable** (Using `--env` flag):
   ```bash
   # In .env file:
   LEAGUE_IDS=123456789,987654321,555444333

   # Then run:
   uv run ff-tracker --env
   ```

3. **Single League** (Simplest):
   ```bash
   uv run ff-tracker 123456
   ```

### ESPN Authentication (Private Leagues Only)

For private leagues, you need ESPN authentication cookies:

1. **Get your cookies**:
   - Log into ESPN Fantasy in your browser
   - Open Developer Tools (F12)
   - Go to Application/Storage > Cookies > espn.com
   - Find `espn_s2` and `SWID` values

2. **Add to .env file**:
   ```env
   ESPN_S2=your_very_long_espn_s2_cookie_value_here
   SWID={YOUR-SWID-VALUE-HERE}
   ```

3. **Use with --private flag**:
   ```bash
   uv run ff-tracker 123456 --private
   ```

## Sample Output

### Console Output

The default console format provides clean, readable tables:

```
Fantasy Football Multi-Division Challenge Tracker (2024)
1 divisions, 10 teams total

Sample Fantasy League STANDINGS
╭──────┬─────────────────────┬──────────────┬────────────┬─────────────────┬────────╮
│ Rank │ Team                │ Owner        │ Points For │ Points Against  │ Record │
├──────┼─────────────────────┼──────────────┼────────────┼─────────────────┼────────┤
│    1 │ * Lightning Bolts   │ Team Owner A │     1267.0 │          1098.4 │ 8-2    │
│    2 │ * Thunder Hawks     │ Team Owner B │     1199.3 │          1156.7 │ 7-3    │
│    3 │ * Fire Dragons      │ Team Owner C │     1156.8 │          1201.2 │ 6-4    │
│    4 │ * Storm Chasers     │ Team Owner D │     1134.2 │          1189.8 │ 6-4    │
│    5 │ Ice Wolves          │ Team Owner E │     1089.7 │          1145.3 │ 5-5    │
╰──────┴─────────────────────┴──────────────┴────────────┴─────────────────┴────────╯

📋 * = Currently in playoff position (Top 4 by record, points-for tiebreaker)

OVERALL SEASON CHALLENGES
╭─────────────────────────┬─────────────────┬──────────────┬───────────┬──────────────────────────╮
│ Challenge               │ Winner          │ Owner        │ Division  │ Details                  │
├─────────────────────────┼─────────────────┼──────────────┼───────────┼──────────────────────────┤
│ Most Points Overall     │ Lightning Bolts │ Team Owner A │ League    │ 1267.0 total points      │
│ Most Points in One Game │ Fire Dragons    │ Team Owner C │ League    │ 186.5 points (Week 2)    │
│ Most Points in a Loss   │ Storm Chasers   │ Team Owner D │ League    │ 173.4 points in loss     │
│ Least Points in a Win   │ Ice Wolves      │ Team Owner E │ League    │ 101.2 points in win      │
│ Closest Victory         │ Steel Panthers  │ Team Owner F │ League    │ Won by 0.4 points        │
╰─────────────────────────┴─────────────────┴──────────────┴───────────┴──────────────────────────╯

Game data: 50 individual results processed
```

### Google Sheets Format

Perfect for importing into spreadsheets (use `--format sheets`):

```
Fantasy Football Multi-Division Challenge Tracker (2024)
1 divisions, 10 teams total

Sample Fantasy League STANDINGS
Rank	Team	Owner	Points For	Points Against	Record	Playoffs
1	Lightning Bolts	Team Owner A	1267.0	1098.4	8-2	Y
2	Thunder Hawks	Team Owner B	1199.3	1156.7	7-3	Y
3	Fire Dragons	Team Owner C	1156.8	1201.2	6-4	Y
4	Storm Chasers	Team Owner D	1134.2	1189.8	6-4	Y
5	Ice Wolves	Team Owner E	1089.7	1145.3	5-5	N

OVERALL SEASON CHALLENGES
Challenge	Winner	Owner	Division	Details
Most Points Overall	Lightning Bolts	Team Owner A	League	1267.0 total points
Most Points in One Game	Fire Dragons	Team Owner C	League	186.5 points (Week 2)
Most Points in a Loss	Storm Chasers	Team Owner D	League	173.4 points in loss
Least Points in a Win	Ice Wolves	Team Owner E	League	101.2 points in win
Closest Victory	Steel Panthers	Team Owner F	League	Won by 0.4 points

Game data: 50 individual results processed
```

### Email HTML Format

Mobile-optimized HTML perfect for weekly email reports (use `--format email`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fantasy Football Challenge Tracker (2024)</title>
    <style>
        /* Mobile-friendly responsive styles */
        body { font-family: Arial, sans-serif; margin: 0; padding: 10px; }
        .container { max-width: 100%; background: white; padding: 15px; border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { padding: 6px 4px; border-bottom: 1px solid #ddd; }
        .winner { color: #27ae60; font-weight: bold; }
        /* More mobile-responsive styles... */
    </style>
</head>
<body>
    <div class="container">
        <h1>Fantasy Football Multi-Division Challenge Tracker (2024)</h1>
        <div class="summary">1 divisions • 10 teams total</div>
        <!-- Responsive tables with challenge results -->
    </div>
</body>
</html>
```

### JSON Format

Structured data format perfect for API integrations and custom processing (use `--format json`):

```json
{
  "current_week": 7,
  "divisions": [
    {
      "name": "Example Fantasy League Division",
      "league_id": 1234567890,
      "teams": [
        {
          "name": "Lightning Bolts",
          "owner": {
            "display_name": "fantasy_pro_2024",
            "first_name": "John",
            "last_name": "Smith",
            "full_name": "John Smith",
            "id": "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}",
            "is_likely_username": false
          },
          "points_for": 799.28,
          "points_against": 716.78,
          "wins": 4,
          "losses": 2,
          "in_playoff_position": true
        },
        {
          "name": "Thunder Hawks",
          "owner": {
            "display_name": "ESPNFAN12345678",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "full_name": "Sarah Johnson",
            "id": "{B2C3D4E5-F6G7-8901-BCDE-F23456789012}",
            "is_likely_username": true
          },
          "points_for": 847.78,
          "points_against": 830.22,
          "wins": 3,
          "losses": 3,
          "in_playoff_position": true
        },
        {
          "name": "Fire Dragons",
          "owner": {
            "display_name": "mike_fantasy",
            "first_name": "Michael",
            "last_name": "Davis",
            "full_name": "Michael Davis",
            "id": "{C3D4E5F6-G7H8-9012-CDEF-345678901234}",
            "is_likely_username": false
          },
          "points_for": 675.84,
          "points_against": 805.34,
          "wins": 3,
          "losses": 3,
          "in_playoff_position": false
        }
      ]
    }
  ],
  "challenges": [
    {
      "name": "Most Points Overall",
      "winner": "Victory Seekers",
      "owner": {
        "display_name": "lisa_champ",
        "first_name": "Lisa",
        "last_name": "Anderson",
        "full_name": "Lisa Anderson",
        "id": "{D4E5F6G7-H8I9-0123-DEFG-456789012345}",
        "is_likely_username": false
      },
      "division": "Example Fantasy League Division",
      "description": "867.0 total points"
    },
    {
      "name": "Most Points in One Game",
      "winner": "Flame Riders",
      "owner": {
        "display_name": "ESPNFAN87654321",
        "first_name": "Robert",
        "last_name": "Wilson",
        "full_name": "Robert Wilson",
        "id": "{E5F6G7H8-I9J0-1234-EFGH-567890123456}",
        "is_likely_username": true
      },
      "division": "Example Fantasy League Division",
      "description": "186.5 points (Week 2)"
    },
    {
      "name": "Most Points in a Loss",
      "winner": "Cosmic Eagles",
      "owner": {
        "display_name": "eagle_eye_99",
        "first_name": "Jennifer",
        "last_name": "Brown",
        "full_name": "Jennifer Brown",
        "id": "{F6G7H8I9-J0K1-2345-FGHI-678901234567}",
        "is_likely_username": false
      },
      "division": "Example Fantasy League Division",
      "description": "157.6 points in loss (Week 5)"
    },
    {
      "name": "Least Points in a Win",
      "winner": "Steel Panthers",
      "owner": {
        "display_name": "steel_defense",
        "first_name": "David",
        "last_name": "Miller",
        "full_name": "David Miller",
        "id": "{G7H8I9J0-K1L2-3456-GHIJ-789012345678}",
        "is_likely_username": false
      },
      "division": "Example Fantasy League Division",
      "description": "67.8 points in win (Week 7)"
    },
    {
      "name": "Closest Victory",
      "winner": "Shadow Hunters",
      "owner": {
        "display_name": "shadow_master",
        "first_name": "Amanda",
        "last_name": "Taylor",
        "full_name": "Amanda Taylor",
        "id": "{H8I9J0K1-L2M3-4567-HIJK-890123456789}",
        "is_likely_username": false
      },
      "division": "Example Fantasy League Division",
      "description": "Won by 0.4 points (Week 5)"
    }
  ]
}
```

## The 5 Season Challenges

1. **Most Points Overall** - Team with highest total regular season points
2. **Most Points in One Game** - Highest single week score across all teams
3. **Most Points in a Loss** - Highest score in a losing effort
4. **Least Points in a Win** - Lowest score that still won the matchup
5. **Closest Victory** - Smallest winning margin between two teams

**Challenge Rules:**
- Only regular season games count (playoffs excluded)
- Ties go to the first team to achieve the result
- If still tied after that, the award splits between tied teams

## Automated Weekly Reports (GitHub Actions)

This repository includes a GitHub Actions workflow that automatically generates and emails weekly fantasy football reports every Tuesday at 6 AM ET.

The workflow uses the `--output-dir` mode to generate all formats (console, TSV, HTML, JSON) in a single execution.

### Setup GitHub Actions Workflow

1. **Fork this repository** to your GitHub account

2. **Configure Repository Secrets** - Go to your repository's Settings → Secrets and variables → Actions, and add these secrets:

   **Required Secrets:**
   - `LEAGUE_IDS` - Comma-separated list of ESPN league IDs (e.g., `123456789,987654321,555444333`)
   - `SMTP_SERVER` - Your SMTP server (e.g., `mail.smtp2go.com`, `smtp.gmail.com`)
   - `SMTP_USERNAME` - Your SMTP username (email address for most providers)
   - `SMTP_PASSWORD` - Your SMTP password or app password
   - `EMAIL_FROM` - The "from" email address (must be verified with your SMTP provider)
   - `EMAIL_RECIPIENTS` - Comma-separated email addresses to receive reports (e.g., `friend1@email.com,friend2@email.com`)

   **Optional Secrets:**
   - `SMTP_PORT` - Your SMTP port (defaults to `587` if not set)
   - `ESPN_SWID` - Your ESPN SWID cookie for private leagues (e.g., `{12345678-1234-1234-1234-123456789ABC}`)
   - `ESPN_S2` - Your ESPN S2 cookie for private leagues (long string ending with `%3D`)

3. **Enable GitHub Actions** - The workflow will automatically run every Tuesday at 9 AM ET during fantasy football season

### Manual Trigger

You can also manually trigger the workflow:
1. Go to your repository's "Actions" tab
2. Select "Weekly Fantasy Football Report"
3. Click "Run workflow"

### Customizing the Schedule

To change when reports are sent, edit `.github/workflows/weekly-report.yml` and modify the cron schedule:
```yaml
# Currently: Tuesdays at 6 AM ET (10:00 UTC)
- cron: '0 10 * * 2'

# Examples:
# Mondays at 8 AM ET: '0 12 * * 1'
# Fridays at 5 PM ET: '0 21 * * 5'
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool!

## License

This project is open source. Use it to make your fantasy football leagues more fun!