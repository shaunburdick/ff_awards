"""
Season Recap Service for end-of-season summary generation.

This service orchestrates data extraction from multiple existing services
to build a comprehensive season summary including:
- Regular season standings and division champions
- Season-long challenge results (5 challenges)
- Playoff bracket results (Semifinals and Finals for all divisions)
- Championship results (overall champion across divisions)

Uses dynamic season structure detection to support any ESPN league configuration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from espn_api.football import League

from ..config import FFTrackerConfig
from ..exceptions import ESPNAPIError, SeasonIncompleteError
from ..models import (
    ChallengeResult,
    ChampionshipLeaderboard,
    DivisionChampion,
    DivisionData,
    PlayoffBracket,
    PlayoffRound,
    PlayoffSummary,
    RegularSeasonSummary,
    SeasonStructure,
    SeasonSummary,
)
from .challenge_service import ChallengeCalculator
from .championship_service import ChampionshipService
from .espn_service import ESPNService

logger = logging.getLogger(__name__)


class SeasonRecapService:
    """
    Service for generating comprehensive end-of-season summaries.

    Orchestrates ESPNService, ChallengeCalculator, and ChampionshipService
    to build a complete SeasonSummary with all season data.
    """

    def __init__(self, config: FFTrackerConfig) -> None:
        """
        Initialize season recap service.

        Args:
            config: Application configuration
        """
        self.config = config
        self.espn_service = ESPNService(config)
        self.challenge_calculator = ChallengeCalculator()
        self.championship_service = ChampionshipService()

    def calculate_season_structure(self, league: League) -> SeasonStructure:
        """
        Calculate dynamic season structure from ESPN league settings.

        Detects regular season boundaries and playoff weeks without
        hardcoded assumptions about league configuration.

        Args:
            league: ESPN League object

        Returns:
            SeasonStructure with week boundaries

        Examples:
            >>> structure = service.calculate_season_structure(league)
            >>> structure.regular_season_start  # 1
            >>> structure.regular_season_end    # 14
            >>> structure.playoff_start         # 15
            >>> structure.playoff_end           # 16
            >>> structure.championship_week     # 17
        """
        reg_end = league.settings.reg_season_count
        # finalScoringPeriod represents the last week of playoffs (before championship)
        playoff_end = getattr(league, "finalScoringPeriod", reg_end + 2)
        round_length = league.settings.playoff_matchup_period_length

        # Calculate number of playoff weeks and rounds
        playoff_weeks = playoff_end - reg_end
        rounds = playoff_weeks // round_length if round_length > 0 else 2

        structure = SeasonStructure(
            regular_season_start=1,
            regular_season_end=reg_end,
            playoff_start=reg_end + 1,
            playoff_end=playoff_end,
            championship_week=playoff_end + 1,
            playoff_rounds=rounds,
            playoff_round_length=round_length,
        )

        logger.debug(
            f"Calculated season structure: Regular season weeks 1-{structure.regular_season_end}, "
            f"Playoffs weeks {structure.playoff_start}-{structure.playoff_end}, "
            f"Championship week {structure.championship_week}"
        )

        return structure

    def validate_season_complete(
        self, league: League, structure: SeasonStructure, force: bool = False
    ) -> tuple[bool, str]:
        """
        Validate that the season is complete and championship week has occurred.

        Args:
            league: ESPN League object
            structure: Season structure with week boundaries
            force: If True, allow partial recap generation

        Returns:
            Tuple of (is_complete, status_message)
            - is_complete: True if season fully complete, False otherwise
            - status_message: Human-readable status ("complete", "in_playoffs", "regular_season")

        Raises:
            SeasonIncompleteError: If season incomplete and force=False
        """
        current_week = league.current_week

        # Determine season status
        if current_week < structure.regular_season_end:
            status = f"regular_season_week_{current_week}"
            is_complete = False
            message = (
                f"Season incomplete: Currently in regular season week {current_week}. "
                f"Championship week is {structure.championship_week}."
            )
        elif current_week < structure.playoff_end:
            # In playoffs
            status = "playoffs"
            is_complete = False
            message = (
                f"Season incomplete: Currently in playoffs (week {current_week}). "
                f"Championship week is {structure.championship_week}."
            )
        elif current_week == structure.playoff_end:
            # Finals week
            status = "finals"
            is_complete = False
            message = (
                f"Season incomplete: Currently in Finals (week {current_week}). "
                f"Championship week is {structure.championship_week}."
            )
        elif current_week == structure.championship_week:
            # Championship week in progress or just started
            status = "championship_week"
            is_complete = False
            message = (
                f"Championship week in progress (week {current_week}). "
                f"Recap may show partial or complete data depending on game completion."
            )
        elif current_week > structure.championship_week:
            # Season fully complete
            status = "complete"
            is_complete = True
            message = f"Season complete through championship week {structure.championship_week}."
        else:
            # Shouldn't happen, but handle it
            status = "unknown"
            is_complete = False
            message = f"Unknown season state: current week {current_week}."

        logger.debug(f"Season validation: status={status}, is_complete={is_complete}")

        # If incomplete and not forcing, raise error
        if not is_complete and not force:
            raise SeasonIncompleteError(
                f"{message} Use --force to generate partial recap.",
                current_week=current_week,
                championship_week=structure.championship_week,
            )

        return is_complete, status

    def get_regular_season_summary(
        self, leagues: list[League], division_names: list[str], structure: SeasonStructure
    ) -> tuple[RegularSeasonSummary, list[ChallengeResult]]:
        """
        Extract regular season summary from all divisions.

        Identifies division champions (top team by record in each division)
        and calculates season challenges across all divisions.

        Args:
            leagues: List of ESPN League objects
            division_names: List of division names (parallel to leagues)
            structure: Season structure with week boundaries

        Returns:
            Tuple of (RegularSeasonSummary, challenge_results)

        Raises:
            ESPNAPIError: If data extraction fails
        """
        try:
            # Load division data using ESPNService
            all_teams = []
            all_games = []
            division_champions: list[DivisionChampion] = []
            final_standings: list[DivisionData] = []

            for league, division_name in zip(leagues, division_names):
                # Extract teams and games
                teams = self.espn_service.extract_teams(league, division_name)
                games = self.espn_service.extract_games(
                    league, division_name, structure.regular_season_end
                )

                all_teams.extend(teams)
                all_games.extend(games)

                # Create DivisionData for final standings
                division_data = DivisionData(
                    league_id=league.league_id,
                    name=division_name,
                    teams=teams,
                    games=games,
                    weekly_games=[],  # Not needed for season recap
                    weekly_players=[],  # Not needed for season recap
                    playoff_bracket=None,  # Not needed for regular season summary
                )
                final_standings.append(division_data)

                # Find division champion (top team by record)
                sorted_teams = sorted(
                    teams,
                    key=lambda t: (t.wins, -t.losses, t.points_for),
                    reverse=True,
                )
                champion_team = sorted_teams[0]

                # Get owner name
                owner_name = champion_team.owner.full_name

                division_champion = DivisionChampion(
                    division_name=division_name,
                    team_name=champion_team.name,
                    owner_name=owner_name,
                    wins=champion_team.wins,
                    losses=champion_team.losses,
                    points_for=champion_team.points_for,
                    points_against=champion_team.points_against,
                    final_rank=1,  # Champion is rank 1
                )
                division_champions.append(division_champion)

                logger.debug(
                    f"Division champion: {champion_team.name} ({owner_name}) - "
                    f"{champion_team.wins}-{champion_team.losses}, {champion_team.points_for} PF"
                )

            # Calculate season challenges using ChallengeCalculator
            challenge_results: list[ChallengeResult] = []

            # 1. Most Points Overall
            challenge_results.append(
                self.challenge_calculator._calculate_most_points_overall(all_teams)
            )

            # 2. Most Points in One Game
            challenge_results.append(
                self.challenge_calculator._calculate_most_points_one_game(all_teams, all_games)
            )

            # 3. Most Points in a Loss
            challenge_results.append(
                self.challenge_calculator._calculate_most_points_in_loss(all_teams, all_games)
            )

            # 4. Least Points in a Win
            challenge_results.append(
                self.challenge_calculator._calculate_least_points_in_win(all_teams, all_games)
            )

            # 5. Closest Victory
            challenge_results.append(
                self.challenge_calculator._calculate_closest_victory(all_teams, all_games)
            )

            # Create RegularSeasonSummary
            summary = RegularSeasonSummary(
                structure=structure,
                division_champions=tuple(division_champions),
                final_standings=tuple(final_standings),
            )

            logger.debug(
                f"Regular season summary: {len(division_champions)} champions, "
                f"{len(challenge_results)} challenges"
            )

            return summary, challenge_results

        except Exception as e:
            raise ESPNAPIError(f"Failed to extract regular season summary: {e}") from e

    def get_playoff_summary(
        self, leagues: list[League], division_names: list[str], structure: SeasonStructure
    ) -> PlayoffSummary:
        """
        Extract playoff summary from all divisions.

        Builds playoff brackets for Semifinals and Finals rounds across
        all divisions using existing playoff extraction logic.

        Args:
            leagues: List of ESPN League objects
            division_names: List of division names (parallel to leagues)
            structure: Season structure with week boundaries

        Returns:
            PlayoffSummary with all playoff rounds

        Raises:
            ESPNAPIError: If playoff data extraction fails
        """
        try:
            rounds_data: list[PlayoffRound] = []

            # Build Semifinals round (first playoff week)
            semifinals_week = structure.playoff_start
            semifinals_brackets: list[PlayoffBracket] = []
            for league, division_name in zip(leagues, division_names):
                bracket = self.espn_service.build_playoff_bracket(
                    league, division_name, semifinals_week
                )
                semifinals_brackets.append(bracket)

            semifinals = PlayoffRound(
                round_name="Semifinals",
                week=semifinals_week,
                division_brackets=tuple(semifinals_brackets),
            )
            rounds_data.append(semifinals)

            logger.debug(f"Extracted Semifinals: {len(semifinals_brackets)} divisions")

            # Build Finals round (second playoff week)
            finals_week = semifinals_week + structure.playoff_round_length
            finals_brackets: list[PlayoffBracket] = []
            for league, division_name in zip(leagues, division_names):
                bracket = self.espn_service.build_playoff_bracket(
                    league, division_name, finals_week
                )
                finals_brackets.append(bracket)

            finals = PlayoffRound(
                round_name="Finals",
                week=finals_week,
                division_brackets=tuple(finals_brackets),
            )
            rounds_data.append(finals)

            logger.debug(f"Extracted Finals: {len(finals_brackets)} divisions")

            playoff_summary = PlayoffSummary(
                structure=structure,
                rounds=tuple(rounds_data),
            )

            return playoff_summary

        except Exception as e:
            raise ESPNAPIError(f"Failed to extract playoff summary: {e}") from e

    def get_championship_summary(
        self, leagues: list[League], division_names: list[str], structure: SeasonStructure
    ) -> ChampionshipLeaderboard:
        """
        Extract championship summary (Week 17 results).

        Uses ChampionshipService to build leaderboard of division winners
        competing in Championship Week.

        Args:
            leagues: List of ESPN League objects
            division_names: List of division names (parallel to leagues)
            structure: Season structure with week boundaries

        Returns:
            ChampionshipLeaderboard with ranked division winners

        Raises:
            ESPNAPIError: If championship data extraction fails
        """
        try:
            leaderboard = self.championship_service.build_leaderboard(
                leagues, division_names, structure.championship_week
            )

            logger.debug(
                f"Championship summary: {len(leaderboard.entries)} entries, "
                f"champion: {leaderboard.champion.team_name}"
            )

            return leaderboard

        except Exception as e:
            raise ESPNAPIError(f"Failed to extract championship summary: {e}") from e

    def generate_season_summary(self, force: bool = False) -> SeasonSummary:
        """
        Generate complete season summary.

        Orchestrates all data extraction to build a comprehensive
        SeasonSummary with regular season, playoffs, and championship results.

        Args:
            force: If True, generate partial recap for incomplete seasons

        Returns:
            Complete SeasonSummary

        Raises:
            SeasonIncompleteError: If season incomplete and force=False
            ESPNAPIError: If data extraction fails
        """
        try:
            # Connect to first league to get season structure
            first_league = self.espn_service.connect_to_league(self.config.league_ids[0])
            structure = self.calculate_season_structure(first_league)

            # Validate season completion
            is_complete, status = self.validate_season_complete(first_league, structure, force)

            if not is_complete and force:
                logger.warning(f"Generating partial recap (--force): Season status is '{status}'")

            # Connect to all leagues
            leagues = [
                self.espn_service.connect_to_league(league_id)
                for league_id in self.config.league_ids
            ]

            # Get division names
            division_names = self.get_division_names(leagues)

            # Extract regular season summary and challenges
            regular_season, season_challenges = self.get_regular_season_summary(
                leagues, division_names, structure
            )

            # Extract playoff summary (if available)
            playoff_summary: PlayoffSummary | None = None
            if first_league.current_week >= structure.playoff_start:
                try:
                    playoff_summary = self.get_playoff_summary(leagues, division_names, structure)
                except Exception as e:
                    logger.warning(f"Could not extract playoff summary: {e}")
                    if not force:
                        raise

            # Extract championship summary (if available)
            # Note: Championship data (Week 17) may be available even if ESPN reports current_week < 17
            # because ESPN updates rosters in real-time via team.roster.
            # We attempt to fetch championship data whenever we're past regular season.
            championship: ChampionshipLeaderboard | None = None
            if first_league.current_week >= structure.playoff_start:
                try:
                    championship = self.get_championship_summary(leagues, division_names, structure)
                    logger.debug("Championship data successfully extracted")
                except Exception as e:
                    logger.warning(f"Could not extract championship summary: {e}")
                    # Championship data may not be available yet - this is OK with --force
                    if not force:
                        raise

            # Generate timestamp
            generated_at = datetime.now(timezone.utc).isoformat()

            # Build complete season summary
            season_summary = SeasonSummary(
                year=self.config.year,
                generated_at=generated_at,
                structure=structure,
                regular_season=regular_season,
                season_challenges=tuple(season_challenges),
                playoffs=playoff_summary,  # type: ignore[arg-type]
                championship=championship,
            )

            logger.info(
                f"Generated season summary for {self.config.year}: "
                f"{len(regular_season.division_champions)} divisions, "
                f"{'complete' if is_complete else 'partial'}"
            )

            return season_summary

        except Exception as e:
            if isinstance(e, SeasonIncompleteError):
                raise
            raise ESPNAPIError(f"Failed to generate season summary: {e}") from e

    def get_division_names(self, leagues: list[League]) -> list[str]:
        """
        Get division names from leagues.

        Uses ESPN league name if available, falls back to positional naming.

        Args:
            leagues: List of ESPN League objects

        Returns:
            List of division names (parallel to leagues)

        Examples:
            >>> names = service.get_division_names([league1, league2, league3])
            >>> names
            ["The Thunder Dome", "League of Legends", "Division 3"]
        """
        division_names = []
        for index, league in enumerate(leagues):
            name = league.settings.name or f"Division {index + 1}"
            division_names.append(name)
            logger.debug(f"Division {index + 1}: {name}")

        return division_names
