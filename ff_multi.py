#!/usr/bin/env python3
"""
Fantasy Football Multi-Division Challenge Tracker

A CLI tool to track 5 specific fantasy football challenges across multiple divisions.

Usage:
    python ff_multi.py <league_id> [league_id2 ...] [--year YEAR] [--private]
    python ff_multi.py --env [--year YEAR] [--private]

Examples:
    # Single public league
    python ff_multi.py 123456789

    # Multiple leagues (divisions)
    python ff_multi.py 123456789 987654321 555444333

    # Use league IDs from .env file (LEAGUE_IDS=123456789,987654321,555444333)
    python ff_multi.py --env

    # Private leagues (requires .env file with ESPN_SWID and ESPN_S2)
    python ff_multi.py 123456789 --private
"""

import argparse
import os
import sys
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from datetime import datetime

from tabulate import tabulate
from dotenv import load_dotenv

try:
    from espn_api.football import League
except ImportError:
    print("Error: espn-api not installed. Please run: pip install espn-api tabulate python-dotenv")
    sys.exit(1)


@dataclass
class GameResult:
    """Container for individual game results"""
    team_name: str
    score: float
    opponent_name: str
    opponent_score: float
    won: bool
    week: int
    margin: float
    division: str


@dataclass
class ChallengeResult:
    """Container for challenge results"""
    challenge_name: str
    winner: str
    owner: str
    division: str
    value: str
    description: str


@dataclass
class TeamStats:
    """Container for team season statistics"""
    name: str
    owner: str
    points_for: float
    points_against: float
    wins: int
    losses: int
    division: str


@dataclass
class DivisionData:
    """Container for division (league) data"""
    league_id: int
    name: str
    teams: List[TeamStats]
    games: List[GameResult]


class MultiDivisionAnalyzer:
    """Analyzes multiple fantasy football leagues as divisions"""

    def __init__(self, league_ids: List[int], year: int = 2024, private: bool = False):
        self.league_ids = league_ids
        self.year = year
        self.private = private
        self.divisions: List[DivisionData] = []
        self.all_teams: List[TeamStats] = []
        self.all_games: List[GameResult] = []

    def connect_and_analyze(self) -> bool:
        """Connect to all leagues and analyze data"""
        load_dotenv()

        success_count = 0

        for i, league_id in enumerate(self.league_ids):
            print(f"\n🔍 Connecting to League {league_id}...")

            try:
                # Connect to league
                if self.private:
                    swid = os.getenv('ESPN_SWID')
                    s2 = os.getenv('ESPN_S2')

                    if not swid or not s2:
                        print(f"❌ Error: Private league requires ESPN_SWID and ESPN_S2 in .env file")
                        continue

                    league = League(league_id=league_id, year=self.year,
                                  espn_s2=s2, swid=swid)
                else:
                    league = League(league_id=league_id, year=self.year)

                # Get league name
                try:
                    settings = getattr(league, 'settings', None)
                    league_name = getattr(settings, 'name', f"Division {i+1}") if settings else f"Division {i+1}"
                except:
                    league_name = f"Division {i+1}"

                print(f"✅ Connected to: {league_name}")

                # Extract teams and games
                teams = self._extract_teams(league, league_name)
                games = self._extract_games(league, league_name)

                # Store division data
                division = DivisionData(
                    league_id=league_id,
                    name=league_name,
                    teams=teams,
                    games=games
                )
                self.divisions.append(division)

                # Add to overall collections
                self.all_teams.extend(teams)
                self.all_games.extend(games)

                success_count += 1
                print(f"📊 Processed {len(teams)} teams, {len(games)} games")

            except Exception as e:
                print(f"❌ Error connecting to league {league_id}: {e}")
                continue

        if success_count == 0:
            print("\n❌ Failed to connect to any leagues")
            return False

        print(f"\n✅ Successfully connected to {success_count}/{len(self.league_ids)} leagues")
        print(f"📊 Total: {len(self.all_teams)} teams, {len(self.all_games)} games")
        return True

    def _extract_teams(self, league: Any, division_name: str) -> List[TeamStats]:
        """Extract team stats from a league"""
        teams = []

        try:
            for team in league.teams:
                # Get team name
                team_name = getattr(team, 'team_name', None)
                if not team_name:
                    team_name = getattr(team, 'team_abbrev', None)
                if not team_name:
                    team_name = f"Team {getattr(team, 'team_id', 'Unknown')}"

                # Get owner name with comprehensive extraction
                owner = self._extract_owner_name(team)

                teams.append(TeamStats(
                    name=team_name,
                    owner=owner,
                    points_for=float(getattr(team, 'points_for', 0.0)),
                    points_against=float(getattr(team, 'points_against', 0.0)),
                    wins=int(getattr(team, 'wins', 0)),
                    losses=int(getattr(team, 'losses', 0)),
                    division=division_name
                ))

        except Exception as e:
            print(f"Warning: Error extracting teams: {e}")

        return teams

    def _extract_owner_name(self, team: Any) -> str:
        """Extract owner name from team object, prioritizing full names over usernames"""
        owner = "Unknown Owner"

        try:
            # Try multiple owner attributes
            owner_obj = getattr(team, 'owner', None)
            if not owner_obj:
                owner_obj = getattr(team, 'owners', None)

            if owner_obj:
                if isinstance(owner_obj, str):
                    owner = owner_obj
                elif hasattr(owner_obj, 'get') and callable(owner_obj.get):
                    # Dict-like with get method - PRIORITIZE REAL NAMES
                    first_name = str(owner_obj.get('firstName', '')).strip()
                    last_name = str(owner_obj.get('lastName', '')).strip()
                    display_name = str(owner_obj.get('displayName', '')).strip()

                    # Prefer first/last name combination over display name
                    if first_name and last_name:
                        owner = f"{first_name} {last_name}"
                    elif first_name:
                        owner = first_name
                    elif last_name:
                        owner = last_name
                    elif display_name and not self._looks_like_username(display_name):
                        # Only use display name if it looks like a real name
                        owner = display_name
                    elif display_name:
                        # Fallback to display name even if it looks like a username
                        owner = display_name

                elif hasattr(owner_obj, '__len__') and len(owner_obj) > 0:
                    # List-like objects
                    first_owner = owner_obj[0]
                    if hasattr(first_owner, 'get') and callable(first_owner.get):
                        first_name = str(first_owner.get('firstName', '')).strip()
                        last_name = str(first_owner.get('lastName', '')).strip()
                        display_name = str(first_owner.get('displayName', '')).strip()

                        if first_name and last_name:
                            owner = f"{first_name} {last_name}"
                        elif first_name:
                            owner = first_name
                        elif last_name:
                            owner = last_name
                        elif display_name:
                            owner = display_name
                        else:
                            owner = str(first_owner)
                    else:
                        owner = str(first_owner)

                elif hasattr(owner_obj, 'firstName') or hasattr(owner_obj, 'lastName'):
                    # Object with direct attributes - prioritize real names
                    first_name = str(getattr(owner_obj, 'firstName', '')).strip()
                    last_name = str(getattr(owner_obj, 'lastName', '')).strip()
                    display_name = str(getattr(owner_obj, 'displayName', '')).strip()

                    if first_name and last_name:
                        owner = f"{first_name} {last_name}"
                    elif first_name:
                        owner = first_name
                    elif last_name:
                        owner = last_name
                    elif display_name:
                        owner = display_name

                elif hasattr(owner_obj, 'displayName'):
                    # Object with displayName attribute
                    owner = str(owner_obj.displayName)

                elif hasattr(owner_obj, '__dict__'):
                    # Check object attributes dictionary
                    attrs = owner_obj.__dict__
                    first_name = str(attrs.get('firstName', '')).strip()
                    last_name = str(attrs.get('lastName', '')).strip()
                    display_name = str(attrs.get('displayName', '')).strip()

                    if first_name and last_name:
                        owner = f"{first_name} {last_name}"
                    elif first_name:
                        owner = first_name
                    elif last_name:
                        owner = last_name
                    elif display_name:
                        owner = display_name

                else:
                    owner_str = str(owner_obj)
                    if owner_str and owner_str != 'None':
                        owner = owner_str

        except Exception:
            pass

        return str(owner)

    def _looks_like_username(self, name: str) -> bool:
        """Check if a name looks like a username rather than a real name"""
        name = name.strip()
        if not name:
            return True

        # Common username patterns
        username_indicators = [
            name.startswith('ESPNFAN'),
            name.startswith('espn'),
            len(name) > 15 and any(c.isdigit() for c in name),  # Long names with numbers
            name.islower() and len(name) > 8,  # Long lowercase strings
            sum(c.isdigit() for c in name) > len(name) // 2,  # More than half digits
        ]

        return any(username_indicators)

    def _extract_games(self, league: Any, division_name: str) -> List[GameResult]:
        """Extract game results from a league"""
        games = []

        try:
            # Get current week and regular season length
            current_week = getattr(league, 'current_week', 1)
            settings = getattr(league, 'settings', None)
            reg_season_count = 14  # Default fallback

            if settings:
                reg_season_count = getattr(settings, 'reg_season_count', 14)

            # Determine max week to process
            # Exclude current week if it appears to be in progress (has very low scores)
            max_week_candidate = min(reg_season_count, current_week)

            # Check if current week seems incomplete by looking for suspiciously low scores
            current_week_complete = True
            if current_week <= reg_season_count:
                try:
                    current_box_scores = league.box_scores(current_week)
                    if current_box_scores:
                        for box_score in current_box_scores:
                            home_score = float(getattr(box_score, 'home_score', 0.0))
                            away_score = float(getattr(box_score, 'away_score', 0.0))
                            # If either team has very low score, week is likely incomplete
                            if (home_score > 0 and home_score < 30) or (away_score > 0 and away_score < 30):
                                current_week_complete = False
                                break
                except:
                    # If we can't check, assume it's incomplete
                    current_week_complete = False

            # If current week appears incomplete, exclude it
            if not current_week_complete and max_week_candidate == current_week:
                max_week = max_week_candidate - 1
                print(f"  📅 Excluding Week {current_week} (appears incomplete)")
            else:
                max_week = max_week_candidate

            # Process each completed week

            for week in range(1, max_week + 1):
                try:
                    box_scores = league.box_scores(week)

                    if not box_scores:
                        continue

                    for box_score in box_scores:
                        try:
                            home_team = getattr(box_score, 'home_team', None)
                            away_team = getattr(box_score, 'away_team', None)
                            home_score = float(getattr(box_score, 'home_score', 0.0))
                            away_score = float(getattr(box_score, 'away_score', 0.0))

                            if not home_team or not away_team or home_score <= 0 or away_score <= 0:
                                continue

                            # Get team names
                            home_name = getattr(home_team, 'team_name', None) or f"Team {getattr(home_team, 'team_id', 'Unknown')}"
                            away_name = getattr(away_team, 'team_name', None) or f"Team {getattr(away_team, 'team_id', 'Unknown')}"

                            margin = abs(home_score - away_score)

                            # Create game results for both teams
                            games.append(GameResult(
                                team_name=home_name,
                                score=home_score,
                                opponent_name=away_name,
                                opponent_score=away_score,
                                won=home_score > away_score,
                                week=week,
                                margin=margin,
                                division=division_name
                            ))

                            games.append(GameResult(
                                team_name=away_name,
                                score=away_score,
                                opponent_name=home_name,
                                opponent_score=home_score,
                                won=away_score > home_score,
                                week=week,
                                margin=margin,
                                division=division_name
                            ))

                        except Exception as e:
                            print(f"Warning: Error processing matchup in week {week}: {e}")
                            continue

                except Exception as e:
                    print(f"Warning: Could not get box scores for week {week}: {e}")
                    continue

        except Exception as e:
            print(f"Warning: Could not extract games: {e}")

        return games

    def _find_owner_for_team(self, team_name: str, division: str) -> str:
        """Find the owner name for a given team name and division"""
        for team in self.all_teams:
            if team.name == team_name and team.division == division:
                return team.owner
        return "Unknown Owner"

    def calculate_overall_challenges(self) -> List[ChallengeResult]:
        """Calculate challenges across all divisions"""
        if not self.all_teams:
            return []

        results = []

        # Challenge 1: Most Points Overall
        highest_scorer = max(self.all_teams, key=lambda x: x.points_for)
        results.append(ChallengeResult(
            challenge_name="Most Points Overall",
            winner=highest_scorer.name,
            owner=highest_scorer.owner,
            division=highest_scorer.division,
            value="",
            description=f"{highest_scorer.points_for:.1f} total points"
        ))

        if not self.all_games:
            # Add placeholders if no game data
            remaining_challenges = [
                ("Most Points in One Game", "Game data unavailable"),
                ("Most Points in a Loss", "Game data unavailable"),
                ("Least Points in a Win", "Game data unavailable"),
                ("Closest Victory", "Game data unavailable")
            ]

            for challenge_name, desc in remaining_challenges:
                results.append(ChallengeResult(
                    challenge_name=challenge_name,
                    winner="Data Unavailable",
                    owner="N/A",
                    division="N/A",
                    value="",
                    description=desc
                ))
            return results

        # Challenge 2: Most Points in One Game
        highest_game = max(self.all_games, key=lambda x: x.score)
        results.append(ChallengeResult(
            challenge_name="Most Points in One Game",
            winner=highest_game.team_name,
            owner=self._find_owner_for_team(highest_game.team_name, highest_game.division),
            division=highest_game.division,
            value="",
            description=f"{highest_game.score:.1f} points (Week {highest_game.week})"
        ))

        # Challenge 3: Most Points in a Loss
        losses = [game for game in self.all_games if not game.won]
        if losses:
            highest_loss = max(losses, key=lambda x: x.score)
            results.append(ChallengeResult(
                challenge_name="Most Points in a Loss",
                winner=highest_loss.team_name,
                owner=self._find_owner_for_team(highest_loss.team_name, highest_loss.division),
                division=highest_loss.division,
                value="",
                description=f"{highest_loss.score:.1f} points in loss (Week {highest_loss.week})"
            ))
        else:
            results.append(ChallengeResult(
                challenge_name="Most Points in a Loss",
                winner="No losses found",
                owner="N/A",
                division="N/A",
                value="",
                description="No losing games recorded yet"
            ))

        # Challenge 4: Least Points in a Win
        wins = [game for game in self.all_games if game.won]
        if wins:
            lowest_win = min(wins, key=lambda x: x.score)
            results.append(ChallengeResult(
                challenge_name="Least Points in a Win",
                winner=lowest_win.team_name,
                owner=self._find_owner_for_team(lowest_win.team_name, lowest_win.division),
                division=lowest_win.division,
                value="",
                description=f"{lowest_win.score:.1f} points in win (Week {lowest_win.week})"
            ))
        else:
            results.append(ChallengeResult(
                challenge_name="Least Points in a Win",
                winner="No wins found",
                owner="N/A",
                division="N/A",
                value="",
                description="No winning games recorded yet"
            ))

        # Challenge 5: Closest Victory
        if wins:
            closest_win = min(wins, key=lambda x: x.margin)
            results.append(ChallengeResult(
                challenge_name="Closest Victory",
                winner=closest_win.team_name,
                owner=self._find_owner_for_team(closest_win.team_name, closest_win.division),
                division=closest_win.division,
                value="",
                description=f"Won by {closest_win.margin:.1f} points (Week {closest_win.week})"
            ))
        else:
            results.append(ChallengeResult(
                challenge_name="Closest Victory",
                winner="No wins found",
                owner="N/A",
                division="N/A",
                value="",
                description="No winning games recorded yet"
            ))

        return results

    def display_results(self, sheets_format: bool = False, output_file: Optional[str] = None) -> None:
        """Display comprehensive results"""
        if sheets_format:
            self._output_sheets_format(output_file)
            return

        print(f"\n🏈 Fantasy Football Multi-Division Challenge Tracker ({self.year})")
        print(f"📊 {len(self.divisions)} divisions, {len(self.all_teams)} teams total")

        # Display division standings
        for division in self.divisions:
            print(f"\n🏆 {division.name} STANDINGS")
            division_table = []
            sorted_teams = sorted(division.teams, key=lambda x: (x.wins, x.points_for), reverse=True)

            for i, team in enumerate(sorted_teams, 1):
                division_table.append([
                    i,
                    team.name[:25],
                    team.owner[:20],
                    f"{team.points_for:.1f}",
                    f"{team.points_against:.1f}",
                    f"{team.wins}-{team.losses}"
                ])

            print(tabulate(division_table,
                         headers=["Rank", "Team", "Owner", "Points For", "Points Against", "Record"],
                         tablefmt="grid"))

        # Display overall standings (top teams across all divisions)
        print(f"\n🌟 OVERALL TOP TEAMS (Across All Divisions)")
        overall_table = []
        sorted_all_teams = sorted(self.all_teams, key=lambda x: (x.wins, x.points_for), reverse=True)[:20]  # Top 20

        for i, team in enumerate(sorted_all_teams, 1):
            overall_table.append([
                i,
                team.name[:20],
                team.owner[:15],
                team.division[:15],
                f"{team.points_for:.1f}",
                f"{team.points_against:.1f}",
                f"{team.wins}-{team.losses}"
            ])

        print(tabulate(overall_table,
                     headers=["Rank", "Team", "Owner", "Division", "Points For", "Points Against", "Record"],
                     tablefmt="grid"))

        # Display overall challenge results
        challenges = self.calculate_overall_challenges()
        if challenges:
            print(f"\n💰 OVERALL SEASON CHALLENGES")
            challenge_table = []
            for challenge in challenges:
                challenge_table.append([
                    challenge.challenge_name,
                    challenge.winner[:25],
                    challenge.owner[:20],
                    challenge.division[:15],
                    challenge.description[:35]
                ])

            print(tabulate(challenge_table,
                         headers=["Challenge", "Winner", "Owner", "Division", "Details"],
                         tablefmt="grid"))

            if self.all_games:
                print(f"📊 Game data: {len(self.all_games)} individual results processed")
            else:
                print("⚠️  Game data: Limited - some challenges may be incomplete")

    def _output_sheets_format(self, output_file: Optional[str] = None) -> None:
        """Output results in Google Sheets compatible TSV format"""
        output_lines = []

        # Header
        output_lines.append(f"Fantasy Football Multi-Division Challenge Tracker ({self.year})")
        output_lines.append(f"{len(self.divisions)} divisions, {len(self.all_teams)} teams total")
        output_lines.append("")

        # Division standings
        for division in self.divisions:
            output_lines.append(f"{division.name} STANDINGS")
            output_lines.append("Rank\tTeam\tOwner\tPoints For\tPoints Against\tRecord")

            sorted_teams = sorted(division.teams, key=lambda x: (x.wins, x.points_for), reverse=True)
            for i, team in enumerate(sorted_teams, 1):
                output_lines.append(f"{i}\t{team.name}\t{team.owner}\t{team.points_for:.1f}\t{team.points_against:.1f}\t{team.wins}-{team.losses}")

            output_lines.append("")

        # Overall top teams
        output_lines.append("OVERALL TOP TEAMS (Across All Divisions)")
        output_lines.append("Rank\tTeam\tOwner\tDivision\tPoints For\tPoints Against\tRecord")

        sorted_all_teams = sorted(self.all_teams, key=lambda x: (x.wins, x.points_for), reverse=True)[:20]
        for i, team in enumerate(sorted_all_teams, 1):
            output_lines.append(f"{i}\t{team.name}\t{team.owner}\t{team.division}\t{team.points_for:.1f}\t{team.points_against:.1f}\t{team.wins}-{team.losses}")

        output_lines.append("")

        # Challenge results
        challenges = self.calculate_overall_challenges()
        if challenges:
            output_lines.append("OVERALL SEASON CHALLENGES")
            output_lines.append("Challenge\tWinner\tOwner\tDivision\tDetails")

            for challenge in challenges:
                output_lines.append(f"{challenge.challenge_name}\t{challenge.winner}\t{challenge.owner}\t{challenge.division}\t{challenge.description}")

            output_lines.append("")

            if self.all_games:
                output_lines.append(f"Game data: {len(self.all_games)} individual results processed")
            else:
                output_lines.append("Game data: Limited - some challenges may be incomplete")

        # Output to file or console
        output_text = "\n".join(output_lines)

        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"✅ Google Sheets format saved to: {output_file}")
                print("💡 You can now copy the contents of this file and paste directly into Google Sheets")
            except Exception as e:
                print(f"❌ Error writing to file {output_file}: {e}")
        else:
            print("📋 GOOGLE SHEETS FORMAT (Copy and paste into Google Sheets)")
            print("=" * 70)
            print(output_text)
            print("=" * 70)
            print("💡 Copy the content above and paste directly into Google Sheets")


def parse_league_ids_from_env() -> List[int]:
    """Parse league IDs from environment variable"""
    load_dotenv()
    league_ids_str = os.getenv('LEAGUE_IDS', '')

    if not league_ids_str:
        print("Error: LEAGUE_IDS not found in .env file")
        print("Add to .env file: LEAGUE_IDS=123456789,987654321,555444333")
        return []

    try:
        league_ids = [int(id.strip()) for id in league_ids_str.split(',') if id.strip()]
        return league_ids
    except ValueError as e:
        print(f"Error parsing LEAGUE_IDS from .env file: {e}")
        print("Format should be: LEAGUE_IDS=123456789,987654321,555444333")
        return []


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Fantasy Football Multi-Division Challenge Tracker - Track 5 season challenges across divisions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ff_multi.py 123456789                         # Single league
  python ff_multi.py 123456789 987654321 555444333     # Multiple divisions
  python ff_multi.py --env                             # Use LEAGUE_IDS from .env
  python ff_multi.py --env --private                   # Private leagues from .env

For multiple leagues, create a .env file with:
  LEAGUE_IDS=123456789,987654321,555444333

For private leagues, also add:
  ESPN_SWID=your_swid_cookie
  ESPN_S2=your_s2_cookie
        """
    )

    parser.add_argument("league_ids", nargs="*", type=int, help="ESPN Fantasy Football League IDs")
    parser.add_argument("--year", type=int, default=datetime.now().year,
                       help="Fantasy season year (default: current year)")
    parser.add_argument("--private", action="store_true",
                       help="Private leagues (requires ESPN_SWID and ESPN_S2 in .env file)")
    parser.add_argument("--env", action="store_true",
                       help="Use league IDs from LEAGUE_IDS in .env file")
    parser.add_argument("--sheets", action="store_true",
                       help="Output in Google Sheets compatible format (TSV)")
    parser.add_argument("--output", type=str,
                       help="Save sheets output to file instead of printing to console")

    args = parser.parse_args()

    # Determine league IDs to use
    if args.env:
        league_ids = parse_league_ids_from_env()
        if not league_ids:
            sys.exit(1)
    elif args.league_ids:
        league_ids = args.league_ids
    else:
        print("Error: Must provide league IDs or use --env flag")
        parser.print_help()
        sys.exit(1)

    print("🏈 Fantasy Football Multi-Division Challenge Tracker")
    print("=" * 60)
    print(f"📅 Season: {args.year}")
    print(f"📊 Analyzing {len(league_ids)} league(s): {league_ids}")

    # Create analyzer and run
    analyzer = MultiDivisionAnalyzer(league_ids, args.year, args.private)

    if not analyzer.connect_and_analyze():
        sys.exit(1)

    analyzer.display_results(sheets_format=args.sheets, output_file=args.output)


if __name__ == "__main__":
    main()