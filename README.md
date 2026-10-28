# Fantasy Football Challenge Tracker

A modern, type-safe command-line tool to analyze ESPN Fantasy Football leagues and track 5 specific season challenges across single leagues or multiple divisions.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Season Recap](#season-recap)
- [Configuration](#configuration)
- [Sample Output](#sample-output)
- [The 5 Season Challenges](#the-5-season-challenges)
- [Automated Weekly Reports (GitHub Actions)](#automated-weekly-reports-github-actions)
- [Contributing](#contributing)
- [License](#license)

## Features

- **🏆 Automatic Playoff Mode** (NEW in v3.0): Seamlessly transitions to playoff brackets when playoffs begin
  - **Semifinals (Week 15)**: Displays matchup brackets (#1 vs #4, #2 vs #3) for all divisions
  - **Finals (Week 16)**: Shows championship matchups with winner tracking
  - **Championship Week (Week 17)**: Ranks all division winners to crown overall champion
  - No manual configuration - automatically detects playoff status based on league week
- **📊 Season Recap** (NEW in v3.3): Comprehensive end-of-season summaries
  - Combines regular season, playoffs, and championship results in one report
  - Shows division champions, final standings, and all 5 season challenges
  - Displays complete playoff brackets (Semifinals + Finals) with winners
  - Championship leaderboard determining the ultimate champion
  - Available in all 5 output formats
- **13 Weekly Highlights**: Track current week's top performances including team challenges (highest/lowest scores, biggest win, closest game, overachiever, below expectations) and player highlights (top scorers by position)
  - During playoffs: Shows 7 player highlights only (team challenges replaced by playoff brackets)
  - Championship week: Player highlights include ALL teams across all divisions
- **5 Season Challenges**: Track Most Points Overall, Most Points in One Game, Most Points in a Loss, Least Points in a Win, and Closest Victory
  - During playoffs: Marked as "Historical" to clarify regular season final results
- **Playoff Positioning**: Shows current playoff qualification (top 4 by record, points-for tiebreaker) with visual indicators
- **Multi-Division Support**: Analyze multiple leagues as divisions with overall rankings
- **Flexible League Input**: Pass league IDs via CLI (comma-separated), environment variable, or .env file
- **Private League Support**: Works with both public and private ESPN leagues
- **Multiple Output Formats**: Console tables, Google Sheets TSV, mobile-friendly HTML email, JSON, and Markdown
  - All formats support playoff brackets and championship leaderboards
- **Multi-Output Mode**: Generate all formats in one execution with `--output-dir`
- **Type Safety**: Comprehensive type annotations with modern Python syntax
- **Fast Error Handling**: Fail-fast approach with clear error messages
- **Modular Architecture**: Clean separation of concerns for easy maintenance and extension
- **Mobile-Friendly**: HTML email format optimized for mobile devices with responsive playoff brackets

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
# Basic usage
uv run ff-tracker <league_id>

# Specific year
uv run ff-tracker <league_id> --year 2023

# Specific week (snapshot in time)
uv run ff-tracker <league_id> --week 10

# Historical analysis: specific year and week
uv run ff-tracker <league_id> --year 2024 --week 10

# Test playoff scenarios
uv run ff-tracker <league_id> --week 15 --private

# Different output format
uv run ff-tracker <league_id> --format sheets
```

### Week Override Feature

Use `--week` to view data as a snapshot in time:

```bash
# View historical week 10 data
uv run ff-tracker 123456 --week 10

# Test playoff bracket for week 15
uv run ff-tracker 123456 --week 15

# Historical analysis from previous season
uv run ff-tracker 123456 --year 2024 --week 12
```

**How it works:**
- Acts as a snapshot in time showing data as it appeared at that specific week
- Season challenges are calculated only through regular season (weeks 1-14)
- Weekly highlights show the specified week's data
- Playoff brackets display if the week is in playoffs (15-17)
- Cannot specify future weeks (must be ≤ current week in ESPN)
- Useful for: reviewing past weeks, testing playoff scenarios, debugging

**Examples:**
- `--week 10`: Shows regular season through week 10
- `--week 15`: Shows Semifinals bracket + season challenges (frozen at week 14)
- `--week 16`: Shows Finals bracket + season challenges (frozen at week 14)

### Output Formats

The script supports multiple output formats:

- **`console`** (default): Human-readable tables for terminal display
- **`sheets`**: Tab-separated values for easy import into Google Sheets
- **`email`**: Mobile-friendly HTML format perfect for email reports
- **`json`**: Structured JSON data for further processing
- **`markdown`**: Markdown format for GitHub, Slack, Discord, wikis, etc.

```bash
# Console output (default)
uv run ff-tracker 123456

# Google Sheets format
uv run ff-tracker 123456 --format sheets > results.tsv

# HTML email format
uv run ff-tracker 123456 --format email > report.html

# JSON data export
uv run ff-tracker 123456 --format json > data.json

# Markdown format
uv run ff-tracker 123456 --format markdown > report.md
```

### Format Arguments

Customize output with `--format-arg` (can be used multiple times):

```bash
# Add a note to any format (global argument)
uv run ff-tracker 123456 --format-arg note="Playoffs start next week!"

# Customize email colors (formatter-specific)
uv run ff-tracker 123456 --format email \
  --format-arg note="Season ends Dec 15th" \
  --format-arg email.accent_color="#ff6b6b" \
  --format-arg email.max_teams=5

# Generate markdown with table of contents
uv run ff-tracker 123456 --format markdown \
  --format-arg note="Championship game this week!" \
  --format-arg markdown.include_toc=true

# Pretty-print JSON output
uv run ff-tracker 123456 --format json --format-arg json.pretty=true
```

**Supported Format Arguments:**

| Argument | Formats | Description |
|----------|---------|-------------|
| `note` | All | Display a message at the top of the output |
| `email.accent_color` | email | Customize border/accent colors (hex color) |
| `email.max_teams` | email | Cap the overall standings table (default: `0` = all teams) |
| `email.ai_team_color` | email | Colour of team names in the AI summary's stylesheet rule (default: `#0b57d0`) |
| `markdown.include_toc` | markdown | Generate table of contents with section links |
| `json.pretty` | json | Enable indented JSON output (true/false) |

### Multi-Output Mode

Generate all formats in a single execution with `--output-dir`:

```bash
# Generate all 5 formats at once (single ESPN API call)
uv run ff-tracker --env --output-dir ./reports

# Creates:
#   ./reports/standings.txt   (console format)
#   ./reports/standings.tsv   (sheets format)
#   ./reports/standings.html  (email format)
#   ./reports/standings.json  (json format)
#   ./reports/standings.md    (markdown format)
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

# Historical week from current season
uv run ff-tracker 123456 --week 10

# Historical week from previous season
uv run ff-tracker 123456 --year 2024 --week 12

# Test playoff bracket without waiting for games
uv run ff-tracker 123456 --week 15 --private

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

# Add a note to console output
uv run ff-tracker 123456 --format-arg note="Playoffs start next week! Good luck!"

# Customize email report colors and add note
uv run ff-tracker 123456 --format email \
  --format-arg note="Championship game December 15th" \
  --format-arg email.accent_color="#28a745"

# Generate markdown with table of contents
uv run ff-tracker --env --format markdown \
  --format-arg markdown.include_toc=true \
  --format-arg note="Final week of regular season"

# Week override with format arguments
uv run ff-tracker 123456 --week 15 --format email \
  --format-arg note="Semifinals - Good luck everyone!"
```

## Season Recap

Generate comprehensive end-of-season summaries combining regular season results, playoffs, and championship data.

### Features

- **Complete Season Summary**: Regular season standings, division champions, and all 5 season challenges
- **Playoff Results**: Semifinals (Week 15) and Finals (Week 16) brackets with winners
- **Championship Leaderboard**: Week 17 overall rankings to determine the ultimate champion
- **Multiple Formats**: Same 5 output formats as weekly reports (console, sheets, email, json, markdown)
- **Multi-Output Mode**: Generate all formats in one execution
- **Force Mode**: Generate partial recaps during playoffs for testing/progress tracking

### Usage

```bash
# Basic season recap (requires completed season)
uv run ff-season-recap --env

# Specific format
uv run ff-season-recap --env --format email > season-recap.html
uv run ff-season-recap 123456,789012 --format markdown > recap.md

# Generate all formats at once
uv run ff-season-recap --env --output-dir ./season-recap
# Creates: season-recap.txt, season-recap.tsv, season-recap.html,
#          season-recap.json, season-recap.md

# Force mode (generate partial recap during playoffs)
uv run ff-season-recap --env --force
uv run ff-season-recap --env --force --format console

# Historical season
uv run ff-season-recap --env --year 2024

# With format arguments
uv run ff-season-recap --env --format email \
  --format-arg note="Official 2025 Season Recap" \
  --format-arg email.accent_color="#ffc107"
```

### Season Requirements

The season recap requires:
- **Regular Season Complete**: All regular season games finished (Weeks 1-14)
- **Playoffs Complete**: Semifinals (Week 15) and Finals (Week 16) finished
- **Championship Complete**: Championship week (Week 17) finished

Use `--force` flag to generate partial recaps if season is incomplete (useful for testing or progress tracking).

### Output Content

**Regular Season Section:**
- Division champions with win-loss records
- Complete final standings (all teams, all divisions)
- All 5 season-long challenge winners:
  - Most Points Overall
  - Most Points in One Game
  - Most Points in a Loss
  - Least Points in a Win
  - Closest Victory

**Playoff Section:**
- Semifinals brackets (Week 15): All 4 matchups per division
- Finals brackets (Week 16): Championship matchups per division
- Winner identification for each matchup

**Championship Section:**
- Week 17 leaderboard ranking all division winners
- Overall champion (highest score in Week 17)

### Examples

```bash
# Console output (human-readable tables)
uv run ff-season-recap --env --format console

# Email report for distribution
uv run ff-season-recap --env --format email > recap-2025.html

# JSON for archival/analysis
uv run ff-season-recap --env --format json > archive/season-2025.json

# Markdown for GitHub wiki
uv run ff-season-recap --env --format markdown \
  --format-arg markdown.include_toc=true > wiki/season-2025.md

# All formats for complete archival
uv run ff-season-recap --env --output-dir ./archive/2025-season \
  --format-arg note="Official 2025 Season Results"

# During playoffs (testing/progress)
uv run ff-season-recap --env --force --format console
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

### Alternate Environment File

All three CLIs (`ff-tracker`, `ff-championship`, `ff-season-recap`) accept
`--env-file PATH`. By default they read `.env` from the working directory; the
flag points them at a different file, which is useful for testing against a
throwaway set of leagues or keeping several multi-league setups side by side.
The file supplies everything an environment does — `LEAGUE_IDS`, the ESPN
cookies, and any `AI_SUMMARY_*` settings — and both the report configuration and
the AI settings read that same file. A path you pass explicitly must exist: a
missing one is an error naming the path, rather than a silent fallback to the
repo's `.env`.

```bash
uv run ff-tracker --env --env-file ./staging.env
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

### AI Summary (Optional, `ff-tracker` Only)

`ff-tracker` can append a short AI-written "commissioner's take" between the
weekly highlights and the season-long challenges, in every format that has a
position (JSON keeps a top-level `ai_summary` key). It is off by default, labelled
AI-generated wherever it appears, and can never change a deterministic value: if
the narrative cannot be generated the report ships without it and says so.

```env
AI_SUMMARY_ENABLED=true
AI_SUMMARY_API_KEY=your_opencode_api_key_here
```

| Variable | Default | Meaning |
|---|---|---|
| `AI_SUMMARY_ENABLED` | `false` | Opt-in switch; a key alone does not enable it |
| `AI_SUMMARY_API_KEY` | none | Bearer token, required when enabled, never printed |
| `AI_SUMMARY_BASE_URL` | `https://opencode.ai/inference/openai/v1` | OpenAI-compatible endpoint root |
| `AI_SUMMARY_MODEL` | `deepseek-v4.1-flash` | Model id, reported in JSON provenance and the attribution line |
| `AI_SUMMARY_TIMEOUT` | `120` | Per-socket-read timeout in seconds |
| `AI_SUMMARY_MAX_TOKENS` | `8000` | Sent as the request's `max_tokens`; too small a budget for the chosen model shows up as a truncation notice |
| `AI_SUMMARY_REASONING_EFFORT` | unset | Optional `low\|medium\|high`; sent as `reasoning_effort` only when set, and an endpoint that ignores it is not an error |
| `AI_SUMMARY_MAX_PROMPT_CHARS` | `8000` | Size cap for the instructions below |
| `AI_SUMMARY_USER_PROMPT` | empty | Free-form instructions appended to the system prompt, sent verbatim |
| `AI_MEMORY_ENABLED` | `false` | Opt-in memory log; inert while `AI_SUMMARY_ENABLED` is off |
| `AI_MEMORY_GIST_ID` | none | Id of the secret gist holding `memory.json`, required when memory is on |
| `AI_MEMORY_GIST_TOKEN` | none | Token with Gists read and write, never printed, required when memory is on |
| `AI_MEMORY_WRITE` | `true` | Read-only switch: `false` reads and uses the archive but writes nothing (`memory_write: "skipped"`, no warning) |

**Why `deepseek-v4.1-flash` is the default:** `glm-5.3-flash` spends the whole
8000-token budget on reasoning for a three-league digest (8000/8000 tokens,
`content: null`, `finish_reason: length`), while `deepseek-v4.1-flash` completes
the same digest in about 2,057 reasoning tokens and roughly 9 seconds.
`glm-5.3-flash` is still selectable through `AI_SUMMARY_MODEL`, at the cost of a
much larger `AI_SUMMARY_MAX_TOKENS` or a `reasoning_effort` the endpoint honours.

**Configuration in GitHub Actions.** The weekly workflow reads the settings from
repository **variables** (Settings → Secrets and variables → Actions →
Variables), with the prompt from a variable or a secret, so changing the model,
budget or prompt is a settings edit rather than a YAML commit. Variables are
**not masked in logs** while secrets are, so a prompt the league would not
publish belongs in the secret.

```bash
# The settings are repository variables, e.g.
gh variable set AI_SUMMARY_MODEL --body "deepseek-v4.1-flash"
gh variable set AI_SUMMARY_MAX_TOKENS --body "8000"

# The prompt: choose ONE of these. A variable is readable in settings and
# unmasked in logs; a secret is masked. Do not set both.
# gh variable set AI_SUMMARY_USER_PROMPT --body "$(cat prompt.txt)"
gh secret set AI_SUMMARY_USER_PROMPT --body "$(cat prompt.txt)"
```

Use `--body "$(cat prompt.txt)"` (or the secret) for a multi-line prompt: the
settings UI accepts only a single line per field, so newlines are easiest to keep
through the CLI or the API.

When the prompt lives in the secret, do **not** also set the variable. An unset
variable falls through to the secret, but a whitespace-only one does not: in
`vars … || secrets …` any non-empty string is truthy, so a few stray spaces would
win the fallback, shadow the secret, and then be stripped by the loader to "no
instructions".

A blank or unset variable means "use the default", which is what an unset
repository variable renders as; a malformed non-blank value (a non-numeric
timeout, an unknown reasoning effort, a URL without a scheme) is a configuration
error that fails the run while the feature is enabled — it never degrades to a
report without the section.

**One-run prompt override.** The manual *Run workflow* dialog has an
`ai_summary_prompt` input for a single run's instructions. Precedence is
`inputs.ai_summary_prompt` → `vars.AI_SUMMARY_USER_PROMPT` →
`secrets.AI_SUMMARY_USER_PROMPT` → empty: an empty input falls through to the
standing prompt rather than clearing it, and the input never persists. Dispatch
string inputs are single-line, so keep a multi-line standing prompt in the
variable or the secret; a dispatch input is also visible in the run's inputs, so
never put a secret in it.

### AI Memory (optional, `ff-tracker` only)

With `AI_MEMORY_ENABLED=true` and a gist configured, the weekly report keeps a
log of what it published: one file, `memory.json`, in one secret gist, with one
entry per week holding that week's summary verbatim. The whole archive goes into
the prompt, so a running bit escalates or retires instead of being repeated, and
the take can cite an earlier week it already wrote about. It is off by default;
off means no store call, no prompt change and output identical to a run without
it.

**What the file never contains:** the archive is this tool's own published prose
and week tags only — no standings, scores, projections, digest, prompt, API key,
gist token or any other credential. **GitHub has no private gist**: a secret gist
is unlisted, not private, so anyone who obtains its URL can read it. The tool
assumes exactly that.

**The store.** `AI_MEMORY_GIST_ID` comes from a repository variable and
`AI_MEMORY_GIST_TOKEN` from a secret — a fine-grained token with Gists read and
write, or a classic token with the `gist` scope. Both are required when memory is
on: a missing or empty one is a configuration error that stops the run, exactly
as a missing API key does, which is why the workflow enables memory only when
both are present. One read happens before the narrative is generated and at most
one write after it is accepted; nothing else about a run changes.

**Test runs.** A manual *Run workflow* with `update_memory` unchecked (or
`AI_MEMORY_WRITE=false` locally) reads the archive and uses it exactly as a normal
run does, but writes nothing: the take still has the earlier weeks behind it,
`provenance.memory_write` reads `"skipped"`, and no warning is emitted because
nothing failed. That is what makes it safe to dispatch the workflow with the
recipients overridden to your own address — a test run must never advance the
archive the real run depends on. Scheduled runs always write; a blank value on a
schedule falls through to the default.

**Append-only.** A run appends its week and replaces that same week's entry on a
re-run, so a dispatch re-run cannot stack a second take. Nothing written earlier
is ever modified, reordered or dropped, which is what makes a hand edit inside an
earlier entry safe by construction. A file that does not parse as the archive shape
is treated as no memory for that run, warned once under Actions, and left exactly
as it is — never overwritten.

**Reading the report.** `provenance.memory_read` (`ok`, `none`, `failed`),
`provenance.memory_write` (`ok`, `failed`, `skipped`) and `provenance.memory_weeks`
(the weeks the model was shown) appear in JSON only when a narrative rendered; the
failure notice carries none of them. A read failure never appears in any format: a
404 is "nothing published yet", a 401/403 warns once under Actions, and a 5xx,
transport error or timeout is silent. **A failed read also skips the write**: with no
archive in hand, appending this week would replace the stored weeks with a single
entry, so the run records the failure and leaves the file untouched — one week of
memory, never the season. A write failure ships the complete report, exits 0, and
warns once under Actions naming scope or authentication. A run whose week is not
1–18 — pre-kickoff, or a week it could not detect — writes nothing and records
`skipped`.

**Seeding past weeks** is a series of ordinary `--week N` runs, not a feature: the
throwaway script that loops over a season is the owner's, not part of this repo.
Each run appends the week it was given, so the archive grows one entry at a time.

**Retire the file at a season boundary.** Entries are keyed by week alone inside a
file whose `season` is fixed when it is created, and the tool never compares that
season to the run's. A Week 6 run next season would therefore **replace** last
season's Week 6 entry — a hand edit included — rather than add to it.

Starting a new gist is the simplest reset. To reuse the same gist, replace the
file's content with a valid empty archive:

```json
{"schema": 1, "season": 2026, "entries": []}
```

That is a hand action on purpose, because a rollover rule would make a legitimate
mid-season correction impossible. **Do not merely blank the file:** an empty or
unparseable `memory.json` is treated as no memory, warned about once under Actions,
and never overwritten — so memory stays off until someone writes a valid archive
back into the gist.

**What leaves the machine:** team names, owner names, points for, points against,
scores and league names are sent to `AI_SUMMARY_BASE_URL`, together with
`AI_SUMMARY_USER_PROMPT`. Never put credentials in the prompt.

**Failure behaviour:** an HTTP error, a timeout, a truncated or malformed
response produces the normal report, a one-line notice where the section would
have been, exit code 0, and a `::warning::` in GitHub Actions. A *configuration*
error **while the feature is enabled** (a missing key, a malformed timeout or
budget, a bad base URL, an oversized prompt) fails the run instead, before any
report is written; the same variables are ignored while the feature is off, so a
stale value cannot deny a report. The weekly workflow sets
`AI_SUMMARY_ENABLED` only when the key secret exists, so a checkout without the
key simply gets a report with the feature off.

`ff-championship` and `ff-season-recap` ignore these variables entirely.

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

## Weekly Highlights (13 Challenges)

Automatically tracks the current week's top performances across team and player categories:

**Team Challenges (6):**
1. **Highest Score This Week** - Team with the most points this week
2. **Lowest Score This Week** - Team with the fewest points this week
3. **Biggest Win This Week** - Largest margin of victory (shows both scores and margin)
4. **Closest Game This Week** - Smallest margin between two teams (shows both scores and margin)
5. **Overachiever** - Team that most exceeded their pre-game starter projections (NEW in v2.2)
6. **Below Expectations** - Team that most underperformed their pre-game starter projections (NEW in v2.2)

**Player Highlights (7):**
7. **Top Scorer (Player)** - Highest scoring player across all positions
8. **Best QB** - Top quarterback performance
9. **Best RB** - Top running back performance
10. **Best WR** - Top wide receiver performance
11. **Best TE** - Top tight end performance
12. **Best K** - Top kicker performance
13. **Best D/ST** - Top defense/special teams performance

**Display Features:**
- Team challenges show division and detailed scores (e.g., "148.78 - 49.00 (Δ99.78)")
- Projection challenges show difference from pre-game expectations (e.g., "+28.62" or "-67.45")
- Player highlights show which fantasy team started each top performer
- Separated into two clear tables for better readability
- Only includes players in starting lineups (bench players excluded)

**True Projection Tracking:**
- Overachiever/Below Expectations use **pre-game starter projections** (sum of individual player projections)
- This provides accurate boom/bust analysis vs ESPN's real-time updated team projections
- JSON output includes `weekly_games` data with both projection types for analysis

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

## Playoff Mode 🏆

**NEW in v3.0**: The tool automatically detects and displays playoff information when your league enters the postseason. No configuration required!

### How It Works

The tool detects playoff mode when `current_week > regular_season_count` (typically Week 15+). All divisions must be in sync (same week and playoff state).

### Playoff Phases

#### **Semifinals (Week 15)**
- Displays 2 matchups per division: #1 seed vs #4 seed, #2 seed vs #3 seed
- Shows team names, owners, seeds, current scores, and winners (✓)
- Handles in-progress games (scores update as games are played)
- Winners bracket only (consolation games excluded)

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ROAD REPO DIVISION - SEMIFINALS                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━┳━━━━━━━━┓
┃ Matchup      ┃ Team (Owner)             ┃ Seed ┃ Score ┃ Result ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━╇━━━━━━━━┩
│ Semifinal 1  │ ILikeTurtles             │ #1   │ TBD   │        │
│              │ Billieve the Champ       │ #4   │ TBD   │        │
├──────────────┼──────────────────────────┼──────┼───────┼────────┤
│ Semifinal 2  │ Can't All Be Bangers     │ #2   │ TBD   │        │
│              │ Team Flower Cupcake      │ #3   │ TBD   │        │
└──────────────┴──────────────────────────┴──────┴───────┴────────┘
```

#### **Finals (Week 16)**
- Displays 1 championship matchup per division
- Winners of the two semifinals face off
- Same format as semifinals

#### **Championship Week (Week 17)**
- **Championship Leaderboard**: Ranks all division winners by their Week 17 score
- **Overall Champion**: Team with highest score crowned supreme champion
- **Medal Ranks**: 🥇 Gold, 🥈 Silver, 🥉 Bronze for top 3 finishers

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                          🏆 CHAMPIONSHIP WEEK 🏆                             ║
║                                                                              ║
║                              OVERALL CHAMPION                                ║
║                            Lightning Bolts (Team Owner A)                    ║
║                          Road Repo Division - 156.8 pts                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┓
┃ Rank ┃ Team (Owner)                ┃ Division    ┃ Score ┃ Status    ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━┩
│ 🥇 1 │ Lightning Bolts             │ Road Repo   │ 156.8 │ CHAMPION! │
│ 🥈 2 │ Thunder Hawks               │ East Coast  │ 142.3 │           │
│ 🥉 3 │ Fire Dragons                │ West Coast  │ 138.1 │           │
└──────┴─────────────────────────────┴─────────────┴───────┴───────────┘
```

### Playoff Adaptations

**Weekly Challenges:**
- **Semifinals/Finals**: Shows 7 player highlights only (team challenges replaced by bracket context)
- **Championship Week**: Shows 7 player highlights across ALL teams (not just division winners)

**Season Challenges:**
- Marked as "REGULAR SEASON FINAL RESULTS (Historical)"
- Data is frozen at end of Week 14 (regular season finale)
- Preserved for end-of-season awards

**Regular Season Standings:**
- Shown at bottom of output as "FINAL REGULAR SEASON STANDINGS"
- Hidden during Championship Week (focus on championship leaderboard)

### All Formats Support Playoffs

Every output format (console, sheets, email, JSON, markdown) automatically displays playoff brackets and championship data when detected.

## Automated Reports (GitHub Actions)

This repository includes three GitHub Actions workflows for automated report generation:

1. **Weekly Reports** (`weekly-report.yml`) - Automatically generates and emails weekly reports every Tuesday at 6 AM ET
2. **Championship Report** (`championship-report.yml`) - Manual trigger for Week 17 championship leaderboard
3. **Season Recap** (`season-recap.yml`) - Manual trigger for comprehensive end-of-season summaries

All workflows use the `--output-dir` mode to generate all formats (console, TSV, HTML, JSON, Markdown) in a single execution.

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

3. **Enable GitHub Actions** - The weekly workflow will automatically run every Tuesday at 9 AM ET during fantasy football season. The championship and season recap workflows are manual-trigger only.

### Manual Trigger

You can manually trigger any of the workflows:
1. Go to your repository's "Actions" tab
2. Select the workflow you want to run:
   - "Weekly Fantasy Football Report" - For current week standings
   - "Championship Report" - For Week 17 championship leaderboard
   - "Season Recap Report" - For comprehensive end-of-season summary
3. Click "Run workflow"
4. Fill in any optional inputs (email recipients, custom notes, etc.)
5. Click "Run workflow" to start execution

**Workflow-Specific Inputs:**
- **Weekly Report**: `weekly_note` (optional note in report)
- **Championship Report**: `championship_week`, `skip_email`, `championship_note`
- **Season Recap**: `season_year`, `skip_email`, `recap_note`, `force_generation`

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