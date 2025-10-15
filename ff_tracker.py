#!/usr/bin/env python3
"""
Fantasy Football Challenge Tracker

A simple CLI tool to track 5 specific fantasy football challenges for cash payouts.

Usage:
    python ff_tracker.py <league_id> [--year YEAR] [--private]

Examples:
    # Public league
    python ff_tracker.py 123456789

    # Private league (requires .env file with ESPN_SWID and ESPN_S2)
    python ff_tracker.py 123456789 --private

    # Specific year
    python ff_tracker.py 123456789 --year 2023
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


@dataclass
class ChallengeResult:
    """Container for challenge results"""
    challenge_name: str
    winner: str
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


class FantasyLeagueAnalyzer:
    """Analyzes fantasy football league data for challenges"""

    def __init__(self, league_id: int, year: int = 2024, private: bool = False):
        self.league_id = league_id
        self.year = year
        self.private = private
        self.league: Optional[Any] = None
        self.game_results: List[GameResult] = []

    def connect_to_league(self) -> bool:
        """Connect to ESPN Fantasy Football league"""
        try:
            if self.private:
                load_dotenv()
                swid = os.getenv('ESPN_SWID')
                s2 = os.getenv('ESPN_S2')

                if not swid or not s2:
                    print("Error: Private league requires ESPN_SWID and ESPN_S2 in .env file")
                    print("Create a .env file with:")
                    print("ESPN_SWID=your_swid_here")
                    print("ESPN_S2=your_s2_here")
                    return False

                self.league = League(league_id=self.league_id, year=self.year,
                                   espn_s2=s2, swid=swid)
            else:
                self.league = League(league_id=self.league_id, year=self.year)

            # Test connection by accessing teams
            teams = self.league.teams
            if not teams:
                print("Warning: No teams found in league")
                return False

            return True

        except Exception as e:
            print(f"Error connecting to league: {e}")
            if "does not exist" in str(e):
                print("League ID may be incorrect or league may be private")
            elif "private" in str(e).lower():
                print("League appears to be private. Try using --private flag")
            return False

    def get_team_stats(self) -> List[TeamStats]:
        """Get basic team statistics"""
        if not self.league:
            return []

        stats: List[TeamStats] = []

        try:
            for team in self.league.teams:
                # Get team name with fallbacks
                team_name = getattr(team, 'team_name', None)
                if not team_name:
                    team_name = getattr(team, 'team_abbrev', None)
                if not team_name:
                    team_name = f"Team {getattr(team, 'team_id', 'Unknown')}"

                # Get owner name with comprehensive extraction
                owner = "Unknown Owner"
                try:
                    # Try multiple owner attributes that ESPN API might use
                    owner_obj = getattr(team, 'owner', None)
                    if not owner_obj:
                        owner_obj = getattr(team, 'owners', None)

                    if owner_obj:
                        # Method 1: Direct string
                        if isinstance(owner_obj, str):
                            owner = owner_obj
                        # Method 2: Dict-like with get method
                        elif hasattr(owner_obj, 'get') and callable(owner_obj.get):
                            display_name = owner_obj.get('displayName', '')
                            first_name = owner_obj.get('firstName', '')
                            last_name = owner_obj.get('lastName', '')

                            if display_name:
                                owner = display_name
                            elif first_name or last_name:
                                owner = f"{first_name} {last_name}".strip()
                        # Method 3: List-like objects
                        elif hasattr(owner_obj, '__len__') and len(owner_obj) > 0:
                            first_owner = owner_obj[0]
                            if hasattr(first_owner, 'get') and callable(first_owner.get):
                                display_name = first_owner.get('displayName', '')
                                first_name = first_owner.get('firstName', '')
                                last_name = first_owner.get('lastName', '')

                                if display_name:
                                    owner = display_name
                                elif first_name or last_name:
                                    owner = f"{first_name} {last_name}".strip()
                                else:
                                    owner = str(first_owner)
                            else:
                                owner = str(first_owner)
                        # Method 4: Object with attributes
                        elif hasattr(owner_obj, 'displayName'):
                            owner = str(owner_obj.displayName)
                        elif hasattr(owner_obj, 'firstName') or hasattr(owner_obj, 'lastName'):
                            first = getattr(owner_obj, 'firstName', '')
                            last = getattr(owner_obj, 'lastName', '')
                            owner = f"{first} {last}".strip()
                        # Method 5: Try common ESPN API patterns
                        elif hasattr(owner_obj, '__dict__'):
                            # Check for common ESPN API owner fields
                            attrs = owner_obj.__dict__
                            if 'displayName' in attrs:
                                owner = str(attrs['displayName'])
                            elif 'firstName' in attrs or 'lastName' in attrs:
                                first = attrs.get('firstName', '')
                                last = attrs.get('lastName', '')
                                owner = f"{first} {last}".strip()
                        # Method 6: Fallback to string conversion
                        else:
                            owner_str = str(owner_obj)
                            if owner_str and owner_str != 'None':
                                owner = owner_str

                    # Ensure owner is always a string
                    if not isinstance(owner, str):
                        owner = str(owner)

                except Exception:
                    pass  # Keep default "Unknown Owner"

                # Ensure owner is definitely a string
                owner_str = str(owner) if owner else "Unknown Owner"

                stats.append(TeamStats(
                    name=team_name,
                    owner=owner_str,
                    points_for=float(getattr(team, 'points_for', 0.0)),
                    points_against=float(getattr(team, 'points_against', 0.0)),
                    wins=int(getattr(team, 'wins', 0)),
                    losses=int(getattr(team, 'losses', 0))
                ))

        except Exception as e:
            print(f"Warning: Error getting team stats: {e}")

        return sorted(stats, key=lambda x: x.points_for, reverse=True)

    def extract_game_results(self) -> None:
        """Extract individual game results from league data"""
        if not self.league:
            return

        self.game_results = []

        try:
            # Get current week and regular season length
            current_week = getattr(self.league, 'current_week', 1)
            settings = getattr(self.league, 'settings', None)
            reg_season_count = 14  # Default fallback

            if settings:
                reg_season_count = getattr(settings, 'reg_season_count', 14)

            # Process each week of the regular season
            max_week = min(reg_season_count, current_week)

            for week in range(1, max_week + 1):
                try:
                    box_scores = self.league.box_scores(week)

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
                            self.game_results.append(GameResult(
                                team_name=home_name,
                                score=home_score,
                                opponent_name=away_name,
                                opponent_score=away_score,
                                won=home_score > away_score,
                                week=week,
                                margin=margin
                            ))

                            self.game_results.append(GameResult(
                                team_name=away_name,
                                score=away_score,
                                opponent_name=home_name,
                                opponent_score=home_score,
                                won=away_score > home_score,
                                week=week,
                                margin=margin
                            ))

                        except Exception as e:
                            print(f"Warning: Error processing matchup in week {week}: {e}")
                            continue

                except Exception as e:
                    print(f"Warning: Could not get box scores for week {week}: {e}")
                    continue

        except Exception as e:
            print(f"Warning: Could not extract game results: {e}")

    def calculate_challenges(self) -> List[ChallengeResult]:
        """Calculate the 5 fantasy football challenges"""
        if not self.league:
            return []

        results: List[ChallengeResult] = []
        team_stats = self.get_team_stats()

        # Challenge 1: Most Points Overall
        if team_stats:
            winner = team_stats[0]  # Already sorted by points_for descending
            results.append(ChallengeResult(
                challenge_name="Most Points Overall",
                winner=f"{winner.name} ({winner.owner})",
                value="$30",
                description=f"{winner.points_for:.1f} total points"
            ))

        # Extract game-by-game data for remaining challenges
        self.extract_game_results()

        if not self.game_results:
            # Add placeholders for challenges that need game data
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
                    value="$30",
                    description=desc
                ))
            return results

        # Challenge 2: Most Points in One Game
        highest_scoring_game = max(self.game_results, key=lambda x: x.score)
        results.append(ChallengeResult(
            challenge_name="Most Points in One Game",
            winner=highest_scoring_game.team_name,
            value="$30",
            description=f"{highest_scoring_game.score:.1f} points (Week {highest_scoring_game.week})"
        ))

        # Challenge 3: Most Points in a Loss
        losses = [game for game in self.game_results if not game.won]
        if losses:
            highest_scoring_loss = max(losses, key=lambda x: x.score)
            results.append(ChallengeResult(
                challenge_name="Most Points in a Loss",
                winner=highest_scoring_loss.team_name,
                value="$30",
                description=f"{highest_scoring_loss.score:.1f} points in loss (Week {highest_scoring_loss.week})"
            ))
        else:
            results.append(ChallengeResult(
                challenge_name="Most Points in a Loss",
                winner="No losses found",
                value="$30",
                description="No losing games recorded yet"
            ))

        # Challenge 4: Least Points in a Win
        wins = [game for game in self.game_results if game.won]
        if wins:
            lowest_scoring_win = min(wins, key=lambda x: x.score)
            results.append(ChallengeResult(
                challenge_name="Least Points in a Win",
                winner=lowest_scoring_win.team_name,
                value="$30",
                description=f"{lowest_scoring_win.score:.1f} points in win (Week {lowest_scoring_win.week})"
            ))
        else:
            results.append(ChallengeResult(
                challenge_name="Least Points in a Win",
                winner="No wins found",
                value="$30",
                description="No winning games recorded yet"
            ))

        # Challenge 5: Closest Victory
        if wins:
            closest_victory = min(wins, key=lambda x: x.margin)
            results.append(ChallengeResult(
                challenge_name="Closest Victory",
                winner=closest_victory.team_name,
                value="$30",
                description=f"Won by {closest_victory.margin:.1f} points (Week {closest_victory.week})"
            ))
        else:
            results.append(ChallengeResult(
                challenge_name="Closest Victory",
                winner="No wins found",
                value="$30",
                description="No winning games recorded yet"
            ))

        return results

    def display_results(self) -> None:
        """Display formatted results"""
        if not self.league:
            print("Error: Not connected to league")
            return

        # Display league info
        try:
            settings = getattr(self.league, 'settings', None)
            league_name = getattr(settings, 'name', f"League {self.league_id}") if settings else f"League {self.league_id}"
            print(f"\n🏈 {league_name} ({self.year})")
        except Exception:
            print(f"\n🏈 League {self.league_id} ({self.year})")

        # Display team standings
        team_stats = self.get_team_stats()
        if team_stats:
            print("\n📊 LEAGUE STANDINGS")
            standings_table = []
            for i, team in enumerate(team_stats, 1):
                standings_table.append([
                    i,
                    team.name[:25],  # Truncate long names
                    team.owner[:20],
                    f"{team.points_for:.1f}",
                    f"{team.wins}-{team.losses}"
                ])

            print(tabulate(standings_table,
                         headers=["Rank", "Team", "Owner", "Points For", "Record"],
                         tablefmt="grid"))

        # Display challenge results
        challenges = self.calculate_challenges()
        if challenges:
            print("\n💰 SEASON CHALLENGES ($30 Each)")
            challenge_table = []
            for challenge in challenges:
                challenge_table.append([
                    challenge.challenge_name,
                    challenge.winner[:30],  # Truncate long names
                    challenge.value,
                    challenge.description[:50]  # Truncate long descriptions
                ])

            print(tabulate(challenge_table,
                         headers=["Challenge", "Winner", "Value", "Details"],
                         tablefmt="grid"))

            total_payout = len([c for c in challenges if c.winner != "Data Unavailable" and c.winner != "No losses found" and c.winner != "No wins found"]) * 30
            print(f"\n💵 Total Payout Pool: ${total_payout}")

            # Show game data status
            if self.game_results:
                print(f"📊 Game data: {len(self.game_results)} individual results processed")
            else:
                print("⚠️  Game data: Limited - some challenges may be incomplete")


def main() -> None:
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Fantasy Football Challenge Tracker - Track 5 season challenges worth $30 each",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ff_tracker.py 123456789                    # Public league, current year
  python ff_tracker.py 123456789 --private          # Private league (needs .env)
  python ff_tracker.py 123456789 --year 2023        # Specific year
  python ff_tracker.py 123456789 --private --year 2023 # Private league, specific year

For private leagues, create a .env file with:
  ESPN_SWID=your_swid_cookie
  ESPN_S2=your_s2_cookie
        """
    )

    parser.add_argument("league_id", type=int, help="ESPN Fantasy Football League ID")
    parser.add_argument("--year", type=int, default=datetime.now().year,
                       help="Fantasy season year (default: current year)")
    parser.add_argument("--private", action="store_true",
                       help="Private league (requires ESPN_SWID and ESPN_S2 in .env file)")

    args = parser.parse_args()

    print("🏈 Fantasy Football Challenge Tracker")
    print("=" * 50)

    # Create analyzer and run
    analyzer = FantasyLeagueAnalyzer(args.league_id, args.year, args.private)

    if not analyzer.connect_to_league():
        print("\n❌ Failed to connect to league. Please check:")
        print("  1. League ID is correct")
        print("  2. League exists for the specified year")
        print("  3. If private, .env file has ESPN_SWID and ESPN_S2")
        print("  4. You have access to this league")
        sys.exit(1)

    print("✅ Successfully connected to league!")
    analyzer.display_results()


if __name__ == "__main__":
    main()