"""
Email HTML formatter for Fantasy Football Challenge Tracker.

Provides mobile-friendly HTML email format suitable for weekly reports.

Template Injection Support:
    The HTML output includes invisible comment markers that can be used for
    metadata injection (e.g., by GitHub Actions):

    <!-- GENERATED_METADATA_START --><!-- GENERATED_METADATA_END -->

    To inject metadata (generation time, execution duration, artifact links):
    1. Generate the HTML normally (markers will be adjacent/empty)
    2. Use sed or similar to replace the marker pair with content:
       sed -i "s|<!-- GENERATED_METADATA_START --><!-- GENERATED_METADATA_END -->|
               <!-- GENERATED_METADATA_START -->YOUR_HTML_HERE<!-- GENERATED_METADATA_END -->|g" file.html
    3. Injected content will appear in the footer, markers remain for debugging

    When markers are not replaced, they are invisible in rendered HTML/email.
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.metadata import version

from ..models import ChallengeResult, ChampionshipLeaderboard, DivisionData, WeeklyChallenge
from .base import BaseFormatter


class EmailFormatter(BaseFormatter):
    """Formatter for mobile-friendly HTML email output."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize email formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        super().__init__(year, format_args)

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for email formatter."""
        return {
            "note": "Optional alert message displayed at top of email",
            "accent_color": "Hex color for highlight sections (default: #ffc107)",
            "max_teams": "Maximum teams to show in overall rankings (default: 20)",
        }

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None,
        championship: ChampionshipLeaderboard | None = None,
    ) -> str:
        """Format complete output for mobile-friendly HTML email."""
        # Get format arguments
        note = self._get_arg("note")
        accent_color = self._get_arg("accent_color", "#ffc107")
        max_teams = self._get_arg_int("max_teams", 20)

        total_divisions, total_teams = self._calculate_total_stats(divisions)

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fantasy Football Challenge Tracker ({self.year})</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            font-size: 14px;
            line-height: 1.4;
            margin: 0;
            padding: 10px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 100%;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            font-size: 18px;
            margin: 0 0 10px 0;
            text-align: center;
        }}
        h2 {{
            color: #34495e;
            font-size: 16px;
            margin: 20px 0 10px 0;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        .summary {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 20px;
            font-size: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 12px;
        }}
        th, td {{
            padding: 6px 4px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #ecf0f1;
            font-weight: bold;
            color: #2c3e50;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .number {{
            text-align: right;
        }}
        .challenge-table td {{
            padding: 8px 4px;
        }}
        .challenge-name {{
            font-weight: bold;
            color: #2980b9;
        }}
        .alert-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: 2px solid #5a67d8;
            padding: 15px;
            margin: 15px 0;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.15);
            font-size: 14px;
        }}
        .weekly-highlight {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid {accent_color};
        }}
        .weekly-highlight h2 {{
            color: #856404;
            margin-top: 0;
        }}
        .weekly-highlight table {{
            margin-bottom: 0;
        }}
        .weekly-highlight table:not(:last-child) {{
            margin-bottom: 15px;
        }}
        .winner {{
            color: #27ae60;
            font-weight: bold;
        }}
        .playoff-bracket {{
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }}
        .playoff-bracket h2 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        .playoff-matchup {{
            background-color: white;
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 5px;
            border: 1px solid #bdc3c7;
        }}
        .playoff-matchup h4 {{
            margin: 0 0 10px 0;
            color: #34495e;
            font-size: 13px;
        }}
        .playoff-team {{
            display: flex;
            justify-content: space-between;
            padding: 8px;
            margin-bottom: 5px;
            background-color: #f8f9fa;
            border-radius: 3px;
        }}
        .playoff-winner {{
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            font-weight: bold;
        }}
        .championship-box {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            border: 3px solid #d63384;
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
            color: white;
            text-align: center;
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }}
        .championship-box h2 {{
            color: white;
            border-bottom: 2px solid white;
            margin-top: 0;
        }}
        .champion-announcement {{
            background-color: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 16px;
        }}
        .historical-note {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px 15px;
            margin: 15px 0;
            border-radius: 5px;
            font-style: italic;
            color: #856404;
        }}
        .footer {{
            text-align: center;
            color: #95a5a6;
            font-size: 10px;
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #ecf0f1;
        }}
        @media (max-width: 480px) {{
            body {{
                font-size: 12px;
                padding: 5px;
            }}
            .container {{
                padding: 10px;
            }}
            h1 {{
                font-size: 16px;
            }}
            h2 {{
                font-size: 14px;
            }}
            table {{
                font-size: 10px;
            }}
            th, td {{
                padding: 4px 2px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Fantasy Football Multi-Division Challenge Tracker ({self.year})</h1>
        <div class="summary">{total_divisions} divisions • {total_teams} teams total • Week {current_week or "Not Found"}</div>
"""

        # Detect playoff mode
        is_playoff_mode = any(d.is_playoff_mode for d in divisions)
        is_championship_week = championship is not None

        # Optional note/alert
        if note:
            html_content += f"""
        <div class="alert-box">
            📢 {self._escape_html(note)}
        </div>
"""

        # Championship leaderboard (first, if championship week)
        if is_championship_week and championship:
            html_content += self._format_championship_leaderboard(championship)

        # Playoff brackets (first, if Semifinals/Finals)
        if is_playoff_mode and not is_championship_week:
            html_content += self._format_playoff_brackets(divisions)

        # Weekly player highlights (playoffs only show player challenges)
        if weekly_challenges and current_week and (is_playoff_mode or is_championship_week):
            # Filter to player challenges only
            player_challenges = [c for c in weekly_challenges if "position" in c.additional_info]
            if player_challenges:
                html_content += self._format_weekly_player_table(player_challenges, current_week)

        # Regular season weekly highlights (both team and player)
        elif weekly_challenges and current_week:
            # Split into team and player challenges
            team_challenges = [c for c in weekly_challenges if "position" not in c.additional_info]
            player_challenges = [c for c in weekly_challenges if "position" in c.additional_info]

            html_content += '<div class="weekly-highlight">\n'
            html_content += f"<h2>🔥 Week {current_week} Highlights</h2>\n"

            # Team challenges
            if team_challenges:
                html_content += "<h3>Team Challenges</h3>\n"
                html_content += "<table>\n"
                html_content += (
                    "<tr><th>Challenge</th><th>Team</th><th>Division</th><th>Value</th></tr>\n"
                )

                for challenge in team_challenges:
                    html_content += (
                        f"<tr>"
                        f'<td class="challenge-name">{self._escape_html(challenge.challenge_name)}</td>'
                        f'<td class="winner">{self._escape_html(challenge.winner)}</td>'
                        f"<td>{self._escape_html(challenge.division)}</td>"
                        f'<td class="number">{self._escape_html(challenge.value)}</td>'
                        f"</tr>\n"
                    )

                html_content += "</table>\n"

            # Player highlights
            if player_challenges:
                html_content += "<h3>Player Highlights</h3>\n"
                html_content += "<table>\n"
                html_content += "<tr><th>Challenge</th><th>Player</th><th>Points</th></tr>\n"

                for challenge in player_challenges:
                    # Include position in player display
                    position = challenge.additional_info.get("position", "")
                    winner_display = f"{challenge.winner} ({position})"

                    html_content += (
                        f"<tr>"
                        f'<td class="challenge-name">{self._escape_html(challenge.challenge_name)}</td>'
                        f'<td class="winner">{self._escape_html(winner_display)}</td>'
                        f'<td class="number">{self._escape_html(challenge.value)}</td>'
                        f"</tr>\n"
                    )

                html_content += "</table>\n"

            html_content += "</div>\n"

        # Season challenges with historical note in playoff mode
        if challenges:
            if is_playoff_mode:
                html_content += """
        <div class="historical-note">
            <strong>Note:</strong> Regular season challenges finalized at end of week 14
        </div>
"""
            html_content += "<h2>Season Challenge Results</h2>\n"
            html_content += '<table class="challenge-table">\n'
            html_content += "<tr><th>Challenge</th><th>Winner</th><th>Owner</th><th>Division</th><th>Details</th></tr>\n"

            for challenge in challenges:
                html_content += (
                    f"<tr>"
                    f'<td class="challenge-name">{self._escape_html(challenge.challenge_name)}</td>'
                    f'<td class="winner">{self._escape_html(challenge.winner)}</td>'
                    f"<td>{self._escape_html(challenge.owner.full_name)}</td>"
                    f"<td>{self._escape_html(challenge.division)}</td>"
                    f"<td>{self._escape_html(challenge.description)}</td>"
                    f"</tr>\n"
                )

            html_content += "</table>\n"

        # Division standings (labeled as historical if playoff mode)
        if is_playoff_mode:
            html_content += """
        <div class="historical-note">
            Final regular season standings from week 14
        </div>
"""
            html_content += "<h2>Final Regular Season Standings</h2>\n"
        else:
            html_content += "<h2>Current Standings</h2>\n"

        for division in divisions:
            html_content += f'<h2><a href="https://fantasy.espn.com/football/league?leagueId={division.league_id}" style="color: #3498db; text-decoration: none;">{division.name} 🔗</a> Standings</h2>\n'
            html_content += "<table>\n"
            html_content += '<tr><th>Rank</th><th>Team</th><th>Owner</th><th class="number">PF</th><th class="number">PA</th><th>Record</th></tr>\n'

            sorted_teams = self._get_sorted_teams_by_division(division)
            for i, team in enumerate(sorted_teams, 1):
                # Add asterisk to beginning of team name if in playoffs
                team_name = team.name
                if team.in_playoff_position:
                    team_name = f"* {team.name}"

                html_content += (
                    f"<tr>"
                    f"<td>{i}</td>"
                    f"<td>{self._escape_html(team_name)}</td>"
                    f"<td>{self._escape_html(team.owner.full_name)}</td>"
                    f'<td class="number">{team.points_for:.2f}</td>'
                    f'<td class="number">{team.points_against:.2f}</td>'
                    f"<td>{team.wins}-{team.losses}</td>"
                    f"</tr>\n"
                )

            html_content += "</table>\n"
            html_content += '<p style="margin-top: 15px; font-style: italic; color: #666;"><strong>*</strong> = Currently in playoff position</p>\n'

        # Overall top teams (labeled as historical if playoff mode)
        if is_playoff_mode:
            html_content += "<h2>Overall Top Teams (Final Regular Season - Week 14)</h2>\n"
        else:
            html_content += "<h2>Overall Top Teams (Across All Divisions)</h2>\n"
        html_content += "<table>\n"
        html_content += '<tr><th>Rank</th><th>Team</th><th>Owner</th><th>Division</th><th class="number">PF</th><th class="number">PA</th><th>Record</th></tr>\n'

        top_teams = self._get_overall_top_teams(divisions, limit=max_teams)
        for i, team in enumerate(top_teams, 1):
            # Add asterisk to beginning of team name if in playoffs
            team_name = team.name
            if team.in_playoff_position:
                team_name = f"* {team.name}"

            html_content += (
                f"<tr>"
                f"<td>{i}</td>"
                f"<td>{self._escape_html(team_name)}</td>"
                f"<td>{self._escape_html(team.owner.full_name)}</td>"
                f"<td>{self._escape_html(team.division)}</td>"
                f'<td class="number">{team.points_for:.2f}</td>'
                f'<td class="number">{team.points_against:.2f}</td>'
                f"<td>{team.wins}-{team.losses}</td>"
                f"</tr>\n"
            )

        html_content += "</table>\n"
        html_content += '<p style="margin-top: 15px; font-style: italic; color: #666;"><strong>*</strong> = Currently in playoff position</p>\n'

        # Footer section (always present)
        total_games = self._calculate_total_games(divisions)
        game_data_text = (
            f"Game data: {total_games} individual results processed"
            if total_games > 0
            else "Game data: Limited - some challenges may be incomplete"
        )

        html_content += f"""
        <div class="footer">
            {game_data_text}<br>
            <!-- GENERATED_METADATA_START --><!-- GENERATED_METADATA_END --><strong>Fantasy Football Challenge Tracker</strong> v{version("ff-awards")}<br>
            <a href="https://github.com/shaunburdick/ff_awards" style="color: #3498db; text-decoration: none;">View on GitHub 🔗</a>
        </div>
"""

        html_content += """
    </div>
</body>
</html>"""

        return html_content

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def _format_playoff_brackets(self, divisions: Sequence[DivisionData]) -> str:
        """Format playoff bracket matchups as HTML."""
        html_content = ""

        playoff_divisions = [d for d in divisions if d.playoff_bracket]
        if not playoff_divisions:
            return html_content

        bracket_round = (
            playoff_divisions[0].playoff_bracket.round
            if playoff_divisions[0].playoff_bracket
            else "Unknown"
        )

        html_content += '<div class="playoff-bracket">\n'
        html_content += f"<h2>🏆 Playoff Bracket - {bracket_round}</h2>\n"

        for div in playoff_divisions:
            if not div.playoff_bracket:
                continue

            html_content += f"<h3>{div.name}</h3>\n"

            for i, matchup in enumerate(div.playoff_bracket.matchups, 1):
                matchup_label = f"Semifinal {i}" if bracket_round == "Semifinals" else "Finals"

                html_content += '<div class="playoff-matchup">\n'
                html_content += f"<h4>{matchup_label}</h4>\n"

                # Team 1
                winner_class1 = " playoff-winner" if matchup.winner_seed == matchup.seed1 else ""
                html_content += f'<div class="playoff-team{winner_class1}">\n'
                html_content += f"  <span>#{matchup.seed1} {self._escape_html(matchup.team1_name)} ({self._escape_html(matchup.owner1_name)})</span>\n"
                html_content += f"  <strong>{matchup.team1_score:.2f}</strong>\n"
                html_content += "</div>\n"

                # Team 2
                winner_class2 = " playoff-winner" if matchup.winner_seed == matchup.seed2 else ""
                html_content += f'<div class="playoff-team{winner_class2}">\n'
                html_content += f"  <span>#{matchup.seed2} {self._escape_html(matchup.team2_name)} ({self._escape_html(matchup.owner2_name)})</span>\n"
                html_content += f"  <strong>{matchup.team2_score:.2f}</strong>\n"
                html_content += "</div>\n"

                html_content += "</div>\n"

        html_content += "</div>\n"

        return html_content

    def _format_championship_leaderboard(self, championship: ChampionshipLeaderboard) -> str:
        """Format championship leaderboard as HTML."""
        html_content = ""

        html_content += '<div class="championship-box">\n'
        html_content += "<h2>🏆 Championship Week - Final Leaderboard 🏆</h2>\n"
        html_content += "<p>Highest score wins overall championship</p>\n"

        html_content += "<table>\n"
        html_content += '<tr><th>Rank</th><th>Team</th><th>Owner</th><th>Division</th><th class="number">Score</th></tr>\n'

        for entry in championship.entries:
            medal = ""
            if entry.rank == 1:
                medal = "🥇 "
            elif entry.rank == 2:
                medal = "🥈 "
            elif entry.rank == 3:
                medal = "🥉 "

            html_content += (
                f"<tr>"
                f"<td>{medal}{entry.rank}</td>"
                f"<td>{self._escape_html(entry.team_name)}</td>"
                f"<td>{self._escape_html(entry.owner_name)}</td>"
                f"<td>{self._escape_html(entry.division_name)}</td>"
                f'<td class="number">{entry.score:.2f}</td>'
                f"</tr>\n"
            )

        html_content += "</table>\n"

        # Champion announcement
        champion = championship.champion
        html_content += '<div class="champion-announcement">\n'
        html_content += "🎉 <strong>OVERALL CHAMPION</strong> 🎉<br>\n"
        html_content += f"<strong>{self._escape_html(champion.team_name)}</strong><br>\n"
        html_content += f"{self._escape_html(champion.owner_name)}<br>\n"
        html_content += (
            f"{self._escape_html(champion.division_name)} Champion - {champion.score:.2f} points\n"
        )
        html_content += "</div>\n"

        html_content += "</div>\n"

        return html_content

    def _format_weekly_player_table(
        self, player_challenges: Sequence[WeeklyChallenge], current_week: int
    ) -> str:
        """Format weekly player highlights table for playoff mode."""
        html_content = ""

        html_content += '<div class="weekly-highlight">\n'
        html_content += f"<h2>⭐ Week {current_week} Player Highlights</h2>\n"
        html_content += "<table>\n"
        html_content += "<tr><th>Challenge</th><th>Player</th><th>Points</th></tr>\n"

        for challenge in player_challenges:
            # Include position in player display
            position = challenge.additional_info.get("position", "")
            winner_display = f"{challenge.winner} ({position})"

            html_content += (
                f"<tr>"
                f'<td class="challenge-name">{self._escape_html(challenge.challenge_name)}</td>'
                f'<td class="winner">{self._escape_html(winner_display)}</td>'
                f'<td class="number">{self._escape_html(challenge.value)}</td>'
                f"</tr>\n"
            )

        html_content += "</table>\n"
        html_content += "</div>\n"

        return html_content
