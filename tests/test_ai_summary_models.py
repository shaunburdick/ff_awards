"""Tests for the AI narrative models and the AI error taxonomy."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ff_tracker.exceptions import (
    AIContractError,
    AIHTTPError,
    AISummaryError,
    AITimeoutError,
    AITransportError,
    AITruncationError,
    DataValidationError,
    FFTrackerError,
)
from ff_tracker.models import (
    AIProvenance,
    AISummary,
    AISummaryLeague,
    AISummaryUnavailable,
)


def _league() -> AISummaryLeague:
    return AISummaryLeague(
        league="MM Driveway Surfers",
        paragraphs=["Butt Fumble stayed unbeaten through six weeks."],
        bullets=["Donut Lose won by 1.08"],
    )


def _provenance() -> AIProvenance:
    return AIProvenance(
        model="deepseek-v4.1-flash",
        prompt_sha="9f2c1ab4e7d0",
        generated_at="2026-10-14T05:03:11Z",
    )


def _summary() -> AISummary:
    return AISummary(
        headline="Six weeks in and nobody has an answer",
        leagues=[_league()],
        season_note="Halfway there.",
        provenance=_provenance(),
    )


class TestAISummaryLeague:
    """Article II validation for one league's subsection."""

    def test_accepts_valid_section(self) -> None:
        assert _league().league == "MM Driveway Surfers"

    def test_rejects_empty_league_name(self) -> None:
        with pytest.raises(DataValidationError, match="League name cannot be empty"):
            AISummaryLeague(league="  ", paragraphs=["A paragraph."], bullets=[])

    def test_rejects_empty_paragraph_list(self) -> None:
        with pytest.raises(DataValidationError, match="at least one paragraph"):
            AISummaryLeague(league="League A", paragraphs=[], bullets=[])

    def test_rejects_whitespace_only_paragraph(self) -> None:
        with pytest.raises(DataValidationError, match="at least one word"):
            AISummaryLeague(league="League A", paragraphs=["   \n\t "], bullets=[])

    def test_rejects_empty_bullet(self) -> None:
        with pytest.raises(DataValidationError, match="Bullet cannot be empty"):
            AISummaryLeague(league="League A", paragraphs=["A paragraph."], bullets=["  "])

    def test_bullets_may_be_empty(self) -> None:
        assert (
            AISummaryLeague(league="League A", paragraphs=["A paragraph."], bullets=[]).bullets
            == []
        )


class TestAIProvenance:
    """Article II validation for provenance."""

    def test_truncated_defaults_to_false(self) -> None:
        assert _provenance().truncated is False

    def test_records_model_and_hash(self) -> None:
        provenance = _provenance()
        assert provenance.model == "deepseek-v4.1-flash"
        assert provenance.prompt_sha == "9f2c1ab4e7d0"

    def test_rejects_empty_model(self) -> None:
        with pytest.raises(DataValidationError, match="model cannot be empty"):
            AIProvenance(model=" ", prompt_sha="abc", generated_at="2026-10-14T05:03:11Z")

    def test_rejects_empty_prompt_hash(self) -> None:
        with pytest.raises(DataValidationError, match="prompt hash cannot be empty"):
            AIProvenance(model="m", prompt_sha=" ", generated_at="2026-10-14T05:03:11Z")

    def test_rejects_empty_timestamp(self) -> None:
        with pytest.raises(DataValidationError, match="timestamp cannot be empty"):
            AIProvenance(model="m", prompt_sha="abc", generated_at=" ")


class TestAttempts:
    """provenance.attempts records whether the one contract retry was spent."""

    def test_defaults_to_one(self) -> None:
        assert _provenance().attempts == 1

    def test_accepts_two(self) -> None:
        provenance = AIProvenance(
            model="deepseek-v4.1-flash",
            prompt_sha="abc",
            generated_at="2026-10-14T05:03:11Z",
            attempts=2,
        )
        assert provenance.attempts == 2

    @pytest.mark.parametrize("value", [0, 3, -1])
    def test_rejects_anything_else(self, value: int) -> None:
        with pytest.raises(DataValidationError, match="attempts must be 1 or 2"):
            AIProvenance(
                model="deepseek-v4.1-flash",
                prompt_sha="abc",
                generated_at="2026-10-14T05:03:11Z",
                attempts=value,
            )


class TestAISummary:
    """Article II validation for the narrative."""

    def test_accepts_valid_narrative(self) -> None:
        summary = _summary()
        assert summary.headline.startswith("Six weeks")
        assert len(summary.leagues) == 1

    def test_rejects_empty_headline(self) -> None:
        with pytest.raises(DataValidationError, match="Headline cannot be empty"):
            AISummary(
                headline=" ",
                leagues=[_league()],
                season_note="Note.",
                provenance=_provenance(),
            )

    def test_rejects_no_leagues(self) -> None:
        with pytest.raises(DataValidationError, match="at least one league"):
            AISummary(
                headline="Headline",
                leagues=[],
                season_note="Note.",
                provenance=_provenance(),
            )

    def test_rejects_empty_season_note(self) -> None:
        with pytest.raises(DataValidationError, match="Season note cannot be empty"):
            AISummary(
                headline="Headline",
                leagues=[_league()],
                season_note=" ",
                provenance=_provenance(),
            )

    def test_is_frozen(self) -> None:
        summary = _summary()
        with pytest.raises(FrozenInstanceError):
            # mypy calls a frozen field read-only; __setattr__ is the call the assignment makes.
            summary.__setattr__("headline", "changed")


class TestAISummaryUnavailable:
    """The degradation result and its notice."""

    def test_notice_wraps_the_reason(self) -> None:
        unavailable = AISummaryUnavailable(reason="timed out after 120s")
        assert (
            unavailable.notice
            == "AI summary unavailable: timed out after 120s. The report is unaffected."
        )

    def test_rejects_empty_reason(self) -> None:
        with pytest.raises(DataValidationError, match="reason cannot be empty"):
            AISummaryUnavailable(reason="  ")


class TestAIErrorReasons:
    """FR-006 reason strings, built where the failure is detected."""

    def test_http_error_names_status_model_and_host_only(self) -> None:
        error = AIHTTPError(status=410, host="opencode.ai", model="deepseek-v4.1-flash")
        assert error.reason == "HTTP 410 (model deepseek-v4.1-flash at opencode.ai)"
        assert "OpenAI" not in error.reason  # host only, never a path segment

    def test_transport_error_names_host(self) -> None:
        assert AITransportError(host="opencode.ai").reason == "connection failed (opencode.ai)"

    def test_timeout_error_names_seconds(self) -> None:
        assert AITimeoutError(seconds=120).reason == "timed out after 120s"

    def test_truncation_error_names_finish_reason(self) -> None:
        assert AITruncationError().reason == "finish_reason=length"

    def test_contract_error_takes_its_reason(self) -> None:
        error = AIContractError("response did not match the summary contract")
        assert error.reason == "response did not match the summary contract"

    def test_hierarchy_is_not_fftrackererror(self) -> None:
        """A cosmetic failure must never be mistaken for a fail-fast error."""
        assert issubclass(AISummaryError, Exception)
        assert not issubclass(AISummaryError, FFTrackerError)
