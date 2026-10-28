"""Tests for the memory archive, the gist store and the session (FR-013, FR-014)."""

from __future__ import annotations

import email.message
import io
import json
import logging
import socket
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from ai_fakes import FakeMemoryStore, FakeTransport, make_memory_archive, make_narrative

from ff_tracker.config import AIMemoryConfig
from ff_tracker.exceptions import AIMemoryStoreError, FFTrackerError
from ff_tracker.services.ai_client import USER_AGENT
from ff_tracker.services.ai_memory import (
    GistMemoryStore,
    MemoryEntry,
    MemoryFile,
    MemoryLeague,
    MemorySession,
    merge_entry,
    parse_archive,
    serialize_archive,
)

WEEK_5_ENTRY = MemoryEntry(
    week=5,
    generated_at="2026-10-07T05:00:00Z",
    headline="Week five headline",
    season_note="Week five note.",
    leagues=[
        MemoryLeague(
            league="MM Driveway Surfers",
            paragraphs=["Butt Fumble kept rolling."],
            bullets=["Donut Lose lost again"],
        )
    ],
)

# Authored here, not captured from the serialiser: the document this tool
# writes is part of the format a hand editor reads.
EXPECTED_ARCHIVE = """{
  "schema": 1,
  "season": 2026,
  "entries": [
    {
      "week": 5,
      "generated_at": "2026-10-07T05:00:00Z",
      "headline": "Week five headline",
      "season_note": "Week five note.",
      "leagues": [
        {
          "league": "MM Driveway Surfers",
          "paragraphs": [
            "Butt Fumble kept rolling."
          ],
          "bullets": [
            "Donut Lose lost again"
          ]
        }
      ]
    }
  ]
}"""


def _entry(week: int, *, generated_at: str | None = None) -> MemoryEntry:
    """A minimal valid entry for one week."""
    return MemoryEntry(
        week=week,
        generated_at=generated_at or f"2026-10-{week:02d}T05:00:00Z",
        headline=f"Week {week} headline",
        season_note=f"Week {week} note.",
        leagues=[MemoryLeague(league="League A", paragraphs=["Prose."], bullets=[])],
    )


def _archive(entries: list[MemoryEntry], *, season: int = 2026) -> MemoryFile:
    return MemoryFile(schema=1, season=season, entries=entries)


def _raw(document: object) -> bytes:
    return json.dumps(document).encode("utf-8")


class TestArchiveRoundTrip:
    """`parse` and `serialize` agree on one authored document."""

    def test_round_trip_is_the_authored_document(self) -> None:
        merged = merge_entry(None, WEEK_5_ENTRY, 2026)

        assert serialize_archive(merged).decode("utf-8") == EXPECTED_ARCHIVE
        reparsed = parse_archive(serialize_archive(merged))
        assert reparsed == merged == _archive([WEEK_5_ENTRY])

    def test_parsed_entries_keep_their_values(self) -> None:
        parsed = parse_archive(EXPECTED_ARCHIVE.encode("utf-8"))

        assert parsed is not None
        assert parsed["season"] == 2026
        assert parsed["entries"] == [WEEK_5_ENTRY]


class TestParseRejectsNonShapes:
    """AC-033: only bytes that do not parse as the archive shape give None."""

    def test_not_json(self) -> None:
        assert parse_archive(b"not json at all") is None

    def test_not_utf8(self) -> None:
        assert parse_archive(b"\xff\xfe{\x00") is None

    def test_not_an_object(self) -> None:
        assert parse_archive(b"[1, 2, 3]") is None

    def test_unsupported_schema(self) -> None:
        assert parse_archive(_raw({"schema": 2, "season": 2026, "entries": []})) is None

    def test_schema_is_not_an_integer(self) -> None:
        assert parse_archive(_raw({"schema": "1", "season": 2026, "entries": []})) is None

    def test_season_is_not_four_digits(self) -> None:
        for season in ("2026", 26, 20266, 999, True):
            assert parse_archive(_raw({"schema": 1, "season": season, "entries": []})) is None

    def test_entries_is_not_a_list(self) -> None:
        assert parse_archive(_raw({"schema": 1, "season": 2026, "entries": {}})) is None

    def test_missing_required_key(self) -> None:
        document = {
            "schema": 1,
            "season": 2026,
            "entries": [
                {"week": 5, "generated_at": "x", "season_note": "y", "leagues": []},
            ],
        }
        assert parse_archive(_raw(document)) is None

    def test_entry_with_a_wrong_value_type(self) -> None:
        document = {
            "schema": 1,
            "season": 2026,
            "entries": [
                {
                    "week": 5,
                    "generated_at": "x",
                    "headline": 7,
                    "season_note": "y",
                    "leagues": [],
                },
            ],
        }
        assert parse_archive(_raw(document)) is None

    def test_week_outside_one_to_eighteen(self) -> None:
        for week in (0, 19, -1, "5", 5.0, True):
            assert (
                parse_archive(_raw({"schema": 1, "season": 2026, "entries": [{"week": week}]}))
                is None
            )

    def test_league_subsection_without_bullets(self) -> None:
        document = {
            "schema": 1,
            "season": 2026,
            "entries": [
                {
                    "week": 5,
                    "generated_at": "x",
                    "headline": "h",
                    "season_note": "n",
                    "leagues": [{"league": "League A", "paragraphs": ["p"]}],
                },
            ],
        }
        assert parse_archive(_raw(document)) is None


class TestParseAccepts:
    """AC-033: content, counts and text length never make a file read-only."""

    def test_twenty_entries_are_accepted(self) -> None:
        entries = [_entry(week) for week in range(1, 11)] * 2
        parsed = parse_archive(serialize_archive(_archive(entries)))

        assert parsed is not None
        assert len(parsed["entries"]) == 20

    def test_extra_top_level_and_entry_fields_are_accepted(self) -> None:
        document = {
            "schema": 1,
            "season": 2026,
            "note": "hand written",
            "entries": [
                {
                    "week": 5,
                    "generated_at": "2026-10-07T05:00:00Z",
                    "headline": "h",
                    "season_note": "n",
                    "leagues": [],
                    "source": "hand edit",
                }
            ],
        }
        parsed = parse_archive(_raw(document))

        assert parsed is not None
        assert dict(parsed["entries"][0])["source"] == "hand edit"

    def test_an_over_long_paragraph_is_accepted(self) -> None:
        long_paragraph = "word " * 500
        document = {
            "schema": 1,
            "season": 2026,
            "entries": [
                {
                    "week": 5,
                    "generated_at": "x",
                    "headline": "h",
                    "season_note": "n",
                    "leagues": [
                        {"league": "League A", "paragraphs": [long_paragraph], "bullets": []}
                    ],
                }
            ],
        }
        parsed = parse_archive(_raw(document))

        assert parsed is not None
        assert parsed["entries"][0]["leagues"][0]["paragraphs"] == [long_paragraph]


class TestMergeEntry:
    """FR-014: append, replace the same week in place, and touch nothing else."""

    def test_none_creates_the_file(self) -> None:
        merged = merge_entry(None, _entry(6), 2026)

        assert merged == _archive([_entry(6)])

    def test_new_week_is_appended_and_ordered(self) -> None:
        archive = _archive([_entry(2), _entry(3)])

        merged = merge_entry(archive, _entry(4), 2026)

        assert [row["week"] for row in merged["entries"]] == [2, 3, 4]

    def test_same_week_is_replaced_in_place(self) -> None:
        first = _entry(3, generated_at="2026-10-03T05:00:00Z")
        second = _entry(3, generated_at="2026-10-03T09:00:00Z")
        archive = _archive([_entry(1), first, _entry(4)])

        merged = merge_entry(archive, second, 2026)

        assert [row["week"] for row in merged["entries"]] == [1, 3, 4]
        assert merged["entries"][1]["generated_at"] == "2026-10-03T09:00:00Z"

    def test_every_other_entry_keeps_its_value(self) -> None:
        archive = _archive([_entry(1), _entry(2), _entry(3), _entry(4)])
        before = {row["week"]: dict(row) for row in archive["entries"]}

        merged = merge_entry(archive, _entry(2, generated_at="2026-10-02T09:00:00Z"), 2026)

        for row in merged["entries"]:
            expected = before[row["week"]]
            if row["week"] == 2:
                assert row["generated_at"] != expected["generated_at"]
            else:
                assert row == expected

    def test_the_read_list_is_not_mutated(self) -> None:
        """The archive read from the store is left exactly as it was."""
        archive = _archive([_entry(1), _entry(2)])
        snapshot = json.loads(json.dumps(archive))

        merge_entry(archive, _entry(3), 2026)

        assert archive == snapshot

    def test_a_merge_into_a_twenty_entry_file_keeps_all_twenty(self) -> None:
        entries = [_entry(week) for week in range(1, 11)] * 2
        archive = _archive(entries)

        merged = merge_entry(archive, _entry(11), 2026)

        assert len(merged["entries"]) == 21
        assert [row["week"] for row in merged["entries"]] == sorted(
            row["week"] for row in [*entries, _entry(11)]
        )

    def test_the_season_header_is_never_rewritten(self) -> None:
        """A 2026 run against a 2025 file keeps season 2025; retiring it is an operator's act."""
        archive = _archive([_entry(1)], season=2025)

        merged = merge_entry(archive, _entry(2), 2026)

        assert merged["season"] == 2025

    def test_an_unknown_key_survives_merge_and_save(self) -> None:
        document = {
            "schema": 1,
            "season": 2026,
            "entries": [
                {
                    "week": 5,
                    "generated_at": "2026-10-07T05:00:00Z",
                    "headline": "h",
                    "season_note": "n",
                    "leagues": [],
                    "source": "hand edit",
                    "mood": "wry",
                }
            ],
        }
        parsed = parse_archive(_raw(document))
        assert parsed is not None
        original = dict(parsed["entries"][0])

        saved = serialize_archive(merge_entry(parsed, _entry(6), 2026))
        reloaded = parse_archive(saved)

        assert reloaded is not None
        surviving = next(row for row in reloaded["entries"] if row["week"] == 5)
        assert surviving == original
        assert dict(surviving)["source"] == "hand edit"


def _memory_config(
    gist_id: str = "gist123",
    gist_token: str = "ghp-secret-token",
    timeout: int = 30,
    write: bool = True,
) -> AIMemoryConfig:
    """The settings a memory-on run carries."""
    return AIMemoryConfig(gist_id=gist_id, gist_token=gist_token, timeout=timeout, write=write)


def _gist_document(files: object) -> bytes:
    """A gist GET response body."""
    return json.dumps({"id": "gist123", "files": files}).encode("utf-8")


class TestStoreErrorTaxonomy:
    """An escaped store error must not read as a configuration failure."""

    def test_it_is_not_a_fftrackererror(self) -> None:
        assert not issubclass(AIMemoryStoreError, FFTrackerError)


class TestGistStoreRequest:
    """The request the store builds: URL, method, headers, body."""

    def _store(self, body: bytes | None = None) -> tuple[GistMemoryStore, FakeTransport]:
        transport = FakeTransport(body=body if body is not None else _gist_document({}))
        return GistMemoryStore(_memory_config(), transport=transport), transport

    def test_load_is_a_get_of_the_gist_with_its_headers(self) -> None:
        store, transport = self._store()

        store.load()

        request, timeout = transport.calls[0]
        assert request.full_url == "https://api.github.com/gists/gist123"
        assert request.get_method() == "GET"
        assert request.headers["Authorization"] == "Bearer ghp-secret-token"
        assert request.headers["Accept"] == "application/vnd.github+json"
        assert request.headers["User-agent"] == USER_AGENT
        assert request.headers["User-agent"] != "Python-urllib/3"
        assert timeout == 30

    def test_save_is_a_patch_carrying_only_the_files_object(self) -> None:
        store, transport = self._store()
        archive = serialize_archive(_archive([_entry(5)]))

        store.save(archive)

        request, _ = transport.calls[0]
        assert request.full_url == "https://api.github.com/gists/gist123"
        assert request.get_method() == "PATCH"
        assert request.headers["Content-type"] == "application/json"
        body = request.data
        assert isinstance(body, bytes)
        assert json.loads(body) == {"files": {"memory.json": {"content": archive.decode("utf-8")}}}
        assert set(json.loads(body)) == {"files"}


class TestGistStoreRead:
    """Reading the one file, and the shapes that mean "nothing published yet"."""

    def test_the_file_content_comes_back_as_bytes(self) -> None:
        archive = serialize_archive(_archive([_entry(5)]))
        store = GistMemoryStore(
            _memory_config(),
            transport=FakeTransport(
                body=_gist_document({"memory.json": {"content": archive.decode()}})
            ),
        )

        assert store.load() == archive

    def test_a_gist_without_the_file_is_none(self) -> None:
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(body=_gist_document({})))

        assert store.load() is None

    def test_an_empty_files_object_is_none(self) -> None:
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(body=_gist_document({})))

        assert store.load() is None

    def test_a_response_that_is_not_an_object_is_a_server_failure(self) -> None:
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(body=b"[]"))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == "server"

    def test_a_response_that_is_not_json_is_a_server_failure(self) -> None:
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(body=b"<html>"))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == "server"


class _ResettingBody(io.BytesIO):
    """An error body that dies while it is being consumed, as a reset proxy is."""

    def read(self, size: int | None = -1) -> bytes:
        raise ConnectionResetError("peer reset while reading the error body")


def _resetting_http_error(status: int) -> urllib.error.HTTPError:
    """An HTTPError whose ``read()`` raises: the error path's own mid-body failure."""
    return urllib.error.HTTPError(
        "https://api.github.com/gists/gist123",
        status,
        "boom",
        email.message.Message(),
        _ResettingBody(),
    )


class TestGistStoreErrors:
    """Every transport outcome maps onto one kind, naming host and status only."""

    @pytest.mark.parametrize(
        ("status", "kind"),
        [(401, "auth"), (403, "auth"), (404, "not_found"), (500, "server"), (422, "server")],
    )
    def test_http_status_to_kind(self, status: int, kind: str) -> None:
        error = urllib.error.HTTPError(
            "https://api.github.com/gists/gist123",
            status,
            "boom",
            email.message.Message(),
            io.BytesIO(b"error body"),
        )
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(error=error))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == kind
        assert str(status) in caught.value.reason
        assert "api.github.com" in caught.value.reason

    @pytest.mark.parametrize(
        ("status", "kind"),
        [(401, "auth"), (404, "not_found"), (500, "server")],
    )
    def test_an_error_body_that_resets_is_still_mapped(self, status: int, kind: str) -> None:
        """A reset while discarding the error body must not escape as an OSError."""
        store = GistMemoryStore(
            _memory_config(), transport=FakeTransport(error=_resetting_http_error(status))
        )

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == kind
        assert str(status) in caught.value.reason

    def test_transport_failure(self) -> None:
        error = urllib.error.URLError(ConnectionResetError("peer reset"))
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(error=error))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.save(b"{}")

        assert caught.value.kind == "transport"
        assert "api.github.com" in caught.value.reason

    def test_url_error_with_a_timeout_reason(self) -> None:
        error = urllib.error.URLError(socket.timeout("timed out"))
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(error=error))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == "timeout"
        assert "30s" in caught.value.reason

    def test_a_plain_timeout(self) -> None:
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(error=TimeoutError()))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == "timeout"

    def test_a_mid_body_reset_is_a_transport_failure(self) -> None:
        store = GistMemoryStore(
            _memory_config(), transport=FakeTransport(error=ConnectionResetError("reset"))
        )

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == "transport"

    @pytest.mark.parametrize(
        "error",
        [
            ValueError("Invalid header value b'Bearer ghp-secret-token\n'"),
            UnicodeEncodeError("ascii", "gist-é", 0, 1, "ordinal not in range(128)"),
        ],
        ids=["malformed-header", "non-ascii-input"],
    )
    def test_a_urlopen_input_failure_maps_to_a_transport_error(self, error: Exception) -> None:
        """A pasted token with a trailing newline must not deny the report."""
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(error=error))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == "transport"
        assert "api.github.com" in caught.value.reason
        assert "ghp-secret-token" not in caught.value.reason

    def test_a_truncated_file_is_a_server_failure_not_an_absent_one(self) -> None:
        """GitHub drops the content above 1 MB; reading that as "no file" would overwrite it."""
        body = _gist_document({"memory.json": {"truncated": True}})
        store = GistMemoryStore(_memory_config(), transport=FakeTransport(body=body))

        with pytest.raises(AIMemoryStoreError) as caught:
            store.load()

        assert caught.value.kind == "server"
        assert "truncated" in caught.value.reason
        assert "gist123" not in caught.value.reason

    def test_the_token_and_the_gist_id_are_in_no_reason(self) -> None:
        cases: list[BaseException] = [
            urllib.error.HTTPError(
                "https://api.github.com/gists/gist123",
                401,
                "no",
                email.message.Message(),
                io.BytesIO(b"unauthorized"),
            ),
            urllib.error.HTTPError(
                "https://api.github.com/gists/gist123",
                404,
                "no",
                email.message.Message(),
                io.BytesIO(b"missing"),
            ),
            urllib.error.URLError(ConnectionResetError("peer")),
            TimeoutError(),
        ]

        for error in cases:
            store = GistMemoryStore(_memory_config(), transport=FakeTransport(error=error))
            with pytest.raises(AIMemoryStoreError) as caught:
                store.load()
            assert "ghp-secret-token" not in caught.value.reason
            assert "gist123" not in caught.value.reason


class TestGistStoreProductionPath:
    """The wrapper no fake covers: one ``urlopen``, one read, ``timeout=`` as a keyword."""

    def test_urlopen_is_called_with_the_timeout_keyword_and_read_once(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = b'{"files": {}}'
        store = GistMemoryStore(_memory_config())

        with patch("urllib.request.urlopen", return_value=response) as urlopen:
            assert store.load() is None

        args, kwargs = urlopen.call_args
        assert kwargs == {"timeout": 30}
        assert isinstance(args[0], urllib.request.Request)
        response.read.assert_called_once_with()


class TestGistStoreLogging:
    """AC-005/FR-009: the token, the gist id and the archive never reach a log line."""

    def test_no_secret_and_no_archive_text_at_any_level(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        archive = serialize_archive(_archive([_entry(5)]))
        store = GistMemoryStore(
            _memory_config(),
            transport=FakeTransport(
                body=_gist_document({"memory.json": {"content": archive.decode()}})
            ),
        )

        with caplog.at_level(logging.DEBUG):
            store.load()
            store.save(archive)

        messages = [record.getMessage() for record in caplog.records]
        assert messages, "the store should say something at INFO"
        for message in messages:
            assert "ghp-secret-token" not in message
            assert "gist123" not in message
            assert "Week 5 headline" not in message


def _session(
    store: FakeMemoryStore,
    *,
    season: int = 2026,
    week: int | None = 6,
) -> MemorySession:
    """A session over a fake store, in the season and week of a normal run."""
    return MemorySession(_memory_config(), season, week, store)


def _error(kind: str) -> AIMemoryStoreError:
    """A store error of one kind, as the store would build it."""
    return AIMemoryStoreError(kind, f"gist failure ({kind} at api.github.com)")


class TestReadPolicy:
    """FR-014's read outcomes: one status, and at most one warning, per cause."""

    def test_an_absent_file_is_none_with_no_warning(self) -> None:
        store = FakeMemoryStore()
        session = _session(store)

        session.open()

        assert session.read_status == "none"
        assert session.entries == []
        assert session.weeks == []
        assert session.warnings == []
        assert session.parsed is False
        assert store.read_calls == 1

    def test_an_empty_gist_is_none(self) -> None:
        session = _session(FakeMemoryStore(data=make_memory_archive(weeks=())))

        session.open()

        assert session.read_status == "none"
        assert session.entries == []

    def test_a_file_with_entries_is_ok_and_ordered_by_week(self) -> None:
        unordered = make_memory_archive(weeks=(5, 2, 4, 1, 3, 6))
        session = _session(FakeMemoryStore(data=unordered))

        session.open()

        assert session.read_status == "ok"
        assert session.weeks == [1, 2, 3, 4, 5, 6]
        assert session.parsed is True

    def test_a_404_read_is_none_and_silent(self) -> None:
        session = _session(FakeMemoryStore(read_errors=[_error("not_found")]))

        session.open()

        assert session.read_status == "none"
        assert session.warnings == []

    @pytest.mark.parametrize("kind", ["auth"])
    def test_an_authentication_read_failure_warns_once(self, kind: str) -> None:
        session = _session(FakeMemoryStore(read_errors=[_error(kind)]))

        session.open()

        assert session.read_status == "failed"
        assert len(session.warnings) == 1
        assert "authentication" in session.warnings[0]
        assert "AI_MEMORY_GIST_TOKEN" in session.warnings[0]

    @pytest.mark.parametrize("kind", ["server", "transport", "timeout"])
    def test_a_silent_read_failure(self, kind: str) -> None:
        session = _session(FakeMemoryStore(read_errors=[_error(kind)]))

        session.open()

        assert session.read_status == "failed"
        assert session.warnings == []

    def test_a_read_error_body_that_resets_is_mapped_not_raised(self) -> None:
        """The one outcome FR-014 forbids: a memory failure stopping the run."""
        store = GistMemoryStore(
            _memory_config(), transport=FakeTransport(error=_resetting_http_error(500))
        )
        session = MemorySession(_memory_config(), 2026, 6, store)

        session.open()

        assert session.read_status == "failed"
        assert session.warnings == []

        session.commit(make_narrative())

        # A failed read leaves nothing to merge into, so the write is skipped
        # rather than replacing the archive; the session still never raises.
        assert session.write_status == "skipped"
        assert session.warnings == []

    def test_a_read_error_body_that_resets_keeps_the_authentication_warning(self) -> None:
        store = GistMemoryStore(
            _memory_config(), transport=FakeTransport(error=_resetting_http_error(401))
        )
        session = MemorySession(_memory_config(), 2026, 6, store)

        session.open()

        assert session.read_status == "failed"
        assert len(session.warnings) == 1
        assert "authentication" in session.warnings[0]

    def test_a_malformed_credential_writes_nothing(self) -> None:
        """A ValueError out of urlopen is a failed read, so no write is attempted."""
        transport = FakeTransport(error=ValueError("Invalid header value"))
        session = MemorySession(
            _memory_config(), 2026, 6, GistMemoryStore(_memory_config(), transport=transport)
        )

        session.open()
        session.commit(make_narrative())

        assert session.read_status == "failed"
        assert session.write_status == "skipped"
        assert session.warnings == []
        assert len(transport.calls) == 1  # the read, and no write after it

    def test_a_truncated_read_suppresses_the_write(self) -> None:
        class TruncatedStore:
            """A store whose read says the file was too big to return."""

            def __init__(self) -> None:
                self.writes = 0

            def load(self) -> bytes | None:
                raise AIMemoryStoreError("server", "gist returned a truncated memory.json")

            def save(self, data: bytes) -> None:
                self.writes += 1

        store = TruncatedStore()
        session = MemorySession(_memory_config(), 2026, 6, store)

        session.open()
        session.commit(make_narrative())

        assert session.read_status == "failed"
        assert session.write_status == "skipped"
        assert store.writes == 0

    def test_an_unparseable_file_is_no_memory_and_is_never_overwritten(self) -> None:
        store = FakeMemoryStore(data=b"{not json")
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert session.read_status == "none"
        assert session.parsed is False
        assert len(session.warnings) == 1
        assert "does not parse" in session.warnings[0]
        assert session.write_status == "skipped"
        assert store.write_calls == 0
        assert store.data == b"{not json"

    def test_a_wrong_schema_is_no_memory_and_is_never_overwritten(self) -> None:
        original = b'{"schema": 2, "season": 2026, "entries": []}'
        store = FakeMemoryStore(data=original)
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert session.read_status == "none"
        assert session.write_status == "skipped"
        assert store.write_calls == 0
        assert store.data == original


class TestWritePolicy:
    """FR-014's write outcomes: ok, failed with one warning, or skipped."""

    def test_a_write_after_a_read_is_ok(self) -> None:
        store = FakeMemoryStore(data=make_memory_archive(weeks=(1, 2)))
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert session.write_status == "ok"
        assert store.write_calls == 1
        saved = parse_archive(store.data or b"")
        assert saved is not None
        assert [row["week"] for row in saved["entries"]] == [1, 2, 6]

    def test_the_written_entry_is_the_published_summary_with_the_reports_instant(self) -> None:
        store = FakeMemoryStore()
        session = _session(store)
        summary = make_narrative()

        session.open()
        session.commit(summary)

        saved = parse_archive(store.data or b"")
        assert saved is not None
        entry = saved["entries"][0]
        assert entry["week"] == 6
        assert entry["generated_at"] == summary.provenance.generated_at
        assert entry["headline"] == summary.headline
        assert entry["season_note"] == summary.season_note
        assert entry["leagues"] == [
            {
                "league": league.league,
                "paragraphs": list(league.paragraphs),
                "bullets": list(league.bullets),
            }
            for league in summary.leagues
        ]

    @pytest.mark.parametrize("kind", ["not_found", "auth", "server", "transport", "timeout"])
    def test_every_write_failure_warns_exactly_once(self, kind: str) -> None:
        store = FakeMemoryStore(write_errors=[_error(kind)])
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert session.write_status == "failed"
        assert len(session.warnings) == 1
        assert "AI memory write failed" in session.warnings[0]

    def test_a_write_authentication_failure_names_the_credential(self) -> None:
        store = FakeMemoryStore(write_errors=[_error("auth")])
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert "authentication" in session.warnings[0]
        assert "AI_MEMORY_GIST_TOKEN" in session.warnings[0]

    def test_an_authentication_read_failure_suppresses_the_write(self) -> None:
        """One cause, one line: a failed read never attempts a write."""
        original = make_memory_archive(weeks=(1, 2, 3))
        store = FakeMemoryStore(
            data=original,
            read_errors=[_error("auth")],
            write_errors=[_error("auth")],
        )
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert session.read_status == "failed"
        assert session.write_status == "skipped"
        assert len(session.warnings) == 1
        assert store.write_calls == 0
        assert store.data == original

    def test_a_read_404_then_a_write_404_warns_once(self) -> None:
        """AC-032's paired fixture: the read is "none" and only the write warns."""
        store = FakeMemoryStore(
            read_errors=[_error("not_found")],
            write_errors=[_error("not_found")],
        )
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert session.read_status == "none"
        assert session.write_status == "failed"
        assert len(session.warnings) == 1

    def test_a_failed_read_writes_nothing_and_keeps_the_archive(self) -> None:
        """A transient 500 costs one week of memory, not the season."""
        original = make_memory_archive(weeks=(1, 2, 3, 4, 5, 6))
        store = FakeMemoryStore(data=original, read_errors=[_error("server")])
        session = _session(store)

        session.open()
        session.commit(make_narrative())

        assert session.read_status == "failed"
        assert session.write_status == "skipped"
        assert session.warnings == []
        assert store.write_calls == 0
        assert store.data == original


class TestWriteGuard:
    """AC-033: a run whose season or week cannot be keyed writes nothing at all."""

    @pytest.mark.parametrize("week", [0, -1, 19, None])
    def test_an_unkeyable_week_writes_nothing(self, week: int | None) -> None:
        store = FakeMemoryStore()
        session = _session(store, week=week)

        session.open()
        session.commit(make_narrative())

        assert session.write_status == "skipped"
        assert store.write_calls == 0

    @pytest.mark.parametrize("season", [1999, 10000, 0])
    def test_an_unkeyable_season_writes_nothing(self, season: int) -> None:
        store = FakeMemoryStore()
        session = _session(store, season=season)

        session.open()
        session.commit(make_narrative())

        assert session.write_status == "skipped"
        assert store.write_calls == 0

    def test_read_only_mode_reads_the_archive_and_writes_nothing(self) -> None:
        """AC-034: the choice, not a failure — no write, no warning."""
        original = make_memory_archive(weeks=(1, 2, 3))
        store = FakeMemoryStore(data=original)
        session = MemorySession(_memory_config(write=False), 2026, 6, store)

        session.open()
        session.commit(make_narrative())

        assert store.read_calls == 1
        assert session.read_status == "ok"
        assert session.weeks == [1, 2, 3]
        assert store.write_calls == 0
        assert store.data == original
        assert session.write_status == "skipped"
        assert session.warnings == []

    def test_a_narrative_that_never_arrived_leaves_the_write_skipped(self) -> None:
        """The service simply does not call commit; the status is "skipped" already."""
        store = FakeMemoryStore()

        session = _session(store)
        session.open()

        assert session.write_status == "skipped"
        assert store.write_calls == 0


class TestSessionPropagation:
    """It catches `AIMemoryStoreError` and nothing else."""

    def test_an_attribute_error_from_the_store_propagates(self) -> None:
        class BrokenStore:
            def load(self) -> bytes | None:
                raise AttributeError("bug in the store")

            def save(self, data: bytes) -> None:
                raise AttributeError("bug in the store")

        session = MemorySession(_memory_config(), 2026, 6, BrokenStore())

        with pytest.raises(AttributeError):
            session.open()

    def test_an_attribute_error_from_a_write_propagates(self) -> None:
        class BrokenWrite:
            def load(self) -> bytes | None:
                return None

            def save(self, data: bytes) -> None:
                raise AttributeError("bug in the store")

        session = MemorySession(_memory_config(), 2026, 6, BrokenWrite())
        session.open()

        with pytest.raises(AttributeError):
            session.commit(make_narrative())
