"""
Fantasy Football Challenge calculation service.

This module handles the business logic for calculating the 5 season challenges
from collected fantasy football data.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from ..exceptions import InsufficientDataError
from ..models import ChallengeResult, DivisionData, GameResult, TeamStats

# Logger for this module
logger = logging.getLogger(__name__)


class ChallengeCalculator:
    """
    Service for calculating fantasy football season challenges.

    Implements the business logic for the 5 tracked challenges:
    1. Most Points Overall
    2. Most Points in One Game
    3. Most Points in a Loss
    4. Least Points in a Win
    5. Closest Victory
    """

    def __init__(self) -> None:
        """Initialize the challenge calculator."""
        pass

    def calculate_all_challenges(
        self,
        divisions: Sequence[DivisionData]
    ) -> list[ChallengeResult]:
        """
        Calculate all 5 challenges across multiple divisions.

        Args:
            divisions: List of division data to analyze

        Returns:
            List of challenge results

        Raises:
            InsufficientDataError: If there's not enough data to calculate challenges
        """
        if not divisions:
            raise InsufficientDataError("No division data provided")

        # Combine all teams and games
        all_teams = self._combine_teams(divisions)
        all_games = self._combine_games(divisions)

        if not all_teams:
            raise InsufficientDataError("No team data found across all divisions")

        logger.info(f"Calculating challenges for {len(all_teams)} teams across {len(divisions)} divisions")

        results: list[ChallengeResult] = []

        # Challenge 1: Most Points Overall
        results.append(self._calculate_most_points_overall(all_teams))

        # Challenges 2-5 require game data
        if not all_games:
            logger.warning("No game data available, adding placeholder results for game-based challenges")
            results.extend(self._create_no_data_placeholders())
        else:
            results.append(self._calculate_most_points_one_game(all_teams, all_games))
            results.append(self._calculate_most_points_in_loss(all_teams, all_games))
            results.append(self._calculate_least_points_in_win(all_teams, all_games))
            results.append(self._calculate_closest_victory(all_teams, all_games))

        logger.info(f"Calculated {len(results)} challenge results")
        return results

    def _combine_teams(self, divisions: Sequence[DivisionData]) -> list[TeamStats]:
        """Combine all teams from multiple divisions."""
        teams: list[TeamStats] = []
        for division in divisions:
            teams.extend(division.teams)
        return teams

    def _combine_games(self, divisions: Sequence[DivisionData]) -> list[GameResult]:
        """Combine all games from multiple divisions."""
        games: list[GameResult] = []
        for division in divisions:
            games.extend(division.games)
        return games

    def _find_owner_for_team(self, team_name: str, division: str, all_teams: list[TeamStats]) -> str:
        """Find the owner name for a given team name and division."""
        for team in all_teams:
            if team.name == team_name and team.division == division:
                return team.owner
        return "Unknown Owner"

    def _calculate_most_points_overall(self, teams: list[TeamStats]) -> ChallengeResult:
        """Calculate Challenge 1: Most Points Overall."""
        logger.debug("Calculating most points overall")

        if not teams:
            raise InsufficientDataError("No teams available for most points overall calculation")

        highest_scorer = max(teams, key=lambda x: x.points_for)

        return ChallengeResult(
            challenge_name="Most Points Overall",
            winner=highest_scorer.name,
            owner=highest_scorer.owner,
            division=highest_scorer.division,
            value="",
            description=f"{highest_scorer.points_for:.1f} total points"
        )

    def _calculate_most_points_one_game(self, teams: list[TeamStats], games: list[GameResult]) -> ChallengeResult:
        """Calculate Challenge 2: Most Points in One Game."""
        logger.debug("Calculating most points in one game")

        if not games:
            raise InsufficientDataError("No games available for most points one game calculation")

        highest_game = max(games, key=lambda x: x.score)

        return ChallengeResult(
            challenge_name="Most Points in One Game",
            winner=highest_game.team_name,
            owner=self._find_owner_for_team(highest_game.team_name, highest_game.division, teams),
            division=highest_game.division,
            value="",
            description=f"{highest_game.score:.1f} points (Week {highest_game.week})"
        )

    def _calculate_most_points_in_loss(self, teams: list[TeamStats], games: list[GameResult]) -> ChallengeResult:
        """Calculate Challenge 3: Most Points in a Loss."""
        logger.debug("Calculating most points in a loss")

        losses = [game for game in games if not game.won]

        if not losses:
            return ChallengeResult(
                challenge_name="Most Points in a Loss",
                winner="No losses found",
                owner="N/A",
                division="N/A",
                value="",
                description="No losing games recorded yet"
            )

        highest_loss = max(losses, key=lambda x: x.score)

        return ChallengeResult(
            challenge_name="Most Points in a Loss",
            winner=highest_loss.team_name,
            owner=self._find_owner_for_team(highest_loss.team_name, highest_loss.division, teams),
            division=highest_loss.division,
            value="",
            description=f"{highest_loss.score:.1f} points in loss (Week {highest_loss.week})"
        )

    def _calculate_least_points_in_win(self, teams: list[TeamStats], games: list[GameResult]) -> ChallengeResult:
        """Calculate Challenge 4: Least Points in a Win."""
        logger.debug("Calculating least points in a win")

        wins = [game for game in games if game.won]

        if not wins:
            return ChallengeResult(
                challenge_name="Least Points in a Win",
                winner="No wins found",
                owner="N/A",
                division="N/A",
                value="",
                description="No winning games recorded yet"
            )

        lowest_win = min(wins, key=lambda x: x.score)

        return ChallengeResult(
            challenge_name="Least Points in a Win",
            winner=lowest_win.team_name,
            owner=self._find_owner_for_team(lowest_win.team_name, lowest_win.division, teams),
            division=lowest_win.division,
            value="",
            description=f"{lowest_win.score:.1f} points in win (Week {lowest_win.week})"
        )

    def _calculate_closest_victory(self, teams: list[TeamStats], games: list[GameResult]) -> ChallengeResult:
        """Calculate Challenge 5: Closest Victory."""
        logger.debug("Calculating closest victory")

        wins = [game for game in games if game.won]

        if not wins:
            return ChallengeResult(
                challenge_name="Closest Victory",
                winner="No wins found",
                owner="N/A",
                division="N/A",
                value="",
                description="No winning games recorded yet"
            )

        closest_win = min(wins, key=lambda x: x.margin)

        return ChallengeResult(
            challenge_name="Closest Victory",
            winner=closest_win.team_name,
            owner=self._find_owner_for_team(closest_win.team_name, closest_win.division, teams),
            division=closest_win.division,
            value="",
            description=f"Won by {closest_win.margin:.1f} points (Week {closest_win.week})"
        )

    def _create_no_data_placeholders(self) -> list[ChallengeResult]:
        """Create placeholder results when game data is unavailable."""
        placeholders = [
            ("Most Points in One Game", "Game data unavailable"),
            ("Most Points in a Loss", "Game data unavailable"),
            ("Least Points in a Win", "Game data unavailable"),
            ("Closest Victory", "Game data unavailable")
        ]

        results: list[ChallengeResult] = []
        for challenge_name, description in placeholders:
            results.append(ChallengeResult(
                challenge_name=challenge_name,
                winner="Data Unavailable",
                owner="N/A",
                division="N/A",
                value="",
                description=description
            ))

        return results
