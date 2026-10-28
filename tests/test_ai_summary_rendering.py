"""Cross-format tests for the AI summary section (AC-001, AC-002, AC-011, AC-012)."""

from __future__ import annotations

import difflib
import io
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from ai_fakes import (
    LEAGUE_A,
    LEAGUE_B,
    FakeAIClient,
    FakeMemoryStore,
    make_championship,
    make_championship_divisions,
    make_division,
    make_memory_archive,
    make_narrative,
    make_playoff_divisions,
    make_regular_divisions,
    make_regular_weekly_challenges,
    make_season_challenge,
    make_team,
    make_three_division_divisions,
)

from ff_tracker.display import (
    BaseFormatter,
    ConsoleFormatter,
    EmailFormatter,
    JsonFormatter,
    MarkdownFormatter,
    SheetsFormatter,
)
from ff_tracker.exceptions import AIMemoryStoreError
from ff_tracker.main import main
from ff_tracker.models import (
    AISummary,
    AISummaryLeague,
    AISummaryResult,
    AISummaryUnavailable,
    ChampionshipLeaderboard,
    DivisionData,
    WeeklyChallenge,
)
from ff_tracker.services.ai_digest import build_digest
from ff_tracker.services.ai_summary_service import MEMORY_HEADING

FORMATTERS: dict[str, Callable[..., BaseFormatter]] = {
    "console": ConsoleFormatter,
    "sheets": SheetsFormatter,
    "email": EmailFormatter,
    "json": JsonFormatter,
    "markdown": MarkdownFormatter,
}


def _render(
    format_name: str,
    divisions: Sequence[DivisionData],
    *,
    ai_summary: AISummaryResult | None = None,
    weekly: Sequence[WeeklyChallenge] | None = None,
    current_week: int | None = 6,
    championship: ChampionshipLeaderboard | None = None,
) -> str:
    formatter = FORMATTERS[format_name](year=2026)
    return formatter.format_output(
        divisions,
        [make_season_challenge()],
        list(weekly) if weekly is not None else make_regular_weekly_challenges(),
        current_week,
        championship,
        None,
        ai_summary,
    )


def _inserted_section(off: str, on: str) -> str:
    """
    Return the text the feature added, asserting it is a pure insertion.

    AC-001's wording: the on-output equals its pre-section prefix followed by
    its post-section suffix, with the new block in between. Email adds two
    blocks (a `.ai-team` stylesheet rule and the section itself), so any number
    of insertions is allowed; what is forbidden is a changed or moved line. The
    opcodes are used rather than a common prefix/suffix split because adjacent
    identical characters (``</p>`` next to ``</div>``) make the naive split
    misalign.
    """
    opcodes = [
        opcode
        for opcode in difflib.SequenceMatcher(None, off, on, autojunk=False).get_opcodes()
        if opcode[0] != "equal"
    ]
    assert opcodes, "nothing was inserted"
    assert all(opcode[0] == "insert" for opcode in opcodes), (
        "the feature-off text was modified, not just extended"
    )

    rebuilt: list[str] = []
    inserted: list[str] = []
    cursor = 0
    for _, _, _, on_start, on_end in opcodes:
        rebuilt.append(on[cursor:on_start])
        inserted.append(on[on_start:on_end])
        cursor = on_end
    rebuilt.append(on[cursor:])
    assert "".join(rebuilt) == off
    return "".join(inserted)


def _both(
    format_name: str,
    divisions: Sequence[DivisionData],
    *,
    weekly: Sequence[WeeklyChallenge] | None = None,
    current_week: int | None = 6,
    championship: ChampionshipLeaderboard | None = None,
) -> tuple[str, str]:
    """Render the same report with the feature off and on."""
    off = _render(
        format_name,
        divisions,
        ai_summary=None,
        weekly=weekly,
        current_week=current_week,
        championship=championship,
    )
    on = _render(
        format_name,
        divisions,
        ai_summary=make_narrative(),
        weekly=weekly,
        current_week=current_week,
        championship=championship,
    )
    return off, on


def _ai_team_rule(html: str) -> str:
    """The `.ai-team` selector block from the email's stylesheet."""
    start = html.index(".ai-team {")
    return html[start : html.index("}", start) + 1]


class TestFeatureOffIsUnchanged:
    """AC-001: with no narrative the output is exactly today's output."""

    @pytest.mark.parametrize("format_name", sorted(FORMATTERS))
    def test_off_output_is_byte_identical(self, format_name: str) -> None:
        off, on = _both(format_name, make_regular_divisions())

        if format_name == "json":
            on_document = json.loads(on)
            assert "ai_summary" in on_document
            del on_document["ai_summary"]
            assert on_document == json.loads(off)
        else:
            section = _inserted_section(off, on)
            assert "ai-generated" in section.lower()
            assert section

    @pytest.mark.parametrize("format_name", sorted(FORMATTERS))
    def test_off_output_has_no_notice_either(self, format_name: str) -> None:
        off = _render(format_name, make_regular_divisions())
        assert "AI summary unavailable" not in off


class TestSectionRendering:
    """AC-002: the section appears, last, labelled AI-generated."""

    @pytest.mark.parametrize("format_name", ["console", "sheets", "email", "markdown"])
    def test_narrative_renders(self, format_name: str) -> None:
        _, on = _both(format_name, make_regular_divisions())

        assert "ai-generated" in on.lower()
        if format_name == "email":
            # Email wraps team names; the prose is unchanged around the span.
            assert ">Butt Fumble</span> stayed unbeaten through six weeks." in on
            assert ">Donut Lose</span> won by 1.08" in on
        else:
            assert "Butt Fumble stayed unbeaten through six weeks." in on
            assert "Donut Lose won by 1.08" in on
        assert "Generated by deepseek-v4.1-flash" in on

    def test_console_shape(self) -> None:
        _, on = _both("console", make_regular_divisions())
        assert "🤖 COMMISSIONER'S TAKE (AI-GENERATED)" in on
        assert "── MM Driveway Surfers ──" in on
        assert "  • Donut Lose won by 1.08" in on
        assert "Generated by deepseek-v4.1-flash · AI-generated text" in on

    def test_markdown_shape(self) -> None:
        _, on = _both("markdown", make_regular_divisions())
        assert "## 🤖 Commissioner's Take (AI-generated)" in on
        assert "### MM Driveway Surfers" in on
        assert "- Donut Lose won by 1.08" in on
        assert "_Generated by deepseek-v4.1-flash · AI-generated text_" in on

    # Where the section must sit: after the weekly highlights, before the
    # season challenges (FR-005). Each format's own markers, not re-derived.
    PLACEMENT = {
        "console": {
            "weekly": "WEEKLY PLAYER HIGHLIGHTS - WEEK 6",
            "season": "SEASON-LONG CHALLENGES",
            "ai": "COMMISSIONER'S TAKE",
        },
        "sheets": {
            "weekly": "WEEK 6 HIGHLIGHTS",
            "season": "OVERALL SEASON CHALLENGES",
            "ai": "AI SUMMARY (AI-GENERATED)",
        },
        "email": {
            "weekly": "🔥 Week 6 Highlights",
            "season": "Season Challenge Results",
            "ai": "Commissioner's Take",
        },
        "markdown": {
            "weekly": "🔥 WEEK 6 HIGHLIGHTS",
            "season": "OVERALL SEASON CHALLENGES",
            "ai": "Commissioner's Take",
        },
    }

    @pytest.mark.parametrize("format_name", sorted(PLACEMENT))
    def test_section_sits_between_weekly_and_season(self, format_name: str) -> None:
        """AC-018: the take renders after the highlights and before the challenges."""
        _, on = _both(format_name, make_regular_divisions())
        markers = self.PLACEMENT[format_name]

        weekly = on.index(markers["weekly"])
        ai = on.index(markers["ai"])
        season = on.index(markers["season"])

        assert weekly < ai < season

    @pytest.mark.parametrize("format_name", sorted(PLACEMENT))
    def test_notice_sits_in_the_same_position(self, format_name: str) -> None:
        """AC-018: the failure notice occupies the section's new position."""
        unavailable = AISummaryUnavailable(reason="timed out after 120s")
        on = _render(format_name, make_regular_divisions(), ai_summary=unavailable)
        markers = self.PLACEMENT[format_name]

        weekly = on.index(markers["weekly"])
        notice = on.index("AI summary unavailable")
        season = on.index(markers["season"])

        assert weekly < notice < season
        assert markers["ai"] not in on

    # Per mode, the marker each format emits on either side of the take.
    MODE_PLACEMENT: dict[str, dict[str, tuple[str, str]]] = {
        "console": {
            "playoffs": ("WEEKLY PLAYER HIGHLIGHTS - WEEK 15", "REGULAR SEASON FINAL RESULTS"),
            "championship": ("WEEKLY PLAYER HIGHLIGHTS - WEEK 17", "SEASON-LONG CHALLENGES"),
        },
        "sheets": {
            "playoffs": ("WEEK 15 PLAYER HIGHLIGHTS", "OVERALL SEASON CHALLENGES"),
            "championship": ("WEEK 17 PLAYER HIGHLIGHTS", "OVERALL SEASON CHALLENGES"),
        },
        "email": {
            "playoffs": ("Week 15 Player Highlights", "Season Challenge Results"),
            "championship": ("Week 17 Player Highlights", "Season Challenge Results"),
        },
        "markdown": {
            "playoffs": ("WEEKLY PLAYER HIGHLIGHTS - WEEK 15", "REGULAR SEASON FINAL RESULTS"),
            "championship": ("WEEKLY PLAYER HIGHLIGHTS - WEEK 17", "OVERALL SEASON CHALLENGES"),
        },
    }

    def _render_mode(self, format_name: str, mode: str) -> str:
        if mode == "playoffs":
            return _render(
                format_name,
                make_playoff_divisions(),
                ai_summary=make_narrative(),
                current_week=15,
            )
        return _render(
            format_name,
            make_championship_divisions(),
            ai_summary=make_narrative(),
            current_week=17,
            championship=make_championship(),
        )

    @pytest.mark.parametrize("format_name", sorted(MODE_PLACEMENT))
    @pytest.mark.parametrize("mode", ["playoffs", "championship"])
    def test_section_sits_between_the_mode_sections(self, format_name: str, mode: str) -> None:
        """AC-018 in Weeks 15-16 and Week 17, not just the regular season."""
        on = self._render_mode(format_name, mode)
        highlights, season = self.MODE_PLACEMENT[format_name][mode]
        ai = self.PLACEMENT[format_name]["ai"]

        assert on.index(highlights) < on.index(ai) < on.index(season)

    @pytest.mark.parametrize("format_name", sorted(MODE_PLACEMENT))
    @pytest.mark.parametrize("mode", ["playoffs", "championship"])
    def test_notice_sits_between_the_mode_sections(self, format_name: str, mode: str) -> None:
        if mode == "playoffs":
            on = _render(
                format_name,
                make_playoff_divisions(),
                ai_summary=AISummaryUnavailable(reason="timed out after 120s"),
                current_week=15,
            )
        else:
            on = _render(
                format_name,
                make_championship_divisions(),
                ai_summary=AISummaryUnavailable(reason="timed out after 120s"),
                current_week=17,
                championship=make_championship(),
            )
        highlights, season = self.MODE_PLACEMENT[format_name][mode]

        assert on.index(highlights) < on.index("AI summary unavailable") < on.index(season)

    @pytest.mark.parametrize("format_name", sorted(PLACEMENT))
    def test_section_renders_without_weekly_challenges(self, format_name: str) -> None:
        """No highlights section at all: the take keeps the same slot."""
        on = _render(
            format_name,
            make_regular_divisions(),
            ai_summary=make_narrative(),
            weekly=[],
            current_week=6,
        )
        season = self.PLACEMENT[format_name]["season"]
        ai = self.PLACEMENT[format_name]["ai"]

        assert on.index(ai) < on.index(season)
        assert "WEEKLY PLAYER HIGHLIGHTS" not in on
        assert "WEEK 6 HIGHLIGHTS" not in on

    def test_email_section_sits_before_the_challenges_not_the_footer(self) -> None:
        _, on = _both("email", make_regular_divisions())
        assert on.index("Commissioner's Take") < on.index("Season Challenge Results")
        assert on.index("Season Challenge Results") < on.index('<div class="footer">')

    def test_sheets_shape(self) -> None:
        _, on = _both("sheets", make_regular_divisions())
        assert "AI SUMMARY (AI-GENERATED)" in on
        assert "HEADLINE:\tSix weeks in and nobody has an answer" in on
        assert "LEAGUE:\tMM Driveway Surfers" in on
        assert "\t- Donut Lose won by 1.08" in on

    def test_email_shape(self) -> None:
        _, on = _both("email", make_regular_divisions())
        assert "<h2>🤖 Commissioner's Take (AI-generated)</h2>" in on
        assert "AI-generated text</strong> - not a league record." in on
        assert '<li><span class="ai-team"' in on
        assert ">Donut Lose</span> won by 1.08</li>" in on
        assert "Generated by deepseek-v4.1-flash · AI-generated text" in on


class TestNoticeRendering:
    """The notice stands in the section's position, in the format's style."""

    NOTICE = "AI summary unavailable: timed out after 120s. The report is unaffected."

    @pytest.mark.parametrize("format_name", sorted(FORMATTERS))
    def test_notice_replaces_the_section(self, format_name: str) -> None:
        off = _render(format_name, make_regular_divisions())
        unavailable = AISummaryUnavailable(reason="timed out after 120s")
        on = _render(format_name, make_regular_divisions(), ai_summary=unavailable)

        if format_name == "json":
            assert json.loads(on)["ai_summary"] == {"error": self.NOTICE}
        else:
            section = _inserted_section(off, on)
            assert self.NOTICE in section

    @pytest.mark.parametrize("format_name", ["console", "sheets", "email", "markdown"])
    def test_notice_has_no_empty_heading(self, format_name: str) -> None:
        unavailable = AISummaryUnavailable(reason="finish_reason=length")
        on = _render(format_name, make_regular_divisions(), ai_summary=unavailable)

        assert "commissioner's take" not in on.lower()
        assert "AI summary unavailable: finish_reason=length." in on


class TestHostileProse:
    """AC-011: prose with tabs, newlines and markup stays intact per format."""

    PARAGRAPH = 'Tab\there "quoted" <b>&</b> emoji 🏈 newline\nsecond line'
    BULLET = 'Bullet\twith "quotes" & <angles> 😀'

    def _summary(self) -> AISummary:
        return make_narrative(
            leagues=[
                AISummaryLeague(
                    league=LEAGUE_A,
                    paragraphs=[self.PARAGRAPH],
                    bullets=[self.BULLET],
                )
            ]
        )

    def test_console_paragraph_is_one_line(self) -> None:
        """AC-011: a tab or newline inside a field must not add a line."""
        on = _render("console", make_regular_divisions(), ai_summary=self._summary())
        section = on.split("COMMISSIONER'S TAKE")[1]

        assert "\t" not in section
        paragraph_lines = [line for line in section.splitlines() if "Tab" in line]
        assert len(paragraph_lines) == 1
        assert "newline second line" in paragraph_lines[0]
        assert 'Tab here "quoted"' in paragraph_lines[0]

        bullet_lines = [line for line in section.splitlines() if line.startswith("  • ")]
        assert len(bullet_lines) == 1
        assert "\t" not in bullet_lines[0]

    def test_markdown_keeps_the_text_verbatim(self) -> None:
        on = _render("markdown", make_regular_divisions(), ai_summary=self._summary())
        assert self.PARAGRAPH in on

    def test_sheet_row_is_one_flattened_cell(self) -> None:
        on = _render("sheets", make_regular_divisions(), ai_summary=self._summary())
        rows = [line for line in on.splitlines() if "Tab here" in line]

        assert len(rows) == 1
        assert rows[0].count("\t") == 1  # one label/value separator, nothing split
        assert "second line" in rows[0]
        assert "\n" not in rows[0]

    def test_bullet_row_keeps_one_tab(self) -> None:
        on = _render("sheets", make_regular_divisions(), ai_summary=self._summary())
        rows = [line for line in on.splitlines() if "Bullet with" in line]

        assert len(rows) == 1
        assert rows[0].count("\t") == 1

    def test_email_escapes_html(self) -> None:
        on = _render("email", make_regular_divisions(), ai_summary=self._summary())
        section = on.split("Commissioner's Take")[1]

        assert "&lt;b&gt;&amp;&lt;/b&gt;" in section
        assert "<b>" not in section
        assert "&quot;quoted&quot;" in section
        assert "🏈" in section


class TestModeAgreement:
    """AC-012: the digest's mode agrees with the marker each format renders."""

    # What each formatter prints for each mode, taken from the formatter itself.
    MODE_MARKERS: dict[str, dict[str, str]] = {
        "console": {
            "playoffs": "FINAL REGULAR SEASON STANDINGS",
            "championship": "CHAMPIONSHIP WEEK",
        },
        "sheets": {
            "playoffs": "FINAL REGULAR SEASON STANDINGS (Week 14)",
            "championship": "CHAMPIONSHIP WEEK - FINAL LEADERBOARD",
        },
        "email": {
            "playoffs": "Final Regular Season Standings",
            "championship": "Championship Week - Final Leaderboard",
        },
        "markdown": {
            "playoffs": "## FINAL REGULAR SEASON STANDINGS",
            "championship": "# 🏆 CHAMPIONSHIP WEEK 🏆",
        },
    }

    @pytest.mark.parametrize(
        ("divisions_factory", "board_factory", "week", "expected_mode"),
        [
            (make_playoff_divisions, None, 15, "playoffs"),
            (make_championship_divisions, make_championship, 17, "championship"),
        ],
        ids=["playoffs", "championship"],
    )
    @pytest.mark.parametrize("format_name", sorted(MODE_MARKERS))
    def test_digest_mode_matches_the_rendered_mode(
        self,
        divisions_factory: Callable[[], list[DivisionData]],
        board_factory: Callable[[], ChampionshipLeaderboard] | None,
        week: int,
        expected_mode: str,
        format_name: str,
    ) -> None:
        divisions = divisions_factory()
        board = board_factory() if board_factory is not None else None

        digest = build_digest(
            divisions,
            [make_season_challenge()],
            make_regular_weekly_challenges(),
            week,
            board,
        )
        assert digest["mode"] == expected_mode

        rendered = _render(
            format_name,
            divisions,
            ai_summary=make_narrative(),
            current_week=week,
            championship=board,
        )
        assert self.MODE_MARKERS[format_name][expected_mode] in rendered

    @pytest.mark.parametrize(
        ("divisions_factory", "board_factory", "week", "expected_report_type"),
        [
            (make_playoff_divisions, None, 15, "playoff_semifinals"),
            (make_championship_divisions, make_championship, 17, "championship_week"),
        ],
        ids=["playoffs", "championship"],
    )
    def test_json_report_type_matches_the_digest_mode(
        self,
        divisions_factory: Callable[[], list[DivisionData]],
        board_factory: Callable[[], ChampionshipLeaderboard] | None,
        week: int,
        expected_report_type: str,
    ) -> None:
        divisions = divisions_factory()
        board = board_factory() if board_factory is not None else None

        digest = build_digest(divisions, [], make_regular_weekly_challenges(), week, board)
        document = json.loads(
            _render(
                "json",
                divisions,
                ai_summary=make_narrative(),
                current_week=week,
                championship=board,
            )
        )
        assert document["report_type"] == expected_report_type
        assert digest["mode"] == (
            "championship" if expected_report_type == "championship_week" else "playoffs"
        )

    def test_regular_season_mode(self) -> None:
        divisions = make_regular_divisions()
        digest = build_digest(divisions, [], make_regular_weekly_challenges(), 6, None)
        console = _render("console", divisions, ai_summary=make_narrative(), current_week=6)

        assert digest["mode"] == "regular_season"
        assert "CHAMPIONSHIP WEEK" not in console
        assert "FINAL REGULAR SEASON STANDINGS" not in console
        assert LEAGUE_B in console


class TestEmailTeamHighlighting:
    """AC-023: team names inside the email narrative are wrapped in a span."""

    def _render(
        self,
        team_names: list[str],
        paragraphs: list[str],
        *,
        bullets: list[str] | None = None,
        headline: str = "Headline",
        season_note: str = "Note.",
        format_args: dict[str, str] | None = None,
    ) -> str:
        divisions = [make_division(LEAGUE_A, teams=[make_team(name) for name in team_names])]
        narrative = make_narrative(
            headline=headline,
            leagues=[
                AISummaryLeague(
                    league=LEAGUE_A,
                    paragraphs=paragraphs,
                    bullets=bullets or [],
                )
            ],
            season_note=season_note,
        )
        formatter = EmailFormatter(year=2026, format_args=format_args or {})
        return formatter.format_output(
            divisions, [make_season_challenge()], [], None, None, None, narrative
        )

    def test_team_name_is_wrapped_and_casing_preserved(self) -> None:
        on = self._render(["Butt Fumble"], ["BUTT FUMBLE won ugly."])

        span = '<span class="ai-team">BUTT FUMBLE</span>'
        assert span + " won ugly." in on
        assert "style=" not in span

    def test_apostrophes_and_trailing_space_are_handled(self) -> None:
        # "I don't consent" carries a trailing space in the fixture data.
        on = self._render(
            ["Drew's Daring Team", "I don't consent "],
            ["Drew's Daring Team lost to I don't consent."],
        )

        assert (
            '<span class="ai-team">Drew&#x27;s Daring Team</span> lost to '
            '<span class="ai-team">I don&#x27;t consent</span>.'
        ) in on

    def test_longest_name_wins(self) -> None:
        on = self._render(
            ["McConkey Kong", "McConkey Kong Two"],
            ["McConkey Kong Two beat McConkey Kong."],
        )

        assert ">McConkey Kong Two</span> beat" in on
        assert '<span class="ai-team">McConkey Kong</span>.' in on

    def test_name_inside_a_longer_word_is_not_wrapped(self) -> None:
        on = self._render(["Butt Fumble"], ["Butt Fumbles everywhere."])

        assert "ai-team" in on  # the script/style rule names the class
        assert ">Butt Fumble</span>" not in on
        assert "Butt Fumbles everywhere." in on

    def test_double_spaces_in_a_name_still_match(self) -> None:
        on = self._render(["Two  Spaces"], ["Two   Spaces won."])

        assert '<span class="ai-team"' in on
        assert ">Two   Spaces</span> won." in on

    def test_prose_without_a_team_name_is_unchanged(self) -> None:
        on = self._render(["Butt Fumble"], ["Nobody in particular won."])

        assert "<p>Nobody in particular won.</p>" in on

    def test_script_payload_is_escaped_not_markup(self) -> None:
        on = self._render(["Butt Fumble"], ['<script>alert("x")</script>'])

        assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;" in on
        assert "<script>" not in on

    def test_colour_argument_changes_the_rule(self) -> None:
        on = self._render(
            ["Butt Fumble"],
            ["Butt Fumble won."],
            format_args={"ai_team_color": "#ff0000"},
        )

        assert "color: #ff0000;" in _ai_team_rule(on)
        assert 'class="ai-team"' in on
        assert 'style="font-weight:700;color:#ff0000"' not in on

    def test_default_colour_is_the_documented_one(self) -> None:
        on = self._render(["Butt Fumble"], ["Butt Fumble won."])

        assert "color: #0b57d0;" in _ai_team_rule(on)

    def test_stylesheet_rule_is_valid_css(self) -> None:
        """The rule is real CSS carrying the whole appearance, not the doubled braces."""
        on = self._render(["Butt Fumble"], ["Butt Fumble won."])

        assert (
            ".ai-team {\n            color: #0b57d0;\n            font-weight: 700;\n        }"
            in on
        )
        assert "{{" not in on
        assert "}}" not in on

    def test_stylesheet_rule_is_absent_on_the_off_path(self) -> None:
        """Feature off: no rule and no span, so AC-001's reference stays clean."""
        divisions = [make_division(LEAGUE_A, teams=[make_team("Butt Fumble")])]
        off = EmailFormatter(year=2026).format_output(
            divisions, [make_season_challenge()], [], None, None, None, None
        )

        assert ".ai-team" not in off
        assert "ai-team" not in off

    def test_stylesheet_rule_is_absent_on_the_notice_path(self) -> None:
        divisions = [make_division(LEAGUE_A, teams=[make_team("Butt Fumble")])]
        notice = EmailFormatter(year=2026).format_output(
            divisions,
            [make_season_challenge()],
            [],
            None,
            None,
            None,
            AISummaryUnavailable(reason="timed out after 120s"),
        )

        assert ".ai-team" not in notice
        assert "{{" not in notice
        assert "}}" not in notice

    def test_notice_path_has_no_spans(self) -> None:
        divisions = [make_division(LEAGUE_A, teams=[make_team("Butt Fumble")])]
        on = EmailFormatter(year=2026).format_output(
            divisions,
            [make_season_challenge()],
            [],
            None,
            None,
            None,
            AISummaryUnavailable(reason="timed out after 120s"),
        )

        assert "AI summary unavailable" in on
        assert '<span class="ai-team"' not in on
        assert ".ai-team {" not in on  # no AI stylesheet rule either

    @pytest.mark.parametrize("format_name", ["console", "markdown", "sheets", "json"])
    def test_other_formats_have_no_span(self, format_name: str) -> None:
        _, on = _both(format_name, make_regular_divisions())
        assert "ai-team" not in on


GOLDEN_PATH = Path(__file__).parent / "fixtures" / "ai_summary_phase1_golden.json"
GOLDEN_MODEL = "deepseek-v4.1-flash"
GOLDEN_RESPONSE = json.dumps(
    {
        "headline": "Three leagues, one long weekend",
        "leagues": [
            {
                "league": "MM Driveway Surfers",
                "paragraphs": ["Butt Fumble stayed unbeaten through six weeks."],
                "bullets": ["Donut Lose won by 1.08"],
            },
            {
                "league": "My 2026 League",
                "paragraphs": ["Sunday Scaries won by 70 and it was not close."],
                "bullets": [],
            },
            {
                "league": "The Hood 2026",
                "paragraphs": ["Hood Rats survived by half a point."],
                "bullets": ["Late Round Larry is still winless"],
            },
        ],
        "season_note": "The middle of every table is a car park.",
    }
)
# Everything the golden pins: a stray variable in the environment would move
# the prompt, the model or the report data.
PINNED_ENV = {
    "AI_SUMMARY_ENABLED": "true",
    "AI_SUMMARY_API_KEY": "sk-golden",
    "AI_SUMMARY_MODEL": GOLDEN_MODEL,
    "AI_SUMMARY_USER_PROMPT": "",
}


class _StubESPNService:
    """The ESPN service ``main`` drives, with the AC-027 fixture behind it."""

    current_week = 6

    def __init__(self, config: object) -> None:
        self.divisions = make_three_division_divisions()

    def load_all_divisions(self) -> list[DivisionData]:
        return self.divisions


def phase1_report_outputs(
    tmp_path: Path,
    *,
    env: Mapping[str, str] | None = None,
    memory_store: FakeMemoryStore | None = None,
    client: FakeAIClient | None = None,
) -> dict[str, object]:
    """
    Run one report end to end for the golden and return the five outputs.

    The patch set is plan Decision 17's: ``sys.argv`` (the league ids come from
    it), ``ESPNService``, the provider client, ``datetime`` **on the summary
    service module** (patching the class globally would leak into the process)
    and the environment. The capture script and the comparison test both call
    this, so the two phases compare one path rather than two copies of it.

    ``env`` is layered over the pinned environment, so a memory run varies one
    variable rather than the whole set.
    """
    argv = ["ff-tracker", "111,222,333", "--year", "2026", "--output-dir", str(tmp_path)]
    ai_client = client if client is not None else FakeAIClient(response=GOLDEN_RESPONSE)
    store = memory_store if memory_store is not None else FakeMemoryStore()
    environment = {**PINNED_ENV, **(env or {})}
    previous_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        with (
            patch.object(sys, "argv", argv),
            patch.dict(os.environ, environment, clear=True),
            patch("ff_tracker.main.ESPNService", _StubESPNService),
            patch("ff_tracker.main.OpenAICompatibleClient", lambda config: ai_client),
            patch("ff_tracker.main.GistMemoryStore", lambda config: store),
            patch("ff_tracker.services.ai_summary_service.datetime") as frozen,
            redirect_stdout(io.StringIO()),
        ):
            frozen.now.return_value = datetime(2026, 10, 14, 5, 3, 11, tzinfo=timezone.utc)
            assert main() == 0
    finally:
        os.chdir(previous_cwd)

    return {
        "console": (tmp_path / "standings.txt").read_text(encoding="utf-8"),
        "sheets": (tmp_path / "standings.tsv").read_text(encoding="utf-8"),
        "email": (tmp_path / "standings.html").read_text(encoding="utf-8"),
        "markdown": (tmp_path / "standings.md").read_text(encoding="utf-8"),
        "json": json.loads((tmp_path / "standings.json").read_text(encoding="utf-8")),
    }


def _first_difference(actual: str, expected: str) -> str:
    """Name the first differing character, so a failure is read as output."""
    for index, (left, right) in enumerate(zip(actual, expected)):
        if left != right:
            window = slice(max(index - 30, 0), index + 30)
            return f"offset {index}: {actual[window]!r} != {expected[window]!r}"
    return f"lengths differ: {len(actual)} != {len(expected)}"


class TestPhase1Golden:
    """
    AC-028's reference: the Phase-1 five outputs, read from disk only.

    Nothing here regenerates the file. A recapture is a deliberate, separate
    commit reviewed as output (plan Decision 17), never a side effect of a test.
    """

    @pytest.fixture(scope="class")
    def produced(self, tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
        return phase1_report_outputs(tmp_path_factory.mktemp("phase1-golden"))

    @pytest.fixture(scope="class")
    def golden(self) -> dict[str, object]:
        document: object = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
        assert isinstance(document, dict)
        return document

    @pytest.mark.parametrize("format_name", ["console", "sheets", "email", "markdown"])
    def test_text_formats_match_the_golden(
        self, produced: dict[str, object], golden: dict[str, object], format_name: str
    ) -> None:
        expected = golden[format_name]
        actual = produced[format_name]

        assert isinstance(expected, str)
        assert isinstance(actual, str)
        assert actual == expected, _first_difference(actual, expected)

    def test_json_matches_the_golden_document(
        self, produced: dict[str, object], golden: dict[str, object]
    ) -> None:
        assert produced["json"] == golden["json"]

    def test_the_golden_carries_the_phase1_provenance(self, golden: dict[str, object]) -> None:
        document = golden["json"]
        assert isinstance(document, dict)
        provenance = document["ai_summary"]["provenance"]

        assert provenance["model"] == GOLDEN_MODEL
        assert provenance["generated_at"] == "2026-10-14T05:03:11Z"
        assert provenance["history_weeks"] == 6


MEMORY_ENV = {
    "AI_MEMORY_ENABLED": "true",
    "AI_MEMORY_GIST_ID": "gist123",
    "AI_MEMORY_GIST_TOKEN": "ghp-golden",
}


@pytest.fixture(scope="module")
def phase1_golden() -> dict[str, object]:
    """The checked-in Phase-1 document, read and never written."""
    document: object = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


class TestMemoryOffMatchesTheGolden:
    """AC-028: memory off is invisible, and memory on changes only the prompt."""

    def _text_formats(self) -> list[str]:
        return ["console", "sheets", "email", "markdown"]

    def test_memory_unset_makes_zero_store_calls_and_reproduces_the_golden(
        self, tmp_path: Path, phase1_golden: dict[str, object]
    ) -> None:
        store = FakeMemoryStore()
        client = FakeAIClient(response=GOLDEN_RESPONSE)

        produced = phase1_report_outputs(tmp_path, memory_store=store, client=client)

        assert store.read_calls == 0 == store.write_calls
        for format_name in self._text_formats():
            assert produced[format_name] == phase1_golden[format_name], format_name
        assert produced["json"] == phase1_golden["json"]
        assert MEMORY_HEADING not in client.requests[0].system_prompt

    def test_memory_explicitly_false_is_the_same(
        self, tmp_path: Path, phase1_golden: dict[str, object]
    ) -> None:
        store = FakeMemoryStore()
        client = FakeAIClient(response=GOLDEN_RESPONSE)

        produced = phase1_report_outputs(
            tmp_path,
            env={"AI_MEMORY_ENABLED": "false"},
            memory_store=store,
            client=client,
        )

        assert store.read_calls == 0 == store.write_calls
        assert produced["json"] == phase1_golden["json"]
        assert MEMORY_HEADING not in client.requests[0].system_prompt

    @pytest.mark.parametrize("kind", ["server", "transport", "timeout"])
    def test_a_read_failure_renders_the_golden_sections(
        self, tmp_path: Path, phase1_golden: dict[str, object], kind: str
    ) -> None:
        """AC-031: a read that fails is invisible in every format but the prompt."""
        store = FakeMemoryStore(
            data=make_memory_archive(), read_errors=[AIMemoryStoreError(kind, "x")]
        )

        produced = phase1_report_outputs(
            tmp_path, env=MEMORY_ENV, memory_store=store, client=FakeAIClient(GOLDEN_RESPONSE)
        )

        for format_name in self._text_formats():
            assert produced[format_name] == phase1_golden[format_name], format_name

        document = produced["json"]
        assert isinstance(document, dict)
        assert isinstance(phase1_golden["json"], dict)
        summary = document["ai_summary"]
        assert isinstance(summary, dict)
        provenance = summary["provenance"]
        assert isinstance(provenance, dict)
        assert provenance["memory_read"] == "failed"
        assert provenance["memory_weeks"] == []
        for key in ("memory_read", "memory_write", "memory_weeks"):
            del provenance[key]
        assert document == phase1_golden["json"]

    def test_the_golden_carries_no_memory_provenance(
        self, phase1_golden: dict[str, object]
    ) -> None:
        document = phase1_golden["json"]
        assert isinstance(document, dict)
        provenance = document["ai_summary"]["provenance"]

        assert set(provenance) == {
            "model",
            "prompt_sha",
            "generated_at",
            "truncated",
            "attempts",
            "history_weeks",
        }

    def test_memory_on_renders_the_golden_section_and_changes_only_provenance(
        self, tmp_path: Path, phase1_golden: dict[str, object]
    ) -> None:
        """AC-030: the archive changes the prompt, not the render."""
        store = FakeMemoryStore(data=make_memory_archive(weeks=(1, 2, 3)))
        client = FakeAIClient(response=GOLDEN_RESPONSE)

        produced = phase1_report_outputs(
            tmp_path, env=MEMORY_ENV, memory_store=store, client=client
        )

        assert store.read_calls == 1
        assert store.write_calls == 1
        assert len(client.requests) == 1
        assert MEMORY_HEADING in client.requests[0].system_prompt

        for format_name in self._text_formats():
            assert produced[format_name] == phase1_golden[format_name], format_name

        document = produced["json"]
        assert isinstance(document, dict)
        assert isinstance(phase1_golden["json"], dict)
        summary = document["ai_summary"]
        assert isinstance(summary, dict)
        provenance = summary["provenance"]
        assert isinstance(provenance, dict)

        # prompt_sha hashes the instructions, so an archive cannot move it.
        golden_provenance = phase1_golden["json"]["ai_summary"]["provenance"]
        assert provenance["prompt_sha"] == golden_provenance["prompt_sha"]
        assert provenance["memory_read"] == "ok"
        assert provenance["memory_write"] == "ok"
        assert provenance["memory_weeks"] == [1, 2, 3]

        for key in ("memory_read", "memory_write", "memory_weeks"):
            del provenance[key]
        assert document == phase1_golden["json"]


class TestMemoryReadOnly:
    """AC-034: writing is a choice, and choosing not to changes no rendered value."""

    def test_the_five_formats_match_a_writing_run(
        self, tmp_path: Path, phase1_golden: dict[str, object]
    ) -> None:
        archive = make_memory_archive(weeks=(1, 2, 3))
        writing_store = FakeMemoryStore(data=archive)
        read_only_store = FakeMemoryStore(data=archive)
        writing_dir = tmp_path / "writing"
        read_only_dir = tmp_path / "read-only"
        writing_dir.mkdir()
        read_only_dir.mkdir()

        writing = phase1_report_outputs(
            writing_dir,
            env={**MEMORY_ENV, "AI_MEMORY_WRITE": "true"},
            memory_store=writing_store,
            client=FakeAIClient(response=GOLDEN_RESPONSE),
        )
        read_only = phase1_report_outputs(
            read_only_dir,
            env={**MEMORY_ENV, "AI_MEMORY_WRITE": "false"},
            memory_store=read_only_store,
            client=FakeAIClient(response=GOLDEN_RESPONSE),
        )

        for format_name in ("console", "sheets", "email", "markdown"):
            assert read_only[format_name] == writing[format_name], format_name

        # JSON carries provenance, so the one field the choice changes is
        # memory_write; everything else, narrative included, is identical.
        writing_json = writing["json"]
        read_only_json = read_only["json"]
        assert isinstance(writing_json, dict)
        assert isinstance(read_only_json, dict)
        writing_provenance = writing_json["ai_summary"]["provenance"]
        read_only_provenance = read_only_json["ai_summary"]["provenance"]
        assert writing_provenance["memory_write"] == "ok"
        assert read_only_provenance["memory_write"] == "skipped"
        assert {
            key: value for key, value in writing_provenance.items() if key != "memory_write"
        } == {key: value for key, value in read_only_provenance.items() if key != "memory_write"}
        assert {
            **writing_json,
            "ai_summary": {**writing_json["ai_summary"], "provenance": None},
        } == {
            **read_only_json,
            "ai_summary": {**read_only_json["ai_summary"], "provenance": None},
        }

        assert writing_store.write_calls == 1
        assert read_only_store.write_calls == 0
        assert read_only_provenance["memory_weeks"] == [1, 2, 3]
