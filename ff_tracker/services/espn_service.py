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
from ..models import DivisionData, GameResult, TeamStats

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

            for team in league.teams:
                # Use team name with fallbacks (team_name is primary, team_abbrev as backup)
                team_name = team.team_name or team.team_abbrev or f"Team {team.team_id}"

                # Extract owner name
                owner = self._extract_owner_name(team)

                teams.append(TeamStats(
                    name=team_name,
                    owner=owner,
                    points_for=team.points_for,
                    points_against=team.points_against,
                    wins=team.wins,
                    losses=team.losses,
                    division=division_name
                ))

            logger.info(f"Extracted {len(teams)} teams from {division_name}")
            return teams

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to extract teams from {division_name}: {e}",
            ) from e

    def _extract_owner_name(self, team: Team) -> str:
        """
        Extract owner name from team object.

        Uses the typed Team.owners attribute to get the first owner's name,
        prioritizing real names over usernames.

        Args:
            team: ESPN team object

        Returns:
            Owner name string
        """
        try:
            # ESPN API provides owners as list[dict[str, Any]]
            if not team.owners or len(team.owners) == 0:
                return "Unknown Owner"

            # Get first owner (teams typically have one owner)
            owner_data = team.owners[0]

            # Extract name fields with safe defaults
            first_name = str(owner_data.get('firstName', '')).strip()
            last_name = str(owner_data.get('lastName', '')).strip()
            display_name = str(owner_data.get('displayName', '')).strip()

            # Prefer first/last name combination over display name
            if first_name and last_name:
                return f"{first_name} {last_name}"
            elif first_name:
                return first_name
            elif last_name:
                return last_name
            elif display_name and not self._looks_like_username(display_name):
                return display_name
            elif display_name:
                return display_name
            else:
                return "Unknown Owner"

        except Exception as e:
            logger.warning(f"Error extracting owner name from team: {e}")
            return "Unknown Owner"

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

            # Store current week from first league processed (for display purposes)
            if self.current_week is None:
                self.current_week = current_week
                logger.info(f"Set current week to {current_week} from {division_name}")

            # Get regular season count from league settings
            reg_season_count = league.settings.reg_season_count

            # Auto-detect max week if not provided
            if max_week is None:
                max_week = self._determine_max_week(league, current_week, reg_season_count)

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

        This implements the logic from the original script to exclude
        incomplete weeks.
        """
        max_week_candidate = min(reg_season_count, current_week)

        # Check if current week seems incomplete
        if current_week <= reg_season_count:
            try:
                current_box_scores = league.box_scores(current_week)
                if current_box_scores:
                    for box_score in current_box_scores:
                        home_score = box_score.home_score
                        away_score = box_score.away_score

                        # If either team has very low score, week is likely incomplete
                        if (home_score > 0 and home_score < 30) or (away_score > 0 and away_score < 30):
                            logger.info(f"Week {current_week} appears incomplete, excluding it")
                            return max_week_candidate - 1
            except Exception:
                # If we can't check, assume it's incomplete
                logger.info(f"Unable to verify week {current_week}, excluding it")
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
                    home_team = box_score.home_team
                    away_team = box_score.away_team
                    home_score = box_score.home_score
                    away_score = box_score.away_score

                    if not home_team or not away_team or home_score <= 0 or away_score <= 0:
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
