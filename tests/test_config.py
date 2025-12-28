"""
Comprehensive tests for configuration management.

Tests cover environment loading, validation, credentials, and configuration creation.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ff_tracker.config import (
    ESPNCredentials,
    FFTrackerConfig,
    create_config,
    detect_fantasy_year,
    load_environment,
    load_espn_credentials,
    parse_league_ids_from_env,
)
from ff_tracker.exceptions import ConfigurationError


class TestESPNCredentials:
    """Tests for ESPNCredentials validation."""

    def test_valid_credentials(self) -> None:
        """Test creation with valid credentials."""
        creds = ESPNCredentials(swid="test-swid", s2="test-s2")
        assert creds.swid == "test-swid"
        assert creds.s2 == "test-s2"

    def test_empty_swid_raises_error(self) -> None:
        """Test that empty SWID raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="ESPN_SWID cannot be empty"):
            ESPNCredentials(swid="", s2="test-s2")

    def test_whitespace_only_swid_raises_error(self) -> None:
        """Test that whitespace-only SWID raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="ESPN_SWID cannot be empty"):
            ESPNCredentials(swid="   ", s2="test-s2")

    def test_empty_s2_raises_error(self) -> None:
        """Test that empty S2 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="ESPN_S2 cannot be empty"):
            ESPNCredentials(swid="test-swid", s2="")

    def test_whitespace_only_s2_raises_error(self) -> None:
        """Test that whitespace-only S2 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="ESPN_S2 cannot be empty"):
            ESPNCredentials(swid="test-swid", s2="   ")

    def test_credentials_are_frozen(self) -> None:
        """Test that credentials are immutable (frozen dataclass)."""
        creds = ESPNCredentials(swid="test-swid", s2="test-s2")
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError is subclass of these
            creds.swid = "new-swid"  # type: ignore[misc]


class TestFFTrackerConfig:
    """Tests for FFTrackerConfig validation."""

    def test_valid_config_minimal(self) -> None:
        """Test creation with minimal valid configuration."""
        config = FFTrackerConfig(
            league_ids=[123456],
            year=2024,
            private=False,
        )
        assert config.league_ids == [123456]
        assert config.year == 2024
        assert config.private is False
        assert config.espn_credentials is None
        assert config.week is None

    def test_valid_config_with_credentials(self) -> None:
        """Test creation with private league credentials."""
        creds = ESPNCredentials(swid="test-swid", s2="test-s2")
        config = FFTrackerConfig(
            league_ids=[123456, 789012],
            year=2024,
            private=True,
            espn_credentials=creds,
            week=10,
        )
        assert config.league_ids == [123456, 789012]
        assert config.year == 2024
        assert config.private is True
        assert config.espn_credentials == creds
        assert config.week == 10

    def test_empty_league_ids_raises_error(self) -> None:
        """Test that empty league IDs list raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="At least one league ID is required"):
            FFTrackerConfig(league_ids=[], year=2024, private=False)

    def test_private_without_credentials_raises_error(self) -> None:
        """Test that private=True without credentials raises ConfigurationError."""
        with pytest.raises(
            ConfigurationError,
            match="ESPN credentials are required for private leagues",
        ):
            FFTrackerConfig(league_ids=[123456], year=2024, private=True, espn_credentials=None)

    def test_year_before_2000_raises_error(self) -> None:
        """Test that year before 2000 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Invalid year: 1999"):
            FFTrackerConfig(league_ids=[123456], year=1999, private=False)

    def test_week_below_minimum_raises_error(self) -> None:
        """Test that week < 1 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Week must be between 1 and 18, got: 0"):
            FFTrackerConfig(league_ids=[123456], year=2024, private=False, week=0)

    def test_week_above_maximum_raises_error(self) -> None:
        """Test that week > 18 raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Week must be between 1 and 18, got: 19"):
            FFTrackerConfig(league_ids=[123456], year=2024, private=False, week=19)

    def test_week_boundary_values(self) -> None:
        """Test that weeks 1 and 18 are valid boundary values."""
        config_week_1 = FFTrackerConfig(league_ids=[123456], year=2024, private=False, week=1)
        assert config_week_1.week == 1

        config_week_18 = FFTrackerConfig(league_ids=[123456], year=2024, private=False, week=18)
        assert config_week_18.week == 18

    def test_config_is_frozen(self) -> None:
        """Test that config is immutable (frozen dataclass)."""
        config = FFTrackerConfig(league_ids=[123456], year=2024, private=False)
        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError is subclass of these
            config.year = 2025  # type: ignore[misc]


class TestLoadEnvironment:
    """Tests for environment loading."""

    def test_load_environment_with_existing_dotenv(self, tmp_path: Path) -> None:
        """Test loading environment from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value\n")

        # Change to temp directory and load
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            load_environment()
            assert os.getenv("TEST_VAR") == "test_value"
        finally:
            # Cleanup
            os.chdir(original_cwd)
            if "TEST_VAR" in os.environ:
                del os.environ["TEST_VAR"]

    def test_load_environment_without_dotenv(self, tmp_path: Path) -> None:
        """Test loading environment when .env doesn't exist (should not raise)."""
        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)
            load_environment()  # Should not raise
        finally:
            os.chdir(original_cwd)


class TestParseLeagueIdsFromEnv:
    """Tests for parsing league IDs from environment."""

    def test_parse_single_league_id(self) -> None:
        """Test parsing a single league ID."""
        with patch.dict(os.environ, {"LEAGUE_IDS": "123456"}):
            league_ids = parse_league_ids_from_env()
            assert league_ids == [123456]

    def test_parse_multiple_league_ids(self) -> None:
        """Test parsing multiple comma-separated league IDs."""
        with patch.dict(os.environ, {"LEAGUE_IDS": "123456,789012,555444"}):
            league_ids = parse_league_ids_from_env()
            assert league_ids == [123456, 789012, 555444]

    def test_parse_with_whitespace(self) -> None:
        """Test parsing league IDs with surrounding whitespace."""
        with patch.dict(os.environ, {"LEAGUE_IDS": " 123456 , 789012 , 555444 "}):
            league_ids = parse_league_ids_from_env()
            assert league_ids == [123456, 789012, 555444]

    def test_parse_with_empty_segments(self) -> None:
        """Test parsing league IDs with empty segments (double commas)."""
        with patch.dict(os.environ, {"LEAGUE_IDS": "123456,,789012"}):
            league_ids = parse_league_ids_from_env()
            assert league_ids == [123456, 789012]

    def test_missing_league_ids_env_raises_error(self) -> None:
        """Test that missing LEAGUE_IDS environment variable raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="LEAGUE_IDS not found in environment"):
                parse_league_ids_from_env()

    def test_empty_league_ids_env_raises_error(self) -> None:
        """Test that empty LEAGUE_IDS environment variable raises error."""
        with patch.dict(os.environ, {"LEAGUE_IDS": ""}):
            with pytest.raises(ConfigurationError, match="LEAGUE_IDS not found in environment"):
                parse_league_ids_from_env()

    def test_only_whitespace_league_ids_raises_error(self) -> None:
        """Test that whitespace-only LEAGUE_IDS raises error."""
        with patch.dict(os.environ, {"LEAGUE_IDS": "   "}):
            with pytest.raises(ConfigurationError, match="No valid league IDs found"):
                parse_league_ids_from_env()

    def test_only_commas_league_ids_raises_error(self) -> None:
        """Test that comma-only LEAGUE_IDS raises error."""
        with patch.dict(os.environ, {"LEAGUE_IDS": ",,,"}):
            with pytest.raises(ConfigurationError, match="No valid league IDs found"):
                parse_league_ids_from_env()

    def test_non_numeric_league_ids_raises_error(self) -> None:
        """Test that non-numeric league IDs raise error."""
        with patch.dict(os.environ, {"LEAGUE_IDS": "123456,abc,789012"}):
            with pytest.raises(ConfigurationError, match="Error parsing LEAGUE_IDS"):
                parse_league_ids_from_env()

    def test_floating_point_league_ids_raises_error(self) -> None:
        """Test that floating point league IDs raise error."""
        with patch.dict(os.environ, {"LEAGUE_IDS": "123456.5,789012"}):
            with pytest.raises(ConfigurationError, match="Error parsing LEAGUE_IDS"):
                parse_league_ids_from_env()


class TestLoadESPNCredentials:
    """Tests for loading ESPN credentials."""

    def test_load_both_credentials(self) -> None:
        """Test loading when both SWID and S2 are present."""
        with patch.dict(os.environ, {"ESPN_SWID": "test-swid", "ESPN_S2": "test-s2"}):
            creds = load_espn_credentials()
            assert creds is not None
            assert creds.swid == "test-swid"
            assert creds.s2 == "test-s2"

    def test_load_no_credentials(self) -> None:
        """Test loading when neither credential is present."""
        with patch.dict(os.environ, {}, clear=True):
            creds = load_espn_credentials()
            assert creds is None

    def test_only_swid_raises_error(self) -> None:
        """Test that only SWID without S2 raises error."""
        with patch.dict(os.environ, {"ESPN_SWID": "test-swid"}, clear=True):
            with pytest.raises(
                ConfigurationError,
                match="Both ESPN_SWID and ESPN_S2 must be provided",
            ):
                load_espn_credentials()

    def test_only_s2_raises_error(self) -> None:
        """Test that only S2 without SWID raises error."""
        with patch.dict(os.environ, {"ESPN_S2": "test-s2"}, clear=True):
            with pytest.raises(
                ConfigurationError,
                match="Both ESPN_SWID and ESPN_S2 must be provided",
            ):
                load_espn_credentials()


class TestDetectFantasyYear:
    """Tests for fantasy year detection.

    Note: These tests use real datetime, so they verify the logic works
    but don't exhaustively test all months. The function is simple enough
    that this level of testing is sufficient.
    """

    def test_detect_fantasy_year_returns_int(self) -> None:
        """Test that detect_fantasy_year returns an integer year."""
        year = detect_fantasy_year()
        assert isinstance(year, int)
        assert year >= 2020  # Reasonable lower bound
        assert year <= datetime.now().year  # Can't be future


class TestCreateConfig:
    """Tests for create_config function."""

    def test_create_config_with_league_ids(self) -> None:
        """Test creating config with explicit league IDs."""
        config = create_config(league_ids=[123456, 789012], year=2024, private=False)
        assert config.league_ids == [123456, 789012]
        assert config.year == 2024
        assert config.private is False
        assert config.espn_credentials is None

    def test_create_config_from_env(self) -> None:
        """Test creating config from environment variables."""
        with patch.dict(os.environ, {"LEAGUE_IDS": "123456,789012"}):
            config = create_config(use_env=True, year=2024, private=False)
            assert config.league_ids == [123456, 789012]
            assert config.year == 2024

    def test_create_config_with_credentials(self) -> None:
        """Test creating config for private league."""
        with patch.dict(os.environ, {"ESPN_SWID": "test-swid", "ESPN_S2": "test-s2"}):
            config = create_config(league_ids=[123456], year=2024, private=True)
            assert config.private is True
            assert config.espn_credentials is not None
            assert config.espn_credentials.swid == "test-swid"

    def test_create_config_with_week(self) -> None:
        """Test creating config with specific week."""
        config = create_config(league_ids=[123456], year=2024, private=False, week=10)
        assert config.week == 10

    def test_create_config_auto_detect_year(self) -> None:
        """Test creating config with auto-detected year."""
        config = create_config(league_ids=[123456], private=False)
        # Just verify it's a reasonable year, don't test specific logic
        assert isinstance(config.year, int)
        assert config.year >= 2020

    def test_create_config_no_league_ids_raises_error(self) -> None:
        """Test that creating config without league IDs raises error."""
        with pytest.raises(
            ConfigurationError,
            match="League IDs must be provided via --env flag or as arguments",
        ):
            create_config(year=2024, private=False)

    def test_create_config_use_env_but_missing_raises_error(self) -> None:
        """Test that use_env=True without LEAGUE_IDS raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError, match="LEAGUE_IDS not found in environment"):
                create_config(use_env=True, year=2024, private=False)

    def test_create_config_private_without_env_credentials_raises_error(self) -> None:
        """Test that private=True without credentials in env raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ConfigurationError,
                match="ESPN credentials are required for private leagues",
            ):
                create_config(league_ids=[123456], year=2024, private=True)

    def test_create_config_validates_year(self) -> None:
        """Test that create_config validates year through FFTrackerConfig."""
        with pytest.raises(ConfigurationError, match="Invalid year"):
            create_config(league_ids=[123456], year=1999, private=False)

    def test_create_config_validates_week(self) -> None:
        """Test that create_config validates week through FFTrackerConfig."""
        with pytest.raises(ConfigurationError, match="Week must be between 1 and 18"):
            create_config(league_ids=[123456], year=2024, private=False, week=20)
