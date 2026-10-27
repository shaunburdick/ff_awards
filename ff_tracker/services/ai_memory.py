"""
The memory log: the archive shape, the gist store and the per-run session.

Memory is a log of what this tool already published — one entry per week holding
that week's summary verbatim, inside one file called ``memory.json`` in one
secret gist. Nothing here is generated, summarised or capped: the tool appends
and replaces, and a hand edit inside an earlier entry survives by construction.

No memory outcome can stop the report or change the narrative. The store maps a
transport outcome onto ``AIMemoryStoreError.kind`` and the session maps that
kind onto FR-014's statuses, so the error taxonomy the narrative degrades on is
exactly as wide as it was before this phase.
"""

from __future__ import annotations

import http.client
import json
import logging
import socket
import time
import urllib.error
import urllib.request
from typing import Protocol, TypedDict, cast

from ..config import AIMemoryConfig
from ..exceptions import AIMemoryStoreError
from ..models import (
    MEMORY_READ_FAILED,
    MEMORY_READ_NONE,
    MEMORY_READ_OK,
    MEMORY_WRITE_FAILED,
    MEMORY_WRITE_OK,
    MEMORY_WRITE_SKIPPED,
    AISummary,
)
from .ai_client import USER_AGENT

logger = logging.getLogger(__name__)

MEMORY_SCHEMA = 1
MEMORY_FILE_NAME = "memory.json"
GIST_HOST = "api.github.com"
GIST_ACCEPT = "application/vnd.github+json"


class MemoryLeague(TypedDict):
    """One league's subsection of a published summary."""

    league: str
    paragraphs: list[str]
    bullets: list[str]


class MemoryEntry(TypedDict):
    """One week's published summary, verbatim, plus its week tag."""

    week: int
    generated_at: str
    headline: str
    season_note: str
    leagues: list[MemoryLeague]


class MemoryFile(TypedDict):
    """The archive as stored: a schema, the season it was created for, the entries."""

    schema: int
    season: int
    entries: list[MemoryEntry]


def parse_archive(raw: bytes) -> MemoryFile | None:
    """
    Parse the archive on structure alone (FR-014).

    ``None`` means the bytes do not parse **as the archive shape** and the run
    must treat them as no memory: valid JSON, an object, the supported schema, a
    four-digit season, ``entries`` a list of objects carrying the required keys
    with the right types, and every ``week`` an integer in 1-18. Content, entry
    counts, text length and season agreement are never reasons to reject a file,
    and unknown keys are carried through untouched — that is what keeps a
    hand-edited file readable and never overwritten.

    Args:
        raw: The bytes the store returned.

    Returns:
        The parsed archive, or ``None`` when it is not the archive shape.
    """
    try:
        payload: object = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    archive: dict[str, object] = payload

    if _as_int(archive.get("schema")) != MEMORY_SCHEMA:
        return None

    season = _as_int(archive.get("season"))
    if season is None or not 1000 <= season <= 9999:
        return None

    entries = archive.get("entries")
    if not isinstance(entries, list):
        return None
    if not all(_is_entry(entry) for entry in entries):
        return None

    # The original mapping, so a key this tool does not know survives the round
    # trip: a TypedDict is a shape, not a whitelist.
    return cast(MemoryFile, archive)


def merge_entry(archive: MemoryFile | None, entry: MemoryEntry, season: int) -> MemoryFile:
    """
    Append the week's entry, replacing that week's entry in place if it has one.

    That replacement is the only mutation in the whole feature: a dispatch
    re-run must not stack a second take for the same week, and every other
    entry keeps its value exactly as it was read.

    Args:
        archive: The archive as read, or ``None`` when there was nothing to read.
        entry: The entry this run published.
        season: Used only when the file does not exist yet; a read file keeps
            the season it was created with.

    Returns:
        The archive to save.
    """
    if archive is None:
        return MemoryFile(schema=MEMORY_SCHEMA, season=season, entries=[entry])

    merged: dict[str, object] = dict(archive)
    entries = [row for row in archive["entries"] if row["week"] != entry["week"]]
    entries.append(entry)
    merged["entries"] = sorted(entries, key=lambda row: row["week"])
    return cast(MemoryFile, merged)


def serialize_archive(archive: MemoryFile) -> bytes:
    """Serialise the archive for the store, in week order and readable in the gist UI."""
    return json.dumps(archive, indent=2, ensure_ascii=False).encode("utf-8")


def _as_int(value: object) -> int | None:
    """An integer from JSON, rejecting the booleans ``isinstance`` also calls ints."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _is_entry(value: object) -> bool:
    """Whether one entry carries the required keys with the right types."""
    if not isinstance(value, dict):
        return False

    week = _as_int(value.get("week"))
    if week is None or not 1 <= week <= 18:
        return False

    for key in ("generated_at", "headline", "season_note"):
        if not isinstance(value.get(key), str):
            return False

    leagues = value.get("leagues")
    if not isinstance(leagues, list):
        return False
    return all(_is_league(league) for league in leagues)


def _is_league(value: object) -> bool:
    """Whether one league subsection carries a name, paragraphs and bullets."""
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("league"), str):
        return False

    paragraphs = value.get("paragraphs")
    bullets = value.get("bullets")
    return (
        isinstance(paragraphs, list)
        and all(isinstance(paragraph, str) for paragraph in paragraphs)
        and isinstance(bullets, list)
        and all(isinstance(bullet, str) for bullet in bullets)
    )


class MemoryTransport(Protocol):
    """One gist request, returning the response body."""

    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes:
        """Perform the request and read the body."""
        ...


class MemoryStore(Protocol):
    """Where the archive lives: one read and at most one write per run."""

    def load(self) -> bytes | None:
        """Return the archive's bytes, or ``None`` when there is nothing stored."""
        ...

    def save(self, data: bytes) -> None:
        """Replace the stored archive with ``data``."""
        ...


def _urlopen(request: urllib.request.Request, timeout: int) -> bytes:
    """Default transport: one request, one read, no retries."""
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body: bytes = response.read()
    return body


class GistMemoryStore:
    """
    The production store: one file in one secret gist, over stdlib ``urllib``.

    A secret gist is unlisted, not private, and the file holds this tool's own
    published prose and week tags — never the digest, the prompt or a
    credential. Every failure becomes an ``AIMemoryStoreError`` with a kind the
    session maps onto a status; nothing here retries or streams.
    """

    def __init__(self, config: AIMemoryConfig, transport: MemoryTransport | None = None) -> None:
        """
        Initialize the store.

        Args:
            config: The gist id and token, plus the read timeout.
            transport: Override for tests; defaults to ``_urlopen``.
        """
        self._config = config
        self._transport: MemoryTransport = transport or _urlopen

    def load(self) -> bytes | None:
        """
        Read ``memory.json`` from the gist.

        Returns:
            The file's content as UTF-8 bytes, or ``None`` when the gist holds
            no such file — "nothing published yet", which is not a failure.
        """
        request = urllib.request.Request(
            self._url(), method="GET", headers=self._headers(include_body=False)
        )
        document = _json_object(self._send(request, "GET"))

        files = document.get("files")
        if not isinstance(files, dict):
            raise AIMemoryStoreError(
                "server", f"gist response carried no files object ({GIST_HOST})"
            )
        stored = files.get(MEMORY_FILE_NAME)
        if not isinstance(stored, dict):
            return None
        content = stored.get("content")
        if not isinstance(content, str):
            return None
        return content.encode("utf-8")

    def save(self, data: bytes) -> None:
        """
        Write the archive to the gist, creating ``memory.json`` if it is absent.

        Args:
            data: The serialised archive.
        """
        payload = {"files": {MEMORY_FILE_NAME: {"content": data.decode("utf-8")}}}
        request = urllib.request.Request(
            self._url(),
            data=json.dumps(payload).encode("utf-8"),
            method="PATCH",
            headers=self._headers(include_body=True),
        )
        self._send(request, "PATCH")

    def _url(self) -> str:
        """The gist's API URL."""
        return f"https://{GIST_HOST}/gists/{self._config.gist_id}"

    def _headers(self, *, include_body: bool) -> dict[str, str]:
        """The gist API headers; the token is only ever this value."""
        headers = {
            "Authorization": f"Bearer {self._config.gist_token}",
            "Accept": GIST_ACCEPT,
            "User-Agent": USER_AGENT,
        }
        if include_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _send(self, request: urllib.request.Request, method: str) -> bytes:
        """Perform the request, mapping every outcome onto a store error kind."""
        started = time.monotonic()
        try:
            body = self._transport(request, self._config.timeout)
        except urllib.error.HTTPError as e:
            _discard(e)
            raise _status_error(e.code) from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (TimeoutError, socket.timeout)):
                raise _timeout_error(self._config.timeout) from None
            raise _transport_error() from None
        except (TimeoutError, socket.timeout):
            raise _timeout_error(self._config.timeout) from None
        except (OSError, http.client.HTTPException):
            # A reset or a short body mid-read is an ordinary transport failure.
            raise _transport_error() from None

        # INFO only: method, status and latency. Never the id, token or content.
        logger.info(
            "gist memory %s: status=200 latency_ms=%d",
            method,
            int((time.monotonic() - started) * 1000),
        )
        return body


def _discard(error: urllib.error.HTTPError) -> None:
    """
    Drain and close the error response without letting its body fail the run.

    A reset or a truncated read while consuming an *error* body is not a
    failure to report: the status already decided the outcome, and an exception
    raised inside ``_send``'s ``except`` block would escape the store as a raw
    ``OSError`` and deny the report. The body is never logged.
    """
    try:
        error.read()
    except (OSError, http.client.HTTPException):
        pass
    finally:
        error.close()


def _status_error(status: int) -> AIMemoryStoreError:
    """Map an HTTP status onto FR-014's kinds."""
    if status in (401, 403):
        return AIMemoryStoreError(
            "auth", f"gist authentication failed (HTTP {status} at {GIST_HOST})"
        )
    if status == 404:
        return AIMemoryStoreError("not_found", f"gist not found (HTTP 404 at {GIST_HOST})")
    return AIMemoryStoreError("server", f"gist request failed (HTTP {status} at {GIST_HOST})")


def _transport_error() -> AIMemoryStoreError:
    """The request never reached GitHub."""
    return AIMemoryStoreError("transport", f"gist connection failed ({GIST_HOST})")


def _timeout_error(seconds: int) -> AIMemoryStoreError:
    """A socket read exceeded the timeout the provider client also uses."""
    return AIMemoryStoreError("timeout", f"gist request timed out after {seconds}s")


def _json_object(raw: bytes) -> dict[str, object]:
    """Parse a gist response body as a JSON object, or fail as a store error."""
    try:
        payload: object = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise AIMemoryStoreError("server", f"gist response was not JSON ({GIST_HOST})") from e

    if not isinstance(payload, dict):
        raise AIMemoryStoreError("server", f"gist response was not an object ({GIST_HOST})")
    return payload


class MemorySession:
    """
    One run's memory lifecycle: at most one read, then at most one write.

    It never raises an ``AIMemoryStoreError`` at its caller and it never decides
    anything about the report: it records FR-014's statuses, collects the
    warnings ``main`` prints under Actions, and hands the entries to the prompt.
    Any other exception propagates, so a programming error fails the run loudly
    rather than being swallowed as a memory failure.
    """

    def __init__(
        self,
        config: AIMemoryConfig,
        season: int,
        week: int | None,
        store: MemoryStore | None = None,
    ) -> None:
        """
        Initialize the session.

        Args:
            config: The gist settings, including the read timeout.
            season: The report's season, used only when the file is created.
            week: The report's week; ``None`` or out of 1-18 suppresses the write.
            store: Override for tests; defaults to ``GistMemoryStore(config)``.
        """
        self._season = season
        self._week = week
        self._store: MemoryStore = store or GistMemoryStore(config)
        # Nothing read yet is "nothing published" and nothing written yet is
        # "skipped": a failed narrative leaves both as they are.
        self.read_status: str = MEMORY_READ_NONE
        self.write_status: str = MEMORY_WRITE_SKIPPED
        self.entries: list[MemoryEntry] = []
        self.warnings: list[str] = []
        # True only when a stored file was present and parsed as the archive.
        self.parsed = False
        self._archive: MemoryFile | None = None
        self._unparseable = False

    @property
    def weeks(self) -> list[int]:
        """The week numbers the prompt carried, in order."""
        return [entry["week"] for entry in self.entries]

    def open(self) -> None:
        """Perform the run's single read and record what it found."""
        try:
            raw = self._store.load()
        except AIMemoryStoreError as e:
            self._record_read_failure(e)
            return

        if raw is None:
            self.read_status = MEMORY_READ_NONE
            return

        archive = parse_archive(raw)
        if archive is None:
            # The file is left exactly as it is: this run reads no memory and
            # will not overwrite what it could not understand (AC-033).
            self._unparseable = True
            self.warnings.append(
                "AI memory was ignored: memory.json does not parse as the archive shape, "
                "so this run reads no memory and will not overwrite it."
            )
            return

        self._archive = archive
        self.parsed = True
        self.entries = sorted(archive["entries"], key=lambda row: row["week"])
        self.read_status = MEMORY_READ_OK if self.entries else MEMORY_READ_NONE

    def commit(self, summary: AISummary) -> None:
        """
        Write this week's entry, once, after the narrative exists.

        The entry copies ``summary.provenance.generated_at``, so the file and the
        report cannot disagree about when the take was made.

        Args:
            summary: The narrative the report is about to render.
        """
        week = self._week
        if week is None or not _can_key_entry(self._season, week):
            self.write_status = MEMORY_WRITE_SKIPPED
            return

        if self._unparseable:
            self.write_status = MEMORY_WRITE_SKIPPED
            return

        archive = merge_entry(self._archive, _entry_from_summary(summary, week), self._season)
        try:
            self._store.save(serialize_archive(archive))
        except AIMemoryStoreError as e:
            self.write_status = MEMORY_WRITE_FAILED
            self.warnings.append(_write_warning(e))
            return

        self._archive = archive
        self.write_status = MEMORY_WRITE_OK

    def _record_read_failure(self, error: AIMemoryStoreError) -> None:
        """Map a read failure: 404 is "none", authentication warns, the rest is silent."""
        if error.kind == "not_found":
            self.read_status = MEMORY_READ_NONE
            return

        self.read_status = MEMORY_READ_FAILED
        if error.kind == "auth":
            self.warnings.append(
                "AI memory read failed: gist authentication was rejected; check "
                "AI_MEMORY_GIST_TOKEN has Gists read and write."
            )


def _can_key_entry(season: int, week: int) -> bool:
    """The one thing that suppresses a write: an entry nothing could ever address."""
    return 2000 <= season <= 9999 and 1 <= week <= 18


def _entry_from_summary(summary: AISummary, week: int) -> MemoryEntry:
    """This week's published summary, verbatim, plus its week tag."""
    return MemoryEntry(
        week=week,
        generated_at=summary.provenance.generated_at,
        headline=summary.headline,
        season_note=summary.season_note,
        leagues=[
            MemoryLeague(
                league=league.league,
                paragraphs=list(league.paragraphs),
                bullets=list(league.bullets),
            )
            for league in summary.leagues
        ],
    )


def _write_warning(error: AIMemoryStoreError) -> str:
    """One line naming scope or authentication where that is identifiable."""
    if error.kind == "auth":
        return (
            "AI memory write failed: gist authentication was rejected; check "
            "AI_MEMORY_GIST_TOKEN has Gists read and write."
        )
    if error.kind == "not_found":
        return "AI memory write failed: the gist was not found (HTTP 404); check AI_MEMORY_GIST_ID."
    return f"AI memory write failed: {error.reason}"
