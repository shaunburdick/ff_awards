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

from ..models import ChallengeResult, DivisionData, WeeklyChallenge
from .base import BaseFormatter


class EmailFormatter(BaseFormatter):
    """Formatter for mobile-friendly HTML email output."""

    def __init__(self, year: int) -> None:
        """
        Initialize email formatter.

        Args:
            year: Fantasy season year for display
        """
        super().__init__()
        self.year = year

    def format_output(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None = None,
        current_week: int | None = None
    ) -> str:
        """Format complete output for mobile-friendly HTML email."""
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
        .weekly-highlight {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #ffc107;
        }}
        .weekly-highlight h2 {{
            color: #856404;
            margin-top: 0;
        }}
        .winner {{
            color: #27ae60;
            font-weight: bold;
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

        # Weekly highlights (at the top for email - most relevant)
        if weekly_challenges and current_week:
            # Split into team and player challenges
            team_challenges = [c for c in weekly_challenges if "position" not in c.additional_info]
            player_challenges = [c for c in weekly_challenges if "position" in c.additional_info]

            html_content += '<div class="weekly-highlight">\n'
            html_content += f'<h2>🔥 Week {current_week} Highlights</h2>\n'

            # Team challenges
            if team_challenges:
                html_content += '<h3>Team Challenges</h3>\n'
                html_content += '<table>\n'
                html_content += '<tr><th>Challenge</th><th>Team</th><th>Division</th><th>Value</th></tr>\n'

                for challenge in team_challenges:
                    html_content += (
                        f'<tr>'
                        f'<td class="challenge-name">{self._escape_html(challenge.challenge_name)}</td>'
                        f'<td class="winner">{self._escape_html(challenge.winner)}</td>'
                        f'<td>{self._escape_html(challenge.division)}</td>'
                        f'<td class="number">{self._escape_html(challenge.value)}</td>'
                        f'</tr>\n'
                    )

                html_content += '</table>\n'

            # Player highlights
            if player_challenges:
                html_content += '<h3>Player Highlights</h3>\n'
                html_content += '<table>\n'
                html_content += '<tr><th>Challenge</th><th>Player</th><th>Points</th></tr>\n'

                for challenge in player_challenges:
                    # Include position in player display
                    position = challenge.additional_info.get("position", "")
                    winner_display = f"{challenge.winner} ({position})"

                    html_content += (
                        f'<tr>'
                        f'<td class="challenge-name">{self._escape_html(challenge.challenge_name)}</td>'
                        f'<td class="winner">{self._escape_html(winner_display)}</td>'
                        f'<td class="number">{self._escape_html(challenge.value)}</td>'
                        f'</tr>\n'
                    )

                html_content += '</table>\n'

            html_content += '</div>\n'

        # Division standings
        for division in divisions:
            html_content += f'<h2><a href="https://fantasy.espn.com/football/league?leagueId={division.league_id}" style="color: #3498db; text-decoration: none;">{division.name} 🔗</a> Standings</h2>\n'
            html_content += '<table>\n'
            html_content += '<tr><th>Rank</th><th>Team</th><th>Owner</th><th class="number">PF</th><th class="number">PA</th><th>Record</th></tr>\n'

            sorted_teams = self._get_sorted_teams_by_division(division)
            for i, team in enumerate(sorted_teams, 1):
                # Add asterisk to beginning of team name if in playoffs
                team_name = team.name
                if team.in_playoff_position:
                    team_name = f"* {team.name}"

                html_content += (
                    f'<tr>'
                    f'<td>{i}</td>'
                    f'<td>{self._escape_html(team_name)}</td>'
                    f'<td>{self._escape_html(team.owner.full_name)}</td>'
                    f'<td class="number">{team.points_for:.2f}</td>'
                    f'<td class="number">{team.points_against:.2f}</td>'
                    f'<td>{team.wins}-{team.losses}</td>'
                    f'</tr>\n'
                )

            html_content += '</table>\n'
            html_content += '<p style="margin-top: 15px; font-style: italic; color: #666;"><strong>*</strong> = Currently in playoff position</p>\n'


        # Overall top teams
        html_content += '<h2>Overall Top Teams (Across All Divisions)</h2>\n'
        html_content += '<table>\n'
        html_content += '<tr><th>Rank</th><th>Team</th><th>Owner</th><th>Division</th><th class="number">PF</th><th class="number">PA</th><th>Record</th></tr>\n'

        top_teams = self._get_overall_top_teams(divisions, limit=20)
        for i, team in enumerate(top_teams, 1):
            # Add asterisk to beginning of team name if in playoffs
            team_name = team.name
            if team.in_playoff_position:
                team_name = f"* {team.name}"

            html_content += (
                f'<tr>'
                f'<td>{i}</td>'
                f'<td>{self._escape_html(team_name)}</td>'
                f'<td>{self._escape_html(team.owner.full_name)}</td>'
                f'<td>{self._escape_html(team.division)}</td>'
                f'<td class="number">{team.points_for:.2f}</td>'
                f'<td class="number">{team.points_against:.2f}</td>'
                f'<td>{team.wins}-{team.losses}</td>'
                f'</tr>\n'
            )

        html_content += '</table>\n'
        html_content += '<p style="margin-top: 15px; font-style: italic; color: #666;"><strong>*</strong> = Currently in playoff position</p>\n'

        # Challenge results
        if challenges:
            html_content += '<h2>Season Challenge Results</h2>\n'
            html_content += '<table class="challenge-table">\n'
            html_content += '<tr><th>Challenge</th><th>Winner</th><th>Owner</th><th>Division</th><th>Details</th></tr>\n'

            for challenge in challenges:
                html_content += (
                    f'<tr>'
                    f'<td class="challenge-name">{self._escape_html(challenge.challenge_name)}</td>'
                    f'<td class="winner">{self._escape_html(challenge.winner)}</td>'
                    f'<td>{self._escape_html(challenge.owner.full_name)}</td>'
                    f'<td>{self._escape_html(challenge.division)}</td>'
                    f'<td>{self._escape_html(challenge.description)}</td>'
                    f'</tr>\n'
                )

            html_content += '</table>\n'

        # Footer section (always present)
        total_games = self._calculate_total_games(divisions)
        game_data_text = f'Game data: {total_games} individual results processed' if total_games > 0 else 'Game data: Limited - some challenges may be incomplete'

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
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))
