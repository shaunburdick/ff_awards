"""
Weekly Challenge calculation service.

This module handles the business logic for calculating week-specific challenges
from collected fantasy football data.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from ..exceptions import InsufficientDataError
from ..models import WeeklyChallenge, WeeklyGameResult, WeeklyPlayerStats

# Logger for this module
logger = logging.getLogger(__name__)


class WeeklyChallengeCalculator:
    """
    Service for calculating weekly fantasy football challenges.

    Implements the business logic for week-specific challenges:
    Team Challenges:
    1. Highest Score This Week
    2. Lowest Score This Week
    3. Biggest Win This Week
    4. Closest Game This Week
    5. Most Over Projection
    6. Most Under Projection

    Player Challenges:
    7. Top Scorer (Overall)
    8. Top Scorer by Position (QB, RB, WR, TE, K, D/ST)
    9. Biggest Boom (exceeded projection most)
    10. Biggest Bust (underperformed projection most)
    """

    def __init__(self) -> None:
        """Initialize the weekly challenge calculator."""
        pass

    def calculate_all_weekly_challenges(
        self,
        weekly_games: Sequence[WeeklyGameResult],
        weekly_players: Sequence[WeeklyPlayerStats],
        week: int
    ) -> list[WeeklyChallenge]:
        """
        Calculate all weekly challenges.

        Args:
            weekly_games: List of weekly game results
            weekly_players: List of weekly player stats
            week: Week number these challenges are for

        Returns:
            List of weekly challenge results

        Raises:
            InsufficientDataError: If there's not enough data to calculate challenges
        """
        if week < 1 or week > 18:
            raise InsufficientDataError(f"Invalid week number: {week}")

        results: list[WeeklyChallenge] = []

        # Team-based challenges (require game data)
        if weekly_games:
            logger.info(f"Calculating team challenges for week {week} with {len(weekly_games)} games")
            results.append(self._calculate_highest_score(weekly_games, week))
            results.append(self._calculate_lowest_score(weekly_games, week))
            results.append(self._calculate_biggest_win(weekly_games, week))
            results.append(self._calculate_closest_game(weekly_games, week))
            results.append(self._calculate_most_over_projection(weekly_games, week))
            results.append(self._calculate_most_under_projection(weekly_games, week))
        else:
            logger.warning(f"No weekly game data for week {week}, skipping team challenges")

        # Player-based challenges (require player data)
        if weekly_players:
            # Filter to starters only for player challenges
            starters = [p for p in weekly_players if p.is_starter]
            logger.info(
                f"Calculating player challenges for week {week} with "
                f"{len(starters)} starters from {len(weekly_players)} total players"
            )

            if starters:
                results.append(self._calculate_top_player(starters, week))
                results.extend(self._calculate_top_by_position(starters, week))
                results.append(self._calculate_biggest_boom(starters, week))
                results.append(self._calculate_biggest_bust(starters, week))
            else:
                logger.warning(f"No starter data for week {week}, skipping player challenges")
        else:
            logger.warning(f"No weekly player data for week {week}, skipping player challenges")

        logger.info(f"Calculated {len(results)} weekly challenge results for week {week}")
        return results

    def _calculate_highest_score(
        self,
        games: Sequence[WeeklyGameResult],
        week: int
    ) -> WeeklyChallenge:
        """Find team with highest score this week."""
        winner = max(games, key=lambda g: g.score)

        return WeeklyChallenge(
            challenge_name="Highest Score This Week",
            week=week,
            winner=winner.team_name,
            owner=None,  # Will need to be filled in by caller if needed
            division=winner.division,
            value=f"{winner.score:.2f}",
            description=f"{winner.team_name} scored {winner.score:.2f} points",
            additional_info={
                "opponent": winner.opponent_name,
                "opponent_score": winner.opponent_score,
                "won": winner.won
            }
        )

    def _calculate_lowest_score(
        self,
        games: Sequence[WeeklyGameResult],
        week: int
    ) -> WeeklyChallenge:
        """Find team with lowest score this week."""
        winner = min(games, key=lambda g: g.score)

        return WeeklyChallenge(
            challenge_name="Lowest Score This Week",
            week=week,
            winner=winner.team_name,
            owner=None,
            division=winner.division,
            value=f"{winner.score:.2f}",
            description=f"{winner.team_name} scored only {winner.score:.2f} points",
            additional_info={
                "opponent": winner.opponent_name,
                "opponent_score": winner.opponent_score,
                "won": winner.won
            }
        )

    def _calculate_biggest_win(
        self,
        games: Sequence[WeeklyGameResult],
        week: int
    ) -> WeeklyChallenge:
        """Find largest margin of victory this week."""
        # Only consider games that were won
        wins = [g for g in games if g.won]

        if not wins:
            # Return placeholder if no wins (shouldn't happen)
            return self._create_no_data_placeholder("Biggest Win This Week", week)

        winner = max(wins, key=lambda g: g.margin)

        return WeeklyChallenge(
            challenge_name="Biggest Win This Week",
            week=week,
            winner=winner.team_name,
            owner=None,
            division=winner.division,
            value=f"{winner.margin:.2f} pts",
            description=f"{winner.team_name} won by {winner.margin:.2f} points",
            additional_info={
                "score": winner.score,
                "opponent": winner.opponent_name,
                "opponent_score": winner.opponent_score
            }
        )

    def _calculate_closest_game(
        self,
        games: Sequence[WeeklyGameResult],
        week: int
    ) -> WeeklyChallenge:
        """Find smallest margin (win or loss) this week."""
        winner = min(games, key=lambda g: g.margin)

        result_type = "won" if winner.won else "lost"

        return WeeklyChallenge(
            challenge_name="Closest Game This Week",
            week=week,
            winner=winner.team_name,
            owner=None,
            division=winner.division,
            value=f"{winner.margin:.2f} pts",
            description=f"{winner.team_name} {result_type} by only {winner.margin:.2f} points",
            additional_info={
                "score": winner.score,
                "opponent": winner.opponent_name,
                "opponent_score": winner.opponent_score,
                "won": winner.won
            }
        )

    def _calculate_most_over_projection(
        self,
        games: Sequence[WeeklyGameResult],
        week: int
    ) -> WeeklyChallenge:
        """Find team that exceeded projection by most."""
        winner = max(games, key=lambda g: g.projection_diff)

        return WeeklyChallenge(
            challenge_name="Most Over Projection",
            week=week,
            winner=winner.team_name,
            owner=None,
            division=winner.division,
            value=f"+{winner.projection_diff:.2f}",
            description=(
                f"{winner.team_name} exceeded projection by {winner.projection_diff:.2f} "
                f"({winner.score:.2f} actual vs {winner.projected_score:.2f} projected)"
            ),
            additional_info={
                "score": winner.score,
                "projected": winner.projected_score,
                "won": winner.won
            }
        )

    def _calculate_most_under_projection(
        self,
        games: Sequence[WeeklyGameResult],
        week: int
    ) -> WeeklyChallenge:
        """Find team that underperformed projection by most."""
        winner = min(games, key=lambda g: g.projection_diff)

        return WeeklyChallenge(
            challenge_name="Most Under Projection",
            week=week,
            winner=winner.team_name,
            owner=None,
            division=winner.division,
            value=f"{winner.projection_diff:.2f}",
            description=(
                f"{winner.team_name} underperformed projection by {abs(winner.projection_diff):.2f} "
                f"({winner.score:.2f} actual vs {winner.projected_score:.2f} projected)"
            ),
            additional_info={
                "score": winner.score,
                "projected": winner.projected_score,
                "won": winner.won
            }
        )

    def _calculate_top_player(
        self,
        players: Sequence[WeeklyPlayerStats],
        week: int
    ) -> WeeklyChallenge:
        """Find highest scoring player this week (starters only)."""
        winner = max(players, key=lambda p: p.points)

        return WeeklyChallenge(
            challenge_name="Top Scorer (Player)",
            week=week,
            winner=winner.name,
            owner=None,
            division=winner.division,
            value=f"{winner.points:.2f}",
            description=f"{winner.name} ({winner.position}) scored {winner.points:.2f} points",
            additional_info={
                "position": winner.position,
                "team": winner.team_name,
                "pro_team": winner.pro_team,
                "projected": winner.projected_points,
                "projection_diff": winner.projection_diff
            }
        )

    def _calculate_top_by_position(
        self,
        players: Sequence[WeeklyPlayerStats],
        week: int
    ) -> list[WeeklyChallenge]:
        """Find top scorer for each position this week (starters only)."""
        results: list[WeeklyChallenge] = []

        # Group players by position
        positions = ["QB", "RB", "WR", "TE", "K", "D/ST"]

        for position in positions:
            position_players = [p for p in players if p.position == position]

            if not position_players:
                continue  # Skip positions with no players

            winner = max(position_players, key=lambda p: p.points)

            results.append(WeeklyChallenge(
                challenge_name=f"Best {position}",
                week=week,
                winner=winner.name,
                owner=None,
                division=winner.division,
                value=f"{winner.points:.2f}",
                description=f"{winner.name} scored {winner.points:.2f} points",
                additional_info={
                    "position": winner.position,
                    "team": winner.team_name,
                    "pro_team": winner.pro_team,
                    "projected": winner.projected_points
                }
            ))

        return results

    def _calculate_biggest_boom(
        self,
        players: Sequence[WeeklyPlayerStats],
        week: int
    ) -> WeeklyChallenge:
        """Find player who exceeded projection by most (starters only)."""
        winner = max(players, key=lambda p: p.projection_diff)

        return WeeklyChallenge(
            challenge_name="Biggest Boom (Player)",
            week=week,
            winner=winner.name,
            owner=None,
            division=winner.division,
            value=f"+{winner.projection_diff:.2f}",
            description=(
                f"{winner.name} ({winner.position}) exceeded projection by {winner.projection_diff:.2f} "
                f"({winner.points:.2f} actual vs {winner.projected_points:.2f} projected)"
            ),
            additional_info={
                "position": winner.position,
                "team": winner.team_name,
                "pro_team": winner.pro_team,
                "points": winner.points,
                "projected": winner.projected_points
            }
        )

    def _calculate_biggest_bust(
        self,
        players: Sequence[WeeklyPlayerStats],
        week: int
    ) -> WeeklyChallenge:
        """Find player who underperformed projection by most (starters only)."""
        winner = min(players, key=lambda p: p.projection_diff)

        return WeeklyChallenge(
            challenge_name="Biggest Bust (Player)",
            week=week,
            winner=winner.name,
            owner=None,
            division=winner.division,
            value=f"{winner.projection_diff:.2f}",
            description=(
                f"{winner.name} ({winner.position}) underperformed projection by {abs(winner.projection_diff):.2f} "
                f"({winner.points:.2f} actual vs {winner.projected_points:.2f} projected)"
            ),
            additional_info={
                "position": winner.position,
                "team": winner.team_name,
                "pro_team": winner.pro_team,
                "points": winner.points,
                "projected": winner.projected_points
            }
        )

    def _create_no_data_placeholder(
        self,
        challenge_name: str,
        week: int
    ) -> WeeklyChallenge:
        """Create a placeholder challenge when data is insufficient."""
        return WeeklyChallenge(
            challenge_name=challenge_name,
            week=week,
            winner="No Data",
            owner=None,
            division="N/A",
            value="N/A",
            description="Insufficient data for this challenge",
            additional_info={}
        )
