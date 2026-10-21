# Implementation Tasks: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: Ready for implementation (Gate 2 revisions applied)
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-21
> **Version**: 1.1
> **Plan**: [plan.md](./plan.md)

Thirteen tasks. Each is independently verifiable, and the suite (`uv run ruff check .`, `uv run mypy ff_tracker`, `uv run pytest -q`) is green at the end of every one. Task numbers are execution order, not importance.

---

## Task Execution Guidelines

- Complete tasks in order; each task names the spec AC ids it satisfies.
- Run the three checks after every task, not only at the end.
- A task that changes a formatter signature must state how output stays byte-identical when `ai_summary is None` (AC-001).
- No new dependency. No network in tests: `FakeAIClient` / `FakeTransport` only, plus the one `patch("urllib.request.urlopen")` test of the production transport.
- If a task needs a decision the plan does not record, stop and raise it rather than inventing behaviour.

---

## Phase 1 — Groundwork

### Task 1: `DivisionData.reg_season_count`

**Goal**: the model field FR-002's "weeks remaining" reads, honest about being unknown.

- [ ] `ff_tracker/models/division.py`: add `reg_season_count: int | None = None` after `playoff_bracket`
- [ ] Validate `None` or `1 <= reg_season_count <= 18` in `validate()` with `DataValidationError`
- [ ] `ff_tracker/services/espn_service.py` (`load_division_data`, the `return DivisionData(...)` near line 1288): pass `reg_season_count=league.settings.reg_season_count`
- [ ] Docstring: `None` means unknown — the digest emits `weeks_remaining: null` rather than a fabricated 14
- [ ] Test: default is `None`, explicit value accepted, `0` and `19` rejected

**Validation**: `pytest -q` green; the 62 existing `DivisionData(...)` sites untouched (default).

**ACs**: FR-002 data requirement · AC-012 (digest input)

**Files**: `models/division.py`, `services/espn_service.py`, `tests/test_model_properties.py`

---

### Task 2: `AISummary` models

**Goal**: the frozen, validated narrative models (Article II).

- [ ] New `ff_tracker/models/ai_summary.py`: `AISummaryLeague`, `AIProvenance`, `AISummary`, `AISummaryUnavailable`, `AISummaryResult`
- [ ] `AISummaryLeague.__post_init__`: league non-empty; ≥1 paragraph; every paragraph has ≥1 word after `strip()`; every bullet non-empty
- [ ] `AISummary.__post_init__`: headline non-empty, ≥1 league, season_note non-empty
- [ ] `AIProvenance.__post_init__`: model/prompt_sha/generated_at non-empty; `truncated` defaults `False`
- [ ] `AISummaryUnavailable.reason` non-empty; `notice` property returns `AI summary unavailable: {reason}. The report is unaffected.`
- [ ] `AISummaryResult = Union[AISummary, AISummaryUnavailable]` — `typing.Union`, not `X | Y` (runtime alias on py3.9)
- [ ] Export all of the above from `models/__init__.py` (`__all__`)
- [ ] `tests/test_ai_summary_models.py`: valid construction, each rejection, `notice` text, `truncated` default

**Validation**: `pytest -q` green; `mypy ff_tracker` clean.

**ACs**: AC-002 (JSON shape) · AC-013/AC-015 (`truncated`) · FR-004 · FR-008

**Files**: new `models/ai_summary.py`, `models/__init__.py`, new `tests/test_ai_summary_models.py`

---

### Task 3: AI error taxonomy

**Goal**: one exception per failure class, each carrying its FR-006 reason.

- [ ] `ff_tracker/exceptions.py`: `AISummaryError(Exception)` with `reason: str` — **not** under `FFTrackerError`
- [ ] Subclasses building their own reason in `__init__`: `AIHTTPError(status, host, model)`, `AITransportError(host)`, `AITimeoutError(seconds)`, `AITruncationError()`, `AIContractError(reason)`
- [ ] Exact strings: `HTTP 410 (model glm-5.3-flash at opencode.ai)`, `connection failed (opencode.ai)`, `timed out after 120s`, `finish_reason=length`, `response did not match the summary contract`, and the count-mismatch string supplied by the caller
- [ ] Docstring: why this hierarchy is not part of `FFTrackerError` (never reaches `main`'s fail-fast handler by accident)
- [ ] `tests/test_ai_summary_models.py`: assert each reason verbatim, and that `AISummaryError` is not an `FFTrackerError`

**Validation**: `pytest -q` green.

**ACs**: AC-004 (reasons) · AC-005 (host only) · FR-006

**Files**: `exceptions.py`, `tests/test_ai_summary_models.py`

---

### Task 4: AI configuration

**Goal**: the seven variables, validated, beside `FFTrackerConfig`, loaded the same way as the existing settings.

- [ ] `ff_tracker/config.py`: frozen `AISummaryConfig` — `enabled`, `api_key` (`field(default="", repr=False)`), `base_url`, `model`, `timeout`, `max_prompt_chars`, `user_prompt`
- [ ] `__post_init__`: enabled → non-empty key naming `AI_SUMMARY_API_KEY`; `timeout > 0`; `max_prompt_chars > 0`; `len(user_prompt) <= max_prompt_chars` with variable + actual length + configured limit
- [ ] `load_ai_summary_config() -> AISummaryConfig`: **calls `load_environment()` first** (it only runs inside `create_config` otherwise); `AI_SUMMARY_ENABLED` in `{true,1,yes,on,false,0,no,off}` (case-insensitive, default false); `TIMEOUT`/`MAX_PROMPT_CHARS` via `int()` with `ConfigurationError` naming the variable; base URL default `https://opencode.ai/inference/openai/v1` for unset/empty/whitespace and trailing `/` stripped; model default `glm-5.3-flash`; user prompt CRLF→LF then `strip()`
- [ ] `tests/test_config.py`: new class covering AC-009 and AC-017 (missing key, bad flag value, non-numeric/zero timeout, non-positive/non-integer limit, oversized prompt names the **configured** limit, unset/empty/whitespace prompt accepted, defaults)
- [ ] `tests/test_config.py`: **`.env`-only test** — `monkeypatch.chdir(tmp_path)` with a written `.env` holding `AI_SUMMARY_ENABLED=true` and the key, `create_config` left unpatched, then `load_ai_summary_config().enabled is True` (the Gate 2 ordering proof)

**Validation**: `pytest -q` green. Nothing reads the loader yet, so no run-time change.

**ACs**: AC-009 · AC-017 · FR-007 · FR-010

**Files**: `config.py`, `tests/test_config.py`

---

## Phase 2 — Payload And Provider

### Task 5: Digest builder

**Goal**: the FR-002 payload, from domain models only, typed so a key typo cannot pass.

- [ ] New `ff_tracker/services/ai_digest.py`: the `TypedDict`s (`AIDigest`, `AILeagueDigest`, `AIStandingsRow`, `AIMatchupRow`, `AIWeeklyChallenge`, `AISeasonChallenge`, `AIPlayoffRound`, `AIPlayoffMatchup`, `AIChampionship`, `AIChampionshipEntry`) exactly as in plan Decision 4 — every key total, unknown values `None`
- [ ] `build_digest(divisions, challenges, weekly_challenges, current_week, championship) -> AIDigest`
- [ ] Mode (local sixth copy): `championship is not None` → `"championship"`; elif `any(d.is_playoff_mode …)` → `"playoffs"`; else `"regular_season"`
- [ ] Per league: name, `teams` count, `week`, `weeks_remaining = max(0, reg_season_count - current_week)` when both are known else `None`, standings (rank/team/owner/record/PF/PA/`playoff_status` `qualified|eliminated`; empty list in championship mode), matchups (one row per `WeeklyGameResult`; opponent true diff from the `(team_name, opponent_name)` mirror lookup, `None` when absent; `margin`), `matchups_note` (`"No matchups this week"` or `None`), weekly challenges filtered on `challenge.division == division.name` and — in playoff/championship modes — `"position" in additional_info`
- [ ] Season challenges with `"historical": true` in playoff/championship modes; `playoffs` populated in playoff mode and `None` otherwise; `championship` populated in championship mode and `None` otherwise
- [ ] Never read `division.league_id`, credentials or the key
- [ ] `tests/test_ai_summary_digest.py`: regular (13 challenges, standings), playoff (bracket, 7 player highlights, team challenges absent), championship (leaderboard, empty standings), no-matchups league, no weekly data, `current_week is None` → `week` and `weeks_remaining` are `None` (with `matchups_note` driven by the matchups list), `reg_season_count is None` → `weeks_remaining is None`, mirror-row pairing present/absent, digest contains no league id and no planted marker
- [ ] `tests/test_ai_summary_digest.py`: **golden recursive key-set assertion** — one expected key set per level, compared against the built digest, so a renamed key fails even if the type checker is satisfied. The golden is **authored from FR-002's field list**, not captured from the builder; a snapshot would bless a wrong key

**Validation**: `pytest -q` green; digest serialises with `json.dumps`; `mypy` clean (a wrong key is a compile error).

**ACs**: AC-012 · FR-002

**Files**: new `services/ai_digest.py`, new `tests/test_ai_summary_digest.py`, `tests/ai_fakes.py` (fixture builders)

---

### Task 6: OpenAI-compatible client

**Goal**: one HTTP call, no retries, the spike's constraints, the error taxonomy, and a testable production transport.

- [ ] New `ff_tracker/services/ai_client.py`: `MAX_TOKENS = 8000`, `CONTRACT_REASON`, frozen `AIRequest(system_prompt, user_message, max_tokens=MAX_TOKENS)`, `AIClient` Protocol (`complete(request) -> str`), `HTTPTransport` Protocol (`__call__(request: urllib.request.Request, timeout: int) -> bytes`)
- [ ] `_urlopen(request: urllib.request.Request, timeout: int) -> bytes` — the production transport: `with urllib.request.urlopen(request, timeout=timeout) as response: return response.read()`
- [ ] `OpenAICompatibleClient(config, transport: HTTPTransport | None = None)` → `self._transport = transport or _urlopen`
- [ ] URL `base_url.rstrip("/") + "/chat/completions"`; headers `Authorization: Bearer`, `Content-Type: application/json`, non-default `User-Agent: ff-awards/<version>`
- [ ] Body `{model, messages: [system, user], max_tokens}`; no `response_format`, no temperature, no streaming
- [ ] `self._transport(request_obj, config.timeout)` inside `try/except`: `HTTPError` → `AIHTTPError` after reading **and discarding** the body; `URLError` with a timeout reason or `TimeoutError` → `AITimeoutError`; other `URLError` → `AITransportError`; envelope shape not as expected → `AIContractError` (explicit check, never a caught `TypeError`)
- [ ] `finish_reason == "length"` → `AITruncationError` even when the content parses
- [ ] Logging: INFO model/status/latency, DEBUG token counts — never key, request or response body; host via `urlsplit(base_url).hostname`; `HTTPError.filename` never read or logged
- [ ] `tests/test_ai_client.py` with `FakeTransport`: URL/headers/UA/body asserted; default vs override base URL (unset, empty, whitespace); each failure class → its reason; a 200 with `finish_reason=length` → truncation; a 401 → `HTTP 401 (model … at opencode.ai)` with no path in the message
- [ ] `tests/test_ai_client.py`: **`patch("urllib.request.urlopen")` test** — a `MagicMock` context manager returning canned bytes proves `_urlopen` passes `timeout=` as a keyword, calls `.read()`, and returns `bytes` (the production path no injected fake covers)
- [ ] `tests/test_ai_client.py`: **logging test (AC-006 client half)** — `caplog` at DEBUG, a fake transport returning a body containing a unique marker, plus a second case whose `HTTPError` body carries the same marker; assert no record at any level contains the API key, the marker, or any path segment of the configured URL. Assert against `record.getMessage()` so `%s`-interpolated arguments are examined, not just `record.args`

**Validation**: `pytest -q` green; no socket is opened by any test.

**ACs**: AC-004 · AC-005 · AC-007 · AC-010 · FR-003

**Files**: new `services/ai_client.py`, new `tests/test_ai_client.py`, `tests/ai_fakes.py`

---

## Phase 3 — Narrative

### Task 7: Summary service — prompt, request, parse, matching, normalisation, fail-open

**Goal**: the whole narrative path in one task (Gate 2 merged the old Tasks 7 and 8: the happy path cannot pass while matching or normalisation is a stub).

- [ ] New `ff_tracker/services/ai_summary_service.py`: `SYSTEM_PROMPT` constant (contract, caps, no-invented-facts, commissioner voice, 60-word floor as guidance), `INSTRUCTIONS_HEADING = "### COMMISSIONER'S INSTRUCTIONS"`
- [ ] `build_system_prompt(user_prompt)` appends the block only when non-empty; `prompt_sha(user_prompt)` = `sha256(template + "\n\x00\n" + prompt).hexdigest()[:12]`
- [ ] `AISummaryService(config, client)`; `generate(...) -> AISummaryResult` = `try: return self._generate(...) except AISummaryError as e: return AISummaryUnavailable(e.reason)`
- [ ] `_generate`: digest → `AIRequest` → `client.complete` → `_parse_response` → `_match_leagues` → `_normalise` → `AISummary`
- [ ] `_parse_response`: bind `json.loads` to `object`, narrow with `isinstance`; convert **only** `json.JSONDecodeError` to `AIContractError(CONTRACT_REASON)`; every other rejection is an explicit check raising `AIContractError` (no `except TypeError`/`ValueError`/`KeyError`, no `except Exception`)
- [ ] `_match_leagues` — FR-004's total order: (1) all names match exactly once after `strip().casefold()` and counts agree → map by name, emit in **digest order**; (2) else equal counts → zip by position, headings from `division.name`, response names discarded; (3) else `AIContractError(f"league count mismatch ({len(divisions)} leagues, {len(entries)} sections)")`
- [ ] `_normalise` — drop bullets beyond 3 → drop paragraphs beyond 3 → drop trailing paragraphs while `len(text.split())` total > 120, truncating the first paragraph at the last word boundary ≤120 with `…` when it alone exceeds the budget (dropping the rest) → headline ≤15 words, `season_note` ≤40 words, both word-boundary + `…`; `truncated` true when anything was dropped or shortened
- [ ] WARNING log with the reason only; DEBUG log of the composed system prompt; never the digest, request body, response body, key, team or owner names
- [ ] `tests/test_ai_summary_service.py` — request/contract:
      valid fake response → `AISummary` with provenance; `prompt_sha` stable and changing with the prompt; instructions block present only when the prompt is set; non-JSON / fenced / missing-key / empty-`paragraphs` → `AISummaryUnavailable` with the contract reason
- [ ] `tests/test_ai_summary_service.py` — **`test_generate_propagates_programming_errors`** (two cases, both must pass):
      (a) a digest builder stubbed to raise `AttributeError` makes `generate` **raise** — proves the outer catch is not `except Exception`;
      (b) `patch("ff_tracker.services.ai_summary_service.json.loads", side_effect=TypeError("bug"))` makes `generate` **raise** — proves `_parse_response` does not catch `TypeError`, which is the defect the first case alone would not detect (Gate 2 re-review M3)
- [ ] `tests/test_ai_summary_service.py` — matching: reordered entries, case/whitespace variants (AC-008 i); stray entry, duplicated entry, all-different names at equal counts → positional headings from our names, no response-supplied name visible (AC-008 ii); differing counts → the exact count-mismatch reason and nothing rendered (AC-008 iii)
- [ ] `tests/test_ai_summary_service.py` — normalisation: four paragraphs + 200-word paragraph + four bullets + 20-word headline + 60-word note → caps met, first paragraph and first three bullets survive, two runs byte-identical (AC-013); 200-word first paragraph → ≤120 words with `…` and the others dropped (AC-014); each drop/shorten sets `truncated` (AC-015)
- [ ] `tests/test_ai_summary_service.py` — logging: `caplog` shows the prompt at DEBUG and no digest marker, team name or key at any level (AC-006)

**Validation**: `pytest -q` green; no formatter can see `ai_summary` yet (nothing passes it).

**ACs**: AC-004 · AC-006 · AC-007 · AC-008 · AC-013 · AC-014 · AC-015 · AC-016 · FR-004 · FR-006 · FR-008 · FR-009 · FR-010

**Files**: new `services/ai_summary_service.py`, new `tests/test_ai_summary_service.py`, `tests/ai_fakes.py`

---

## Phase 4 — Rendering

### Task 8: `format_output` signature + JSON `ai_summary`

**Goal**: the protocol change and the one format that carries provenance.

- [ ] `display/base.py`: `ai_summary: AISummaryResult | None = None` on `OutputFormatter.format_output` (`:88`) **and** `BaseFormatter.format_output` (`:239`), last and defaulted; import the types from `..models`
- [ ] All five concrete `format_output` signatures gain the same parameter **in this task** — mypy rejects an override that omits a supertype parameter, so they must move together (only JSON renders yet)
- [ ] `display/json.py`: append `data["ai_summary"]` last when the argument is not `None` — `AISummary` → `{headline, season_note, leagues, provenance{model, prompt_sha, generated_at, truncated}}`; `AISummaryUnavailable` → `{"error": <notice>}`; `None` → key absent
- [ ] `tests/test_json_formatter.py`: narrative object shape and provenance values; error object; key absent when `None`; **AC-001 prefix/suffix**: parse both documents, drop `ai_summary` from the on-document, compare equal

**Byte-identical when off**: the parameter defaults to `None`, and the JSON key is only assigned when it is not `None`; with `None` the serialised document is unchanged, so existing JSON tests and AC-001 hold without touching any other branch.

**Validation**: `pytest -q` green; `mypy ff_tracker` clean (this is where a split signature would fail).

**ACs**: AC-001 (JSON) · AC-002 (JSON) · FR-005 · FR-008

**Files**: `display/base.py`, `display/json.py`, all five formatter signatures, `tests/test_json_formatter.py`

---

### Task 9: Console and markdown rendering

**Goal**: the two text formats.

- [ ] `display/console.py`: `_format_ai_summary` → separator rules + `🤖 COMMISSIONER'S TAKE (AI-GENERATED)`, headline, per-league name line, one line per paragraph (no wrapping), `• ` bullets, `Generated by <model> · AI-generated text`; appended at the end (after the trailing `📊 Game data:` line when present, which keeps its position — the insertion is an append, not a move); notice is one line in the same place
- [ ] `display/markdown.py`: `_format_ai_summary` → `## 🤖 Commissioner's Take (AI-generated)`, `### <league>`, paragraphs, `- ` bullets, `_Generated by <model> · AI-generated text_`; same append rule; notice one italic line; TOC untouched
- [ ] `tests/test_ai_summary_rendering.py`: AC-001 for both (prefix/suffix against the same input with `ai_summary=None`), AC-002 (section present, after the standings section, labelled), notice-only case, a paragraph with tab/newline/quotes/`<`/`&`/emoji stays one console line (AC-011)

**Byte-identical when off**: the block is appended only when the argument is not `None`; no separator, blank line or heading is added on the `None` path, so AC-001's suffix is the existing trailing content, byte for byte.

**Validation**: `pytest -q` green.

**ACs**: AC-001 · AC-002 · AC-011 · FR-005

**Files**: `display/console.py`, `display/markdown.py`, new `tests/test_ai_summary_rendering.py`

---

### Task 10: Sheets and email rendering

**Goal**: the two escaping-sensitive formats.

- [ ] `display/sheets.py`: blank row, `AI SUMMARY (AI-GENERATED)`, `HEADLINE:`, one `LEAGUE:` row per league, one row per paragraph, `- ` bullet rows, attribution row; every cell flattened (`\t`/`\r`/`\n` → space) so column counts never break; appended at the very end (sheets' `Game data:` line is mid-report, so the last section is the overall table)
- [ ] `display/email.py`: section before `<div class="footer">` — `<h2>🤖 Commissioner's Take (AI-generated)</h2>`, AI-generated marker, `<p>` paragraphs via `_escape_html`, `<ul><li>` bullets, attribution line; notice as a single `<p>`
- [ ] `tests/test_ai_summary_rendering.py`: AC-001 for both, AC-002, notice case, AC-011 (tab/newline/`"`/`<`/`&`/emoji: one sheet row with the right tab count, HTML-escaped in email, and the email section lands before the footer)
- [ ] `tests/test_ai_summary_rendering.py`: **AC-012 mode agreement** — parametrise over a playoff fixture and a championship fixture; for each, build the digest from the same inputs and assert `digest["mode"]` matches the mode marker the five outputs already emit (`FINAL REGULAR SEASON STANDINGS` for playoffs, `CHAMPIONSHIP WEEK` for championship, `report_type` in JSON). The assertion is about the digest's *filtering* agreeing with what the formatters render, not about re-deriving the predicate

**Byte-identical when off**: same `None` guard; email's footer block keeps its exact position and content, and sheets gains no trailing rows at all.

**Validation**: `pytest -q` green; the sheet output has a constant field count per row in the new block.

**ACs**: AC-001 · AC-002 · AC-011 · FR-005

**Files**: `display/sheets.py`, `display/email.py`, `tests/test_ai_summary_rendering.py`

---

## Phase 5 — Wiring

### Task 11: `main.py` wiring, `::warning::`, `--help` egress

**Goal**: one generation per run, every mode, every format.

- [ ] `main.py`: `ai_config = load_ai_summary_config()` — **after** `create_config(...)` (which loads `.env`) and before any ESPN call, inside the existing `try:`
- [ ] After weekly challenges, before the output branches: build `OpenAICompatibleClient(ai_config)` + `AISummaryService` and call `generate(...)` **once** when `ai_config.enabled`; otherwise `ai_summary = None`
- [ ] `print(f"::warning::{ai_summary.notice}")` when the result is `AISummaryUnavailable` and `os.environ.get("GITHUB_ACTIONS") == "true"`; nothing outside Actions
- [ ] Both `format_output(...)` call sites pass `ai_summary=ai_summary` (single-format and `--output-dir` branches)
- [ ] `create_parser()` epilog: an **AI Summary (optional)** paragraph — off by default; enabled by `AI_SUMMARY_API_KEY` plus `AI_SUMMARY_ENABLED`; the FR-009 egress sentence (team names, owner names and scores are sent to `AI_SUMMARY_BASE_URL`, the user prompt is sent verbatim, the key is never printed, `-vv` logs the system prompt so it must not be used in CI). **No variable table** — `.env.example` and the README own the list and defaults (Gate 2 cut)
- [ ] `tests/test_main_cli.py`: with a patched `AISummaryService`, one call for 1/3/10 leagues and one call in `--output-dir` mode (AC-003); `GITHUB_ACTIONS=true` + failure → exactly one `::warning::` line, exit 0; unset → no `::warning::` (AC-004); `ConfigurationError` from the loader → exit 1, no report, zero service calls (AC-009); `--help` contains the egress wording and no credential values

**Validation**: `pytest -q` green. This is the first task where a real run can render the section; feature-off output must still equal today's byte for byte (AC-001 re-run for all five).

**ACs**: AC-001 · AC-003 · AC-004 · AC-009 · AC-012 · FR-001 · FR-006 · FR-009

**Files**: `main.py`, `tests/test_main_cli.py`, `tests/ai_fakes.py`

---

## Phase 6 — Ops And Docs

### Task 12: Weekly workflow guard

**Goal**: a checkout without the key produces a normal report (FR-007), and the flag cannot be in an `if:`.

- [ ] `.github/workflows/weekly-report.yml`: job-level `env:` gains `AI_SUMMARY_ENABLED: ${{ secrets.AI_SUMMARY_API_KEY != '' }}` and the committed `AI_SUMMARY_USER_PROMPT: |` block scalar (empty by default). The explanatory comment sits on a `#` line **above** `AI_SUMMARY_USER_PROMPT:`, never inside the block scalar — anything inside it is literal prompt text, would be sent to the provider, and would change `prompt_sha`
- [ ] **No `AI_SUMMARY_MODEL`** (or base URL / timeout / cap) in the workflow — those come from repository settings or the code defaults, so the workflow cannot pin a model that drifts from `config.py` (Gate 2 cut). The user prompt stays because it is content, not a setting
- [ ] "Create .env file from secrets" step: append `AI_SUMMARY_ENABLED=true` and `AI_SUMMARY_API_KEY=…` **only** inside `if [ "$AI_SUMMARY_ENABLED" = "true" ]; then … fi`
- [ ] No `if:` anywhere in the file references `AI_SUMMARY_ENABLED`
- [ ] Test (static, no YAML dependency — string assertions on the file): the expression exists and references `secrets.AI_SUMMARY_API_KEY`; the `.env` appends are inside the guard; no `if:` mentions the flag; `AI_SUMMARY_MODEL` is absent

**Validation**: `pytest -q` green. The other two workflows are untouched.

**ACs**: WC-001 · FR-007

**Files**: `.github/workflows/weekly-report.yml`, new `tests/test_ai_summary_config_workflow.py`

---

### Task 13: Documentation

**Goal**: an operator can enable the feature, understand the egress, and find the defaults without reading code.

- [ ] `.env.example`: the seven variables, commented, with real defaults and the egress note
- [ ] `README.md` → Configuration: "AI Summary (optional)" — what leaves the machine, key-only enablement, `ff-championship`/`ff-season-recap` unaffected, `.env` multi-line quoting and the Actions `env:` block scalar
- [ ] `CHANGELOG.md`: `## [Unreleased]` → `### Added - AI Summary (optional)`
- [ ] **No `AGENTS.md` change** (Gate 2 cut): no FR requires it, and a fourth copy of the description in the file every agent reads is drift, not documentation
- [ ] No `--help` change here (Task 11 ships it with the code it documents)

**Validation**: `pytest -q` green; `README`/`.env.example` names match `config.py` exactly (no typo'd variable can pass review).

**ACs**: FR-009 (documented egress) · Configuration table (defaults published)

**Files**: `.env.example`, `README.md`, `CHANGELOG.md`

---

## Success Criteria Checklist

- [ ] All 17 ACs covered by an offline test (task list above), plus WC-001 statically
- [ ] Feature off: five formats byte-identical, zero calls, no notice, no warning (AC-001)
- [ ] Feature on: section in all five formats, last, labelled, before the format footer (AC-002/FR-005)
- [ ] One provider call per run across 1/3/10 leagues and `--output-dir` (AC-003)
- [ ] Every failure path: full report, exit 0, one notice, one `::warning::` under Actions (AC-004)
- [ ] No key, request body, response body or endpoint path in any artefact (AC-005)
- [ ] `test_generate_propagates_programming_errors` exists and passes; the production `_urlopen` path is covered by a patched-`urlopen` test
- [ ] The digest's recursive key set is asserted against a golden
- [ ] `ruff`, `mypy`, `pytest` clean after every task; zero new mypy errors (baseline is 0 on this branch)
- [ ] No new dependency; no network in the suite
- [ ] LV-001…LV-004 run manually once against the live provider before release

---

## Estimated Effort

| Phase | Tasks | Estimate |
|---|---|---|
| 1 — Groundwork | 1–4 | 3–4 h |
| 2 — Payload & provider | 5–6 | 3–4 h |
| 3 — Narrative | 7 | 4–5 h |
| 4 — Rendering | 8–10 | 3–4 h |
| 5 — Wiring | 11 | 1–2 h |
| 6 — Ops & docs | 12–13 | 1 h |

**Total**: 15–20 h of implementation, plus one live-provider pass (LV-001…004) that cannot be automated in the suite.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-10-21 | AI Agent | Initial 14-task breakdown, one AC map per task, signature-ordering constraint recorded |
| 1.1 | 2026-10-21 | AI Agent | Gate 2 revisions: old Tasks 7 and 8 merged into one narrative task (13 total, renumbered); Task 7 gains `test_generate_propagates_programming_errors` and the `JSONDecodeError`-only parse rule; Task 5 adopts `TypedDict` plus a golden recursive key-set test; Task 6 corrects the transport to `_urlopen(request, timeout) -> bytes` and adds the `patch("urllib.request.urlopen")` test; Task 4 adds the `.env`-only ordering test; Task 1 uses `int \| None = None`; Task 11's `--help` reduces to the egress paragraph; Task 12 drops `AI_SUMMARY_MODEL`; Task 13 drops `AGENTS.md` |
