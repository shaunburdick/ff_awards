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
        response_data: str | None = None
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
