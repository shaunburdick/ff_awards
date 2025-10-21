"""
ESPN Fantasy Football API integration service.

This module handles all interactions with the ESPN Fantasy Football API,
including authentication, data extraction, and error handling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

# Import League type only for type checking to avoid runtime import issues
if TYPE_CHECKING:
    from espn_api.football import League, Team

from ..config import FFTrackerConfig
from ..exceptions import ESPNAPIError, LeagueConnectionError, PrivateLeagueError
from ..models import DivisionData, GameResult, Owner, TeamStats

# Logger for this module
logger = logging.getLogger(__name__)


class ESPNService:
    """
    Service for interacting with ESPN Fantasy Football API.

    Handles league connections, data extraction, and error management.
    """

    def __init__(self, config: FFTrackerConfig) -> None:
        """
        Initialize ESPN service with configuration.

        Args:
            config: Application configuration including credentials
        """
        self.config = config
        self.current_week: int | None = None

    def connect_to_league(self, league_id: int) -> League:
        """
        Connect to a specific ESPN league.

        Args:
            league_id: ESPN league ID to connect to

        Returns:
            ESPN League object

        Raises:
            LeagueConnectionError: If connection fails
            PrivateLeagueError: If private league credentials are invalid
        """
        try:
            from espn_api.football import League

            logger.info(f"Connecting to league {league_id} (year {self.config.year})")

            if self.config.private:
                if not self.config.espn_credentials:
                    raise PrivateLeagueError(
                        "Private league credentials not configured",
                        league_id=league_id
                    )

                league = League(
                    league_id=league_id,
                    year=self.config.year,
                    espn_s2=self.config.espn_credentials.s2,
                    swid=self.config.espn_credentials.swid
                )
            else:
                league = League(league_id=league_id, year=self.config.year)

            logger.info(f"Successfully connected to league {league_id}")
            return league

        except Exception as e:
            # Convert various ESPN API exceptions to our exception hierarchy
            error_msg = str(e)

            if "404" in error_msg or "not found" in error_msg.lower():
                raise LeagueConnectionError(
                    f"League {league_id} not found or not accessible",
                    league_id=league_id
                ) from e
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise PrivateLeagueError(
                    f"Invalid credentials for private league {league_id}",
                    league_id=league_id
                ) from e
            else:
                raise LeagueConnectionError(
                    f"Failed to connect to league {league_id}: {error_msg}",
                    league_id=league_id
                ) from e

    def _calculate_playoff_status(self, teams: list[TeamStats]) -> dict[str, bool]:
        """
        Calculate playoff qualification for teams in a division.

        Top 4 teams qualify based on record (wins-losses), with points_for as tiebreaker.

        Note: Could potentially use league.standings() method from ESPN API in the future
        for optimization, but current implementation gives us full control over tiebreakers.

        Args:
            teams: List of team statistics for the division

        Returns:
            Dictionary mapping team names to playoff qualification status
        """
        # Sort teams by record (wins desc, losses asc), then by points_for desc
        sorted_teams = sorted(
            teams,
            key=lambda t: (t.wins, -t.losses, t.points_for),
            reverse=True
        )

        # Top 4 teams make playoffs
        playoff_teams: set[str] = set()
        for i, team in enumerate(sorted_teams):
            if i < 4:  # Top 4 teams qualify
                playoff_teams.add(team.name)

        return {team.name: team.name in playoff_teams for team in teams}

    def extract_teams(self, league: League, division_name: str) -> list[TeamStats]:
        """
        Extract team statistics from ESPN league.

        Args:
            league: ESPN League object
            division_name: Name to assign to this division

        Returns:
            List of team statistics

        Raises:
            ESPNAPIError: If team extraction fails
        """
        teams: list[TeamStats] = []

        try:
            logger.debug(f"Extracting teams from {division_name}")

            # Build teams efficiently with typed ESPN data
            temp_teams: list[TeamStats] = []
            for team in league.teams:
                # Use team name with fallbacks (team_name is primary, team_abbrev as backup)
                team_name = team.team_name or team.team_abbrev or f"Team {team.team_id}"

                # Extract owner object efficiently with typed owners
                owners = self.convert_team_owners(team)
                owner = owners[0] if owners else self._create_unknown_owner()

                temp_teams.append(TeamStats(
                    name=team_name,
                    owner=owner,
                    points_for=team.points_for,
                    points_against=team.points_against,
                    wins=team.wins,
                    losses=team.losses,
                    division=division_name,
                    in_playoff_position=False  # Will be updated below
                ))

            # Calculate playoff status for all teams
            playoff_status = self._calculate_playoff_status(temp_teams)

            # Create final teams with correct playoff status
            teams = [
                TeamStats(
                    name=temp_team.name,
                    owner=temp_team.owner,
                    points_for=temp_team.points_for,
                    points_against=temp_team.points_against,
                    wins=temp_team.wins,
                    losses=temp_team.losses,
                    division=temp_team.division,
                    in_playoff_position=playoff_status[temp_team.name]
                )
                for temp_team in temp_teams
            ]

            logger.info(f"Extracted {len(teams)} teams from {division_name}")
            return teams

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to extract teams from {division_name}: {e}",
            ) from e



    def _looks_like_username(self, name: str) -> bool:
        """Check if a name looks like a username rather than a real name."""
        name = name.strip()
        if not name:
            return True

        # Common username patterns (from original script)
        username_indicators = [
            name.startswith('ESPNFAN'),
            name.startswith('espn'),
            len(name) > 15 and any(c.isdigit() for c in name),
            name.islower() and len(name) > 8,
            sum(c.isdigit() for c in name) > len(name) // 2,
        ]

        return any(username_indicators)

    def _create_unknown_owner(self) -> Owner:
        """Create an Owner object for when owner information is missing."""
        return Owner(
            display_name="Unknown Owner",
            first_name="",
            last_name="",
            id="unknown"
        )

    def convert_team_owners(self, team: Team) -> list[Owner]:
        """
        Convert team's owners data to our typed Owner objects.

        Args:
            team: ESPN team object with typed owners data

        Returns:
            List of our typed Owner objects
        """
        if not team.owners:
            return []

        # Convert ESPN Owner TypedDict to our Owner model
        return [
            Owner(
                display_name=espn_owner.get('displayName', ''),
                first_name=espn_owner.get('firstName', ''),
                last_name=espn_owner.get('lastName', ''),
                id=espn_owner.get('id', ''),
            )
            for espn_owner in team.owners
        ]

    def extract_games(
        self,
        league: League,
        division_name: str,
        max_week: int | None = None
    ) -> list[GameResult]:
        """
        Extract game results from ESPN league.

        Args:
            league: ESPN League object
            division_name: Name to assign to this division
            max_week: Maximum week to process (auto-detected if None)

        Returns:
            List of game results

        Raises:
            ESPNAPIError: If game extraction fails
        """
        games: list[GameResult] = []

        try:
            # Determine week range to process
            current_week = league.current_week

            # Get regular season count from league settings
            reg_season_count = league.settings.reg_season_count

            # Auto-detect max week if not provided
            if max_week is None:
                max_week = self._determine_max_week(league, current_week, reg_season_count)

            # Store the actual last complete week from first league processed (for display purposes)
            # This is the max_week we're actually processing, not ESPN's current_week
            if self.current_week is None:
                self.current_week = max_week
                logger.info(f"Set current week to {max_week} (last complete week) from {division_name}")

            logger.info(f"Processing weeks 1-{max_week} for {division_name}")

            # Process each week
            for week in range(1, max_week + 1):
                try:
                    week_games = self._extract_week_games(league, week, division_name)
                    games.extend(week_games)
                except Exception as e:
                    logger.warning(f"Failed to process week {week} for {division_name}: {e}")
                    continue

            logger.info(f"Extracted {len(games)} games from {division_name}")
            return games

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to extract games from {division_name}: {e}",
            ) from e

    def _determine_max_week(self, league: League, current_week: int, reg_season_count: int) -> int:
        """
        Determine the maximum week to process based on current state.

        Checks if the current week has been played by examining box scores.
        A week is considered incomplete if any game has both teams with 0 points.

        Args:
            league: ESPN League object
            current_week: The week ESPN reports as current
            reg_season_count: Total number of regular season weeks

        Returns:
            The last complete week number to process
        """
        max_week_candidate = min(reg_season_count, current_week)

        # Check if current week has been played
        if current_week <= reg_season_count:
            try:
                current_box_scores = league.box_scores(current_week)
                if current_box_scores:
                    # If ANY game has both teams at 0 points, the week hasn't started
                    for box_score in current_box_scores:
                        home_score = box_score.home_score
                        away_score = box_score.away_score

                        # Both teams at 0 means game hasn't been played
                        if home_score == 0 and away_score == 0:
                            logger.info(f"Week {current_week} has unplayed games (0-0), using week {max_week_candidate - 1}")
                            return max_week_candidate - 1

                        # Very low scores might indicate incomplete/in-progress games
                        # But we need at least one team to have scored something
                        if home_score > 0 and away_score > 0:
                            # Both teams have scored, so at least some games are complete
                            continue
                        elif home_score == 0 or away_score == 0:
                            # One team at 0 while the other has points likely means incomplete
                            logger.info(f"Week {current_week} appears in progress (partial scores), using week {max_week_candidate - 1}")
                            return max_week_candidate - 1

                    # All games appear to have valid scores
                    logger.info(f"Week {current_week} appears complete, including it")
                    return max_week_candidate
                else:
                    # No box scores available, week hasn't started
                    logger.info(f"No box scores for week {current_week}, using week {max_week_candidate - 1}")
                    return max_week_candidate - 1

            except Exception as e:
                # If we can't check, assume it's incomplete to be safe
                logger.info(f"Unable to verify week {current_week} ({e}), using week {max_week_candidate - 1}")
                return max_week_candidate - 1

        return max_week_candidate

    def _extract_week_games(self, league: League, week: int, division_name: str) -> list[GameResult]:
        """Extract games for a specific week."""
        games: list[GameResult] = []

        try:
            box_scores = league.box_scores(week)
            if not box_scores:
                return games

            for box_score in box_scores:
                try:
                    # Extract typed data from BoxScore - now we know exact types
                    home_team = box_score.home_team  # Team
                    away_team = box_score.away_team  # Team
                    home_score = box_score.home_score  # float
                    away_score = box_score.away_score  # float

                    # Validate game data with better type awareness
                    if not home_team or not away_team or home_score <= 0 or away_score <= 0:
                        logger.debug(f"Skipping invalid game in week {week}: "
                                   f"home_score={home_score}, away_score={away_score}")
                        continue

                    # Get team names with fallbacks
                    home_name = home_team.team_name or f"Team {home_team.team_id}"
                    away_name = away_team.team_name or f"Team {away_team.team_id}"

                    margin = abs(home_score - away_score)

                    # Create game results for both teams
                    games.extend([
                        GameResult(
                            team_name=home_name,
                            score=home_score,
                            opponent_name=away_name,
                            opponent_score=away_score,
                            won=home_score > away_score,
                            week=week,
                            margin=margin,
                            division=division_name
                        ),
                        GameResult(
                            team_name=away_name,
                            score=away_score,
                            opponent_name=home_name,
                            opponent_score=home_score,
                            won=away_score > home_score,
                            week=week,
                            margin=margin,
                            division=division_name
                        )
                    ])

                except Exception as e:
                    logger.warning(f"Error processing matchup in week {week}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Could not get box scores for week {week}: {e}")

        return games

    def load_division_data(self, league_id: int) -> DivisionData:
        """
        Load complete data for a single division.

        Args:
            league_id: ESPN league ID to load

        Returns:
            Complete division data

        Raises:
            LeagueConnectionError: If unable to connect to league
            ESPNAPIError: If data extraction fails
        """
        league = self.connect_to_league(league_id)

        # Get league name from settings
        league_name = league.settings.name or f"League {league_id}"

        logger.info(f"Loading data for {league_name}")

        # Extract teams and games
        teams = self.extract_teams(league, league_name)
        games = self.extract_games(league, league_name)

        return DivisionData(
            league_id=league_id,
            name=league_name,
            teams=teams,
            games=games
        )

    def load_all_divisions(self) -> list[DivisionData]:
        """
        Load data for all configured divisions.

        Returns:
            List of complete division data for all leagues

        Raises:
            LeagueConnectionError: If unable to connect to any league
            ESPNAPIError: If data extraction fails for any league
        """
        divisions: list[DivisionData] = []

        for league_id in self.config.league_ids:
            try:
                division_data = self.load_division_data(league_id)
                divisions.append(division_data)
                logger.info(f"Successfully loaded division: {division_data.name}")
            except Exception as e:
                logger.error(f"Failed to load league {league_id}: {e}")
                raise ESPNAPIError(f"Failed to load league {league_id}: {e}") from e

        return divisions

    def __enter__(self) -> ESPNService:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup if needed."""
        # No specific cleanup needed for ESPN API connections
        pass
