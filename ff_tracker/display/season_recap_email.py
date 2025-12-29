"""
Email HTML formatter for Season Recap.

Provides mobile-friendly HTML email format suitable for end-of-season summaries.
"""

from __future__ import annotations

from importlib.metadata import version

from ..models.season_summary import SeasonSummary


class SeasonRecapEmailFormatter:
    """Formatter for season recap HTML email output."""

    def __init__(self, year: int, format_args: dict[str, str] | None = None) -> None:
        """
        Initialize season recap email formatter.

        Args:
            year: Fantasy season year for display
            format_args: Optional dict of formatter-specific arguments
        """
        self.year = year
        self.format_args = format_args or {}

    @classmethod
    def get_supported_args(cls) -> dict[str, str]:
        """Return supported format arguments for email formatter."""
        return {
            "note": "Optional alert message displayed at top of email",
            "accent_color": "Hex color for highlight sections (default: #ffc107)",
        }

    def _get_arg(self, key: str, default: str | None = None) -> str | None:
        """
        Safely retrieve a format argument with optional default.

        Args:
            key: Argument name to retrieve
            default: Default value if argument not provided

        Returns:
            Argument value or default
        """
        return self.format_args.get(key, default)

    def format(self, summary: SeasonSummary) -> str:
        """
        Format complete season summary as mobile-friendly HTML email.

        Args:
            summary: Complete season summary data

        Returns:
            HTML string suitable for email delivery
        """
        # Get format arguments
        note = self._get_arg("note")
        accent_color = self._get_arg("accent_color", "#ffc107")

        # Get package version
        try:
            pkg_version = version("ff_tracker")
        except Exception:
            pkg_version = "unknown"

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Season Recap {self.year}</title>
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
            font-size: 20px;
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
        h3 {{
            color: #2c3e50;
            font-size: 14px;
            margin: 15px 0 10px 0;
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
        .championship-box table {{
            background-color: white;
            border-radius: 5px;
            overflow: hidden;
        }}
        .championship-box th {{
            background-color: #2c3e50;
            color: white;
        }}
        .championship-box td {{
            color: #2c3e50;
            background-color: white;
        }}
        .championship-box tr:nth-child(even) td {{
            background-color: #f8f9fa;
        }}
        .champion-announcement {{
            background-color: rgba(255,255,255,0.95);
            color: #2c3e50;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            font-size: 16px;
            border: 2px solid white;
        }}
        .champion-announcement strong {{
            color: #d63384;
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
        .playoff-division {{
            margin-bottom: 20px;
        }}
        .playoff-division h4 {{
            margin: 0 0 10px 0;
            color: #34495e;
            font-size: 14px;
            font-weight: bold;
        }}
        .playoff-matchup {{
            background-color: white;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
            border: 1px solid #bdc3c7;
        }}
        .playoff-team {{
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
        .season-highlight {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid {accent_color};
        }}
        .season-highlight h2 {{
            color: #856404;
            margin-top: 0;
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
                font-size: 18px;
            }}
            h2 {{
                font-size: 14px;
            }}
            h3 {{
                font-size: 12px;
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
        <h1>🏆 {self.year} Season Recap</h1>
        <div class="summary">
            {summary.total_divisions} divisions •
            Regular Season: Weeks {summary.structure.regular_season_start}-{summary.structure.regular_season_end}
"""

        if summary.playoffs:
            html_content += f" • Playoffs: Weeks {summary.structure.playoff_start}-{summary.structure.playoff_end}"

        if summary.championship:
            html_content += f" • Championship: Week {summary.structure.championship_week}"

        html_content += "\n        </div>\n"

        # Optional note
        if note:
            html_content += f"""
        <div class="alert-box">
            ⚠️ {note}
        </div>
"""

        # Championship results (if available)
        if summary.championship:
            html_content += """
        <div class="championship-box">
            <h2>🏆 Championship Week</h2>
            <p>Division Winners Compete for Overall Title</p>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Team</th>
                        <th>Owner</th>
                        <th>Division</th>
                        <th class="number">Score</th>
                    </tr>
                </thead>
                <tbody>
"""
            for entry in summary.championship.entries:
                champion_marker = "🏆 " if entry.rank == 1 else ""
                html_content += f"""
                    <tr>
                        <td>{entry.rank}</td>
                        <td>{champion_marker}{entry.team_name}</td>
                        <td>{entry.owner_name}</td>
                        <td>{entry.division_name}</td>
                        <td class="number">{entry.score:.2f}</td>
                    </tr>
"""

            html_content += """
                </tbody>
            </table>
"""

            if summary.overall_champion:
                html_content += f"""
            <div class="champion-announcement">
                <p><strong>🎉 Season Champion: {summary.overall_champion.team_name}</strong></p>
                <p>{summary.overall_champion.owner_name} from {summary.overall_champion.division_name} won with {summary.overall_champion.score:.2f} points!</p>
            </div>
"""

            html_content += """
        </div>
"""

        # Playoff results (reverse chronological: Finals → Semifinals)
        if summary.playoffs:
            # Finals (show first - most recent)
            if summary.playoffs.finals:
                html_content += f"""
        <div class="playoff-bracket">
            <h2>Finals - Week {summary.playoffs.finals.week}</h2>
"""
                for bracket in summary.playoffs.finals.division_brackets:
                    html_content += f"""
            <div class="playoff-division">
                <h4>{bracket.division_name}</h4>
"""
                    for matchup in bracket.matchups:
                        winner1 = (
                            " playoff-winner" if matchup.winner_name == matchup.team1_name else ""
                        )
                        winner2 = (
                            " playoff-winner" if matchup.winner_name == matchup.team2_name else ""
                        )
                        score1 = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
                        score2 = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"

                        html_content += f"""
                <div class="playoff-matchup">
                    <div class="playoff-team{winner1}">
                        #{matchup.seed1} {matchup.team1_name} ({matchup.owner1_name}) - {score1}
                    </div>
                    <div class="playoff-team{winner2}">
                        #{matchup.seed2} {matchup.team2_name} ({matchup.owner2_name}) - {score2}
                    </div>
                </div>
"""

                    html_content += """
            </div>
"""

                html_content += """
        </div>
"""

            # Semifinals (show second - earlier round)
            if summary.playoffs.semifinals:
                html_content += f"""
        <div class="playoff-bracket">
            <h2>Semifinals - Week {summary.playoffs.semifinals.week}</h2>
"""
                for bracket in summary.playoffs.semifinals.division_brackets:
                    html_content += f"""
            <div class="playoff-division">
                <h4>{bracket.division_name}</h4>
"""
                    for matchup in bracket.matchups:
                        winner1 = (
                            " playoff-winner" if matchup.winner_name == matchup.team1_name else ""
                        )
                        winner2 = (
                            " playoff-winner" if matchup.winner_name == matchup.team2_name else ""
                        )
                        score1 = f"{matchup.score1:.2f}" if matchup.score1 is not None else "TBD"
                        score2 = f"{matchup.score2:.2f}" if matchup.score2 is not None else "TBD"

                        html_content += f"""
                <div class="playoff-matchup">
                    <div class="playoff-team{winner1}">
                        #{matchup.seed1} {matchup.team1_name} ({matchup.owner1_name}) - {score1}
                    </div>
                    <div class="playoff-team{winner2}">
                        #{matchup.seed2} {matchup.team2_name} ({matchup.owner2_name}) - {score2}
                    </div>
                </div>
"""

                    html_content += """
            </div>
"""

                html_content += """
        </div>
"""

        # Regular season results
        html_content += """
        <h2>Regular Season Results</h2>

        <div class="season-highlight">
            <h3>Regular Season Division Champions</h3>
            <table>
                <thead>
                    <tr>
                        <th>Division</th>
                        <th>Team</th>
                        <th>Owner</th>
                        <th>Record</th>
                        <th class="number">PF</th>
                    </tr>
                </thead>
                <tbody>
"""

        for champion in summary.regular_season.division_champions:
            record = f"{champion.wins}-{champion.losses}"
            html_content += f"""
                    <tr>
                        <td>{champion.division_name}</td>
                        <td>{champion.team_name}</td>
                        <td>{champion.owner_name}</td>
                        <td>{record}</td>
                        <td class="number">{champion.points_for:.2f}</td>
                    </tr>
"""

        html_content += """
                </tbody>
            </table>
        </div>

        <div class="season-highlight">
            <h3>Season-Long Challenges</h3>
            <table>
                <thead>
                    <tr>
                        <th>Challenge</th>
                        <th>Winner</th>
                        <th>Division</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
"""

        for challenge in summary.season_challenges:
            html_content += f"""
                    <tr>
                        <td>{challenge.challenge_name}</td>
                        <td>{challenge.winner}</td>
                        <td>{challenge.division}</td>
                        <td>{challenge.value}</td>
                    </tr>
"""

        html_content += """
                </tbody>
            </table>
        </div>

        <h3>Final Standings</h3>
"""

        # Final standings by division
        for division_data in summary.regular_season.final_standings:
            html_content += f"""
        <h4>{division_data.name}</h4>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Team</th>
                    <th>Owner</th>
                    <th>Record</th>
                    <th class="number">PF</th>
                    <th class="number">PA</th>
                </tr>
            </thead>
            <tbody>
"""

            # Sort teams
            sorted_teams = sorted(
                division_data.teams, key=lambda t: (t.wins, t.points_for), reverse=True
            )

            for rank, team in enumerate(sorted_teams, start=1):
                record = f"{team.wins}-{team.losses}"
                owner_name = f"{team.owner.first_name} {team.owner.last_name}"
                html_content += f"""
                <tr>
                    <td>{rank}</td>
                    <td>{team.name}</td>
                    <td>{owner_name}</td>
                    <td>{record}</td>
                    <td class="number">{team.points_for:.2f}</td>
                    <td class="number">{team.points_against:.2f}</td>
                </tr>
"""

            html_content += """
            </tbody>
        </table>
"""

        # Footer
        html_content += f"""
        <div class="footer">
            Generated by Fantasy Football Challenge Tracker v{pkg_version}<br>
            <!-- GENERATED_METADATA_START --><!-- GENERATED_METADATA_END -->
        </div>
    </div>
</body>
</html>
"""

        return html_content
