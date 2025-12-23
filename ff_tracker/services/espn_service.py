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
from ..models import DivisionData, GameResult, Owner, TeamStats, WeeklyGameResult, WeeklyPlayerStats

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
                        "Private league credentials not configured", league_id=league_id
                    )

                league = League(
                    league_id=league_id,
                    year=self.config.year,
                    espn_s2=self.config.espn_credentials.s2,
                    swid=self.config.espn_credentials.swid,
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
                    f"League {league_id} not found or not accessible", league_id=league_id
                ) from e
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                raise PrivateLeagueError(
                    f"Invalid credentials for private league {league_id}", league_id=league_id
                ) from e
            else:
                raise LeagueConnectionError(
                    f"Failed to connect to league {league_id}: {error_msg}", league_id=league_id
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
        sorted_teams = sorted(teams, key=lambda t: (t.wins, -t.losses, t.points_for), reverse=True)

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

                temp_teams.append(
                    TeamStats(
                        name=team_name,
                        owner=owner,
                        points_for=team.points_for,
                        points_against=team.points_against,
                        wins=team.wins,
                        losses=team.losses,
                        division=division_name,
                        in_playoff_position=False,  # Will be updated below
                    )
                )

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
                    in_playoff_position=playoff_status[temp_team.name],
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
            name.startswith("ESPNFAN"),
            name.startswith("espn"),
            len(name) > 15 and any(c.isdigit() for c in name),
            name.islower() and len(name) > 8,
            sum(c.isdigit() for c in name) > len(name) // 2,
        ]

        return any(username_indicators)

    def _create_unknown_owner(self) -> Owner:
        """Create an Owner object for when owner information is missing."""
        return Owner(display_name="Unknown Owner", first_name="", last_name="", id="unknown")

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
                display_name=espn_owner.get("displayName", ""),
                first_name=espn_owner.get("firstName", ""),
                last_name=espn_owner.get("lastName", ""),
                id=espn_owner.get("id", ""),
            )
            for espn_owner in team.owners
        ]

    def extract_games(
        self, league: League, division_name: str, max_week: int | None = None
    ) -> list[GameResult]:
        """
        Extract all completed games from the league up to the specified week.

        Args:
            league: ESPN League object
            division_name: Name to assign to this division
            max_week: Maximum week to process (auto-detected if None, or from config.week)

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

            # Check if week override is provided in config
            if self.config.week is not None:
                # User specified a week override - validate it's not in the future
                if self.config.week > current_week:
                    raise ESPNAPIError(
                        f"Cannot specify future week. Requested week {self.config.week} "
                        f"but league is currently in week {current_week}. "
                        f"Week override must be <= current week.",
                        league_id=league.league_id,
                    )
                # Use the override week for display/weekly data
                # But cap games at regular season for season challenges
                requested_week = self.config.week
                max_week = min(requested_week, reg_season_count)

                # Store the requested week (for weekly data and playoff display)
                if self.current_week is None:
                    self.current_week = requested_week
                    logger.info(
                        f"Week override: {requested_week}. "
                        f"Processing season challenge games through week {max_week} (regular season cap). "
                        f"Weekly data will show week {requested_week}."
                    )
            elif max_week is None:
                # Auto-detect max week if not provided and no override
                max_week = self._determine_max_week(league, current_week, reg_season_count)

                # Store the actual last complete week from first league processed (for display purposes)
                # This is the max_week we're actually processing, not ESPN's current_week
                if self.current_week is None:
                    self.current_week = max_week
                    logger.info(
                        f"Set current week to {max_week} (last complete week) from {division_name}"
                    )

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

        For regular season: Only processes up to reg_season_count.
        For playoffs: Checks if current playoff week is complete (e.g., if current_week=16,
        checks if week 16 is complete; if not, falls back to week 15).

        ESPN's current_week represents the active/current week in the league.

        Args:
            league: ESPN League object
            current_week: The week ESPN reports as current (active week)
            reg_season_count: Total number of regular season weeks

        Returns:
            The last complete week number to process
        """
        # Determine what week to check for completion
        if current_week <= reg_season_count:
            # Regular season: check current week, max out at reg_season_count
            week_to_check = current_week
            max_week_candidate = min(reg_season_count, current_week)
        else:
            # Playoffs: check current week first (ESPN's current_week represents the active week)
            # If current week is complete, use it; if incomplete, fall back to previous week
            week_to_check = current_week
            max_week_candidate = current_week

        # Check if the week_to_check has been played
        try:
            box_scores = league.box_scores(week_to_check)
            if box_scores:
                # If ANY game has both teams at 0 points, the week hasn't started
                for box_score in box_scores:
                    home_score = box_score.home_score
                    away_score = box_score.away_score

                    # Both teams at 0 means game hasn't been played
                    if home_score == 0 and away_score == 0:
                        logger.info(
                            f"Week {week_to_check} has unplayed games (0-0), using week {max_week_candidate - 1}"
                        )
                        return max_week_candidate - 1

                    # Very low scores might indicate incomplete/in-progress games
                    # But we need at least one team to have scored something
                    if home_score > 0 and away_score > 0:
                        # Both teams have scored, so at least some games are complete
                        continue
                    elif home_score == 0 or away_score == 0:
                        # One team at 0 while the other has points likely means incomplete
                        logger.info(
                            f"Week {week_to_check} appears in progress (partial scores), using week {max_week_candidate - 1}"
                        )
                        return max_week_candidate - 1

                # All games appear to have valid scores
                logger.info(
                    f"Week {week_to_check} appears complete, using week {max_week_candidate}"
                )
                return max_week_candidate
            else:
                # No box scores available, week hasn't started
                logger.info(
                    f"No box scores for week {week_to_check}, using week {max_week_candidate - 1}"
                )
                return max_week_candidate - 1

        except Exception as e:
            # If we can't check, assume it's incomplete to be safe
            logger.info(
                f"Unable to verify week {week_to_check} ({e}), using week {max_week_candidate - 1}"
            )
            return max_week_candidate - 1

    def _extract_week_games(
        self, league: League, week: int, division_name: str
    ) -> list[GameResult]:
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
                        logger.debug(
                            f"Skipping invalid game in week {week}: "
                            f"home_score={home_score}, away_score={away_score}"
                        )
                        continue

                    # Get team names with fallbacks
                    home_name = home_team.team_name or f"Team {home_team.team_id}"
                    away_name = away_team.team_name or f"Team {away_team.team_id}"

                    margin = abs(home_score - away_score)

                    # Create game results for both teams
                    games.extend(
                        [
                            GameResult(
                                team_name=home_name,
                                score=home_score,
                                opponent_name=away_name,
                                opponent_score=away_score,
                                won=home_score > away_score,
                                week=week,
                                margin=margin,
                                division=division_name,
                            ),
                            GameResult(
                                team_name=away_name,
                                score=away_score,
                                opponent_name=home_name,
                                opponent_score=home_score,
                                won=away_score > home_score,
                                week=week,
                                margin=margin,
                                division=division_name,
                            ),
                        ]
                    )

                except Exception as e:
                    logger.warning(f"Error processing matchup in week {week}: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Could not get box scores for week {week}: {e}")

        return games

    def extract_weekly_games(
        self, league: League, division_name: str, week: int
    ) -> list[WeeklyGameResult]:
        """
        Extract game results for a specific week with projections.

        Args:
            league: ESPN League object
            division_name: Name of this division
            week: Week number to extract data for

        Returns:
            List of weekly game results with projections

        Raises:
            ESPNAPIError: If weekly game extraction fails
        """
        weekly_games: list[WeeklyGameResult] = []

        try:
            logger.debug(f"Extracting weekly games for {division_name} week {week}")

            box_scores = league.box_scores(week)
            if not box_scores:
                logger.warning(f"No box scores available for week {week}")
                return weekly_games

            for box_score in box_scores:
                try:
                    # Extract team information
                    home_team = box_score.home_team
                    away_team = box_score.away_team

                    home_name = (
                        home_team.team_name or home_team.team_abbrev or f"Team {home_team.team_id}"
                    )
                    away_name = (
                        away_team.team_name or away_team.team_abbrev or f"Team {away_team.team_id}"
                    )

                    home_score = box_score.home_score
                    away_score = box_score.away_score
                    home_projected = box_score.home_projected
                    away_projected = box_score.away_projected

                    # Calculate starter-based projections (sum of starters' pre-game projections)
                    home_starter_projected = self._calculate_starter_projections(
                        box_score.home_lineup
                    )
                    away_starter_projected = self._calculate_starter_projections(
                        box_score.away_lineup
                    )

                    # Calculate margins
                    margin = abs(home_score - away_score)

                    # Create WeeklyGameResult for both teams
                    weekly_games.extend(
                        [
                            WeeklyGameResult(
                                team_name=home_name,
                                score=home_score,
                                projected_score=home_projected,
                                opponent_name=away_name,
                                opponent_score=away_score,
                                opponent_projected_score=away_projected,
                                won=home_score > away_score,
                                week=week,
                                margin=margin,
                                projection_diff=home_score - home_projected,
                                division=division_name,
                                starter_projected_score=home_starter_projected,
                                true_projection_diff=home_score - home_starter_projected
                                if home_starter_projected is not None
                                else None,
                            ),
                            WeeklyGameResult(
                                team_name=away_name,
                                score=away_score,
                                projected_score=away_projected,
                                opponent_name=home_name,
                                opponent_score=home_score,
                                opponent_projected_score=home_projected,
                                won=away_score > home_score,
                                week=week,
                                margin=margin,
                                projection_diff=away_score - away_projected,
                                division=division_name,
                                starter_projected_score=away_starter_projected,
                                true_projection_diff=away_score - away_starter_projected
                                if away_starter_projected is not None
                                else None,
                            ),
                        ]
                    )

                except Exception as e:
                    logger.warning(f"Error processing box score for week {week}: {e}")
                    continue

            logger.info(f"Extracted {len(weekly_games)} weekly game results for week {week}")
            return weekly_games

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to extract weekly games for {division_name} week {week}: {e}"
            ) from e

    def extract_weekly_players(
        self, league: League, division_name: str, week: int
    ) -> list[WeeklyPlayerStats]:
        """
        Extract player performances for a specific week.

        Args:
            league: ESPN League object
            division_name: Name of this division
            week: Week number to extract data for

        Returns:
            List of weekly player statistics

        Raises:
            ESPNAPIError: If weekly player extraction fails
        """
        weekly_players: list[WeeklyPlayerStats] = []

        try:
            logger.debug(f"Extracting weekly players for {division_name} week {week}")

            box_scores = league.box_scores(week)
            if not box_scores:
                logger.warning(f"No box scores available for week {week}")
                return weekly_players

            for box_score in box_scores:
                try:
                    # Process home team lineup
                    home_team = box_score.home_team
                    home_name = (
                        home_team.team_name or home_team.team_abbrev or f"Team {home_team.team_id}"
                    )

                    for box_player in box_score.home_lineup:
                        weekly_players.append(
                            self._create_weekly_player_stat(
                                box_player, home_name, division_name, week
                            )
                        )

                    # Process away team lineup
                    away_team = box_score.away_team
                    away_name = (
                        away_team.team_name or away_team.team_abbrev or f"Team {away_team.team_id}"
                    )

                    for box_player in box_score.away_lineup:
                        weekly_players.append(
                            self._create_weekly_player_stat(
                                box_player, away_name, division_name, week
                            )
                        )

                except Exception as e:
                    logger.warning(f"Error processing player lineup for week {week}: {e}")
                    continue

            logger.info(f"Extracted {len(weekly_players)} weekly player stats for week {week}")
            return weekly_players

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to extract weekly players for {division_name} week {week}: {e}"
            ) from e

    def _create_weekly_player_stat(
        self, box_player: Any, team_name: str, division: str, week: int
    ) -> WeeklyPlayerStats:
        """
        Create WeeklyPlayerStats from a BoxPlayer object.

        Args:
            box_player: ESPN BoxPlayer object
            team_name: Fantasy team name
            division: Division name
            week: Week number

        Returns:
            WeeklyPlayerStats object
        """
        return WeeklyPlayerStats(
            name=box_player.name,
            position=box_player.position,
            team_name=team_name,
            division=division,
            points=box_player.points,
            projected_points=box_player.projected_points,
            projection_diff=box_player.points - box_player.projected_points,
            slot_position=box_player.slot_position,
            week=week,
            pro_team=box_player.proTeam if hasattr(box_player, "proTeam") else "UNK",
            pro_opponent=box_player.pro_opponent if hasattr(box_player, "pro_opponent") else "",
        )

    def _calculate_starter_projections(self, lineup: list[Any]) -> float | None:
        """
        Calculate total projected points for starters only (excludes bench).

        This provides a "true" pre-game projection by summing individual player
        projections, which are more static than ESPN's real-time team projections.

        Args:
            lineup: List of BoxPlayer objects from a team's lineup

        Returns:
            Sum of projected points for starters, or None if calculation fails
        """
        try:
            total_projected = 0.0
            for player in lineup:
                # Only include starters (slot_position != 'BE' for bench)
                if hasattr(player, "slot_position") and player.slot_position != "BE":
                    if hasattr(player, "projected_points"):
                        total_projected += player.projected_points
            return total_projected
        except Exception as e:
            logger.warning(f"Could not calculate starter projections: {e}")
            return None

    def is_in_playoffs(self, league: League) -> bool:
        """
        Check if a league is currently in playoffs.

        Playoff detection is based on ESPN's week numbering: playoffs start
        when the current week exceeds the regular season count.

        Args:
            league: ESPN League object

        Returns:
            True if league is in playoffs, False otherwise

        Examples:
            >>> # Regular season: Week 14, reg_season_count=14
            >>> service.is_in_playoffs(league)  # False
            >>> # Playoffs: Week 15, reg_season_count=14
            >>> service.is_in_playoffs(league)  # True
        """
        return bool(league.current_week > league.settings.reg_season_count)

    def get_playoff_round(self, league: League, week: int | None = None) -> str:
        """
        Determine the playoff round for a league based on a specific week.

        Args:
            league: ESPN League object
            week: Week number to check (uses league.current_week if None)

        Returns:
            Playoff round name: "Semifinals", "Finals", or "Championship Week"

        Raises:
            ESPNAPIError: If not in playoffs or unexpected playoff week

        Examples:
            >>> # Week 15 (first playoff week)
            >>> service.get_playoff_round(league, 15)  # "Semifinals"
            >>> # Week 16 (second playoff week)
            >>> service.get_playoff_round(league, 16)  # "Finals"
            >>> # Week 17 (championship week)
            >>> service.get_playoff_round(league, 17)  # "Championship Week"
        """
        # Use provided week or fallback to league's current week
        check_week = week if week is not None else league.current_week

        # Verify league is in playoffs based on ESPN's current week
        if not self.is_in_playoffs(league):
            raise ESPNAPIError(
                f"League is not in playoffs. Current week: {league.current_week}, "
                f"Regular season ends: {league.settings.reg_season_count}",
                league_id=league.league_id,
            )

        # Calculate which playoff week we're checking
        playoff_week = check_week - league.settings.reg_season_count

        if playoff_week == 1:
            return "Semifinals"
        elif playoff_week == 2:
            return "Finals"
        elif playoff_week == 3:
            return "Championship Week"
        else:
            raise ESPNAPIError(
                f"Unexpected playoff week: {playoff_week} (week: {check_week}, "
                f"regular season: {league.settings.reg_season_count})",
                league_id=league.league_id,
            )

    def check_division_sync(self, leagues: list[League]) -> tuple[bool, str]:
        """
        Check if all divisions are synchronized for multi-league operations.

        For playoff mode to work correctly, all divisions must be in the same state:
        - All in same week number
        - All in playoffs OR all in regular season
        - If in playoffs, all in same playoff round

        Args:
            leagues: List of ESPN League objects to check

        Returns:
            Tuple of (is_synced, error_message)
            - is_synced: True if all leagues are synchronized
            - error_message: Empty string if synced, detailed error if not

        Examples:
            >>> # All leagues in Week 15 Semifinals
            >>> synced, msg = service.check_division_sync([league1, league2, league3])
            >>> assert synced and msg == ""

            >>> # Mixed: Week 14 and Week 15
            >>> synced, msg = service.check_division_sync([league1, league2])
            >>> assert not synced
            >>> print(msg)  # "Divisions are out of sync..."
        """
        if not leagues:
            return True, ""

        # Check current week sync
        first_week = leagues[0].current_week
        for league in leagues[1:]:
            if league.current_week != first_week:
                # Build detailed error message with all league states
                states: dict[str, str] = {}
                for lg in leagues:
                    league_name = lg.settings.name or f"League {lg.league_id}"
                    states[league_name] = f"Week {lg.current_week}"

                error_msg = (
                    f"Divisions are out of sync (different weeks). "
                    f"States: {', '.join(f'{name}: {state}' for name, state in states.items())}"
                )
                return False, error_msg

        # Check playoff state sync
        first_in_playoffs = self.is_in_playoffs(leagues[0])
        for league in leagues[1:]:
            if self.is_in_playoffs(league) != first_in_playoffs:
                # Build detailed error message showing playoff states
                playoff_states: dict[str, str] = {}
                for lg in leagues:
                    league_name = lg.settings.name or f"League {lg.league_id}"
                    if self.is_in_playoffs(lg):
                        playoff_states[league_name] = f"Week {lg.current_week} (Playoffs)"
                    else:
                        playoff_states[league_name] = f"Week {lg.current_week} (Regular Season)"

                error_msg = (
                    f"Divisions are out of sync (mixed playoff states). "
                    f"States: {', '.join(f'{name}: {state}' for name, state in playoff_states.items())}"
                )
                return False, error_msg

        # If in playoffs, check playoff round sync
        if first_in_playoffs:
            first_round = self.get_playoff_round(leagues[0])
            for league in leagues[1:]:
                if self.get_playoff_round(league) != first_round:
                    # Build detailed error message showing playoff rounds
                    round_states: dict[str, str] = {}
                    for lg in leagues:
                        league_name = lg.settings.name or f"League {lg.league_id}"
                        round_name = self.get_playoff_round(lg)
                        round_states[league_name] = f"Week {lg.current_week} ({round_name})"

                    error_msg = (
                        f"Divisions are out of sync (different playoff rounds). "
                        f"States: {', '.join(f'{name}: {state}' for name, state in round_states.items())}"
                    )
                    return False, error_msg

        return True, ""

    def extract_playoff_matchups(
        self, league: League, division_name: str, playoff_week: int
    ) -> list[Any]:  # Returns list[PlayoffMatchup] but using Any to avoid circular import
        """
        Extract playoff matchups from ESPN API for a specific playoff week.

        Filters to winners bracket only (excludes consolation games) and extracts
        all matchup information including seeds, teams, owners, scores, and winners.

        Args:
            league: ESPN League object
            division_name: Name of the division (for matchup IDs)
            playoff_week: The playoff week to extract matchups from (e.g., 15 for semifinals)

        Returns:
            List of PlayoffMatchup objects

        Raises:
            ESPNAPIError: If matchup extraction fails

        Examples:
            >>> # Week 15 (Semifinals)
            >>> matchups = service.extract_playoff_matchups(league, "Division 1", 15)
            >>> len(matchups)  # 2 semifinal matchups
            2
            >>> # Week 16 (Finals)
            >>> matchups = service.extract_playoff_matchups(league, "Division 2", 16)
            >>> len(matchups)  # 1 finals matchup
            1
        """
        from ..models import PlayoffMatchup

        try:
            # Get box scores for the specified playoff week
            # This uses the tool's calculated current_week, not league.current_week
            box_scores = league.box_scores(playoff_week)

            # Filter to winners bracket playoff games only
            playoff_box_scores = [
                bs for bs in box_scores if bs.is_playoff and bs.matchup_type == "WINNERS_BRACKET"
            ]

            if not playoff_box_scores:
                logger.warning(
                    f"No playoff matchups found for {division_name} in week {league.current_week}"
                )
                return []

            matchups: list[Any] = []
            playoff_round = self.get_playoff_round(league)

            # Determine round name for matchup IDs
            round_prefix = "sf" if playoff_round == "Semifinals" else "finals"

            for idx, box_score in enumerate(playoff_box_scores, start=1):
                # Extract teams
                home_team = box_score.home_team
                away_team = box_score.away_team

                # Get team names
                team1_name = home_team.team_name or f"Team {home_team.team_id}"
                team2_name = away_team.team_name or f"Team {away_team.team_id}"

                # Get seeds from team.standing
                seed1 = home_team.standing
                seed2 = away_team.standing

                # Get owner names
                owner1_names = self.convert_team_owners(home_team)
                owner2_names = self.convert_team_owners(away_team)
                owner1_name = owner1_names[0].full_name if owner1_names else "Unknown Owner"
                owner2_name = owner2_names[0].full_name if owner2_names else "Unknown Owner"

                # Get scores
                score1 = box_score.home_score
                score2 = box_score.away_score

                # Determine winner (None if game not complete)
                winner_name: str | None = None
                winner_seed: int | None = None

                # Only set winner if both scores are non-zero and different
                if score1 > 0 and score2 > 0 and score1 != score2:
                    if score1 > score2:
                        winner_name = team1_name
                        winner_seed = seed1
                    else:
                        winner_name = team2_name
                        winner_seed = seed2

                # Create round name for display
                if playoff_round == "Semifinals":
                    round_display = f"Semifinal {idx}"
                else:
                    round_display = "Finals"

                # Create matchup ID
                matchup_id = f"{division_name.lower().replace(' ', '_')}_{round_prefix}{idx if playoff_round == 'Semifinals' else ''}"

                matchup = PlayoffMatchup(
                    matchup_id=matchup_id,
                    round_name=round_display,
                    seed1=seed1,
                    team1_name=team1_name,
                    owner1_name=owner1_name,
                    score1=score1 if score1 > 0 else None,
                    seed2=seed2,
                    team2_name=team2_name,
                    owner2_name=owner2_name,
                    score2=score2 if score2 > 0 else None,
                    winner_name=winner_name,
                    winner_seed=winner_seed,
                    division_name=division_name,
                )

                matchups.append(matchup)
                logger.debug(
                    f"Extracted {round_display}: {team1_name} (#{seed1}) vs {team2_name} (#{seed2})"
                )

            return matchups

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to extract playoff matchups from {division_name}: {e}",
                league_id=league.league_id,
            ) from e

    def build_playoff_bracket(
        self, league: League, division_name: str, playoff_week: int
    ) -> Any:  # Returns PlayoffBracket but using Any to avoid circular import
        """
        Build a complete playoff bracket for a division.

        Combines playoff round detection with matchup extraction to create
        a validated PlayoffBracket object.

        Args:
            league: ESPN League object
            division_name: Name of the division
            playoff_week: The playoff week to build bracket for (from self.current_week)

        Returns:
            PlayoffBracket object with all matchups

        Raises:
            ESPNAPIError: If bracket building fails

        Examples:
            >>> bracket = service.build_playoff_bracket(league, "Division 1", 15)
            >>> bracket.round  # "Semifinals" or "Finals"
            "Semifinals"
            >>> bracket.week
            15
            >>> len(bracket.matchups)  # 2 for semifinals, 1 for finals
            2
        """
        from ..models import PlayoffBracket

        try:
            # Get playoff round based on the specific week we're reporting on
            playoff_round = self.get_playoff_round(league, playoff_week)

            # Extract matchups for the specific playoff week
            matchups = self.extract_playoff_matchups(league, division_name, playoff_week)

            # Create bracket with the playoff week we're reporting on
            bracket = PlayoffBracket(round=playoff_round, week=playoff_week, matchups=matchups)

            logger.info(
                f"Built {playoff_round} bracket for {division_name}: {len(matchups)} matchup(s)"
            )

            return bracket

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to build playoff bracket for {division_name}: {e}",
                league_id=league.league_id,
            ) from e

    def extract_championship_entry(
        self, league: League, division_name: str, championship_week: int
    ) -> Any:  # Returns ChampionshipEntry but using Any to avoid circular import
        """
        Extract championship entry for a division winner.

        Finds the division champion from the Finals matchup and gets their
        Championship Week score for the overall championship competition.

        Args:
            league: ESPN League object
            division_name: Name of the division
            championship_week: Week number for championship (typically 17)

        Returns:
            ChampionshipEntry object (rank will be set later by leaderboard builder)

        Raises:
            ESPNAPIError: If championship data extraction fails

        Note:
            This method may need adjustment after Week 17 testing to confirm
            the exact structure of championship week data.

        Examples:
            >>> entry = service.extract_championship_entry(league, "Division 1", 17)
            >>> entry.team_name  # Division champion
            "Thunder Cats"
            >>> entry.score  # Championship week score
            163.45
        """
        from ..models import ChampionshipEntry

        try:
            # Find the division winner from Finals (week before championship)
            finals_week = championship_week - 1

            # Get Finals matchup to determine winner
            finals_box_scores = league.box_scores(finals_week)
            finals_matchups = [
                bs
                for bs in finals_box_scores
                if bs.is_playoff and bs.matchup_type == "WINNERS_BRACKET"
            ]

            if not finals_matchups:
                raise ESPNAPIError(
                    f"No Finals matchup found for {division_name} in week {finals_week}",
                    league_id=league.league_id,
                )

            if len(finals_matchups) > 1:
                logger.warning(
                    f"Found {len(finals_matchups)} Finals matchups, expected 1. Using first."
                )

            finals_matchup = finals_matchups[0]

            # Determine winner from Finals
            if finals_matchup.home_score > finals_matchup.away_score:
                winner_team = finals_matchup.home_team
                winner_score = finals_matchup.home_score
            else:
                winner_team = finals_matchup.away_team
                winner_score = finals_matchup.away_score

            # Validate winner has non-zero score
            if winner_score <= 0:
                raise ESPNAPIError(
                    f"Finals matchup in {division_name} appears incomplete (scores: "
                    f"{finals_matchup.home_score} - {finals_matchup.away_score})",
                    league_id=league.league_id,
                )

            winner_name = winner_team.team_name or f"Team {winner_team.team_id}"

            # Get owner information
            owners = self.convert_team_owners(winner_team)
            owner_name = owners[0].full_name if owners else "Unknown Owner"

            # Get championship week score
            # Try to find the team's score in championship week
            champ_box_scores = league.box_scores(championship_week)
            champ_score = 0.0

            # Find the winner's score in championship week
            for box_score in champ_box_scores:
                if box_score.home_team.team_id == winner_team.team_id:
                    champ_score = box_score.home_score
                    break
                elif box_score.away_team.team_id == winner_team.team_id:
                    champ_score = box_score.away_score
                    break

            # If we couldn't find a matchup, try getting score directly from team
            if champ_score <= 0:
                # Fall back to trying to get the team's score directly
                # This may need adjustment after Week 17 testing
                logger.warning(
                    f"Could not find {winner_name} in championship week matchups, "
                    f"using score 0.0 (may need adjustment after Week 17 testing)"
                )

            # Create entry with rank=1 (will be updated by leaderboard builder)
            entry = ChampionshipEntry(
                rank=1,  # Placeholder, will be set by leaderboard builder
                team_name=winner_name,
                owner_name=owner_name,
                division_name=division_name,
                score=champ_score,
                is_champion=False,  # Will be set by leaderboard builder
            )

            logger.info(
                f"Extracted championship entry for {division_name}: "
                f"{winner_name} ({owner_name}) - Score: {champ_score}"
            )

            return entry

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to extract championship entry for {division_name}: {e}",
                league_id=league.league_id,
            ) from e

    def build_championship_leaderboard(
        self, leagues: list[Any], division_names: list[str], championship_week: int
    ) -> Any:  # Returns ChampionshipLeaderboard but using Any to avoid circular import
        """
        Build championship leaderboard from all division winners.

        Collects championship entries from all divisions, sorts by score,
        and declares the overall champion (highest scorer).

        Args:
            leagues: List of ESPN League objects
            division_names: List of division names (parallel to leagues)
            championship_week: Week number for championship (typically 17)

        Returns:
            ChampionshipLeaderboard with ranked entries

        Raises:
            ESPNAPIError: If leaderboard building fails

        Note:
            This method may need adjustment after Week 17 testing.

        Examples:
            >>> leaderboard = service.build_championship_leaderboard(
            ...     [league1, league2, league3],
            ...     ["Division 1", "Division 2", "Division 3"],
            ...     17
            ... )
            >>> leaderboard.champion.team_name
            "Pineapple Express"
        """
        from ..models import ChampionshipEntry, ChampionshipLeaderboard

        try:
            # Extract entries for all divisions
            entries: list[ChampionshipEntry] = []

            for league, division_name in zip(leagues, division_names):
                entry = self.extract_championship_entry(league, division_name, championship_week)
                entries.append(entry)

            # Sort by score (highest first)
            sorted_entries = sorted(entries, key=lambda e: e.score, reverse=True)

            # Rebuild entries with correct ranks and champion flag
            ranked_entries: list[ChampionshipEntry] = []
            for rank, entry in enumerate(sorted_entries, start=1):
                ranked_entry = ChampionshipEntry(
                    rank=rank,
                    team_name=entry.team_name,
                    owner_name=entry.owner_name,
                    division_name=entry.division_name,
                    score=entry.score,
                    is_champion=(rank == 1),
                )
                ranked_entries.append(ranked_entry)

            # Create leaderboard
            leaderboard = ChampionshipLeaderboard(week=championship_week, entries=ranked_entries)

            logger.info(
                f"Built championship leaderboard: {leaderboard.champion.team_name} "
                f"({leaderboard.champion.owner_name}) wins with {leaderboard.champion.score} points"
            )

            return leaderboard

        except Exception as e:
            raise ESPNAPIError(f"Failed to build championship leaderboard: {e}") from e

    def load_division_data(self, league_id: int) -> DivisionData:
        """
        Load complete data for a single division.

        Args:
            league_id: ESPN league ID to load

        Returns:
            Complete division data (includes playoff bracket if in playoffs)

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

        # Extract weekly data if current week is available
        weekly_games: list[WeeklyGameResult] = []
        weekly_players: list[WeeklyPlayerStats] = []

        if self.current_week is not None and self.current_week > 0:
            try:
                logger.info(f"Extracting weekly data for week {self.current_week}")
                weekly_games = self.extract_weekly_games(league, league_name, self.current_week)
                weekly_players = self.extract_weekly_players(league, league_name, self.current_week)
            except Exception as e:
                logger.warning(f"Could not extract weekly data for week {self.current_week}: {e}")
                # Continue without weekly data - not a fatal error

        # Extract playoff bracket if in playoffs
        playoff_bracket = None
        # Check if the week we're displaying (self.current_week) is in playoffs
        # Not league.current_week, which may be different when using --week override
        if self.current_week is not None and self.current_week > league.settings.reg_season_count:
            try:
                # Get playoff round based on self.current_week (last complete week)
                playoff_round = self.get_playoff_round(league, self.current_week)
                # Only build bracket for Semifinals and Finals (not Championship Week)
                if playoff_round in ("Semifinals", "Finals"):
                    logger.info(f"Building playoff bracket for {playoff_round}")
                    # Use self.current_week (last complete week) for bracket extraction
                    playoff_bracket = self.build_playoff_bracket(
                        league, league_name, self.current_week
                    )
                else:
                    logger.info("Championship Week detected - no bracket needed")
            except Exception as e:
                logger.warning(f"Could not extract playoff bracket: {e}")
                # Continue without playoff bracket - will fall back to regular display

        return DivisionData(
            league_id=league_id,
            name=league_name,
            teams=teams,
            games=games,
            weekly_games=weekly_games,
            weekly_players=weekly_players,
            playoff_bracket=playoff_bracket,
        )

    def load_all_divisions(self) -> list[DivisionData]:
        """
        Load data for all configured divisions.

        Validates division synchronization for playoff operations.

        Returns:
            List of complete division data for all leagues

        Raises:
            LeagueConnectionError: If unable to connect to any league
            ESPNAPIError: If data extraction fails for any league
            DivisionSyncError: If divisions are out of sync
        """
        from ..exceptions import DivisionSyncError

        # Load all leagues first (need League objects for sync check)
        leagues: list[Any] = []  # List[League]
        for league_id in self.config.league_ids:
            try:
                league = self.connect_to_league(league_id)
                leagues.append(league)
            except Exception as e:
                logger.error(f"Failed to connect to league {league_id}: {e}")
                raise

        # Check division synchronization
        synced, error_msg = self.check_division_sync(leagues)
        if not synced:
            # Build state dictionary for error
            states: dict[str, str] = {}
            for league in leagues:
                league_name = league.settings.name or f"League {league.league_id}"
                if self.is_in_playoffs(league):
                    round_name = self.get_playoff_round(league)
                    states[league_name] = f"Week {league.current_week} ({round_name})"
                else:
                    states[league_name] = f"Week {league.current_week} (Regular Season)"

            raise DivisionSyncError(error_msg, division_states=states)

        # Now load division data for all leagues
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
