# Fantasy Football Awards CLI Tool

A simple command-line tool to analyze ESPN Fantasy Football leagues and generate award statistics for end-of-season analysis.

## Features

- 🏆 **Award Categories**: Champion, High Scorer, Most Consistent, Boom/Bust, and more
- 📊 **Detailed Statistics**: Team standings, scoring stats, and league insights
- 🔒 **Private League Support**: Works with both public and private ESPN leagues
- 📋 **Clean Table Output**: Well-formatted tables using tabulate library
- ⚡ **Simple CLI**: Just pass in your league ID and get instant results

## Installation

1. **Clone or download this repository**
   ```bash
   git clone <repository-url>
   cd ff-awards
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **For private leagues only**: Set up authentication
   ```bash
   cp .env.example .env
   # Edit .env with your ESPN credentials (see section below)
   ```

## Usage

### Basic Usage (Public League)
```bash
python ff_stats.py <league_id>
```

### Private League
```bash
python ff_stats.py <league_id> --private
```

### Specific Year
```bash
python ff_stats.py <league_id> --year 2023
```

### All Options
```bash
python ff_stats.py <league_id> --private --year 2023
```

## Examples

```bash
# Analyze a public league for current season
python ff_stats.py 123456789

# Analyze a private league for 2023 season
python ff_stats.py 987654321 --private --year 2023
```

## ESPN Authentication (Private Leagues Only)

For private leagues, you need to get your ESPN authentication cookies:

1. **Log into ESPN Fantasy Football** at [fantasy.espn.com](https://fantasy.espn.com)
2. **Open browser developer tools** (F12 in most browsers)
3. **Navigate to cookies**:
   - Chrome/Edge: Application → Storage → Cookies → https://fantasy.espn.com
   - Firefox: Storage → Cookies → https://fantasy.espn.com
4. **Copy these two values**:
   - `SWID` - Should look like `{12345678-1234-1234-1234-123456789ABC}`
   - `espn_s2` - Long string ending with `%3D`
5. **Add to .env file**:
   ```
   ESPN_SWID={your-swid-here}
   ESPN_S2=your-espn-s2-here
   ```

## Sample Output

```
🏈 Fantasy Football League Analyzer
==================================================
✅ Connected to league: Friends League 2025
📅 Season: 2025
👥 Teams: 12📊 LEAGUE STANDINGS
==================================================
+--------+----------------------+-----------------+----------+-------------+------------------+-------------+
|   Rank | Team                 | Owner           | Record   | Points For  | Points Against   | Avg Score   |
+========+======================+=================+==========+=============+==================+=============+
|      1 | Touchdown Dynasty    | John            | 11-3     | 1567.8      | 1234.5          | 112.0       |
|      2 | Fantasy Fanatics     | Sarah           | 10-4     | 1543.2      | 1345.7          | 110.2       |
+--------+----------------------+-----------------+----------+-------------+------------------+-------------+

🏆 SEASON AWARDS
==================================================
+-------------------------+---------------------------+----------+----------------------------------------+
| Award                   | Winner                    | Value    | Description                            |
+=========================+===========================+==========+========================================+
| 🏆 League Champion      | Touchdown Dynasty         | 11-3     | Best record with 1567.8 total points  |
| 🎯 Most Points Scored   | Touchdown Dynasty         | 1567.8   | Season total points leader             |
| 💥 Highest Single Week  | Fantasy Fanatics          | 156.7    | Best weekly performance                |
+-------------------------+---------------------------+----------+----------------------------------------+
```

## Awards Calculated

- **🏆 League Champion** - Best win-loss record
- **🎯 Most Points Scored** - Highest season total points
- **💥 Highest Single Week** - Best individual week performance
- **🚽 Toilet Bowl Award** - Lowest single week score
- **🎯 Most Consistent** - Lowest scoring variance (standard deviation)
- **🎢 Boom or Bust** - Highest scoring variance
- **😢 Unluckiest Team** - Most points scored against
- **🔄 Waiver Wire King** - Most waiver acquisitions

## Requirements

- Python 3.9+
- ESPN Fantasy Football league (public or private access)
- Internet connection for API access

## Troubleshooting

**"Import espn-api could not be resolved"**
- Run: `pip install -r requirements.txt`

**"Error connecting to league"**
- Check that league ID is correct
- For private leagues, verify ESPN_SWID and ESPN_S2 in .env file
- Make sure you have access to the league

**"Private league requires ESPN_SWID and ESPN_S2"**
- Create .env file with your ESPN credentials (see authentication section)

## Dependencies

- `espn-api` - ESPN Fantasy Sports API wrapper
- `pandas` - Data manipulation and analysis
- `tabulate` - Pretty table formatting
- `python-dotenv` - Environment variable management

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this tool!

## License

This project is open source. Use it to make your fantasy football leagues more fun! 🏈