"""
Championship Week specific data models.

This module defines data structures for Week 17 Championship Week,
including division winners, roster validation, and championship leaderboards.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DataValidationError


@dataclass(frozen=True)
class ChampionshipTeam:
    """A division winner competing in Championship Week."""

    team_name: str
    owner_name: str
    division_name: str
    team_id: int  # ESPN team ID for API calls
    seed: int  # What seed they were in Finals (1-4)

    def __post_init__(self) -> None:
        """Validate championship team data after construction."""
        # Validate required fields
        if not self.team_name.strip():
            raise DataValidationError("Team name cannot be empty")
        if not self.owner_name.strip():
            raise DataValidationError("Owner name cannot be empty")
        if not self.division_name.strip():
            raise DataValidationError("Division name cannot be empty")
        if self.team_id <= 0:
            raise DataValidationError(f"Team ID must be positive: {self.team_id}")
        if self.seed <= 0:
            raise DataValidationError(f"Seed must be positive: {self.seed}")


@dataclass(frozen=True)
class RosterSlot:
    """A single roster slot with player info."""

    position: str  # "QB", "RB", "WR", "TE", "FLEX", "K", "D/ST", "BE", "IR"
    player_name: str | None  # None if empty slot
    player_team: str | None  # NFL team (e.g., "KC", "DAL")
    projected_points: float
    actual_points: float
    game_status: str  # "not_started", "in_progress", "final"
    injury_status: str | None  # "OUT", "DOUBTFUL", "QUESTIONABLE", None
    is_bye: bool
    is_starter: bool = True  # Can be False for bench players

    def __post_init__(self) -> None:
        """Validate roster slot after construction."""
        # Validate position is valid
        # Note: "RB/WR/TE" is ESPN's representation of FLEX position
        valid_positions = {
            "QB",
            "RB",
            "WR",
            "TE",
            "FLEX",
            "RB/WR/TE",
            "K",
            "D/ST",
            "BE",
            "IR",
            "BN",
        }
        if self.position not in valid_positions:
            raise DataValidationError(f"Invalid position: {self.position}")

        # Validate player name if present
        if self.player_name and not self.player_name.strip():
            raise DataValidationError("Player name cannot be empty")

        # Validate points are non-negative
        if self.actual_points < 0:
            raise DataValidationError(f"Actual points cannot be negative: {self.actual_points}")
        if self.projected_points < 0:
            raise DataValidationError(
                f"Projected points cannot be negative: {self.projected_points}"
            )

        # Validate status values
        valid_statuses = {"not_started", "in_progress", "final", "locked"}
        if self.game_status not in valid_statuses:
            raise DataValidationError(f"Invalid game status: {self.game_status}")

        # Validate that starter has actual points when game is final
        if self.is_starter and self.game_status == "final" and self.actual_points < 0:
            raise DataValidationError(
                f"Starter cannot have negative points in final game: {self.player_name} = {self.actual_points}"
            )


@dataclass(frozen=True)
class ChampionshipRoster:
    """Complete roster for a championship team."""

    team: ChampionshipTeam
    starters: list[RosterSlot]
    bench: list[RosterSlot]
    total_score: float
    projected_score: float
    is_complete: bool  # All required slots filled?
    empty_slots: list[str]  # ["RB2", "FLEX"] if any empty
    warnings: list[str]  # ["QB on bye", "WR is OUT"]
    last_modified: str | None  # Timestamp if available from ESPN

    def __post_init__(self) -> None:
        """Validate championship roster after construction."""
        # Check for empty slots (players with None names)
        empty_positions = [slot.position for slot in self.starters if not slot.player_name]

        # Validate completeness - just check if all starter slots have players
        is_complete = len(empty_positions) == 0

        # Set attributes via __dict__ to work around @dataclass limitation
        object.__setattr__(self, "empty_slots", empty_positions)
        object.__setattr__(self, "warnings", self._calculate_warnings())
        object.__setattr__(self, "is_complete", is_complete)

    def _get_required_slots(self) -> list[str]:
        """Get required starting positions based on starter positions."""
        positions = {slot.position for slot in self.starters}

        # ESPN uses "RB/WR/TE" for FLEX position, normalize it
        has_flex = "FLEX" in positions or "RB/WR/TE" in positions

        if has_flex:
            # Need at least: 1 QB, 2 RB/WR/TE (can include FLEX), 1 K, 1 D/ST
            required = {"QB"}  # QB always required

            # Count RB/WR/TE
            rb_wr_te_count = sum(1 for pos in positions if pos in {"RB", "WR", "TE"})
            if rb_wr_te_count >= 2:
                required.update({"RB", "WR", "TE"})

            # Check for K/DST
            if "K" in positions:
                required.add("K")
            if "D/ST" in positions:
                required.add("D/ST")

            return list(required)
        else:
            # No FLEX, need exact positions
            # Standard lineup: 1 QB, 2 RB, 2 WR, 1 TE, 1 FLEX, 1 K, 1 D/ST
            return ["QB", "RB", "WR", "TE", "FLEX", "K", "D/ST"]

    def _calculate_warnings(self) -> list[str]:
        """Calculate roster validation warnings."""
        warnings = []

        for slot in self.starters:
            # Check for injured players
            if slot.injury_status in {"OUT", "DOUBTFUL", "QUESTIONABLE"}:
                warnings.append(f"{slot.position} {slot.player_name} ({slot.injury_status})")

            # Check for bye weeks (unlikely in Week 17 but worth checking)
            if slot.is_bye:
                warnings.append(f"{slot.position} {slot.player_name} (BYE week)")

        # Check for empty bench slots that might indicate issues
        for slot in self.bench:
            if slot.player_name:
                position_warnings = []
                if slot.injury_status in {"OUT", "DOUBTFUL", "QUESTIONABLE"}:
                    position_warnings.append(f"({slot.injury_status})")

                if position_warnings:
                    warnings.append(
                        f"Bench {slot.position} {slot.player_name} {' '.join(position_warnings)}"
                    )

        return warnings


@dataclass(frozen=True)
class ChampionshipProgress:
    """Progress tracking for Championship Week."""

    status: str  # "not_started", "in_progress", "final"
    games_completed: int  # Number of games completed (out of total)
    total_games: int  # Total games being tracked
    last_updated: str  # Timestamp of last update

    def __post_init__(self) -> None:
        """Validate championship progress data."""
        valid_statuses = {"not_started", "in_progress", "final", "completed"}
        if self.status not in valid_statuses:
            raise DataValidationError(f"Invalid progress status: {self.status}")

        if self.games_completed < 0 or self.total_games <= 0:
            raise DataValidationError(
                f"Invalid game counts: completed={self.games_completed}, total={self.total_games}"
            )

        if self.games_completed > self.total_games:
            raise DataValidationError(
                f"Games completed cannot exceed total: {self.games_completed} > {self.total_games}"
            )
