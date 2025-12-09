# Playoff Mode Examples - Overview

This directory contains example outputs for the Playoff Mode feature (006) across different playoff stages and output formats.

## Example Files

### Console Format (Terminal Output)
1. **01-semifinals-console.txt** - Semifinals (Week 15)
   - Shows 3 divisions with 2 matchups each
   - Displays seeds, teams, owners, scores, winners
   - Includes 7 player highlights
   - Shows historical season challenges
   - Displays final regular season standings

2. **02-finals-console.txt** - Division Finals (Week 16)
   - Shows championship matchup for each division
   - Declares division champions
   - Same structure for highlights and historical data

3. **03-championship-console.txt** - Championship Week (Week 17)
   - Leaderboard of 3 division winners
   - Ranked by score (highest wins)
   - Shows overall champion
   - Player highlights across all 30 teams
   - Historical season challenges

### Markdown Format (GitHub/Slack/Discord)
4. **04-semifinals-markdown.md** - Semifinals in Markdown
   - Clean table-based layout
   - Easy to copy/paste into GitHub issues or Slack
   - Preserves all data from console version

5. **05-championship-markdown.md** - Championship Week in Markdown
   - Medal emojis for top 3 finishers
   - Clear champion declaration
   - Concise format suitable for announcements

### JSON Format (Structured Data)
6. **06-semifinals-json.json** - Semifinals structured data
   - `playoff_bracket` object with divisions and matchups
   - Detailed matchup objects with all fields
   - `weekly_player_highlights` array
   - `season_challenges` with historical note
   - `standings` for context

7. **07-championship-json.json** - Championship Week structured data
   - `championship` object with leaderboard
   - `overall_champion` field for easy access
   - Player highlights with note about scope
   - Historical season challenges

### Email/HTML Format (Mobile-Friendly)
8. **08-semifinals-email.html** - Semifinals HTML email
   - Purple gradient header for playoff excitement
   - Winner rows highlighted in green with left border
   - Responsive tables that work on mobile
   - Historical note with yellow alert styling
   - Division headers with pink gradient

9. **09-championship-email.html** - Championship Week HTML email
   - Gold-themed styling for championship atmosphere
   - Large trophy banner with gradient background
   - Champion row prominently highlighted
   - Medal emojis (🥇🥈🥉) in leaderboard
   - Blue info box noting player highlights scope

## Key Design Elements

### Playoff Bracket Display
- **Seed Numbers**: #1, #2, #3, #4 for playoff seeding
- **Team + Owner**: Both shown for clarity (e.g., "Thunder Cats (John)")
- **Scores**: Displayed when games are complete
- **Winner Indicator**: ✓ checkmark or "Winner" label

### Visual Hierarchy
1. **Top Section**: Playoff brackets (most important during playoffs)
2. **Middle Section**: Weekly player highlights (still relevant)
3. **Bottom Section**: Historical season challenges + regular season standings (context)

### Championship Week Specifics
- **Leaderboard Format**: Rank, medals (🥇🥈🥉), team, division, score
- **Clear Winner**: Prominent display of overall champion
- **Note**: Player highlights include all teams, not just championship participants

### JSON Structure
```json
{
  "playoff_bracket": {
    "round": "Semifinals" | "Finals" | "Championship Week",
    "divisions": [/* per-division matchups */]
  },
  "championship": {
    "leaderboard": [/* ranked division winners */],
    "overall_champion": {/* winner details */}
  }
}
```

## Design Iterations Welcome

These examples are starting points for iteration. Consider:
- **Bracket Visualization**: ASCII art brackets vs tables?
- **Color/Emphasis**: How to highlight winners in console?
- **Sheets Format**: How to structure TSV for easy Google Sheets import?
- **Email Format**: HTML layout with responsive design?
- **Incomplete Games**: How to show in-progress matchups (0-0 scores)?

## Testing Notes

These examples assume:
- 3 divisions with 10 teams each
- 4 teams per division make playoffs
- 2-round playoffs (semifinals → finals) + championship week
- All divisions synchronized

When testing with live ESPN data, verify:
- Actual playoff bracket structure matches examples
- Seeding numbers align with `team.standing`
- `is_playoff` flag correctly identifies playoff games
- Scores and team names extract properly

---

**Created**: 2025-12-08
**Spec Version**: 0.1
