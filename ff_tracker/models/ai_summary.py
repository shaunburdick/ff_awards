"""
AI-written narrative models for the weekly report.

The narrative is generated text: it is labelled AI-generated everywhere it is
rendered, carries no authority over the deterministic sections, and is
represented here as data only (Article II).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from ..exceptions import DataValidationError

# FR-014's two status vocabularies. They live beside the model that validates
# them because the memory module imports this one, not the other way round.
MEMORY_READ_OK = "ok"
MEMORY_READ_NONE = "none"
MEMORY_READ_FAILED = "failed"
MEMORY_WRITE_OK = "ok"
MEMORY_WRITE_FAILED = "failed"
MEMORY_WRITE_SKIPPED = "skipped"

MEMORY_READ_STATUSES = (MEMORY_READ_OK, MEMORY_READ_NONE, MEMORY_READ_FAILED)
MEMORY_WRITE_STATUSES = (MEMORY_WRITE_OK, MEMORY_WRITE_FAILED, MEMORY_WRITE_SKIPPED)


@dataclass(frozen=True)
class AISummaryLeague:
    """
    One league's subsection of the narrative.

    Headings always come from our league names, never from the provider, so
    ``league`` is always a name this project already holds.
    """

    league: str
    paragraphs: list[str]
    bullets: list[str]

    def __post_init__(self) -> None:
        """Validate the league section after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate the league section."""
        if not self.league.strip():
            raise DataValidationError("League name cannot be empty")

        if not self.paragraphs:
            raise DataValidationError("League section must contain at least one paragraph")

        for paragraph in self.paragraphs:
            if not paragraph.split():
                raise DataValidationError("Paragraph must contain at least one word")

        for bullet in self.bullets:
            if not bullet.strip():
                raise DataValidationError("Bullet cannot be empty")


@dataclass(frozen=True)
class AIProvenance:
    """Where a narrative came from, for the JSON archive."""

    model: str
    prompt_sha: str
    generated_at: str  # ISO 8601 UTC
    truncated: bool = False
    # 1, or 2 when one contract-failure retry was spent on sampling noise.
    attempts: int = 1
    # Distinct weeks every league's history block carried, unioned (FR-011).
    history_weeks: int = 0
    # FR-014's three memory fields: all set when memory is on, all absent when
    # it is off, and never on the notice path.
    memory_read: str | None = None
    memory_write: str | None = None
    memory_weeks: list[int] | None = None

    def __post_init__(self) -> None:
        """Validate provenance after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate provenance."""
        if not self.model.strip():
            raise DataValidationError("Provenance model cannot be empty")

        if not self.prompt_sha.strip():
            raise DataValidationError("Provenance prompt hash cannot be empty")

        if not self.generated_at.strip():
            raise DataValidationError("Provenance timestamp cannot be empty")

        if self.attempts not in (1, 2):
            raise DataValidationError(f"Provenance attempts must be 1 or 2: {self.attempts}")

        if self.history_weeks < 0:
            raise DataValidationError(
                f"Provenance history weeks cannot be negative: {self.history_weeks}"
            )

        self._validate_memory()

    def _validate_memory(self) -> None:
        """Validate the memory trio: all absent, or all set against FR-014's vocabularies."""
        read, write, weeks = self.memory_read, self.memory_write, self.memory_weeks
        if read is None and write is None and weeks is None:
            return

        if read is None or write is None or weeks is None:
            raise DataValidationError(
                "Provenance memory fields must be all set or all absent: "
                f"read={read!r}, write={write!r}, weeks={weeks!r}"
            )

        if read not in MEMORY_READ_STATUSES:
            raise DataValidationError(
                f"Provenance memory_read must be one of {'|'.join(MEMORY_READ_STATUSES)}: {read}"
            )

        if write not in MEMORY_WRITE_STATUSES:
            raise DataValidationError(
                f"Provenance memory_write must be one of {'|'.join(MEMORY_WRITE_STATUSES)}: {write}"
            )

        for week in weeks:
            if not 1 <= week <= 18:
                raise DataValidationError(f"Provenance memory week must be 1-18: {week}")


@dataclass(frozen=True)
class AISummary:
    """
    A complete AI-written narrative, validated against the response contract.

    Length caps are enforced before construction, so an ``AISummary`` that
    exists is already normalised.
    """

    headline: str
    leagues: list[AISummaryLeague]
    season_note: str
    provenance: AIProvenance

    def __post_init__(self) -> None:
        """Validate the narrative after construction."""
        self.validate()

    def validate(self) -> None:
        """Validate the narrative."""
        if not self.headline.strip():
            raise DataValidationError("Headline cannot be empty")

        if not self.leagues:
            raise DataValidationError("Narrative must contain at least one league")

        if not self.season_note.strip():
            raise DataValidationError("Season note cannot be empty")


@dataclass(frozen=True)
class AISummaryUnavailable:
    """
    The narrative could not be produced; the report ships without it.

    ``reason`` names what failed and never contains the API key, the response
    body or an endpoint path.
    """

    reason: str

    def __post_init__(self) -> None:
        """Validate the reason after construction."""
        if not self.reason.strip():
            raise DataValidationError("Unavailable reason cannot be empty")

    @property
    def notice(self) -> str:
        """Return the one-line notice every format renders in place of the section."""
        return f"AI summary unavailable: {self.reason}. The report is unaffected."


# Runtime alias, so typing.Union rather than ``X | Y`` (Python 3.9 target).
AISummaryResult = Union[AISummary, AISummaryUnavailable]
