"""
Configuration management for Fantasy Football Challenge Tracker.

Handles environment variables, league IDs, and ESPN authentication.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

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
    week: int | None = None

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

        if self.week is not None:
            if self.week < 1 or self.week > 18:
                raise ConfigurationError(f"Week must be between 1 and 18, got: {self.week}")


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
    use_env: bool = False,
    week: int | None = None,
) -> FFTrackerConfig:
    """
    Create configuration object from various sources.

    Args:
        league_ids: List of league IDs, or None to load from environment
        year: Fantasy season year, or None for current year
        private: Whether to use private league authentication
        use_env: Whether to load league IDs from environment
        week: Optional week override (1-18) for historical/testing purposes

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

    # Determine year
    resolved_year = detect_fantasy_year() if year is None else year

    # Load ESPN credentials if needed
    espn_credentials = load_espn_credentials() if private else None

    return FFTrackerConfig(
        league_ids=resolved_league_ids,
        year=resolved_year,
        private=private,
        espn_credentials=espn_credentials,
        week=week,
    )


def detect_fantasy_year() -> int:
    """
    Detect the current fantasy football year.

    Fantasy seasons run from August to December, so:
    - If the current month is August (8) or later, return the current year.
    - If the current month is before August, return the previous year.
    """
    import datetime

    now = datetime.datetime.now()
    return now.year if now.month >= 8 else now.year - 1


DEFAULT_AI_BASE_URL = "https://opencode.ai/inference/openai/v1"
# glm-5.3-flash spends the whole default budget on reasoning for a three-league
# digest (8000/8000, content null); this model completes it in ~2000 reasoning
# tokens. The old default remains selectable through AI_SUMMARY_MODEL.
DEFAULT_AI_MODEL = "deepseek-v4.1-flash"
DEFAULT_AI_TIMEOUT = 120
DEFAULT_AI_MAX_TOKENS = 8000
DEFAULT_AI_MAX_PROMPT_CHARS = 8000

_AI_BOOL_VALUES = {"true", "1", "yes", "on", "false", "0", "no", "off"}
AI_REASONING_EFFORTS = ("low", "medium", "high")


@dataclass(frozen=True)
class AISummaryConfig:
    """
    Optional AI narrative settings, loaded beside ``FFTrackerConfig``.

    They are not part of ``FFTrackerConfig`` on purpose: ``create_config``
    serves three CLIs and the feature covers ``ff-tracker`` only, so a malformed
    ``AI_SUMMARY_*`` variable must not break the championship or season-recap
    scripts.
    """

    enabled: bool = False
    # Never in a repr or a traceback: this value must not reach a log line.
    api_key: str = field(default="", repr=False)
    base_url: str = DEFAULT_AI_BASE_URL
    model: str = DEFAULT_AI_MODEL
    timeout: int = DEFAULT_AI_TIMEOUT
    max_tokens: int = DEFAULT_AI_MAX_TOKENS
    # None means "send no reasoning_effort key at all", never null or "".
    reasoning_effort: str | None = None
    max_prompt_chars: int = DEFAULT_AI_MAX_PROMPT_CHARS
    user_prompt: str = ""

    def __post_init__(self) -> None:
        """Validate the settings; configuration errors are not degraded."""
        if self.enabled and not self.api_key.strip():
            raise ConfigurationError(
                "AI_SUMMARY_API_KEY is required when AI_SUMMARY_ENABLED is true. "
                "Set the key, or unset AI_SUMMARY_ENABLED to ship the report without a narrative."
            )

        if not self.base_url.strip():
            raise ConfigurationError("AI_SUMMARY_BASE_URL cannot be empty")

        parts = urlsplit(self.base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ConfigurationError(
                "AI_SUMMARY_BASE_URL must be an http(s) URL with a host, "
                f"got: '{self.base_url}'"
            )

        if not self.model.strip():
            raise ConfigurationError("AI_SUMMARY_MODEL cannot be empty")

        if self.timeout <= 0:
            raise ConfigurationError(
                f"AI_SUMMARY_TIMEOUT must be a positive integer, got: {self.timeout}"
            )

        if self.max_tokens <= 0:
            raise ConfigurationError(
                f"AI_SUMMARY_MAX_TOKENS must be a positive integer, got: {self.max_tokens}"
            )

        if self.reasoning_effort is not None:
            normalised = self.reasoning_effort.strip().lower()
            if normalised and normalised not in AI_REASONING_EFFORTS:
                raise ConfigurationError(
                    "AI_SUMMARY_REASONING_EFFORT must be one of "
                    f"{'|'.join(AI_REASONING_EFFORTS)}, got: '{self.reasoning_effort}'"
                )
            # Frozen, so normalise in place: one lowercase value, and empty
            # means "no key" rather than an empty string.
            object.__setattr__(self, "reasoning_effort", normalised or None)

        if self.max_prompt_chars <= 0:
            raise ConfigurationError(
                "AI_SUMMARY_MAX_PROMPT_CHARS must be a positive integer, "
                f"got: {self.max_prompt_chars}"
            )

        if len(self.user_prompt) > self.max_prompt_chars:
            raise ConfigurationError(
                f"AI_SUMMARY_USER_PROMPT is {len(self.user_prompt)} characters, "
                f"longer than AI_SUMMARY_MAX_PROMPT_CHARS={self.max_prompt_chars}"
            )


def _parse_ai_bool(value: str) -> bool:
    """Parse AI_SUMMARY_ENABLED, accepting only the documented eight values."""
    normalised = value.strip().lower()
    if normalised not in _AI_BOOL_VALUES:
        raise ConfigurationError(
            "AI_SUMMARY_ENABLED must be one of true/1/yes/on/false/0/no/off, "
            f"got: '{value}'"
        )
    return normalised in {"true", "1", "yes", "on"}


def _parse_positive_int(name: str, value: str, default: int) -> int:
    """Parse a positive-integer variable, naming itself on failure."""
    if not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as e:
        raise ConfigurationError(f"{name} must be a positive integer, got: '{value}'") from e
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be a positive integer, got: '{value}'")
    return parsed


def load_ai_summary_config() -> AISummaryConfig:
    """
    Load the AI narrative settings from the environment (or ``.env``).

    ``load_environment`` normally runs inside ``create_config``; it is called
    here too so a ``.env``-only setup works no matter which loader runs first.
    ``load_dotenv`` never overrides an already-set variable, so a workflow
    ``env:`` value wins over ``.env`` either way.

    Returns:
        Validated settings; ``enabled`` is false unless explicitly switched on.
        While the feature is off only ``AI_SUMMARY_ENABLED`` is read, so no
        other AI variable can deny a report by being malformed.

    Raises:
        ConfigurationError: If ``AI_SUMMARY_ENABLED`` is unreadable, or the
            feature is enabled and a setting is malformed: a missing key, a bad
            base URL, a non-positive budget or timeout, an unknown reasoning
            effort, or an oversized user prompt.
    """
    load_environment()

    enabled_raw = os.getenv("AI_SUMMARY_ENABLED", "")
    if not enabled_raw.strip():
        # Nothing else is read: with the feature off, no AI variable can deny a
        # report by being malformed. Only the flag itself is validated.
        return AISummaryConfig()
    if not _parse_ai_bool(enabled_raw):
        return AISummaryConfig()

    enabled = True

    timeout = _parse_positive_int(
        "AI_SUMMARY_TIMEOUT", os.getenv("AI_SUMMARY_TIMEOUT", ""), DEFAULT_AI_TIMEOUT
    )
    max_tokens = _parse_positive_int(
        "AI_SUMMARY_MAX_TOKENS", os.getenv("AI_SUMMARY_MAX_TOKENS", ""), DEFAULT_AI_MAX_TOKENS
    )
    max_prompt_chars = _parse_positive_int(
        "AI_SUMMARY_MAX_PROMPT_CHARS",
        os.getenv("AI_SUMMARY_MAX_PROMPT_CHARS", ""),
        DEFAULT_AI_MAX_PROMPT_CHARS,
    )

    base_url = os.getenv("AI_SUMMARY_BASE_URL", "").strip().rstrip("/") or DEFAULT_AI_BASE_URL
    model = os.getenv("AI_SUMMARY_MODEL", "").strip() or DEFAULT_AI_MODEL
    reasoning_effort = os.getenv("AI_SUMMARY_REASONING_EFFORT", "").strip().lower() or None
    user_prompt = os.getenv("AI_SUMMARY_USER_PROMPT", "").replace("\r\n", "\n").strip()

    return AISummaryConfig(
        enabled=enabled,
        api_key=os.getenv("AI_SUMMARY_API_KEY", ""),
        base_url=base_url,
        model=model,
        timeout=timeout,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        max_prompt_chars=max_prompt_chars,
        user_prompt=user_prompt,
    )
