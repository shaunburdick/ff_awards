"""
Generate the AI narrative: prompt, request, parse, league matching, normalisation.

Failure policy (FR-006): anything this module raises as an ``AISummaryError``
degrades the section to a notice. Everything else propagates, so a programming
error cannot hide behind "AI summary unavailable".
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timezone
from typing import TypedDict

from ..config import AISummaryConfig
from ..exceptions import AIContractError, AISummaryError
from ..models import (
    AIProvenance,
    AISummary,
    AISummaryLeague,
    AISummaryResult,
    AISummaryUnavailable,
    ChallengeResult,
    ChampionshipLeaderboard,
    DivisionData,
    WeeklyChallenge,
)
from .ai_client import CONTRACT_REASON, AIClient, AIRequest
from .ai_digest import build_digest, history_week_count
from .ai_memory import MemoryEntry, MemorySession

logger = logging.getLogger(__name__)

INSTRUCTIONS_HEADING = "### COMMISSIONER'S INSTRUCTIONS"
PROMPT_HASH_LENGTH = 12

HEADLINE_WORD_CAP = 15
SEASON_NOTE_WORD_CAP = 40
LEAGUE_WORD_CAP = 120
MAX_PARAGRAPHS = 3
MAX_BULLETS = 3

# FR-012's two rules about the league-wide block: they are instructions, so
# they sit inside the hashed prompt, and the narrative may not read a division
# rank as an overall one.
LEAGUE_WIDE_RULES: tuple[str, str] = (
    "An overall claim - the best team, the worst team, the biggest blowup across "
    "everyone - may come only from the league-wide block (overall_standings and "
    "weekly_extremes). Each league's standings rank is a rank inside that league's "
    "own table, not the best record in the setup.",
    "The league-wide block is the source for any cross-division statement, and "
    "nothing in it changes a per-league value.",
)

# The system prompt is a module constant so a prompt edit is one reviewable
# diff and prompt_sha (which hashes it plus the user prompt) cannot drift.
SYSTEM_PROMPT = """You write the weekly "commissioner's take" for a fantasy football report.

You receive one JSON object describing the week: every league's name, standings,
the week's matchups, the challenge winners, and - in playoff or championship
weeks - the bracket or the championship leaderboard.

Reply with one JSON object and nothing else: no prose before or after it, no
markdown fences, no commentary. The shape is exactly:

{
  "headline": "one sentence",
  "leagues": [
    {"league": "one of the league names given", "paragraphs": ["..."], "bullets": ["..."]}
  ],
  "season_note": "one sentence"
}

Rules:
- One "leagues" entry per league in the digest, using its name verbatim.
- Each league needs at least one paragraph; no paragraph may be empty.
- At most 3 paragraphs, at most 3 bullets and at most 120 words per league
  across its paragraphs. Aim for at least 60 words per league; a shorter take
  is fine, padding is not.
- headline: at most 15 words. season_note: at most 40 words.
- Voice: a commissioner addressing the league. Direct, dry, allowed to be wry.
- Use only the names and numbers in the digest. Never invent a statistic, a
  player, a team, an event or a result that is not in it.
- Do not present the summary as fact-checked or as a league record.
"""


MEMORY_HEADING = "### MEMORY"
MEMORY_INTRO = (
    "Below is what you published in earlier weeks, one entry per week. It is a "
    "transcript of your own past reports, not part of this week's data."
)
MEMORY_RULES: tuple[str, str] = (
    "Quotation: the archive is what you published in earlier weeks - a record of your "
    "own reports, never a source of league fact. This week's data is the truth; where "
    "the two disagree, the current data wins and the older line may only be quoted as "
    "something you said.",
    "Continue, don't repeat: a running bit escalates or retires. Repeating a joke in the "
    "same words is the failure this memory exists to prevent.",
)


class _RawLeague(TypedDict):
    """A league section as the provider shaped it, before normalisation."""

    league: str
    paragraphs: list[str]
    bullets: list[str]


class _RawNarrative(TypedDict):
    """A contract-valid response, before league matching and normalisation."""

    headline: str
    leagues: list[_RawLeague]
    season_note: str


def build_system_prompt(user_prompt: str, league_names: Sequence[str]) -> str:
    """
    Return the system prompt: contract, the exact league scope, then the block.

    The league count and names are built from the digest at request time, so the
    model is anchored to exactly the sections that exist: a live run returned
    four sections for three leagues, which no case-insensitive matching can
    repair. An empty or whitespace-only user prompt means "no extra
    instructions" and that block is omitted rather than sent empty.
    """
    prompt = SYSTEM_PROMPT + "".join(f"- {rule}\n" for rule in LEAGUE_WIDE_RULES)

    if league_names:
        count = len(league_names)
        noun = "league" if count == 1 else "leagues"
        quoted = ", ".join(f'"{name}"' for name in league_names)
        prompt += (
            f"\nLeague scope: this report covers exactly {count} {noun}: {quoted}.\n"
            f'Return exactly {count} entries in "leagues" - one for each name above, '
            "using those names verbatim and in that order. Do not add, duplicate, "
            "split or rename a league.\n"
        )

    if user_prompt.strip():
        prompt += f"\n\n{INSTRUCTIONS_HEADING}\n{user_prompt}"
    return prompt


def prompt_sha(system_prompt: str) -> str:
    """
    Hash the composed system prompt.

    The composed prompt already contains the league scope and, when set, the
    commissioner's block, so hashing it once covers the template, the scope and
    the user prompt. The limitation is stated in the spec: the prompt itself is
    not archived, so an archived CI report is reproducible only from the
    committed workflow value together with this hash.
    """
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:PROMPT_HASH_LENGTH]


def render_memory_block(entries: Sequence[MemoryEntry], redact: bool = False) -> str:
    """
    Render the archive in week order, each entry under its week tag (FR-014).

    No selection, no window, no truncation and no caps: a hand-edited entry is
    sent exactly as it was written. ``redact`` keeps the block's shape — heading,
    intro, one week tag per entry, the two rules — and drops every word of prose,
    which is what the DEBUG line logs (FR-009).

    Args:
        entries: The entries the run read, in any order.
        redact: Replace each entry's prose with its week tag.

    Returns:
        The composed block, ready to append to the instructions.
    """
    lines = [MEMORY_HEADING, MEMORY_INTRO, ""]
    for entry in sorted(entries, key=lambda row: row["week"]):
        if redact:
            lines.append(f"Week {entry['week']}")
            continue

        lines.append(f"Week {entry['week']} (published {entry['generated_at']})")
        lines.append(entry["headline"])
        lines.append(entry["season_note"])
        for league in entry["leagues"]:
            lines.append(f"League: {league['league']}")
            lines.extend(league["paragraphs"])
            lines.extend(f"- {bullet}" for bullet in league["bullets"])
        lines.append("")

    lines.extend(f"- {rule}" for rule in MEMORY_RULES)
    return "\n".join(lines)


def build_memory_block(entries: Sequence[MemoryEntry]) -> str:
    """The archive as the model reads it: every entry, verbatim, then the two rules."""
    return render_memory_block(entries)


def compose_system_prompt(instructions: str, entries: Sequence[MemoryEntry]) -> str:
    """
    Assemble the request's system prompt: instructions, then the archive block.

    ``prompt_sha`` hashes ``instructions`` alone, so a block that changes every
    week cannot move it (FR-008).
    """
    if not entries:
        return instructions
    return f"{instructions}\n\n{build_memory_block(entries)}"


class AISummaryService:
    """Generate the narrative once per report run."""

    def __init__(
        self, config: AISummaryConfig, client: AIClient, memory: MemorySession | None = None
    ) -> None:
        """
        Initialize the service.

        Args:
            config: Feature settings (model, prompt, caps).
            client: Provider client, injected so tests need no network.
            memory: The run's memory session, or ``None`` when memory is off.
        """
        self._config = config
        self._client = client
        self._memory = memory

    def generate(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None,
        current_week: int | None,
        championship: ChampionshipLeaderboard | None,
    ) -> AISummaryResult:
        """
        Produce the narrative, or a notice explaining why there is none.

        This is the whole fail-open boundary: it catches ``AISummaryError`` and
        nothing else, so a programming error still crashes the run.
        """
        try:
            return self._generate(
                divisions, challenges, weekly_challenges, current_week, championship
            )
        except AISummaryError as e:
            logger.warning("AI summary unavailable: %s", e.reason)
            return AISummaryUnavailable(reason=e.reason)

    def _generate(
        self,
        divisions: Sequence[DivisionData],
        challenges: Sequence[ChallengeResult],
        weekly_challenges: Sequence[WeeklyChallenge] | None,
        current_week: int | None,
        championship: ChampionshipLeaderboard | None,
    ) -> AISummary:
        """
        Build, send, parse, match and normalise one narrative.

        At most one retry, and only for a contract failure: malformed JSON, a
        wrong shape, a league count or name mismatch, or an empty required
        field. Those are sampling noise. HTTP errors, transport failures,
        timeouts and truncation are not retried — the second attempt would fail
        identically at the same cost. The retry reuses the same request
        object, so prompt, payload, model and budget are unchanged.
        """
        # One read, before the digest and the request: the archive is prompt
        # input, and a failed read simply means the take is written without it.
        if self._memory is not None:
            self._memory.open()
            entries = self._memory.entries
        else:
            entries = []

        digest = build_digest(divisions, challenges, weekly_challenges, current_week, championship)
        league_names = [league["league"] for league in digest["leagues"]]
        history_weeks = history_week_count(digest)
        instructions = build_system_prompt(self._config.user_prompt, league_names)
        request = AIRequest(
            system_prompt=compose_system_prompt(instructions, entries),
            user_message=json.dumps(digest, ensure_ascii=False),
            max_tokens=self._config.max_tokens,
            reasoning_effort=self._config.reasoning_effort,
        )
        # DEBUG only: the prompt carries no report data, but Actions logs are
        # world-readable, so a local -vv run is the only place it belongs. The
        # archive is logged as week tags: its shape is visible, its prose is not.
        logged_prompt = (
            f"{instructions}\n\n{render_memory_block(entries, redact=True)}"
            if entries
            else instructions
        )
        logger.debug("AI summary system prompt:\n%s", logged_prompt)

        attempts = 1
        while True:
            try:
                content = self._client.complete(request)
                narrative = self._parse_response(content)
                matched = self._match_leagues(narrative["leagues"], divisions)
                summary = self._normalise(narrative, matched, attempts, instructions, history_weeks)
                break
            except AIContractError:
                if attempts >= 2:
                    raise
                # DEBUG: FR-009's allowlist covers model/status/latency/tokens,
                # and provenance.attempts is the durable record of the retry.
                logger.debug("AI summary contract failure; retrying once")
                attempts = 2

        # The write happens only now, so the entry copies the instant the
        # report already carries rather than reading the clock a second time.
        if self._memory is None:
            return summary

        self._memory.commit(summary)
        return replace(
            summary,
            provenance=replace(
                summary.provenance,
                memory_read=self._memory.read_status,
                memory_write=self._memory.write_status,
                memory_weeks=self._memory.weeks,
            ),
        )

    def _parse_response(self, content: str) -> _RawNarrative:
        """
        Parse the provider's JSON, converting only expected failures.

        The one caught exception is ``JSONDecodeError``; every other rejection
        is an explicit check, so an unanticipated structure crashes instead of
        being reported as a provider fault.
        """
        try:
            payload: object = json.loads(content)
        except json.JSONDecodeError as e:
            raise AIContractError(CONTRACT_REASON) from e

        if not isinstance(payload, dict):
            raise AIContractError(CONTRACT_REASON)
        envelope: dict[str, object] = payload

        headline = _require_text(envelope.get("headline"))
        season_note = _require_text(envelope.get("season_note"))

        raw_leagues = envelope.get("leagues")
        if not isinstance(raw_leagues, list) or not raw_leagues:
            raise AIContractError(CONTRACT_REASON)

        return _RawNarrative(
            headline=headline,
            leagues=[_parse_league(entry) for entry in raw_leagues],
            season_note=season_note,
        )

    @staticmethod
    def _match_leagues(
        raw_leagues: Sequence[_RawLeague], divisions: Sequence[DivisionData]
    ) -> list[tuple[str, _RawLeague]]:
        """
        Apply FR-004's total order, once per response.

        Returns pairs of (our heading, the raw section), so headings always come
        from our league names and never from the provider.
        """
        if not divisions:
            raise AIContractError(CONTRACT_REASON)

        entry_keys = [entry["league"].strip().casefold() for entry in raw_leagues]
        league_keys = [division.name.strip().casefold() for division in divisions]
        counts_match = len(raw_leagues) == len(divisions)
        names_resolve = (
            len(set(entry_keys)) == len(entry_keys)
            and len(set(league_keys)) == len(league_keys)
            and set(entry_keys) == set(league_keys)
        )

        if counts_match and names_resolve:
            by_name = {entry["league"].strip().casefold(): entry for entry in raw_leagues}
            return [
                (division.name, by_name[division.name.strip().casefold()]) for division in divisions
            ]

        if counts_match:
            # A stray, renamed or duplicated entry still renders; the heading is
            # ours, so a response-supplied name can never appear.
            return [(division.name, entry) for division, entry in zip(divisions, raw_leagues)]

        raise AIContractError(
            f"league count mismatch ({len(divisions)} leagues, {len(raw_leagues)} sections)"
        )

    def _normalise(
        self,
        narrative: _RawNarrative,
        matched: Sequence[tuple[str, _RawLeague]],
        attempts: int,
        instructions: str,
        history_weeks: int,
    ) -> AISummary:
        """Apply the caps, structurally, and record whether anything was cut."""
        truncated = False
        leagues: list[AISummaryLeague] = []

        for heading, raw in matched:
            league, was_truncated = _normalise_league(heading, raw)
            leagues.append(league)
            truncated = truncated or was_truncated

        headline, headline_cut = _cap_words(narrative["headline"], HEADLINE_WORD_CAP)
        season_note, note_cut = _cap_words(narrative["season_note"], SEASON_NOTE_WORD_CAP)

        return AISummary(
            headline=headline,
            leagues=leagues,
            season_note=season_note,
            provenance=AIProvenance(
                model=self._config.model,
                prompt_sha=prompt_sha(instructions),
                generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                truncated=truncated or headline_cut or note_cut,
                attempts=attempts,
                history_weeks=history_weeks,
            ),
        )


def _require_text(value: object) -> str:
    """Require a non-empty string, as a contract check rather than a caught error."""
    if not isinstance(value, str) or not value.strip():
        raise AIContractError(CONTRACT_REASON)
    return value


def _parse_league(value: object) -> _RawLeague:
    """Validate one league entry's shape."""
    if not isinstance(value, dict):
        raise AIContractError(CONTRACT_REASON)
    entry: dict[str, object] = value

    league = _require_text(entry.get("league"))

    raw_paragraphs = entry.get("paragraphs")
    if not isinstance(raw_paragraphs, list) or not raw_paragraphs:
        raise AIContractError(CONTRACT_REASON)
    paragraphs: list[str] = []
    for paragraph in raw_paragraphs:
        if not isinstance(paragraph, str) or not paragraph.split():
            raise AIContractError(CONTRACT_REASON)
        paragraphs.append(paragraph)

    raw_bullets = entry.get("bullets", [])
    if not isinstance(raw_bullets, list):
        raise AIContractError(CONTRACT_REASON)
    bullets: list[str] = []
    for bullet in raw_bullets:
        if not isinstance(bullet, str) or not bullet.strip():
            raise AIContractError(CONTRACT_REASON)
        bullets.append(bullet)

    return _RawLeague(league=league, paragraphs=paragraphs, bullets=bullets)


def _normalise_league(heading: str, raw: _RawLeague) -> tuple[AISummaryLeague, bool]:
    """Apply the bullets, paragraphs and word caps to one league section."""
    truncated = False

    bullets = raw["bullets"]
    if len(bullets) > MAX_BULLETS:
        bullets = bullets[:MAX_BULLETS]
        truncated = True

    paragraphs = raw["paragraphs"]
    if len(paragraphs) > MAX_PARAGRAPHS:
        paragraphs = paragraphs[:MAX_PARAGRAPHS]
        truncated = True

    if _word_count(paragraphs) > LEAGUE_WORD_CAP:
        if _word_count(paragraphs[:1]) > LEAGUE_WORD_CAP:
            paragraphs = [_truncate_words(paragraphs[0], LEAGUE_WORD_CAP)]
            truncated = True
        else:
            while len(paragraphs) > 1 and _word_count(paragraphs) > LEAGUE_WORD_CAP:
                paragraphs = paragraphs[:-1]
                truncated = True

    return (
        AISummaryLeague(league=heading, paragraphs=paragraphs, bullets=bullets),
        truncated,
    )


def _word_count(paragraphs: Sequence[str]) -> int:
    """Count words across paragraphs."""
    return sum(len(paragraph.split()) for paragraph in paragraphs)


def _cap_words(text: str, cap: int) -> tuple[str, bool]:
    """Truncate text beyond ``cap`` words at a word boundary, appending an ellipsis."""
    if len(text.split()) <= cap:
        return text, False
    return _truncate_words(text, cap), True


def _truncate_words(text: str, cap: int) -> str:
    """Keep the first ``cap`` words and mark the cut."""
    return " ".join(text.split()[:cap]) + "…"
