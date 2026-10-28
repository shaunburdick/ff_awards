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
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MAX_PROMPT_CHARS,
    DEFAULT_AI_MAX_TOKENS,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_TIMEOUT,
    AIMemoryConfig,
    AISummaryConfig,
    ESPNCredentials,
    FFTrackerConfig,
    create_config,
    detect_fantasy_year,
    load_ai_summary_config,
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
            with patch("ff_tracker.config.load_environment"):  # Mock to prevent .env loading
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


class TestAISummaryConfig:
    """AI narrative configuration: FR-007 and FR-010."""

    _VARS = (
        "AI_SUMMARY_ENABLED",
        "AI_SUMMARY_API_KEY",
        "AI_SUMMARY_BASE_URL",
        "AI_SUMMARY_MODEL",
        "AI_SUMMARY_TIMEOUT",
        "AI_SUMMARY_MAX_TOKENS",
        "AI_SUMMARY_REASONING_EFFORT",
        "AI_SUMMARY_MAX_PROMPT_CHARS",
        "AI_SUMMARY_USER_PROMPT",
    )

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clear every AI variable and stop the repo's .env leaking in."""
        for name in self._VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr("ff_tracker.config.load_environment", lambda *args, **kwargs: None)

    @pytest.fixture
    def enabled_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Turn the feature on, so the other variables are actually read."""
        monkeypatch.setenv("AI_SUMMARY_ENABLED", "true")
        monkeypatch.setenv("AI_SUMMARY_API_KEY", "sk-test")

    def test_defaults_when_nothing_is_set(self) -> None:
        config = load_ai_summary_config()
        assert config.enabled is False
        assert config.api_key == ""
        assert config.base_url == DEFAULT_AI_BASE_URL
        assert config.model == DEFAULT_AI_MODEL
        assert config.timeout == DEFAULT_AI_TIMEOUT
        assert config.max_prompt_chars == DEFAULT_AI_MAX_PROMPT_CHARS
        assert config.user_prompt == ""

    @pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE", " Yes "])
    def test_enabled_accepts_the_true_spellings(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_ENABLED", value)
        monkeypatch.setenv("AI_SUMMARY_API_KEY", "sk-test")
        assert load_ai_summary_config().enabled is True

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "OFF"])
    def test_enabled_accepts_the_false_spellings(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_ENABLED", value)
        assert load_ai_summary_config().enabled is False

    def test_bad_enabled_value_raises_naming_the_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_ENABLED", "maybe")
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_ENABLED must be one of"):
            load_ai_summary_config()

    def test_enabled_without_key_raises_naming_the_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_ENABLED", "true")
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_API_KEY is required"):
            load_ai_summary_config()

    def test_enabled_with_whitespace_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_SUMMARY_ENABLED", "true")
        monkeypatch.setenv("AI_SUMMARY_API_KEY", "   ")
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_API_KEY is required"):
            load_ai_summary_config()

    def test_a_key_alone_does_not_enable_the_feature(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_SUMMARY_API_KEY", "sk-test")
        assert load_ai_summary_config().enabled is False

    def test_other_variables_are_ignored_when_the_feature_is_off(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FR-007: a stale AI variable cannot deny a report while the feature is off."""
        monkeypatch.setenv("AI_SUMMARY_TIMEOUT", "abc")
        monkeypatch.setenv("AI_SUMMARY_MAX_TOKENS", "nonsense")
        monkeypatch.setenv("AI_SUMMARY_REASONING_EFFORT", "extreme")
        monkeypatch.setenv("AI_SUMMARY_BASE_URL", "not a url")
        monkeypatch.setenv("AI_SUMMARY_MAX_PROMPT_CHARS", "0")

        config = load_ai_summary_config()

        assert config.enabled is False
        assert config.timeout == DEFAULT_AI_TIMEOUT
        assert config.max_tokens == DEFAULT_AI_MAX_TOKENS
        assert config.reasoning_effort is None
        assert config.base_url == DEFAULT_AI_BASE_URL

    def test_malformed_flag_is_still_an_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An unreadable flag cannot be read as off."""
        monkeypatch.setenv("AI_SUMMARY_ENABLED", "maybe")
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_ENABLED must be one of"):
            load_ai_summary_config()

    def test_bad_base_url_raises_naming_the_variable(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A URL urlopen cannot parse must fail as configuration, not as ValueError."""
        monkeypatch.setenv("AI_SUMMARY_BASE_URL", "opencode.ai/inference/openai/v1")
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_BASE_URL must be an http"):
            load_ai_summary_config()

    def test_base_url_without_a_host_raises(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_BASE_URL", "https:///v1")
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_BASE_URL must be an http"):
            load_ai_summary_config()

    @pytest.mark.parametrize("value", ["0", "-5", "abc", "1.5"])
    def test_bad_timeout_raises_naming_the_variable(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_TIMEOUT", value)
        with pytest.raises(
            ConfigurationError, match="AI_SUMMARY_TIMEOUT must be a positive integer"
        ):
            load_ai_summary_config()

    @pytest.mark.parametrize("value", ["0", "-1", "lots"])
    def test_bad_prompt_limit_raises_naming_the_variable(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_MAX_PROMPT_CHARS", value)
        with pytest.raises(
            ConfigurationError, match="AI_SUMMARY_MAX_PROMPT_CHARS must be a positive integer"
        ):
            load_ai_summary_config()

    def test_oversized_prompt_names_length_and_configured_limit(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_MAX_PROMPT_CHARS", "100")
        monkeypatch.setenv("AI_SUMMARY_USER_PROMPT", "x" * 101)
        with pytest.raises(ConfigurationError) as excinfo:
            load_ai_summary_config()
        message = str(excinfo.value)
        assert "AI_SUMMARY_USER_PROMPT" in message
        assert "101" in message
        assert "100" in message

    def test_prompt_at_the_limit_is_accepted(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_MAX_PROMPT_CHARS", "100")
        monkeypatch.setenv("AI_SUMMARY_USER_PROMPT", "x" * 100)
        assert len(load_ai_summary_config().user_prompt) == 100

    @pytest.mark.parametrize("value", ["", "   ", "\n\t "])
    def test_empty_prompt_is_a_no_op(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_USER_PROMPT", value)
        assert load_ai_summary_config().user_prompt == ""

    def test_prompt_is_stripped_and_crlf_normalised(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_USER_PROMPT", "  Be dry.\r\nNo emoji.  ")
        assert load_ai_summary_config().user_prompt == "Be dry.\nNo emoji."

    @pytest.mark.parametrize("value", ["", "   "])
    def test_blank_base_url_falls_back_to_the_default(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_BASE_URL", value)
        assert load_ai_summary_config().base_url == DEFAULT_AI_BASE_URL

    def test_explicit_base_url_overrides_and_loses_trailing_slash(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_BASE_URL", "https://proxy.example/v1/")
        assert load_ai_summary_config().base_url == "https://proxy.example/v1"

    def test_api_key_is_not_in_the_repr(self) -> None:
        config = AISummaryConfig(enabled=True, api_key="sk-secret-value")
        assert "sk-secret-value" not in repr(config)

    def test_dotenv_only_configuration_enables_the_feature(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A .env-only setup works with create_config left unpatched (Gate 2)."""
        monkeypatch.setattr("ff_tracker.config.load_environment", load_environment)
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "LEAGUE_IDS=123456\n"
            "AI_SUMMARY_ENABLED=true\n"
            "AI_SUMMARY_API_KEY=sk-from-dotenv\n"
            "AI_SUMMARY_MODEL=dotenv-model\n",
            encoding="utf-8",
        )

        # load_dotenv writes os.environ directly, outside monkeypatch's control.
        snapshot = dict(os.environ)
        try:
            create_config(league_ids=[123456], year=2024, private=False)
            config = load_ai_summary_config()
        finally:
            os.environ.clear()
            os.environ.update(snapshot)

        assert config.enabled is True
        assert config.api_key == "sk-from-dotenv"
        assert config.model == "dotenv-model"


class TestAISummaryBudgetAndEffort:
    """AI_SUMMARY_MAX_TOKENS and AI_SUMMARY_REASONING_EFFORT (spec v0.9)."""

    _VARS = (
        "AI_SUMMARY_ENABLED",
        "AI_SUMMARY_API_KEY",
        "AI_SUMMARY_BASE_URL",
        "AI_SUMMARY_MODEL",
        "AI_SUMMARY_TIMEOUT",
        "AI_SUMMARY_MAX_TOKENS",
        "AI_SUMMARY_REASONING_EFFORT",
        "AI_SUMMARY_MAX_PROMPT_CHARS",
        "AI_SUMMARY_USER_PROMPT",
    )

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in self._VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr("ff_tracker.config.load_environment", lambda *args, **kwargs: None)

    @pytest.fixture
    def enabled_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Turn the feature on, so the other variables are actually read."""
        monkeypatch.setenv("AI_SUMMARY_ENABLED", "true")
        monkeypatch.setenv("AI_SUMMARY_API_KEY", "sk-test")

    @pytest.mark.parametrize(
        ("variable", "expected"),
        [
            ("AI_SUMMARY_TIMEOUT", DEFAULT_AI_TIMEOUT),
            ("AI_SUMMARY_MAX_TOKENS", DEFAULT_AI_MAX_TOKENS),
            ("AI_SUMMARY_MAX_PROMPT_CHARS", DEFAULT_AI_MAX_PROMPT_CHARS),
            ("AI_SUMMARY_MODEL", DEFAULT_AI_MODEL),
            ("AI_SUMMARY_BASE_URL", DEFAULT_AI_BASE_URL),
            ("AI_SUMMARY_REASONING_EFFORT", None),
        ],
    )
    def test_a_blank_variable_means_the_default(
        self,
        enabled_env: None,
        monkeypatch: pytest.MonkeyPatch,
        variable: str,
        expected: object,
    ) -> None:
        """An unset repository variable renders empty; blank must not be an error."""
        monkeypatch.setenv(variable, "")
        config = load_ai_summary_config()

        resolved: dict[str, object] = {
            "AI_SUMMARY_TIMEOUT": config.timeout,
            "AI_SUMMARY_MAX_TOKENS": config.max_tokens,
            "AI_SUMMARY_MAX_PROMPT_CHARS": config.max_prompt_chars,
            "AI_SUMMARY_MODEL": config.model,
            "AI_SUMMARY_BASE_URL": config.base_url,
            "AI_SUMMARY_REASONING_EFFORT": config.reasoning_effort,
        }
        assert resolved[variable] == expected

    def test_all_optional_variables_blank_together(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The workflow's own shape: every optional variable unset at once."""
        for name in (
            "AI_SUMMARY_TIMEOUT",
            "AI_SUMMARY_MAX_TOKENS",
            "AI_SUMMARY_MAX_PROMPT_CHARS",
            "AI_SUMMARY_MODEL",
            "AI_SUMMARY_BASE_URL",
            "AI_SUMMARY_REASONING_EFFORT",
        ):
            monkeypatch.setenv(name, "")

        config = load_ai_summary_config()

        assert config.timeout == DEFAULT_AI_TIMEOUT
        assert config.max_tokens == DEFAULT_AI_MAX_TOKENS
        assert config.max_prompt_chars == DEFAULT_AI_MAX_PROMPT_CHARS
        assert config.model == DEFAULT_AI_MODEL
        assert config.base_url == DEFAULT_AI_BASE_URL
        assert config.reasoning_effort is None

    def test_model_default_is_deepseek(self) -> None:
        assert load_ai_summary_config().model == "deepseek-v4.1-flash"
        assert DEFAULT_AI_MODEL == "deepseek-v4.1-flash"

    def test_max_tokens_defaults_to_eight_thousand(self) -> None:
        assert load_ai_summary_config().max_tokens == DEFAULT_AI_MAX_TOKENS == 8000

    def test_max_tokens_is_read_from_the_environment(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_MAX_TOKENS", "1234")
        assert load_ai_summary_config().max_tokens == 1234

    @pytest.mark.parametrize("value", ["0", "-1", "abc", "1.5"])
    def test_bad_max_tokens_raises_naming_the_variable(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_MAX_TOKENS", value)
        with pytest.raises(
            ConfigurationError, match="AI_SUMMARY_MAX_TOKENS must be a positive integer"
        ):
            load_ai_summary_config()

    def test_reasoning_effort_defaults_to_none(self) -> None:
        assert load_ai_summary_config().reasoning_effort is None

    @pytest.mark.parametrize("value", ["", "   "])
    def test_blank_reasoning_effort_means_unset(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_REASONING_EFFORT", value)
        assert load_ai_summary_config().reasoning_effort is None

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("low", "low"), ("LOW", "low"), ("Medium", "medium"), (" high ", "high")],
    )
    def test_reasoning_effort_is_normalised_to_lowercase(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch, value: str, expected: str
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_REASONING_EFFORT", value)
        assert load_ai_summary_config().reasoning_effort == expected

    def test_bad_reasoning_effort_lists_the_allowed_values(
        self, enabled_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_REASONING_EFFORT", "extreme")
        with pytest.raises(ConfigurationError) as excinfo:
            load_ai_summary_config()
        message = str(excinfo.value)
        assert "AI_SUMMARY_REASONING_EFFORT" in message
        for allowed in ("low", "medium", "high"):
            assert allowed in message

    def test_direct_construction_normalises_and_rejects(self) -> None:
        assert AISummaryConfig(reasoning_effort="LOW").reasoning_effort == "low"
        assert AISummaryConfig(reasoning_effort="  ").reasoning_effort is None
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_REASONING_EFFORT"):
            AISummaryConfig(reasoning_effort="ludicrous")
        with pytest.raises(ConfigurationError, match="AI_SUMMARY_MAX_TOKENS"):
            AISummaryConfig(max_tokens=0)


class TestEnvFile:
    """--env-file: an explicit path is loaded, and a missing one is an error."""

    _VARS = (
        "LEAGUE_IDS",
        "ESPN_SWID",
        "ESPN_S2",
        "AI_SUMMARY_ENABLED",
        "AI_SUMMARY_API_KEY",
        "AI_SUMMARY_MODEL",
        "AI_SUMMARY_BASE_URL",
        "AI_SUMMARY_TIMEOUT",
        "AI_SUMMARY_MAX_TOKENS",
        "AI_SUMMARY_REASONING_EFFORT",
        "AI_SUMMARY_MAX_PROMPT_CHARS",
        "AI_SUMMARY_USER_PROMPT",
    )

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in self._VARS:
            monkeypatch.delenv(name, raising=False)

    def test_explicit_file_supplies_league_ids(self, tmp_path: Path) -> None:
        """The functional claim: --env-file is the file that is read."""
        alt = tmp_path / "alt.env"
        alt.write_text("LEAGUE_IDS=111111,222222\n", encoding="utf-8")

        config = create_config(use_env=True, year=2024, env_file=alt)

        assert config.league_ids == [111111, 222222]

    def test_repo_dotenv_is_not_read_when_an_explicit_file_is_given(self, tmp_path: Path) -> None:
        alt = tmp_path / "alt.env"
        alt.write_text("LEAGUE_IDS=333333\n", encoding="utf-8")

        config = create_config(use_env=True, year=2024, env_file=alt)

        assert config.league_ids == [333333]

    def test_explicit_file_supplies_espn_credentials(self, tmp_path: Path) -> None:
        alt = tmp_path / "alt.env"
        alt.write_text(
            "LEAGUE_IDS=444444\nESPN_SWID=swid-from-file\nESPN_S2=s2-from-file\n",
            encoding="utf-8",
        )

        config = create_config(use_env=True, year=2024, private=True, env_file=alt)

        assert config.espn_credentials is not None
        assert config.espn_credentials.swid == "swid-from-file"
        assert config.espn_credentials.s2 == "s2-from-file"

    def test_ai_settings_come_from_the_same_file(self, tmp_path: Path) -> None:
        """Both loaders read one file: no second, different .env."""
        alt = tmp_path / "alt.env"
        alt.write_text(
            "LEAGUE_IDS=555555\n"
            "AI_SUMMARY_ENABLED=true\n"
            "AI_SUMMARY_API_KEY=sk-from-alt\n"
            "AI_SUMMARY_MODEL=model-from-alt\n",
            encoding="utf-8",
        )

        create_config(use_env=True, year=2024, env_file=alt)
        ai_config = load_ai_summary_config(alt)

        assert ai_config.enabled is True
        assert ai_config.api_key == "sk-from-alt"
        assert ai_config.model == "model-from-alt"

    def test_missing_explicit_file_raises_naming_it(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.env"

        with pytest.raises(ConfigurationError, match="Environment file not found"):
            create_config(use_env=True, year=2024, env_file=missing)

        with pytest.raises(ConfigurationError, match=str(missing)):
            load_environment(missing)

    def test_default_behaviour_is_unchanged_without_a_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No --env-file: .env in the working directory, loaded only if present."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("LEAGUE_IDS", raising=False)

        load_environment()  # no file, no error — the old behaviour
        assert "LEAGUE_IDS" not in os.environ

        (tmp_path / ".env").write_text("LEAGUE_IDS=666666\n", encoding="utf-8")
        load_environment()
        assert os.environ.get("LEAGUE_IDS") == "666666"


class TestMemoryConfig:
    """FR-013/FR-007: the memory group, validated only inside the enabled branch."""

    _VARS = (
        "AI_SUMMARY_ENABLED",
        "AI_SUMMARY_API_KEY",
        "AI_SUMMARY_TIMEOUT",
        "AI_MEMORY_ENABLED",
        "AI_MEMORY_GIST_ID",
        "AI_MEMORY_GIST_TOKEN",
    )

    @pytest.fixture(autouse=True)
    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in self._VARS:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr("ff_tracker.config.load_environment", lambda *args, **kwargs: None)

    @pytest.fixture
    def memory_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The feature and memory both on, with both settings present."""
        monkeypatch.setenv("AI_SUMMARY_ENABLED", "true")
        monkeypatch.setenv("AI_SUMMARY_API_KEY", "sk-test")
        monkeypatch.setenv("AI_MEMORY_ENABLED", "true")
        monkeypatch.setenv("AI_MEMORY_GIST_ID", "abc123")
        monkeypatch.setenv("AI_MEMORY_GIST_TOKEN", "ghp-test")

    def test_memory_is_none_when_the_group_is_unset(self) -> None:
        assert load_ai_summary_config().memory is None

    def test_a_configured_gist_is_returned(self, memory_env: None) -> None:
        memory = load_ai_summary_config().memory

        assert memory is not None
        assert memory.gist_id == "abc123"
        assert memory.gist_token == "ghp-test"

    @pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE", " On "])
    def test_enabled_accepts_the_true_spellings(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_MEMORY_ENABLED", value)
        memory = load_ai_summary_config().memory

        assert memory is not None

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", "OFF"])
    def test_false_spellings_mean_no_memory(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_MEMORY_ENABLED", value)
        assert load_ai_summary_config().memory is None

    def test_bad_flag_value_raises_naming_the_variable(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_MEMORY_ENABLED", "maybe")
        with pytest.raises(ConfigurationError, match="AI_MEMORY_ENABLED must be one of"):
            load_ai_summary_config()

    @pytest.mark.parametrize("value", ["", "   "])
    def test_missing_gist_id_raises_naming_the_variable(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_MEMORY_GIST_ID", value)
        with pytest.raises(ConfigurationError, match="AI_MEMORY_GIST_ID is required"):
            load_ai_summary_config()

    def test_unset_gist_id_raises_naming_the_variable(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AI_MEMORY_GIST_ID")
        with pytest.raises(ConfigurationError, match="AI_MEMORY_GIST_ID is required"):
            load_ai_summary_config()

    @pytest.mark.parametrize("value", ["", "   "])
    def test_missing_gist_token_raises_naming_the_variable(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("AI_MEMORY_GIST_TOKEN", value)
        with pytest.raises(ConfigurationError, match="AI_MEMORY_GIST_TOKEN is required"):
            load_ai_summary_config()

    def test_token_keeps_its_whitespace(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A token is never stripped: whitespace inside it may be significant."""
        monkeypatch.setenv("AI_MEMORY_GIST_TOKEN", "  ghp-spaced  ")
        memory = load_ai_summary_config().memory

        assert memory is not None
        assert memory.gist_token == "  ghp-spaced  "

    def test_malformed_memory_variables_are_ignored_with_the_feature_off(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Memory is inert without the narrative feature: no error, no store."""
        monkeypatch.setenv("AI_MEMORY_ENABLED", "maybe")
        monkeypatch.setenv("AI_MEMORY_GIST_ID", "")

        config = load_ai_summary_config()

        assert config.enabled is False
        assert config.memory is None

    def test_the_token_is_absent_from_a_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError) as caught:
            AIMemoryConfig(gist_id="", gist_token="ghp-marker-token")

        assert "AI_MEMORY_GIST_ID" in str(caught.value)
        assert "ghp-marker-token" not in str(caught.value)

    def test_token_is_absent_from_the_repr(self, memory_env: None) -> None:
        config = load_ai_summary_config()
        rendered = repr(config)

        assert "ghp-test" not in rendered
        assert "gist_token" not in rendered
        assert "abc123" in rendered  # the id is not a credential

    def test_timeout_is_the_summary_timeout_not_a_memory_setting(
        self, memory_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AI_SUMMARY_TIMEOUT", "7")
        memory = load_ai_summary_config().memory

        assert memory is not None
        assert memory.timeout == 7
