"""
Configuration management for Fantasy Football Challenge Tracker.

Handles environment variables, league IDs, and ESPN authentication.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigurationError


@dataclass(frozen=True)
class ESPNCredentials:
    """ESPN private league authentication credentials."""
    swid: str
    s2: str

    def __post_init__(self) -> None:
        """Validate credentials are not empty."""
        if not self.swid.strip():
            raise ConfigurationError("ESPN_SWID cannot be empty")
        if not self.s2.strip():
            raise ConfigurationError("ESPN_S2 cannot be empty")


@dataclass(frozen=True)
class FFTrackerConfig:
    """Main configuration object for the Fantasy Football Tracker."""
    league_ids: list[int]
    year: int
    private: bool
    espn_credentials: ESPNCredentials | None = None

    def __post_init__(self) -> None:
        """Validate configuration consistency."""
        if not self.league_ids:
            raise ConfigurationError("At least one league ID is required")

        if self.private and self.espn_credentials is None:
            raise ConfigurationError(
                "ESPN credentials are required for private leagues. "
                "Set ESPN_SWID and ESPN_S2 environment variables."
            )

        if self.year < 2000:
            raise ConfigurationError(f"Invalid year: {self.year}")


def load_environment() -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file)


def parse_league_ids_from_env() -> list[int]:
    """
    Parse league IDs from the LEAGUE_IDS environment variable.

    Returns:
        List of league IDs parsed from comma-separated string.

    Raises:
        ConfigurationError: If LEAGUE_IDS is not found or malformed.
    """
    league_ids_str = os.getenv("LEAGUE_IDS")
    if not league_ids_str:
        raise ConfigurationError(
            "LEAGUE_IDS not found in environment. "
            "Add to .env file: LEAGUE_IDS=123456789,987654321,555444333"
        )

    try:
        league_ids = [int(id_str.strip()) for id_str in league_ids_str.split(",") if id_str.strip()]
        if not league_ids:
            raise ValueError("No valid league IDs found")
        return league_ids
    except ValueError as e:
        raise ConfigurationError(
            f"Error parsing LEAGUE_IDS from environment: {e}. "
            f"Format should be: LEAGUE_IDS=123456789,987654321,555444333"
        ) from e


def load_espn_credentials() -> ESPNCredentials | None:
    """
    Load ESPN credentials from environment variables.

    Returns:
        ESPN credentials if both SWID and S2 are present, None otherwise.

    Raises:
        ConfigurationError: If only one credential is provided.
    """
    swid = os.getenv("ESPN_SWID")
    s2 = os.getenv("ESPN_S2")

    if swid and s2:
        return ESPNCredentials(swid=swid, s2=s2)
    elif swid or s2:
        raise ConfigurationError(
            "Both ESPN_SWID and ESPN_S2 must be provided for private leagues. "
            "Either provide both or neither."
        )

    return None


def create_config(
    league_ids: list[int] | None = None,
    year: int | None = None,
    private: bool = False,
    use_env: bool = False
) -> FFTrackerConfig:
    """
    Create configuration object from various sources.

    Args:
        league_ids: List of league IDs, or None to load from environment
        year: Fantasy season year, or None for current year
        private: Whether to use private league authentication
        use_env: Whether to load league IDs from environment

    Returns:
        Configured FFTrackerConfig object

    Raises:
        ConfigurationError: If configuration is invalid or incomplete
    """
    # Load environment if needed
    load_environment()

    # Determine league IDs
    if use_env:
        resolved_league_ids = parse_league_ids_from_env()
    elif league_ids:
        resolved_league_ids = league_ids
    else:
        raise ConfigurationError("League IDs must be provided via --env flag or as arguments")

    # Determine year (could be enhanced to auto-detect current fantasy year)
    import datetime
    resolved_year = year if year is not None else datetime.datetime.now().year

    # Load ESPN credentials if needed
    espn_credentials = load_espn_credentials() if private else None

    return FFTrackerConfig(
        league_ids=resolved_league_ids,
        year=resolved_year,
        private=private,
        espn_credentials=espn_credentials
    )
