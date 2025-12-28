"""
Championship Week service for Week 17 operations.

This service handles Championship Week specific logic including:
- Finding division winners from Week 16 Finals
- Fetching and calculating Week 17 rosters and scores
- Building championship leaderboards
- Roster validation
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from espn_api.football import League, Team

from ..exceptions import ESPNAPIError
from ..models.championship import (
    ChampionshipProgress,
    ChampionshipRoster,
    ChampionshipTeam,
    RosterSlot,
)
from ..models.playoff import ChampionshipEntry, ChampionshipLeaderboard

logger = logging.getLogger(__name__)


class ChampionshipService:
    """Service for Championship Week operations."""

    def get_division_winners(
        self, leagues: list[League], division_names: list[str]
    ) -> list[ChampionshipTeam]:
        """
        Find division winners from Week 16 Finals matchups.

        Args:
            leagues: List of ESPN League objects
            division_names: List of division names (parallel to leagues)

        Returns:
            List of ChampionshipTeam objects for each division winner

        Raises:
            ESPNAPIError: If finals data cannot be extracted
        """
        winners = []

        for league, division_name in zip(leagues, division_names):
            try:
                # Get Week 16 Finals matchup
                finals_box_scores = league.box_scores(16)
                finals_matchups = [
                    bs
                    for bs in finals_box_scores
                    if bs.is_playoff and bs.matchup_type == "WINNERS_BRACKET"
                ]

                if not finals_matchups:
                    raise ESPNAPIError(
                        f"No Finals matchup found for {division_name} in Week 16",
                        league_id=league.league_id,
                    )

                if len(finals_matchups) > 1:
                    logger.warning(
                        f"Found {len(finals_matchups)} Finals matchups for {division_name}, "
                        f"expected 1. Using first."
                    )

                finals_matchup = finals_matchups[0]

                # Determine winner
                if finals_matchup.home_score > finals_matchup.away_score:
                    winner_team = finals_matchup.home_team
                    winner_score = finals_matchup.home_score
                    winner_seed = self._get_team_seed(winner_team)
                else:
                    winner_team = finals_matchup.away_team
                    winner_score = finals_matchup.away_score
                    winner_seed = self._get_team_seed(winner_team)

                # Validate winner has non-zero score
                if winner_score <= 0:
                    raise ESPNAPIError(
                        f"Finals matchup in {division_name} appears incomplete "
                        f"(scores: {finals_matchup.home_score} - {finals_matchup.away_score})",
                        league_id=league.league_id,
                    )

                # Get owner information
                from ..config import create_config
                from .espn_service import ESPNService

                # Create a minimal config for owner extraction
                config = create_config(league_ids=[league.league_id], year=league.year)
                service = ESPNService(config)
                owners = service.convert_team_owners(winner_team)
                owner_name = owners[0].full_name if owners else "Unknown Owner"

                # Create ChampionshipTeam
                champion = ChampionshipTeam(
                    team_name=winner_team.team_name or f"Team {winner_team.team_id}",
                    owner_name=owner_name,
                    division_name=division_name,
                    team_id=winner_team.team_id,
                    seed=winner_seed,
                )

                winners.append(champion)
                logger.debug(
                    f"Division winner: {champion.team_name} ({champion.owner_name}) "
                    f"from {division_name}"
                )

            except Exception as e:
                raise ESPNAPIError(
                    f"Failed to get division winner for {division_name}: {e}",
                    league_id=league.league_id,
                ) from e

        return winners

    def get_roster(
        self, league: League, team: ChampionshipTeam, week: int = 17
    ) -> ChampionshipRoster:
        """
        Get roster for a championship team.

        For Week 17+, ESPN's box_scores() returns stale data from previous weeks
        because leagues end at Week 16. This method detects Week 17+ and uses
        team.roster to fetch live Week 17 data instead.

        Args:
            league: ESPN League object
            team: ChampionshipTeam to get roster for
            week: Week number (default 17)

        Returns:
            ChampionshipRoster with complete roster details

        Raises:
            ESPNAPIError: If roster cannot be fetched
        """
        # For Week 17+, use roster-based approach
        # ESPN returns stale Week 16 data from box_scores(17)
        if week >= 17:
            return self._get_roster_from_team_roster(league, team, week)
        else:
            return self._get_roster_from_box_score(league, team, week)

    def _get_roster_from_team_roster(
        self, league: League, team: ChampionshipTeam, week: int
    ) -> ChampionshipRoster:
        """
        Get roster data from team.roster for Week 17+ (post-season).

        ESPN's box_scores() returns stale data for weeks after league ends,
        but team.roster contains live Week 17 stats in player.stats[week].

        Args:
            league: ESPN League object
            team: ChampionshipTeam to get roster for
            week: Week number

        Returns:
            ChampionshipRoster with complete roster details
        """
        try:
            # Find the ESPN Team object
            espn_team = None
            for t in league.teams:
                if t.team_id == team.team_id:  # type: ignore[attr-defined]
                    espn_team = t
                    break

            if not espn_team:
                raise ESPNAPIError(
                    f"Could not find team {team.team_name} in league",
                    league_id=league.league_id,
                )

            # Get the team's roster
            roster_players = espn_team.roster  # type: ignore[attr-defined]

            # Convert to RosterSlot objects
            starters = []
            bench = []
            total_score = 0.0
            projected_score = 0.0

            for player in roster_players:
                # Check if player has Week data
                if not hasattr(player, "stats") or not isinstance(player.stats, dict):
                    continue

                if week not in player.stats:
                    continue

                week_data = player.stats[week]

                # Get points and projections from week data
                actual_points = week_data.get("points", 0.0)
                proj_points = week_data.get("projected_points", 0.0)

                # Determine if starter or bench based on lineupSlot
                slot_position = player.lineupSlot if hasattr(player, "lineupSlot") else "BE"
                is_starter = slot_position != "BE" and slot_position != "IR"

                # Get game status based on Week data
                game_status = self._get_game_status_from_week_data(week_data, proj_points)

                # Create RosterSlot
                slot = RosterSlot(
                    position=slot_position,
                    player_name=player.name if hasattr(player, "name") else None,
                    player_team=player.proTeam if hasattr(player, "proTeam") else None,
                    projected_points=proj_points,
                    actual_points=actual_points,
                    game_status=game_status,
                    injury_status=player.injuryStatus if hasattr(player, "injuryStatus") else None,
                    is_bye=self._is_bye_week(player),
                    is_starter=is_starter,
                )

                if is_starter:
                    starters.append(slot)
                    total_score += slot.actual_points
                    projected_score += slot.projected_points
                else:
                    bench.append(slot)

            # Create ChampionshipRoster
            roster = ChampionshipRoster(
                team=team,
                starters=starters,
                bench=bench,
                total_score=total_score,
                projected_score=projected_score,
                is_complete=True,  # Will be validated in __post_init__
                empty_slots=[],  # Will be calculated in __post_init__
                warnings=[],  # Will be calculated in __post_init__
                last_modified=None,  # ESPN doesn't provide this easily
            )

            logger.debug(
                f"Fetched roster for {team.team_name} from team.roster: "
                f"{len(starters)} starters, {len(bench)} bench, score: {total_score}"
            )

            return roster

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to get roster for {team.team_name}: {e}",
                league_id=league.league_id,
            ) from e

    def _get_roster_from_box_score(
        self, league: League, team: ChampionshipTeam, week: int
    ) -> ChampionshipRoster:
        """
        Get roster data from box_scores (for Week 16 and earlier).

        Args:
            league: ESPN League object
            team: ChampionshipTeam to get roster for
            week: Week number

        Returns:
            ChampionshipRoster with complete roster details
        """
        try:
            # Get box score for the team in the specified week
            box_scores = league.box_scores(week)

            # Find the box score containing this team
            team_box_score = None
            for box_score in box_scores:
                if (
                    box_score.home_team.team_id == team.team_id
                    or box_score.away_team.team_id == team.team_id
                ):
                    team_box_score = box_score
                    break

            if not team_box_score:
                raise ESPNAPIError(
                    f"No box score found for {team.team_name} in Week {week}",
                    league_id=league.league_id,
                )

            # Get lineup for this team
            if team_box_score.home_team.team_id == team.team_id:
                lineup = team_box_score.home_lineup
            else:
                lineup = team_box_score.away_lineup

            # Convert to RosterSlot objects
            starters = []
            bench = []
            total_score = 0.0
            projected_score = 0.0

            for player in lineup:
                # Determine if starter or bench
                is_starter = player.slot_position != "BE" and player.slot_position != "IR"

                # Get player details
                slot = RosterSlot(
                    position=player.slot_position,
                    player_name=player.name if hasattr(player, "name") else None,
                    player_team=player.proTeam if hasattr(player, "proTeam") else None,
                    projected_points=player.projected_points
                    if hasattr(player, "projected_points")
                    else 0.0,
                    actual_points=player.points if hasattr(player, "points") else 0.0,
                    game_status=self._get_game_status(player),
                    injury_status=player.injuryStatus if hasattr(player, "injuryStatus") else None,
                    is_bye=self._is_bye_week(player),
                    is_starter=is_starter,
                )

                if is_starter:
                    starters.append(slot)
                    total_score += slot.actual_points
                    projected_score += slot.projected_points
                else:
                    bench.append(slot)

            # Create ChampionshipRoster
            roster = ChampionshipRoster(
                team=team,
                starters=starters,
                bench=bench,
                total_score=total_score,
                projected_score=projected_score,
                is_complete=True,  # Will be validated in __post_init__
                empty_slots=[],  # Will be calculated in __post_init__
                warnings=[],  # Will be calculated in __post_init__
                last_modified=None,  # ESPN doesn't provide this easily
            )

            logger.debug(
                f"Fetched roster for {team.team_name} from box_score: "
                f"{len(starters)} starters, {len(bench)} bench, score: {total_score}"
            )

            return roster

        except Exception as e:
            raise ESPNAPIError(
                f"Failed to get roster for {team.team_name}: {e}",
                league_id=league.league_id,
            ) from e

    def calculate_score(self, roster: ChampionshipRoster) -> float:
        """
        Calculate total score from roster starters.

        Args:
            roster: ChampionshipRoster to calculate score for

        Returns:
            Total points from all starters
        """
        return sum(slot.actual_points for slot in roster.starters)

    def build_leaderboard(
        self,
        leagues: list[League],
        division_names: list[str],
        week: int = 17,
    ) -> ChampionshipLeaderboard:
        """
        Build championship leaderboard from all division winners.

        Args:
            leagues: List of ESPN League objects
            division_names: List of division names (parallel to leagues)
            week: Championship week number (default 17)

        Returns:
            ChampionshipLeaderboard with ranked entries

        Raises:
            ESPNAPIError: If leaderboard cannot be built
        """
        try:
            # Get division winners
            winners = self.get_division_winners(leagues, division_names)

            # Get rosters and scores for each winner
            winner_scores = []
            for winner, league in zip(winners, leagues):
                roster = self.get_roster(league, winner, week)
                score = self.calculate_score(roster)
                winner_scores.append((winner, score))

            # Sort by score (descending)
            winner_scores.sort(key=lambda x: x[1], reverse=True)

            # Create entries with correct ranks
            entries = []
            for rank, (winner, score) in enumerate(winner_scores, start=1):
                entry = ChampionshipEntry(
                    rank=rank,
                    team_name=winner.team_name,
                    owner_name=winner.owner_name,
                    division_name=winner.division_name,
                    score=score,
                    is_champion=(rank == 1),  # Champion is rank 1
                )
                entries.append(entry)

            leaderboard = ChampionshipLeaderboard(week=week, entries=entries)

            logger.debug(
                f"Built championship leaderboard with {len(entries)} entries. "
                f"Champion: {entries[0].team_name} ({entries[0].score} pts)"
            )

            return leaderboard

        except Exception as e:
            raise ESPNAPIError(f"Failed to build championship leaderboard: {e}") from e

    def get_progress(self, rosters: list[ChampionshipRoster]) -> ChampionshipProgress:
        """
        Calculate championship progress from rosters.

        Args:
            rosters: List of ChampionshipRoster objects

        Returns:
            ChampionshipProgress with status and completion counts
        """
        total_games = 0
        completed_games = 0

        for roster in rosters:
            for slot in roster.starters:
                total_games += 1
                if slot.game_status == "final":
                    completed_games += 1

        # Determine status
        if completed_games == 0:
            status = "not_started"
        elif completed_games < total_games:
            status = "in_progress"
        else:
            status = "final"

        return ChampionshipProgress(
            status=status,
            games_completed=completed_games,
            total_games=total_games,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    def _get_team_seed(self, team: Team) -> int:
        """
        Get playoff seed for a team.

        Args:
            team: ESPN Team object

        Returns:
            Playoff seed (1-4)
        """
        # Try to get playoff seed from team
        if hasattr(team, "playoff_seed"):
            seed = team.playoff_seed
            if seed:
                return int(seed)

        # Fall back to using standing (may not be accurate for playoff seed)
        if hasattr(team, "standing"):
            standing = team.standing
            if standing:
                return int(standing)

        # Default to 1 if we can't determine
        logger.warning(f"Could not determine seed for {team.team_name}, defaulting to 1")
        return 1

    def _get_game_status(self, player: object) -> str:
        """
        Get game status for a player using projection-based detection.

        For post-season consolation weeks (Week 17+), ESPN provides static scores
        rather than live updates. We use projections to infer game status:
        - projected=0, points=0: Player ruled out/inactive (counts as "final")
        - projected>0, points=0: Game not started yet (counts as "not_started")
        - points>0: Game started or complete (counts as "final")

        Args:
            player: ESPN Player object

        Returns:
            Game status: "final", "not_started", or "in_progress"
        """
        points = player.points if hasattr(player, "points") else 0.0
        projected = player.projected_points if hasattr(player, "projected_points") else 0.0

        # Player ruled out/inactive (projection set to 0 before game)
        if projected == 0.0 and points == 0.0:
            return "final"

        # Player has projection but no points = game not started
        if points == 0.0 and projected > 0.0:
            return "not_started"

        # Player has points = game started or complete
        # (We can't distinguish between in_progress and final with ESPN's data)
        return "final"

    def _get_game_status_from_week_data(self, week_data: dict, projected: float) -> str:
        """
        Get game status from player's week stats dictionary.

        Used for Week 17+ when accessing data from player.stats[week].

        Args:
            week_data: Dictionary containing week stats (from player.stats[week])
            projected: Projected points for the week

        Returns:
            Game status: "final", "not_started", or "in_progress"
        """
        points = week_data.get("points", 0.0)

        # Player ruled out/inactive (projection set to 0 before game)
        if projected == 0.0 and points == 0.0:
            return "final"

        # Player has projection but no points = game not started
        if points == 0.0 and projected > 0.0:
            return "not_started"

        # Player has points = game started or complete
        return "final"

    def _is_bye_week(self, player: object) -> bool:
        """
        Check if player is on bye week.

        Args:
            player: ESPN Player object

        Returns:
            True if on bye, False otherwise
        """
        # Week 17 typically has no byes, but check just in case
        if hasattr(player, "on_bye_week"):
            return bool(player.on_bye_week)
        return False
