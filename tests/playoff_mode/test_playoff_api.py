#!/usr/bin/env python3
"""
Test script to inspect ESPN API playoff data structure.

This script will help us understand:
1. How to detect playoff weeks
2. How playoff matchups are structured
3. How seeding information is available
4. What playoff-specific fields exist
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from espn_api.football import League


def main() -> None:
    """Inspect ESPN API playoff data structure."""

    # Load environment variables
    load_dotenv()

    # Get league configuration
    league_ids_str = os.getenv("LEAGUE_IDS", "")
    if not league_ids_str:
        print("ERROR: LEAGUE_IDS not set in .env file")
        return

    league_ids = [int(lid.strip()) for lid in league_ids_str.split(",")]
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    year = 2025  # Current season

    print(f"Testing with {len(league_ids)} leagues for year {year}")
    print("=" * 80)

    for league_id in league_ids:
        print(f"\n🏈 LEAGUE {league_id}")
        print("-" * 80)

        # Connect to league
        if espn_s2 and swid:
            league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
        else:
            league = League(league_id=league_id, year=year)

        # Basic league info
        print(f"League Name: {league.settings.name}")
        print(f"Current Week: {league.current_week}")
        print(f"Regular Season Weeks: {league.settings.reg_season_count}")
        print(f"Playoff Team Count: {league.settings.playoff_team_count}")
        print(f"Playoff Matchup Period Length: {league.settings.playoff_matchup_period_length}")
        print(f"Playoff Seed Tie Rule: {league.settings.playoff_seed_tie_rule}")

        # Check if we're in playoffs
        in_playoffs = league.current_week > league.settings.reg_season_count
        print(f"\n📊 Status: {'PLAYOFFS' if in_playoffs else 'REGULAR SEASON'}")

        # Inspect current week's matchups
        print(f"\n📅 Week {league.current_week} Matchups:")
        try:
            box_scores = league.box_scores(league.current_week)
            for i, box_score in enumerate(box_scores, 1):
                print(f"\n  Matchup {i}:")
                print(f"    is_playoff: {box_score.is_playoff}")
                print(f"    matchup_type: {box_score.matchup_type}")
                print(
                    f"    Home: {box_score.home_team.team_name} (standing: {box_score.home_team.standing})"
                )
                print(
                    f"    Away: {box_score.away_team.team_name} (standing: {box_score.away_team.standing})"
                )
                print(f"    Score: {box_score.home_score} - {box_score.away_score}")
        except Exception as e:
            print(f"  ERROR getting box scores: {e}")

        # Team standings and playoff info
        print("\n📋 Team Standings (with playoff info):")
        for team in sorted(league.teams, key=lambda t: t.standing):
            print(
                f"  {team.standing:2d}. {team.team_name:30s} "
                f"({team.wins}-{team.losses}) "
                f"- standing: {team.standing}, "
                f"final_standing: {team.final_standing}, "
                f"playoff_pct: {team.playoff_pct:.3f}"
            )

        # Check if there's matchup_periods data
        print("\n🗓️  Matchup Periods:")
        print(f"  {league.settings.matchup_periods}")

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
