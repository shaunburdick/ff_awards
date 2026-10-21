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
