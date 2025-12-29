"""
Custom exceptions for Fantasy Football Challenge Tracker.

This module defines a hierarchy of custom exceptions that provide clear,
user-friendly error messages for different failure scenarios.
"""

from __future__ import annotations


class FFTrackerError(Exception):
    """Base exception for all Fantasy Football Tracker errors."""

    def __init__(self, message: str, *, league_id: int | None = None) -> None:
        self.message = message
        self.league_id = league_id
        super().__init__(message)


class ConfigurationError(FFTrackerError):
    """Raised when there are configuration or environment issues."""

    pass


class ESPNAPIError(FFTrackerError):
    """Raised when ESPN API calls fail."""

    def __init__(
        self,
        message: str,
        *,
        league_id: int | None = None,
        status_code: int | None = None,
        response_data: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message, league_id=league_id)


class LeagueConnectionError(ESPNAPIError):
    """Raised when unable to connect to a specific league."""

    pass


class PrivateLeagueError(ESPNAPIError):
    """Raised when private league credentials are missing or invalid."""

    pass


class DataValidationError(FFTrackerError):
    """Raised when data validation fails."""

    pass


class InsufficientDataError(FFTrackerError):
    """Raised when there isn't enough data to complete challenge calculations."""

    pass


class OutputFormatError(FFTrackerError):
    """Raised when output formatting fails."""

    pass


class DivisionSyncError(FFTrackerError):
    """
    Raised when divisions are out of sync for playoff operations.

    This error occurs when divisions are in different playoff states
    (e.g., some in playoffs, some in regular season) or different
    playoff rounds (e.g., some in semifinals, some in finals).

    Attributes:
        division_states: Dictionary mapping division names to their current state descriptions
    """

    def __init__(self, message: str, division_states: dict[str, str]) -> None:
        self.division_states = division_states
        super().__init__(message)


class SeasonIncompleteError(FFTrackerError):
    """
    Raised when attempting to generate season recap before season is complete.

    This error occurs when trying to generate a complete season summary
    before the championship week has finished. Can be bypassed with --force flag.

    Attributes:
        current_week: The current week number in the league
        championship_week: The week number when championship occurs
    """

    def __init__(self, message: str, *, current_week: int, championship_week: int) -> None:
        self.current_week = current_week
        self.championship_week = championship_week
        super().__init__(message)
