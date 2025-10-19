# Fantasy Football Challenge Tracker

A modern, type-safe command-line tool to analyze ESPN Fantasy Football leagues and track 5 specific season challenges across single leagues or multiple divisions.

**New in v2.0**: Complete rewrite with modern Python patterns, modular architecture, comprehensive type safety, and improved error handling.

## Table of Contents

- [Fantasy Football Challenge Tracker](#fantasy-football-challenge-tracker)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Examples](#examples)
  - [Configuration](#configuration)
  - [Sample Output](#sample-output)
  - [The 5 Season Challenges](#the-5-season-challenges)
  - [Requirements](#requirements)
  - [Google Sheets Export](#google-sheets-export)
  - [Automated Weekly Reports (GitHub Actions)](#automated-weekly-reports-github-actions)
  - [Contributing](#contributing)
  - [License](#license)

## Features

- **🏆 5 Season Challenges**: Track Most Points Overall, Most Points in One Game, Most Points in a Loss, Least Points in a Win, and Closest Victory
- **🏢 Multi-Division Support**: Analyze multiple leagues as divisions with overall rankings
- **🔒 Private League Support**: Works with both public and private ESPN leagues
- **📊 Multiple Output Formats**: Console tables, Google Sheets TSV, and mobile-friendly HTML email
- **🛡️ Type Safety**: Comprehensive type annotations with modern Python syntax
- **⚡ Fast Error Handling**: Fail-fast approach with clear error messages
- **🏗️ Modular Architecture**: Clean separation of concerns for easy maintenance and extension
- **📱 Mobile-Friendly**: HTML email format optimized for mobile devices

## Installation

### Quick Start with uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast, modern Python package manager that handles virtual environments automatically.

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

# Single private league
uv run ff-tracker <league_id> --private

# Specific year
uv run ff-tracker <league_id> --year 2023

# Different output format
uv run ff-tracker <league_id> --format sheets
```

### Output Formats

The new modular architecture supports multiple output formats:

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
```

## Examples

```bash
# Basic single league analysis
uv run ff-tracker 123456

# Private league with specific year
uv run ff-tracker 123456 --private --year 2024

# Generate Google Sheets compatible output
uv run ff-tracker 123456 --format sheets > weekly_report.tsv

# Create HTML email report
uv run ff-tracker 123456 --format email > email_report.html

# Multiple leagues (requires .env setup - see Configuration)
# Note: Multi-league support requires configuration file setup
```

## Configuration

### Multi-Division Setup (.env file)

For analyzing multiple leagues as divisions, create a `.env` file:

```bash
# Copy the example
cp .env.example .env
```

Example `.env` content:
```env
# Multiple league IDs (comma-separated)
LEAGUE_IDS=123456789,987654321,555444333

# Private league authentication (if needed)
ESPN_S2=your_espn_s2_cookie_here
SWID=your_swid_value_here
```

**Example**: Analyze multiple leagues as divisions:
```bash
uv run ff-tracker --env --format console   # Console output for all leagues
uv run ff-tracker --env --format sheets    # TSV output for Google Sheets
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
│    1 │ Lightning Bolts     │ Team Owner A │     1267.0 │          1098.4 │ 8-2    │
│    2 │ Thunder Hawks       │ Team Owner B │     1199.3 │          1156.7 │ 7-3    │
│    3 │ Fire Dragons        │ Team Owner C │     1156.8 │          1201.2 │ 6-4    │
╰──────┴─────────────────────┴──────────────┴────────────┴─────────────────┴────────╯

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
Rank	Team	Owner	Points For	Points Against	Record
1	Lightning Bolts	Team Owner A	1267.0	1098.4	8-2
2	Thunder Hawks	Team Owner B	1199.3	1156.7	7-3
3	Fire Dragons	Team Owner C	1156.8	1201.2	6-4

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
          "owner": "Team Owner A",
          "points_for": 799.28,
          "points_against": 716.78,
          "wins": 4,
          "losses": 2
        },
        {
          "name": "Thunder Hawks",
          "owner": "Team Owner B",
          "points_for": 847.78,
          "points_against": 830.22,
          "wins": 3,
          "losses": 3
        },
        {
          "name": "Fire Dragons",
          "owner": "Team Owner C",
          "points_for": 675.84,
          "points_against": 805.34,
          "wins": 3,
          "losses": 3
        },
        {
          "name": "Storm Chasers",
          "owner": "Team Owner D",
          "points_for": 640.6,
          "points_against": 757.46,
          "wins": 2,
          "losses": 4
        },
        {
          "name": "Ice Wolves",
          "owner": "Team Owner E",
          "points_for": 780.16,
          "points_against": 718.3,
          "wins": 3,
          "losses": 3
        },
        {
          "name": "Steel Panthers",
          "owner": "Team Owner F",
          "points_for": 817.86,
          "points_against": 773.24,
          "wins": 3,
          "losses": 3
        },
        {
          "name": "Cosmic Eagles",
          "owner": "Team Owner G",
          "points_for": 784.98,
          "points_against": 838.94,
          "wins": 2,
          "losses": 4
        },
        {
          "name": "Shadow Hunters",
          "owner": "Team Owner H",
          "points_for": 776.5,
          "points_against": 810.46,
          "wins": 3,
          "losses": 3
        },
        {
          "name": "Flame Riders",
          "owner": "Team Owner I",
          "points_for": 785.4,
          "points_against": 760.6,
          "wins": 2,
          "losses": 4
        },
        {
          "name": "Victory Seekers",
          "owner": "Team Owner J",
          "points_for": 867.02,
          "points_against": 764.08,
          "wins": 5,
          "losses": 1
        }
      ]
    }
  ],
  "challenges": [
    {
      "name": "Most Points Overall",
      "winner": "Victory Seekers",
      "owner": "Team Owner J",
      "division": "Example Fantasy League Division",
      "description": "867.0 total points"
    },
    {
      "name": "Most Points in One Game",
      "winner": "Flame Riders",
      "owner": "Team Owner I",
      "division": "Example Fantasy League Division",
      "description": "186.5 points (Week 2)"
    },
    {
      "name": "Most Points in a Loss",
      "winner": "Cosmic Eagles",
      "owner": "Team Owner G",
      "division": "Example Fantasy League Division",
      "description": "157.6 points in loss (Week 5)"
    },
    {
      "name": "Least Points in a Win",
      "winner": "Steel Panthers",
      "owner": "Team Owner F",
      "division": "Example Fantasy League Division",
      "description": "67.8 points in win (Week 7)"
    },
    {
      "name": "Closest Victory",
      "winner": "Shadow Hunters",
      "owner": "Team Owner H",
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

## Requirements

- Python 3.9+
- ESPN Fantasy Football league (public or private access)
- Internet connection for API access

## Google Sheets Export

The tool supports exporting results in a format that can be easily copied into Google Sheets:

**Console Output (for copy-paste):**
```bash
uv run ff-tracker 123456789 --format sheets        # Single league
uv run ff-tracker --env --format sheets            # Multiple leagues
```

**File Output (save to file first):**
```bash
uv run ff-tracker 123456789 --format sheets > results.tsv
uv run ff-tracker --env --format sheets > multi_results.tsv
```

The output uses tab-separated values (TSV) format which Google Sheets automatically recognizes when pasting. Simply copy the output and paste it directly into a Google Sheets document.

## Automated Weekly Reports (GitHub Actions)

This repository includes a GitHub Actions workflow that automatically generates and emails weekly fantasy football reports every Tuesday at 9 AM ET.

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

### What Gets Emailed

The automated email includes:
- **Subject**: "Weekly Fantasy Football Report - Week [X]"
- **Body**:
  - Beautiful HTML formatting with the complete report
  - All standings tables and challenge results
  - Easy-to-read monospace formatting

### Customizing the Schedule

To change when reports are sent, edit `.github/workflows/weekly-report.yml` and modify the cron schedule:
```yaml
# Currently: Tuesdays at 9 AM ET (13:00 UTC)
- cron: '0 13 * * 2'

# Examples:
# Mondays at 8 AM ET: '0 12 * * 1'
# Fridays at 5 PM ET: '0 21 * * 5'
```

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool!

## License

This project is open source. Use it to make your fantasy football leagues more fun!