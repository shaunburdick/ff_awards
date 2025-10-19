# Fantasy Football Challenge Tracker

A command-line tool to analyze ESPN Fantasy Football leagues and track 5 specific season challenges worth $30 each across single leagues or multiple divisions.

## Table of Contents

- [Fantasy Football Challenge Tracker](#fantasy-football-challenge-tracker)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Installation](#installation)
    - [Option 1: Modern Installation with uv (Recommended)](#option-1-modern-installation-with-uv-recommended)
    - [Option 2: Traditional Installation with Virtual Environment](#option-2-traditional-installation-with-virtual-environment)
    - [Authentication Setup (All Methods)](#authentication-setup-all-methods)
  - [Usage](#usage)
    - [League Analysis](#league-analysis)
  - [Examples](#examples)
  - [Configuration](#configuration)
    - [Multi-Division Setup (.env file)](#multi-division-setup-env-file)
    - [ESPN Authentication (Private Leagues Only)](#espn-authentication-private-leagues-only)
  - [Sample Output](#sample-output)
    - [Regular Console Output](#regular-console-output)
    - [Google Sheets Format (with --sheets flag)](#google-sheets-format-with---sheets-flag)
  - [The 5 Season Challenges ($30 Each)](#the-5-season-challenges-30-each)
  - [Requirements](#requirements)
  - [Google Sheets Export](#google-sheets-export)
  - [Automated Weekly Reports (GitHub Actions)](#automated-weekly-reports-github-actions)
    - [Setup GitHub Actions Workflow](#setup-github-actions-workflow)
    - [Manual Trigger](#manual-trigger)
    - [What Gets Emailed](#what-gets-emailed)
    - [Customizing the Schedule](#customizing-the-schedule)
  - [Dependencies](#dependencies)
  - [Contributing](#contributing)
  - [License](#license)

## Features

- **5 Season Challenges**: Track Most Points Overall, Most Points in One Game, Most Points in a Loss, Least Points in a Win, and Closest Victory
- **Multi-Division Support**: Analyze multiple leagues as divisions with overall rankings
- **Private League Support**: Works with both public and private ESPN leagues
- **Clean Table Output**: Well-formatted tables using tabulate library
- **Google Sheets Export**: Output results in tab-separated format for easy copy-paste into Google Sheets
- **Simple CLI**: Just pass in your league ID(s) and get instant results

## Installation

### Option 1: Modern Installation with uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast, modern Python package manager that handles virtual environments automatically.

1. **Install uv**
   ```bash
   # macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

   # Alternative: via pip/pipx (if you have them)
   pip install uv
   # or
   pipx install uv
   ```

2. **Clone and setup the project**
   ```bash
   git clone <repository-url>
   cd ff-awards

   # Install dependencies (creates virtual environment automatically)
   uv sync
   ```

3. **Run the tools**
   ```bash
   # uv automatically manages the virtual environment
   uv run ff-multi <league_id>         # Single league
   uv run ff-multi --env               # Multiple leagues from .env
   ```

### Option 2: Traditional Installation with Virtual Environment

If you prefer the traditional approach or can't install uv:

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ff-awards
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate it (macOS/Linux)
   source venv/bin/activate

   # Activate it (Windows)
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the tools**
   ```bash
   # Make sure virtual environment is activated first
   python ff_multi.py <league_id>      # Single league
   python ff_multi.py --env            # Multiple leagues from .env
   ```

### Authentication Setup (All Methods)

**For private leagues only**: Set up ESPN authentication
```bash
cp .env.example .env
# Edit .env with your ESPN credentials (see section below)
```

## Usage

### League Analysis
```bash
# Single league (public)
python ff_multi.py <league_id>

# Single private league
python ff_multi.py <league_id> --private

# Multiple leagues as divisions
python ff_multi.py <league_id1> <league_id2> <league_id3>

# Use league IDs from .env file
python ff_multi.py --env

# Specific year
python ff_multi.py <league_id> --year 2023

# Google Sheets format output
python ff_multi.py <league_id> --sheets

# Save Google Sheets format to file
python ff_multi.py <league_id> --sheets --output results.tsv
```

## Examples

```bash
# Analyze a single public league
python ff_multi.py 123456789

# Analyze multiple divisions from .env file
python ff_multi.py --env

# Get Google Sheets format for a private league
python ff_multi.py 987654321 --private --sheets

# Save multi-division results to file
python ff_multi.py --env --sheets --output season_results.tsv
```

## Configuration

### Multi-Division Setup (.env file)
For analyzing multiple leagues as divisions, create a `.env` file:
```bash
# League IDs separated by commas
LEAGUE_IDS=123456789,987654321,555444333

# For private leagues, also add:
ESPN_SWID={12345678-1234-1234-1234-123456789ABC}
ESPN_S2=your-long-espn-s2-cookie-here%3D
```

### ESPN Authentication (Private Leagues Only)

For private leagues, you need to get your ESPN authentication cookies:

1. **Log into ESPN Fantasy Football** at [fantasy.espn.com](https://fantasy.espn.com)
2. **Open browser developer tools** (F12 in most browsers)
3. **Navigate to cookies**:
   - Chrome/Edge: Application → Storage → Cookies → https://fantasy.espn.com
   - Firefox: Storage → Cookies → https://fantasy.espn.com
4. **Copy these two values**:
   - `SWID` - Should look like `{12345678-1234-1234-1234-123456789ABC}`
   - `espn_s2` - Long string ending with `%3D`
5. **Add to .env file** as shown above

## Sample Output

### Regular Console Output
```
Sample Fantasy League Division (2025)

 LEAGUE STANDINGS
+------+------------------------+---------------+------------+--------+
| Rank | Team                   | Owner         | Points For | Record |
+======+========================+===============+============+========+
|    1 | Lightning Bolts       | Team Owner A  | 867.0      | 5-1    |
|    2 | Thunder Hawks         | Team Owner B  | 799.3      | 4-2    |
+------+------------------------+---------------+------------+--------+

SEASON CHALLENGES ($30 Each)
+-------------------------+----------------------+-------+---------------------------+
| Challenge               | Winner               | Value | Details                   |
+=========================+======================+=======+===========================+
| Most Points Overall     | Lightning Bolts     | $30   | 867.0 total points       |
| Most Points in One Game | Fire Dragons        | $30   | 186.5 points (Week 2)    |
| Most Points in a Loss   | Storm Chasers       | $30   | 173.4 points in loss     |
| Least Points in a Win   | Ice Wolves          | $30   | 101.2 points in win      |
| Closest Victory         | Steel Panthers      | $30   | Won by 0.4 points        |
+-------------------------+----------------------+-------+---------------------------+
```

### Google Sheets Format (with --sheets flag)
```
Fantasy Football Multi-Division Challenge Tracker (2025)
3 divisions, 30 teams total

Sample Fantasy League Division STANDINGS
Rank    Team    Owner   Points For      Record
1       Lightning Bolts Team Owner A    867.0   5-1
2       Thunder Hawks   Team Owner B    799.3   4-2

OVERALL SEASON CHALLENGES ($30 Each)
Challenge       Winner  Owner   Division        Value   Details
Most Points Overall     Golden Eagles   Team Owner C    Championship Division   $30     971.9 total points
Most Points in One Game Fire Dragons    Team Owner D    Sample Fantasy League Division  $30     186.5 points (Week 2)
```

## The 5 Season Challenges ($30 Each)

1. **Most Points Overall** - Team with highest total regular season points
2. **Most Points in One Game** - Highest single week score across all teams
3. **Most Points in a Loss** - Highest score in a losing effort
4. **Least Points in a Win** - Lowest score that still won the matchup
5. **Closest Victory** - Smallest winning margin between two teams

**Challenge Rules:**
- Only regular season games count (playoffs excluded)
- Ties go to the first team to achieve the result
- If still tied after that, the payout splits between tied teams

## Requirements

- Python 3.9+
- ESPN Fantasy Football league (public or private access)
- Internet connection for API access

## Google Sheets Export

The tool supports exporting results in a format that can be easily copied into Google Sheets:

**Console Output (for copy-paste):**
```bash
python ff_multi.py 123456789 --sheets        # Single league
python ff_multi.py --env --sheets            # Multiple leagues
```

**File Output (save to file first):**
```bash
python ff_multi.py 123456789 --sheets --output results.tsv
python ff_multi.py --env --sheets --output multi_results.tsv
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
- **Attachment**: `weekly-report.tsv` - Google Sheets compatible format

### Customizing the Schedule

To change when reports are sent, edit `.github/workflows/weekly-report.yml` and modify the cron schedule:
```yaml
# Currently: Tuesdays at 9 AM ET (13:00 UTC)
- cron: '0 13 * * 2'

# Examples:
# Mondays at 8 AM ET: '0 12 * * 1'
# Fridays at 5 PM ET: '0 21 * * 5'
```

## Dependencies

- `espn-api` - ESPN Fantasy Sports API wrapper
- `tabulate` - Pretty table formatting
- `python-dotenv` - Environment variable management

**Installation**: Use `uv sync` (recommended) or `pip install -r requirements.txt` in a virtual environment.

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool!

## License

This project is open source. Use it to make your fantasy football leagues more fun!