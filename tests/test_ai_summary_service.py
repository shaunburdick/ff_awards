"""Tests for the AI summary service: contract, matching, normalisation, fail-open."""

from __future__ import annotations

import http.client
import json
import logging
import re

import pytest
from ai_fakes import LEAGUE_A, LEAGUE_B, FakeAIClient, FakeTransport, make_regular_divisions

from ff_tracker.config import DEFAULT_AI_MAX_TOKENS, DEFAULT_AI_MODEL, AISummaryConfig
from ff_tracker.exceptions import (
    AIHTTPError,
    AISummaryError,
    AITruncationError,
)
from ff_tracker.models import AISummary, AISummaryUnavailable
from ff_tracker.services.ai_summary_service import (
    HEADLINE_WORD_CAP,
    INSTRUCTIONS_HEADING,
    LEAGUE_WORD_CAP,
    MAX_BULLETS,
    MAX_PARAGRAPHS,
    SEASON_NOTE_WORD_CAP,
    SYSTEM_PROMPT,
    AISummaryService,
    build_system_prompt,
    prompt_sha,
)

USER_PROMPT = "Be dry. Never mention the commissioner's team."


def _config(
    user_prompt: str = "",
    *,
    max_tokens: int = DEFAULT_AI_MAX_TOKENS,
    reasoning_effort: str | None = None,
) -> AISummaryConfig:
    return AISummaryConfig(
        enabled=True,
        api_key="sk-test",
        model=DEFAULT_AI_MODEL,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        user_prompt=user_prompt,
    )


def _league_section(
    name: str,
    paragraphs: list[str] | None = None,
    bullets: list[str] | None = None,
) -> dict[str, object]:
    return {
        "league": name,
        "paragraphs": paragraphs if paragraphs is not None else [f"{name} had a week."],
        "bullets": bullets if bullets is not None else [],
    }


def _response(
    leagues: list[dict[str, object]] | None = None,
    *,
    headline: str = "Six weeks in and nobody has an answer",
    season_note: str = "Halfway there, and the middle of the table is a car park.",
) -> str:
    payload = {
        "headline": headline,
        "leagues": leagues
        if leagues is not None
        else [_league_section(LEAGUE_A), _league_section(LEAGUE_B)],
        "season_note": season_note,
    }
    return json.dumps(payload)


def _service(
    response: str = "",
    *,
    user_prompt: str = "",
    error: AISummaryError | None = None,
    max_tokens: int = DEFAULT_AI_MAX_TOKENS,
    reasoning_effort: str | None = None,
):
    client = FakeAIClient(response=response, error=error)
    config = _config(user_prompt, max_tokens=max_tokens, reasoning_effort=reasoning_effort)
    return AISummaryService(config, client), client


def _generate(service: AISummaryService, divisions=None) -> object:
    return service.generate(
        divisions if divisions is not None else make_regular_divisions(),
        [],
        None,
        6,
        None,
    )


class TestHappyPath:
    """A valid response becomes a validated narrative."""

    def test_returns_an_ai_summary_with_provenance(self) -> None:
        service, _ = _service(_response())
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert result.headline == "Six weeks in and nobody has an answer"
        assert result.season_note.startswith("Halfway there")
        assert [league.league for league in result.leagues] == [LEAGUE_A, LEAGUE_B]
        assert result.provenance.model == "deepseek-v4.1-flash"
        assert result.provenance.truncated is False

    def test_prompt_sha_is_twelve_hex_characters(self) -> None:
        service, _ = _service(_response())
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert re.fullmatch(r"[0-9a-f]{12}", result.provenance.prompt_sha)

    def test_generated_at_is_iso_utc(self) -> None:
        service, _ = _service(_response())
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", result.provenance.generated_at)

    def test_one_request_per_generate(self) -> None:
        service, client = _service(_response())
        _generate(service)
        _generate(service)
        assert len(client.requests) == 2

    def test_digest_is_the_user_message(self) -> None:
        service, client = _service(_response())
        _generate(service)

        digest = json.loads(client.requests[0].user_message)
        assert digest["mode"] == "regular_season"
        assert digest["week"] == 6
        assert len(digest["leagues"]) == 2

    def test_max_tokens_defaults_to_eight_thousand(self) -> None:
        service, client = _service(_response())
        _generate(service)
        assert client.requests[0].max_tokens == DEFAULT_AI_MAX_TOKENS == 8000

    def test_budget_and_effort_come_from_configuration(self) -> None:
        """AC-010: a non-default budget and an upper-case effort reach the request."""
        service, client = _service(
            _response(), max_tokens=1234, reasoning_effort="LOW"
        )
        _generate(service)

        request = client.requests[0]
        assert request.max_tokens == 1234
        assert request.reasoning_effort == "low"

    def test_reasoning_effort_is_unset_by_default(self) -> None:
        service, client = _service(_response())
        _generate(service)
        assert client.requests[0].reasoning_effort is None


class TestSystemPrompt:
    """FR-010: the commissioner's instructions arrive in a delimited block."""

    def test_no_block_without_a_user_prompt(self) -> None:
        assert build_system_prompt("") == SYSTEM_PROMPT
        assert INSTRUCTIONS_HEADING not in build_system_prompt("   \n ")

    def test_block_is_appended_verbatim(self) -> None:
        composed = build_system_prompt(USER_PROMPT)
        assert composed.startswith(SYSTEM_PROMPT)
        assert f"{INSTRUCTIONS_HEADING}\n{USER_PROMPT}" in composed

    def test_request_carries_the_block(self) -> None:
        service, client = _service(_response(), user_prompt=USER_PROMPT)
        _generate(service)
        assert f"{INSTRUCTIONS_HEADING}\n{USER_PROMPT}" in client.requests[0].system_prompt

    def test_prompt_sha_is_stable_and_sensitive(self) -> None:
        assert prompt_sha(USER_PROMPT) == prompt_sha(USER_PROMPT)
        assert prompt_sha(USER_PROMPT) != prompt_sha("")
        assert prompt_sha("") != prompt_sha("Different tone.")

    def test_prompt_sha_reaches_provenance(self) -> None:
        service, _ = _service(_response(), user_prompt=USER_PROMPT)
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert result.provenance.prompt_sha == prompt_sha(USER_PROMPT)

    def test_system_prompt_names_the_contract_and_the_caps(self) -> None:
        assert "headline" in SYSTEM_PROMPT
        assert "leagues" in SYSTEM_PROMPT
        assert "season_note" in SYSTEM_PROMPT
        assert "JSON" in SYSTEM_PROMPT


class TestContractFailures:
    """Shape problems degrade to the notice with the contract reason."""

    @pytest.mark.parametrize(
        "response",
        [
            "not json",
            "```json\n{}\n```",
            '{"headline": "h", "leagues": [], "season_note": "n"}',
            '{"leagues": [{"league": "A", "paragraphs": ["p"]}], "season_note": "n"}',
            '{"headline": "h", "season_note": "n"}',
            '{"headline": "h", "leagues": [{"league": "A", "paragraphs": []}], "season_note": "n"}',
            '{"headline": "h", "leagues": [{"league": "A", "paragraphs": ["  "]}], "season_note": "n"}',
            '{"headline": "h", "leagues": [{"league": "", "paragraphs": ["p"]}], "season_note": "n"}',
            '{"headline": "h", "leagues": [{"league": "A", "paragraphs": ["p"], "bullets": [""]}], "season_note": "n"}',
            '{"headline": "h", "leagues": "nope", "season_note": "n"}',
            "[]",
        ],
    )
    def test_bad_shape_becomes_the_contract_notice(self, response: str) -> None:
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummaryUnavailable)
        assert result.reason == "response did not match the summary contract"


class TestFailureDegradation:
    """FR-006: provider failures become the notice, never an exception."""

    def test_http_error(self) -> None:
        service, _ = _service(error=AIHTTPError(status=410, host="opencode.ai", model="deepseek-v4.1-flash"))
        result = _generate(service)

        assert isinstance(result, AISummaryUnavailable)
        assert result.reason == "HTTP 410 (model deepseek-v4.1-flash at opencode.ai)"
        assert result.notice.endswith("The report is unaffected.")

    def test_truncation(self) -> None:
        service, _ = _service(error=AITruncationError())
        result = _generate(service)
        assert isinstance(result, AISummaryUnavailable)
        assert result.reason == "finish_reason=length"

    def test_count_mismatch_names_both_counts(self) -> None:
        service, _ = _service(_response(leagues=[_league_section(LEAGUE_A)]))
        result = _generate(service)  # two divisions, one section

        assert isinstance(result, AISummaryUnavailable)
        assert result.reason == "league count mismatch (2 leagues, 1 sections)"


class TestMidBodyFailure:
    """The transport mapping must reach the notice, not main's error branch."""

    def test_mid_body_failure_degrades_to_a_notice(self) -> None:
        from ff_tracker.services.ai_client import OpenAICompatibleClient

        config = _config()
        client = OpenAICompatibleClient(
            config, FakeTransport(error=ConnectionResetError("peer reset"))
        )
        result = _generate(AISummaryService(config, client))

        assert isinstance(result, AISummaryUnavailable)
        assert result.reason == "connection failed (opencode.ai)"
        assert result.notice.endswith("The report is unaffected.")

    def test_incomplete_read_degrades_to_a_notice(self) -> None:
        from ff_tracker.services.ai_client import OpenAICompatibleClient

        config = _config()
        client = OpenAICompatibleClient(
            config, FakeTransport(error=http.client.IncompleteRead(b"partial"))
        )
        result = _generate(AISummaryService(config, client))

        assert isinstance(result, AISummaryUnavailable)
        assert result.reason == "connection failed (opencode.ai)"


class TestProgrammerErrorsPropagate:
    """Gate 2 M3: the boundary must not hide a coding error."""

    def test_attribute_error_from_the_digest_builder_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _explode(*args: object, **kwargs: object) -> object:
            raise AttributeError("bug in the builder")

        monkeypatch.setattr(
            "ff_tracker.services.ai_summary_service.build_digest", _explode
        )
        service, _ = _service(_response())

        with pytest.raises(AttributeError, match="bug in the builder"):
            _generate(service)

    def test_type_error_from_the_parser_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _explode(*args: object, **kwargs: object) -> object:
            raise TypeError("bug in the parse")

        monkeypatch.setattr("ff_tracker.services.ai_summary_service.json.loads", _explode)
        service, _ = _service(_response())

        with pytest.raises(TypeError, match="bug in the parse"):
            _generate(service)


class TestLeagueMatching:
    """FR-004's total order, AC-008."""

    def test_name_match_with_reordered_entries(self) -> None:
        response = _response(
            leagues=[_league_section(LEAGUE_B), _league_section(LEAGUE_A)]
        )
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert [league.league for league in result.leagues] == [LEAGUE_A, LEAGUE_B]
        assert result.leagues[0].paragraphs == [f"{LEAGUE_A} had a week."]

    def test_name_match_ignores_case_and_surrounding_space(self) -> None:
        response = _response(
            leagues=[
                _league_section(f"  {LEAGUE_B.upper()}  ", paragraphs=["B lives here."]),
                _league_section(LEAGUE_A.lower(), paragraphs=["A lives here."]),
            ]
        )
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert [league.league for league in result.leagues] == [LEAGUE_A, LEAGUE_B]
        assert result.leagues[0].paragraphs == ["A lives here."]
        assert result.leagues[1].paragraphs == ["B lives here."]

    def test_stray_entry_renders_by_position_under_our_names(self) -> None:
        response = _response(
            leagues=[
                _league_section("Some Other League"),
                _league_section("Another League"),
            ]
        )
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummary)
        headings = [league.league for league in result.leagues]
        assert headings == [LEAGUE_A, LEAGUE_B]
        assert "Some Other League" not in headings
        assert "Another League" not in headings

    def test_duplicate_entry_renders_by_position(self) -> None:
        response = _response(
            leagues=[_league_section(LEAGUE_A), _league_section(LEAGUE_A)]
        )
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert [league.league for league in result.leagues] == [LEAGUE_A, LEAGUE_B]

    def test_no_response_supplied_name_ever_becomes_a_heading(self) -> None:
        response = _response(
            leagues=[_league_section("Mine"), _league_section("Yours")]
        )
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummary)
        headings = [league.league for league in result.leagues]
        assert headings == [LEAGUE_A, LEAGUE_B]


class TestNormalisation:
    """FR-004's structural caps, AC-013 to AC-015."""

    def _long_response(self) -> str:
        two_hundred_words = " ".join(["word"] * 200)
        headline = " ".join(["headline"] * 20)
        season_note = " ".join(["note"] * 60)
        return _response(
            leagues=[
                _league_section(
                    LEAGUE_A,
                    paragraphs=[
                        "First paragraph survives.",
                        "Second paragraph survives.",
                        "Third paragraph survives.",
                        "Fourth paragraph is dropped.",
                    ],
                    bullets=["One", "Two", "Three", "Four"],
                ),
                _league_section(LEAGUE_B, paragraphs=[two_hundred_words]),
            ],
            headline=headline,
            season_note=season_note,
        )

    def test_caps_are_enforced(self) -> None:
        service, _ = _service(self._long_response())
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert len(result.headline.split()) <= HEADLINE_WORD_CAP
        assert len(result.season_note.split()) <= SEASON_NOTE_WORD_CAP
        for league in result.leagues:
            assert len(league.paragraphs) <= MAX_PARAGRAPHS
            assert len(league.bullets) <= MAX_BULLETS
            assert sum(len(p.split()) for p in league.paragraphs) <= LEAGUE_WORD_CAP

    def test_first_paragraph_and_first_three_bullets_survive(self) -> None:
        service, _ = _service(self._long_response())
        result = _generate(service)

        assert isinstance(result, AISummary)
        first = result.leagues[0]
        assert first.paragraphs[0] == "First paragraph survives."
        assert first.bullets == ["One", "Two", "Three"]

    def test_trailing_paragraphs_are_dropped_to_fit_the_word_cap(self) -> None:
        """Three 60-word paragraphs fit in two; the third is dropped whole."""
        sixty = " ".join(["word"] * 60)
        response = _response(
            leagues=[
                _league_section(
                    LEAGUE_A, paragraphs=[sixty, sixty, sixty]
                ),
                _league_section(LEAGUE_B),
            ]
        )
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummary)
        paragraphs = result.leagues[0].paragraphs
        assert len(paragraphs) == 2
        assert sum(len(paragraph.split()) for paragraph in paragraphs) <= LEAGUE_WORD_CAP
        assert result.provenance.truncated is True

    def test_lone_overlong_first_paragraph_is_cut_at_a_word_boundary(self) -> None:
        long_paragraph = " ".join(["word"] * 200)
        response = _response(
            leagues=[
                _league_section(
                    LEAGUE_A,
                    paragraphs=[long_paragraph, "Dropped entirely."],
                ),
                _league_section(LEAGUE_B),
            ]
        )
        service, _ = _service(response)
        result = _generate(service)

        assert isinstance(result, AISummary)
        paragraphs = result.leagues[0].paragraphs
        assert len(paragraphs) == 1
        assert paragraphs[0].endswith("…")
        words = paragraphs[0].removesuffix("…").split()
        assert len(words) == LEAGUE_WORD_CAP
        assert all(word == "word" for word in words)

    def test_truncation_flag_is_set_when_anything_was_cut(self) -> None:
        service, _ = _service(self._long_response())
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert result.provenance.truncated is True

    def test_truncation_flag_is_false_when_nothing_was_cut(self) -> None:
        service, _ = _service(_response())
        result = _generate(service)

        assert isinstance(result, AISummary)
        assert result.provenance.truncated is False

    def test_normalisation_is_deterministic(self) -> None:
        first = _generate(_service(self._long_response())[0])
        second = _generate(_service(self._long_response())[0])

        assert isinstance(first, AISummary)
        assert isinstance(second, AISummary)

        def shape(summary: AISummary) -> object:
            return (
                summary.headline,
                [(league.league, league.paragraphs, league.bullets) for league in summary.leagues],
                summary.season_note,
                summary.provenance.truncated,
            )

        assert shape(first) == shape(second)


class TestLogging:
    """AC-006: the prompt may be logged at DEBUG; nothing else may be logged."""

    MARKER = "DIGEST-MARKER-9c1f"

    def test_debug_shows_the_prompt_and_nothing_sensitive(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.DEBUG)
        service, _ = _service(_response(), user_prompt=USER_PROMPT)

        result = _generate(service)
        assert isinstance(result, AISummary)

        prompt_records = [r.getMessage() for r in caplog.records if SYSTEM_PROMPT in r.getMessage()]
        assert prompt_records, "the system prompt must be visible at DEBUG"
        assert INSTRUCTIONS_HEADING in prompt_records[0]

        joined = "\n".join(r.getMessage() for r in caplog.records)
        assert "sk-test" not in joined
        assert "Butt Fumble" not in joined
        assert "MM Driveway Surfers" not in joined

    def test_warning_carries_only_the_reason(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.WARNING)
        service, _ = _service(error=AIHTTPError(status=410, host="opencode.ai", model="m"))

        _generate(service)

        assert any("AI summary unavailable: HTTP 410" in r.getMessage() for r in caplog.records)
