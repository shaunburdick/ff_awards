# Implementation Tasks: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: v2.5 — Gate 2 closed; Phase A may start (v2.3 records a behaviour change already in code; v2.4 adds T211, read-only memory; v2.5 corrects the memory-setting counts)
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-28
> **Version**: 2.5
> **Plan**: [plan.md](./plan.md) v2.5
> **Spec**: [spec.md](./spec.md) v0.29

**Tasks 1–13 are shipped — read them as context, not as instructions.** Where a line disagrees with
the code, the code wins. Three shipped tasks were corrected in place so an engineer cannot follow
them into a regression — **Task 4** (the settings, including `AI_SUMMARY_MAX_TOKENS` and
`AI_SUMMARY_REASONING_EFFORT`), **Task 6** (no hard-coded budget; `reasoning_effort` omitted when
unset) and **Task 12** (`AI_SUMMARY_MODEL` is forwarded from `vars.*`, not absent) — and the two
purely historical ones are marked here:

- **Task 1** (`reg_season_count`) and **Task 8** (`ai_summary` on `format_output`) are **already in the code**; treat them as descriptions of what exists.
- The shipped defaults are `deepseek-v4.1-flash`, 8000 tokens, 120 s and `https://opencode.ai/inference/openai/v1`; nothing below pins a different one.

Two phases follow, each its own engineer pass and each revertable alone:

- **Phase A** — spec Phase 1, season history and the league-wide view: **T101–T103, T105, T106 (5 tasks)**.
- **Phase B** — spec Phase 2, the memory log: **T201–T208, T210 (9 tasks)**, planned against a **merged** Phase A.

Both are inside the ~15-task ceiling for a single pass. T104 was folded into T103 and T209 into T210,
so the phase ids keep their old numbers and the gaps are deliberate.

---

## Task Execution Guidelines

- Complete tasks in order; each task names the spec AC ids it satisfies.
- Run the three checks after every task, not only at the end.
- A task that changes a formatter signature must state how output stays byte-identical when `ai_summary is None` (AC-001).
- No new dependency. No network in tests: `FakeAIClient` / `FakeTransport` / `FakeMemoryStore` only, plus the one `patch("urllib.request.urlopen")` test of the provider transport, the store's own small equivalent, and the checked-in golden.
- If a task needs a decision the plan does not record, stop and raise it rather than inventing behaviour.
- **Phase boundaries**: Phase B does not start until Phase A is merged. No Phase B task changes a Phase A behaviour; reverting B leaves A's digest, prompt rules and golden intact.

### Dependency map

**Phase A** — `T101` is independent of both. `T103` requires `T102`: it calls `rank_overall_teams`, which T102 creates, so the two cannot be done in either order. `T105` requires `T101` (it counts the weeks in the history block). `T106` requires all four and is last.

**Phase B** — `T201`, `T202` and `T203` are independent. `T204` requires `T201`, `T202`, `T203`. `T205` requires `T202` and `T204` (the block renders what the session read). `T206` requires `T204` and `T205`. `T207` requires `T206`. `T208` requires `T206` and reads the golden committed by `T106`. `T210` is independent and last only because nothing depends on it. `T211` (read-only memory) requires `T201` and `T204`; it is independent of `T205`–`T210` but ships after them so the doc paragraphs it edits exist.

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
- [ ] `AIProvenance.__post_init__`: model/prompt_sha/generated_at non-empty; `truncated` defaults `False`; `attempts` defaults `1` and must be 1 or 2
- [ ] `AISummaryUnavailable.reason` non-empty; `notice` property returns `AI summary unavailable: {reason}. The report is unaffected.`
- [ ] `AISummaryResult = Union[AISummary, AISummaryUnavailable]` — `typing.Union`, not `X | Y` (runtime alias on py3.9)
- [ ] Export all of the above from `models/__init__.py` (`__all__`)
- [ ] `tests/test_ai_summary_models.py`: valid construction, each rejection, `notice` text, `truncated` default

**Validation**: `pytest -q` green; `mypy ff_tracker` clean.

**ACs**: AC-002 (JSON shape) · AC-013/AC-015 (`truncated`) · AC-022 (`attempts: 1`) · FR-004 · FR-008

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

### Task 4: AI configuration  *(shipped — corrected to the shape that shipped)*

**Goal**: the AI settings, validated, beside `FFTrackerConfig`, loaded the same way as the existing settings.

- [ ] `ff_tracker/config.py`: frozen `AISummaryConfig` — `enabled`, `api_key` (`field(default="", repr=False)`), `base_url`, `model`, `timeout`, `max_tokens`, `reasoning_effort` (`str | None`), `max_prompt_chars`, `user_prompt`
- [ ] `__post_init__`: enabled → non-empty key naming `AI_SUMMARY_API_KEY`; `timeout > 0`; `max_tokens > 0`; `max_prompt_chars > 0`; base URL an `http(s)` URL with a host; `reasoning_effort` blank normalised to `None`, otherwise in `low|medium|high`; `len(user_prompt) <= max_prompt_chars` with variable + actual length + configured limit
- [ ] `load_ai_summary_config() -> AISummaryConfig`: **calls `load_environment()` first** (it only runs inside `create_config` otherwise); `AI_SUMMARY_ENABLED` in `{true,1,yes,on,false,0,no,off}` (case-insensitive, default false); `TIMEOUT`/`MAX_TOKENS`/`MAX_PROMPT_CHARS` via `int()` with `ConfigurationError` naming the variable and its value; base URL default `https://opencode.ai/inference/openai/v1` for unset/empty/whitespace and trailing `/` stripped; model `.strip()` with default `deepseek-v4.1-flash`; `REASONING_EFFORT` lowercased, empty → `None`; user prompt CRLF→LF then `strip()`
- [ ] While the feature is off the loader returns the disabled default after reading **only** the flag (FR-007's single exception is the flag itself)
- [ ] `tests/test_config.py`: new class covering AC-009 and AC-017 (missing key, bad flag value, non-numeric/zero timeout, non-positive budget, non-positive/non-integer limit, bad reasoning effort, oversized prompt names the **configured** limit, unset/empty/whitespace prompt accepted, defaults)
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
- [ ] Per league: name, `teams` count, `week`, `weeks_remaining = max(0, reg_season_count - current_week)` when both are known else `None`, standings (rank/team/owner/record/PF/PA/`playoff_status` `in_playoff_position|outside_playoff_position`; empty list in championship mode) and `standings_note` (the field is the current top-four cutoff position and not a final outcome; `None` when the standings list is empty), matchups (one row per `WeeklyGameResult`; opponent true diff from the `(team_name, opponent_name)` mirror lookup, `None` when absent; `margin`), `matchups_note` (`"No matchups this week"` or `None`), weekly challenges filtered on `challenge.division == division.name` and — in playoff/championship modes — `"position" in additional_info`
- [ ] Season challenges with `"historical": true` in playoff/championship modes; `playoffs` populated in playoff mode and `None` otherwise; `championship` populated in championship mode and `None` otherwise
- [ ] Never read `division.league_id`, credentials or the key
- [ ] `tests/test_ai_summary_digest.py`: regular (13 challenges, standings), playoff (bracket, 7 player highlights, team challenges absent), championship (leaderboard, empty standings), no-matchups league, no weekly data, `current_week is None` → `week` and `weeks_remaining` are `None` (with `matchups_note` driven by the matchups list), `reg_season_count is None` → `weeks_remaining is None`, mirror-row pairing present/absent, digest contains no league id and no planted marker
- [ ] `tests/test_ai_summary_digest.py`: **golden recursive key-set assertion** — one expected key set per level, compared against the built digest, so a renamed key fails even if the type checker is satisfied. The golden is **authored from FR-002's field list**, not captured from the builder; a snapshot would bless a wrong key

**Validation**: `pytest -q` green; digest serialises with `json.dumps`; `mypy` clean (a wrong key is a compile error).

**ACs**: AC-012 · FR-002

**Files**: new `services/ai_digest.py`, new `tests/test_ai_summary_digest.py`, `tests/ai_fakes.py` (fixture builders)

---

### Task 6: OpenAI-compatible client  *(shipped — corrected to the shape that shipped)*

**Goal**: one HTTP call, no retries, the spike's constraints, the error taxonomy, and a testable production transport.

- [ ] New `ff_tracker/services/ai_client.py`: `CONTRACT_REASON`, `USER_AGENT = f"ff-awards/{version('ff-awards')}"`, frozen `AIRequest(system_prompt, user_message, max_tokens, reasoning_effort=None)` — **no default on `max_tokens`**: the configured budget is its only source — `AIClient` Protocol (`complete(request) -> str`), `HTTPTransport` Protocol (`__call__(request: urllib.request.Request, timeout: int) -> bytes`)
- [ ] `_urlopen(request: urllib.request.Request, timeout: int) -> bytes` — the production transport: `with urllib.request.urlopen(request, timeout=timeout) as response: return response.read()`
- [ ] `OpenAICompatibleClient(config, transport: HTTPTransport | None = None)` → `self._transport = transport or _urlopen`
- [ ] URL `base_url.rstrip("/") + "/chat/completions"`; headers `Authorization: Bearer`, `Content-Type: application/json`, non-default `User-Agent: ff-awards/<version>`
- [ ] Body `{model, messages: [system, user], max_tokens}` plus `reasoning_effort` **only when it is set**; no `response_format`, no temperature, no streaming. There is no `MAX_TOKENS` constant: the value is `config.max_tokens` on every call (FR-003, AC-010)
- [ ] `self._transport(request_obj, config.timeout)` inside `try/except`: `HTTPError` → `AIHTTPError` after reading **and discarding** the body; `URLError` with a timeout reason or `TimeoutError` → `AITimeoutError`; other `URLError` → `AITransportError`; a mid-body `(OSError, http.client.HTTPException)` → `AITransportError`; envelope shape not as expected → `AIContractError` (explicit check, never a caught `TypeError`)
- [ ] `finish_reason == "length"` → `AITruncationError` even when the content parses
- [ ] Logging: INFO model/status/latency, DEBUG token counts — never key, request or response body; host via `urlsplit(base_url).hostname`; `HTTPError.filename` never read or logged
- [ ] `tests/test_ai_client.py` with `FakeTransport`: URL/headers/UA/body asserted; `max_tokens` and `reasoning_effort` come from configuration (absent when unset, present when set, and changing either variable changes the request); default vs override base URL (unset, empty, whitespace); each failure class → its reason; a 200 with `finish_reason=length` → truncation; a 401 → `HTTP 401 (model … at opencode.ai)` with no path in the message
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
- [ ] `build_system_prompt(user_prompt, league_names)` appends (a) the league scope built from the digest at request time — exact count, names verbatim, "exactly N entries, in that order, no add/duplicate/split/rename" — and (b) the block only when non-empty; `prompt_sha(system_prompt, user_prompt)` = `sha256(composed + "\n\x00\n" + user_prompt).hexdigest()[:12]`, so the league scope is part of the hash
- [ ] `AISummaryService(config, client)`; `generate(...) -> AISummaryResult` = `try: return self._generate(...) except AISummaryError as e: return AISummaryUnavailable(e.reason)`
- [ ] `_generate`: digest → `AIRequest` → `client.complete` → `_parse_response` → `_match_leagues` → `_normalise` → `AISummary`
- [ ] `_generate` retry: at most **two** attempts, looping around client+parse+match, catching **only** `AIContractError`; the second attempt reuses the same `AIRequest` object (same prompt, payload, model, budget); a second contract failure re-raises into the fail-open boundary; `AIHTTPError`/`AITransportError`/`AITimeoutError`/`AITruncationError` are never retried
- [ ] `_normalise(..., attempts)` writes `attempts` into `AIProvenance` (1 or 2)
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
- [ ] `tests/test_ai_summary_service.py` — prompt: the scope states "exactly N leagues" and the quoted names from the digest; a different league set changes the sentence and `prompt_sha`; no scope for an empty league list
- [ ] `tests/test_ai_summary_service.py` — **retry** (AC-019…AC-022): invalid-then-valid → 2 calls, `attempts: 2`, byte-identical requests; invalid twice → 2 calls and the notice; HTTP 500 / transport / timeout / truncation → 1 call each; first-attempt success → `attempts: 1`
- [ ] `tests/test_ai_summary_service.py` — logging: `caplog` shows the prompt at DEBUG and no digest marker, team name, score or key at any level (AC-006)

**Validation**: `pytest -q` green; no formatter can see `ai_summary` yet (nothing passes it).

**ACs**: AC-004 · AC-006 · AC-007 · AC-008 · AC-013 · AC-014 · AC-015 · AC-016 · AC-019 · AC-020 · AC-021 · AC-022 · FR-003 · FR-004 · FR-006 · FR-008 · FR-009 · FR-010

**Files**: new `services/ai_summary_service.py`, new `tests/test_ai_summary_service.py`, `tests/ai_fakes.py`

---

## Phase 4 — Rendering

### Task 8: `format_output` signature + JSON `ai_summary`

**Goal**: the protocol change and the one format that carries provenance.

- [ ] `display/base.py`: `ai_summary: AISummaryResult | None = None` on `OutputFormatter.format_output` (`:88`) **and** `BaseFormatter.format_output` (`:239`), last and defaulted; import the types from `..models`
- [ ] All five concrete `format_output` signatures gain the same parameter **in this task** — mypy rejects an override that omits a supertype parameter, so they must move together (only JSON renders yet)
- [ ] `display/json.py`: top-level `data["ai_summary"]` when the argument is not `None` (position unchanged; JSON has no order-sensitive slot) — `AISummary` → `{headline, season_note, leagues, provenance{model, prompt_sha, generated_at, truncated, attempts}}`; `AISummaryUnavailable` → `{"error": <notice>}`; `None` → key absent
- [ ] `tests/test_json_formatter.py`: narrative object shape and provenance values; error object; key absent when `None`; **AC-001 prefix/suffix**: parse both documents, drop `ai_summary` from the on-document, compare equal

**Byte-identical when off**: the parameter defaults to `None`, and the JSON key is only assigned when it is not `None`; with `None` the serialised document is unchanged, so existing JSON tests and AC-001 hold without touching any other branch.

**Validation**: `pytest -q` green; `mypy ff_tracker` clean (this is where a split signature would fail).

**ACs**: AC-001 (JSON) · AC-002 (JSON) · FR-005 · FR-008

**Files**: `display/base.py`, `display/json.py`, all five formatter signatures, `tests/test_json_formatter.py`

---

### Task 9: Console and markdown rendering

**Goal**: the two text formats.

- [ ] `display/console.py`: `_format_ai_summary` → separator rules + `🤖 COMMISSIONER'S TAKE (AI-GENERATED)`, headline, per-league name line, one line per paragraph (no wrapping), `• ` bullets, `Generated by <model> · AI-generated text`; inserted **after the weekly highlights and before the season-long challenges** (FR-005 v0.12); notice is one line in that same slot
- [ ] `display/markdown.py`: `_format_ai_summary` → `## 🤖 Commissioner's Take (AI-generated)`, `### <league>`, paragraphs, `- ` bullets, `_Generated by <model> · AI-generated text_`; inserted after the weekly highlight sections and before the season challenges; notice one italic line in the same slot; TOC untouched
- [ ] `tests/test_ai_summary_rendering.py`: AC-001 for both (prefix/suffix against the same input with `ai_summary=None`), AC-002 (section present, after the standings section, labelled), notice-only case, a paragraph with tab/newline/quotes/`<`/`&`/emoji stays one console line (AC-011)

**Byte-identical when off**: the block is appended only when the argument is not `None`; no separator, blank line or heading is added on the `None` path, so AC-001's suffix is the existing trailing content, byte for byte.

**Validation**: `pytest -q` green.

**ACs**: AC-001 · AC-002 · AC-011 · AC-018 · FR-005

**Files**: `display/console.py`, `display/markdown.py`, new `tests/test_ai_summary_rendering.py`

---

### Task 10: Sheets and email rendering

**Goal**: the two escaping-sensitive formats.

- [ ] `display/sheets.py`: blank row, `AI SUMMARY (AI-GENERATED)`, `HEADLINE:`, one `LEAGUE:` row per league, one row per paragraph, `- ` bullet rows, attribution row; every cell flattened (`\t`/`\r`/`\n` → space) so column counts never break; inserted after the weekly challenge rows and before the season-challenge rows
- [ ] `display/email.py`: section after the weekly-highlight `<div>` and before the season challenges — `<h2>🤖 Commissioner's Take (AI-generated)</h2>`, AI-generated marker, `<p>` paragraphs via `_escape_html`, `<ul><li>` bullets, attribution line; notice as a single `<p>` in the same slot
- [ ] `tests/test_ai_summary_rendering.py`: AC-001 for both, AC-002, notice case, AC-011 (tab/newline/`"`/`<`/`&`/emoji: one sheet row with the right tab count, HTML-escaped in email, and the email section lands before the season challenges)
- [ ] `tests/test_ai_summary_rendering.py`: **AC-012 mode agreement** — parametrise over a playoff fixture and a championship fixture; for each, build the digest from the same inputs and assert `digest["mode"]` matches the mode marker the five outputs already emit (`FINAL REGULAR SEASON STANDINGS` for playoffs, `CHAMPIONSHIP WEEK` for championship, `report_type` in JSON). The assertion is about the digest's *filtering* agreeing with what the formatters render, not about re-deriving the predicate

**Byte-identical when off**: same `None` guard; email's footer block keeps its exact position and content, and sheets gains no trailing rows at all.

**Validation**: `pytest -q` green; the sheet output has a constant field count per row in the new block.

**ACs**: AC-001 · AC-002 · AC-011 · AC-018 · FR-005

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

### Task 12: Weekly workflow guard  *(shipped — the model line corrected)*

**Goal**: a checkout without the key produces a normal report (FR-007), and the flag cannot be in an `if:`.

- [ ] `.github/workflows/weekly-report.yml`: workflow-level `env:` gains `AI_SUMMARY_ENABLED: ${{ secrets.AI_SUMMARY_API_KEY != '' }}` plus `AI_SUMMARY_BASE_URL`, `AI_SUMMARY_MODEL`, `AI_SUMMARY_TIMEOUT`, `AI_SUMMARY_MAX_TOKENS`, `AI_SUMMARY_REASONING_EFFORT` and `AI_SUMMARY_MAX_PROMPT_CHARS` from `vars.*`; the report step's own `env:` gains `AI_SUMMARY_USER_PROMPT: ${{ vars.AI_SUMMARY_USER_PROMPT || secrets.AI_SUMMARY_USER_PROMPT }}`, since a secret prompt must not reach checkout or the setup steps. No shell guards: an unset variable renders empty and means the default. These settings are never written to `.env` — the writer handles `LEAGUE_IDS`, the ESPN cookies and `AI_SUMMARY_ENABLED`/`AI_SUMMARY_API_KEY` only. Every explanatory comment sits on a `#` line above its key
- [ ] **No literal model, base URL, timeout or cap in the workflow**: each comes from `vars.*`, so the file cannot pin a value that drifts from `config.py` (Gate 2's cut). `AI_SUMMARY_MODEL` **is** forwarded — `${{ vars.AI_SUMMARY_MODEL }}` — which is what shipped and what the workflow test asserts; the rule was never "the key is absent", it was "no constant in this file". The user prompt stays because it is content, not a setting
- [ ] "Create .env file from secrets" step: append `AI_SUMMARY_ENABLED=true` and `AI_SUMMARY_API_KEY=…` **only** inside `if [ "$AI_SUMMARY_ENABLED" = "true" ]; then … fi`
- [ ] No `if:` anywhere in the file references `AI_SUMMARY_ENABLED`
- [ ] Test (static, no YAML dependency — string assertions on the file): the expression exists and references `secrets.AI_SUMMARY_API_KEY`; the `.env` appends are inside the guard; no `if:` mentions the flag; every optional setting is a `vars.*`/`secrets.*` expression rather than a literal

**Validation**: `pytest -q` green. The other two workflows are untouched.

**ACs**: WC-001 · FR-007

**Files**: `.github/workflows/weekly-report.yml`, new `tests/test_ai_summary_config_workflow.py`

---

### Task 13: Documentation

**Goal**: an operator can enable the feature, understand the egress, and find the defaults without reading code.

- [ ] `.env.example`: the shipped settings, commented, with real defaults (`https://opencode.ai/inference/openai/v1`, `deepseek-v4.1-flash`, `120`, `8000`, an unset `AI_SUMMARY_REASONING_EFFORT`) and the egress note
- [ ] `README.md` → Configuration: "AI Summary (optional)" — what leaves the machine, key-only enablement, `ff-championship`/`ff-season-recap` unaffected, the repository-variable settings, the prompt as a variable **or** a secret (never both; a whitespace-only variable shadows the secret), and multi-line prompts via `gh … --body "$(cat prompt.txt)"`
- [ ] `CHANGELOG.md`: `## [Unreleased]` → `### Added - AI Summary (optional)`
- [ ] **No `AGENTS.md` change** (Gate 2 cut): no FR requires it, and a fourth copy of the description in the file every agent reads is drift, not documentation
- [ ] No `--help` change here (Task 11 ships it with the code it documents)

**Validation**: `pytest -q` green; `README`/`.env.example` names match `config.py` exactly (no typo'd variable can pass review).

**ACs**: FR-009 (documented egress) · Configuration table (defaults published)

**Files**: `.env.example`, `README.md`, `CHANGELOG.md`

---

## Phase A — Season history and the league-wide view (spec Phase 1)

> Five tasks. Plan Decisions 9–12 and 17. Each leaves the suite green; none renders anything.

### Task T101: The `history` block per league

**Deliverable**: FR-011's per-league history block, built from `DivisionData.games` with the newest week anchored on the standings.

- [ ] New `ff_tracker/services/ai_history.py`: the `TypedDict`s from plan Component 13 and `build_history(games, teams, anchor) -> AILeagueHistory | None`
- [ ] `weeks_included` = distinct `week` values ascending; `None` for a league with no games
- [ ] `rank_by_week` = one row per week present. Weeks before the newest are recomputed: wins descending, then points for descending, over that team's games with `week <= N`, ties keeping the anchor's relative order. The newest week takes the anchor's rank **verbatim** — that is the whole point of the anchor (FR-011, ledger B7)
- [ ] `head_to_head` = one row per opponent met (`opponent`, `wins`, `losses`), sorted by opponent name; `streak` = the run ending at that team's latest game; `scoring_trend` = latest score against the mean of the team's earlier weeks (`up` above +1.0, `down` below −1.0, `flat` inside, `None` under two weeks); `best_week`/`worst_week` = `{week, score}`; `average_margin` = signed mean of `score - opponent_score`; `largest_win`/`largest_loss` = magnitudes, `None` where the team has not won or not lost
- [ ] A team with no game in `games` carries `None` for `streak`, `best_week`, `worst_week` and `average_margin` (plan Decision 12); a tie counts as a loss, because `GameResult.won` is `score > opponent_score`
- [ ] `services/ai_digest.py`: `AILeagueDigest` gains `history: AILeagueHistory | None`; `_league_digest` computes `rows = _standings_rows(division)` once and passes it as the anchor, so the anchor is the same list the `standings` key uses
- [ ] `tests/test_ai_summary_history.py`: AC-024 in full — one fixture per `scoring_trend` value, each naming the number it beats; the **second fixture whose `games` is missing a week the standings count**, proving the newest column does not move; `largest_loss: null` for an unbeaten team; magnitudes and the signed mean asserted as values
- [ ] `tests/test_ai_summary_history.py`: AC-025 — no games → `"history": null`; one week → one `weeks_included` entry, `streak` length 1 and `scoring_trend: null` for every team; the block is present in the regular, playoff and championship fixtures
- [ ] `tests/test_ai_summary_digest.py`: `EXPECTED_KEYS` gains `history` on the league and the block's own key sets, authored from FR-011 rather than captured

**Validation**: `uv run pytest tests/test_ai_summary_history.py tests/test_ai_summary_digest.py -q`, `uv run ruff check .`, `uv run mypy ff_tracker`.

**ACs**: AC-024 · AC-025 · AC-026 (key set) · FR-011

**Files**: new `services/ai_history.py`, new `tests/test_ai_summary_history.py`, `services/ai_digest.py`, `tests/test_ai_summary_digest.py`, `tests/ai_fakes.py` (multi-week game builders)

**Done when**: the two test files pass and `git diff --name-only` lists exactly the five files above.

---

### Task T102: One comparator, shared with the formatters

**Deliverable**: `rank_overall_teams` as the only ordering expression in the codebase, called by both the formatters and the digest.

- [ ] New `ff_tracker/services/rankings.py`: `rank_overall_teams(divisions, limit=None) -> list[TeamStats]` — wins descending then points for descending, `limit=None` or `<= 0` meaning every team (today's semantics exactly)
- [ ] `display/base.py`: both `_get_overall_top_teams` and `_get_sorted_teams_by_division` keep their signatures, docstrings and `limit` semantics and become delegates (the second is the same comparator over one division); the four `limit=20`/`max_teams` call sites (`console.py:442`, `markdown.py:433`, `sheets.py:212`, `email.py:481`) are **not touched**
- [ ] `services/ai_digest.py:_standings_rows` calls `rank_overall_teams([division])`, so the per-league standings and the overall table provably use one rule
- [ ] Tests, on two fixtures rather than one: `limit=None` returns every team, `limit=20` truncates, `limit=0` returns every team (the comparator's own fixtures). Then, on a three-division fixture of **fewer than 20 teams**, the console's rendered overall table equals `overall_standings` row for row in rank order. The >20-team agreement case is T103's, because there the console truncates at 20 and the comparison is the rendered 20 against the first 20
- [ ] State in the test's docstring what the agreement case does and does not prove: both sides now call `rank_overall_teams`, so it guards the *rendering* order (that no formatter re-sorts or reads another collection), not the comparator's correctness — that is the `limit` fixtures' job
- [ ] `season_recap_*` formatters keep their own copies of this sort: that path is outside spec 009 and is not touched
- [ ] No formatter test is edited: if one fails, the delegate is wrong, not the test

**Validation**: `uv run pytest -q` (whole suite, unchanged elsewhere), `uv run mypy ff_tracker`.

**ACs**: AC-027 (ordering) · AC-001 (unchanged formatter output) · FR-012

**Files**: new `services/rankings.py`, `display/base.py`, `services/ai_digest.py`, `tests/test_ai_summary_digest.py` (comparator and order cases)

**Done when**: `grep -rn "points_for), reverse=True" ff_tracker/services/ai_digest.py ff_tracker/services/ai_history.py ff_tracker/services/rankings.py ff_tracker/display/base.py ff_tracker/display/console.py ff_tracker/display/markdown.py ff_tracker/display/sheets.py ff_tracker/display/email.py ff_tracker/display/json.py` prints exactly one line, in `services/rankings.py`, and the full suite passes with no formatter test modified.

---

### Task T103: `overall_standings`, `weekly_extremes`, and the two league-wide prompt rules

**Deliverable**: FR-012's two digest keys and the two rules that keep the model from reading a division rank as an overall one. (Absorbs the former T104: same two files, same test run, and the rules are meaningless without the block they describe.)

- [ ] `services/ai_digest.py`: `AIOverallStandingRow` (`rank`, `team`, `division`, `record`, `points_for`) and `AIWeeklyExtremes` (`highest_score`, `lowest_score`, `biggest_win`, `closest_game`); `AIDigest` gains `overall_standings: list[AIOverallStandingRow] | None` and `weekly_extremes: AIWeeklyExtremes | None`
- [ ] `overall_standings` = `rank_overall_teams(divisions)` with **no limit** (every team, past the console's 20), `rank` 1-based, `division` = `team.division`, `record` = `wins-losses`, `points_for` = `team.points_for`; `None` when no division has a completed game
- [ ] `weekly_extremes` from every division's `weekly_games`: `{team, division, score}` for highest and lowest, `{team, division, opponent, margin}` for biggest win (won rows only) and closest game; closest picks the winning row of a tie, as `WeeklyChallengeCalculator._calculate_closest_game` does; `None` when there are no weekly rows
- [ ] `services/ai_summary_service.py`: `LEAGUE_WIDE_RULES: tuple[str, str]` — an overall claim may come only from the league-wide block, and a division's `rank` is a division rank (not the best record in the setup); `build_system_prompt` appends them **inside the hashed region**, after `SYSTEM_PROMPT`, whose own bytes are untouched
- [ ] Tests (AC-027), each case on its own fixture: a three-division fixture whose highest score, biggest margin and closest game each come from a different division, and the winner of each agrees with that division's weekly challenge winner where they coincide; **on a fixture of more than 20 teams** the console's rendered overall table — which stops at 20 — equals the first 20 rows of `overall_standings`, while `overall_standings` itself carries every team; a single-division fixture yields that division's teams in the standings order, with `rank`, `record` and `points_for` matching its standings; a no-games fixture sends `null` for both and still makes exactly one provider call
- [ ] Prompt-rule tests in `tests/test_ai_summary_service.py`: each constant appears verbatim in the composed prompt in the regular, playoff and championship fixtures, and monkeypatching one constant changes `prompt_sha` (the rule is inside the hash). The test asserts on the **constants**, never on a copied sentence
- [ ] `tests/test_ai_summary_digest.py`: `EXPECTED_KEYS` gains the two keys and their nested sets
- [ ] In playoff and championship modes `weekly_extremes` is `null` (the digest carries no weekly rows there) and `overall_standings` is still present

**Validation**: `uv run pytest tests/test_ai_summary_digest.py tests/test_ai_summary_service.py -q`, `uv run mypy ff_tracker`.

**ACs**: AC-026 (key set) · AC-027 · FR-012

**Files**: `services/ai_digest.py`, `services/ai_summary_service.py`, `tests/test_ai_summary_digest.py`, `tests/test_ai_summary_service.py`, `tests/ai_fakes.py` (three-division and >20-team fixtures)

**Done when**: both test files pass, the >20-team case and the "every team appears" case are separate tests, and `grep -n "LEAGUE_WIDE_RULES" tests/test_ai_summary_service.py` shows only imports and assertions, no prompt text.

---

### Task T105: `provenance.history_weeks`

**Deliverable**: the one output-visible field Phase 1 adds.

- [ ] `models/ai_summary.py`: `AIProvenance.history_weeks: int = 0`, validated `>= 0`; the memory fields are not added in this phase
- [ ] `services/ai_digest.py`: `history_week_count(digest) -> int` = the size of the union of every league's `weeks_included`, `0` when no league has a game
- [ ] `services/ai_summary_service.py`: `_normalise` records the count in provenance
- [ ] `display/json.py`: `provenance` carries `history_weeks` on every narrative; the notice object still carries no provenance
- [ ] Tests: `0` for a no-games fixture; the union count where two leagues' weeks overlap (a `[1,2,3]` and a `[2,3,4]` fixture must yield `4`, not `6`); JSON provenance's key set is exactly the FR-008 five plus `history_weeks`; the notice path has no `provenance` key

**Validation**: `uv run pytest tests/test_ai_summary_models.py tests/test_json_formatter.py tests/test_ai_summary_service.py -q`.

**ACs**: AC-026 (only `history_weeks` differs in JSON) · FR-005 · FR-008

**Files**: `models/ai_summary.py`, `services/ai_digest.py`, `services/ai_summary_service.py`, `display/json.py`, `tests/test_ai_summary_models.py`, `tests/test_json_formatter.py`, `tests/test_ai_summary_service.py`

**Done when**: those three test files pass and the JSON provenance key-set assertion fails when any sixth key is added (spot-check, then revert).

---

### Task T106: Capture the Phase-1 golden

**Deliverable**: `tests/fixtures/ai_summary_phase1_golden.json`, committed, that Phase 2's AC-028 will compare against.

- [ ] Run the whole path once through `main()` and commit the five outputs. The full patch set is: `sys.argv` (the run is invoked as `--output-dir <tmp>` with the pinned flags), the league ids (`create_config`/`parse_league_ids_from_arg` unpatched but driven from the patched argv, or `create_config` patched — pick one and use the same in T208), `ff_tracker.main.ESPNService` with the AC-027 three-division fixture, `ff_tracker.main.OpenAICompatibleClient` with a fake returning one canned response, and the `datetime` **attribute on `ff_tracker.services.ai_summary_service`** — the module imports the class, so replacing `datetime.datetime` globally would leak into every other check in the process
- [ ] Pin the rest (plan Decision 17): `AI_SUMMARY_MODEL` at the golden's id, `AI_SUMMARY_USER_PROMPT` empty, `year=2026`, week 6, no format args
- [ ] Keep the harness in one place: T208 runs the same `main()` call with the same patches, so the two phases compare identical paths rather than two re-implementations of one
- [ ] Golden shape: one JSON object with `console`, `sheets`, `email`, `markdown` as exact strings and `json` as the parsed document (dict equality, so indentation cannot fake a pass)
- [ ] The comparison test in `tests/test_ai_summary_rendering.py` **reads only**; the capture is a throwaway command, not a module the test imports, and no helper regenerates the file
- [ ] Review the golden as a diff before committing, line by line as output: it is the reference Phase 2 is judged against, so a wrong value committed here is blessed for two phases

**Recapture procedure** (the only accepted way to change the file after this task):

1. Regenerate with the harness at the commit whose output is being captured, and commit it alone, with the reason in the commit message — never in the same commit as a behaviour change.
2. A recapture must still prove the criterion: the four text formats render the same deterministic sections and the same narrative as the golden's own copy of them, so the diff is read as output, not accepted as a blob.
3. **May break it**: a deliberate change to a rendered format, to the report data shown, or to `SYSTEM_PROMPT`/`LEAGUE_WIDE_RULES` (which moves `prompt_sha`). **May not**: anything memory-related — that is the failure mode to name. AC-028 goes red, and a recapture blesses the memory regression the criterion exists to catch.

**Validation**: `uv run pytest tests/test_ai_summary_rendering.py -q` on a clean tree.

**ACs**: AC-026 (five formats byte-identical) · AC-001 (re-asserted) · prerequisite for AC-028

**Files**: new `tests/fixtures/ai_summary_phase1_golden.json`, `tests/test_ai_summary_rendering.py`

**Done when**: `git ls-files tests/fixtures/ai_summary_phase1_golden.json` prints the path, the comparison test passes, deleting one character from the golden makes it fail (spot-check, then restore), and the recapture procedure above is quoted in the commit message or the PR body so the next engineer finds it.

---

## Phase B — The memory log (spec Phase 2)

> Nine tasks, planned against a **merged** Phase A. Plan Decisions 13–16. Off by default throughout: until T206, every task's tests run with memory off and the Phase-1 golden still passes.

### Task T201: Memory configuration

**Deliverable**: `AI_MEMORY_*` validated inside the enabled branch, and inert when the feature is off.

- [ ] `config.py`: frozen `AIMemoryConfig(enabled, gist_id, gist_token: str = field(repr=False))`; `AISummaryConfig.memory: AIMemoryConfig | None = None`
- [ ] `load_ai_summary_config`: read `AI_MEMORY_*` **only** after the enabled branch is taken — the existing early return already guarantees no memory variable can deny a report while the feature is off
- [ ] `AI_MEMORY_ENABLED` accepts the same eight values, case-insensitive; anything else is a `ConfigurationError`; blank or `false` means `memory is None`
- [ ] Memory on with a missing or empty `AI_MEMORY_GIST_ID` or `AI_MEMORY_GIST_TOKEN` → `ConfigurationError` naming that variable; there are no defaults for either, and a blank value is the missing-value error, never a fallback
- [ ] The token keeps its whitespace exactly as `AI_SUMMARY_API_KEY` does, and never appears in a repr or a message
- [ ] `tests/test_config.py`: a `TestMemoryConfig` class covering each bullet, plus "a malformed memory variable with the feature off is ignored" and "the token's value is absent from `repr(config)`"

**Validation**: `uv run pytest tests/test_config.py -q`.

**ACs**: AC-033 (config half) · FR-007 · FR-013

**Files**: `config.py`, `tests/test_config.py`

**Done when**: `uv run pytest tests/test_config.py::TestMemoryConfig -q` reports a passing class and `uv run mypy ff_tracker` is clean.

---

### Task T202: The archive: shape, structural read, and the merge

**Deliverable**: `memory.json` parsed on structure alone and merged by week, with no way for its content to make it read-only.

- [ ] New `services/ai_memory.py`: `MemoryLeague`, `MemoryEntry`, `MemoryFile` `TypedDict`s exactly as plan Component 15
- [ ] `parse_archive(raw: bytes) -> MemoryFile | None`: `None` only when the bytes do not parse **as the archive shape** — not JSON, not an object, `schema != 1`, a `season` that is not a four-digit int, `entries` not a list, an entry missing a required key or carrying a wrong type, a `week` that is not an int in 1–18. Content, entry or summary counts and any text length are never reasons to reject a file, and unknown keys are carried through
- [ ] `merge_entry(archive, entry, season) -> MemoryFile`: create `{schema: 1, season}` when there is none; otherwise replace the entry whose `week` equals the new one **in place** and append otherwise, then order by `week`. Nothing else is touched, reordered or dropped
- [ ] Tests: a round trip asserted against an **authored** expected document, not a recomputation; unparseable bytes, a wrong `schema`, a `week` of 0 or 19 and a missing key each give `None`; a file with 20 entries and one with extra fields are accepted; a same-week merge leaves every other entry unchanged in value; a merge into a 20-entry file keeps all 20 plus the new week when it is new
- [ ] **An entry carrying a key the tool does not know survives a successful merge-and-save unchanged in value** — merge, serialise, re-parse, and compare that entry's value (canonical form, since the whole file is written by the tool) against the parsed original, so nothing it does not understand is silently dropped
- [ ] Tests assert the write path never rewrites the file's `season` header: a merge into a 2025 file with a 2026 run keeps `season: 2025`

**Validation**: `uv run pytest tests/test_ai_memory.py -q`, `uv run mypy ff_tracker`.

**ACs**: AC-029 (entry contents) · AC-032 (same-week replacement) · AC-033 (unparseable, extra fields, over-long text) · FR-014

**Files**: new `services/ai_memory.py`, new `tests/test_ai_memory.py`

**Done when**: `tests/test_ai_memory.py` passes and the round-trip test's expected JSON is a string literal in the test file.

---

### Task T203: The gist store

**Deliverable**: one read and one write against one gist over stdlib `urllib`, with the token never in a message.

- [ ] **Premise first, manually, once**: one `curl` against a scratch gist — `GET /gists/{id}` and a `PATCH` adding `memory.json` — with the two responses pasted into the **PR description**. Do not build on the assumed shape without doing it; do not commit the responses (no `research.md`, no fixture: they are evidence for a reviewer, not something the code or the suite reads). **This step is manual and not in the suite.**
- [ ] `exceptions.py`: `AIMemoryStoreError(Exception)` with `kind: str` (`auth`, `not_found`, `server`, `transport`, `timeout`) and a reason naming the host and status only — deriving from `Exception`, not `FFTrackerError`, so an escaped one cannot read as a configuration error
- [ ] `services/ai_memory.py`: `MemoryStore` Protocol (`load() -> bytes | None`, `save(data: bytes) -> None`); a module-private transport wrapper `(urllib.request.Request, int) -> bytes` shaped like the provider client's `_urlopen`, the store's own — `services/ai_client.py` is shipped and is **not edited**; `GistMemoryStore(memory_config, transport=None)`
- [ ] `load()`: `GET https://api.github.com/gists/{id}` → `None` when the status is 404 or `files` has no `memory.json`; otherwise the file's `content` encoded as UTF-8. `save()`: `PATCH` the same URL with `{"files": {"memory.json": {"content": <json text>}}}`
- [ ] Headers: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, a non-default `User-Agent`; socket read bounded by `AI_SUMMARY_TIMEOUT`; no retries, no streaming
- [ ] Every failure maps to a kind: 401/403 → `auth`, 404 → `not_found`, other 4xx/5xx → `server`, `URLError` → `transport`, a timeout (including mid-body `OSError`/`HTTPException`) → `transport`/`timeout`. No message, log line or `repr` carries the token or the gist id
- [ ] `tests/ai_fakes.py`: `FakeMemoryStore` (records calls, fails per call, holds an in-memory archive) and gist fixtures built with the existing `FakeTransport`
- [ ] Tests: URL, method, header, and that the PATCH body carries only the `files` object; each status → kind; the store's own wrapper driven through `patch("urllib.request.urlopen")` and returning bytes (the production path no fake covers); a `caplog` sweep at DEBUG shows no token, no gist id, no archive text

**Validation**: `uv run pytest tests/test_ai_memory.py -q`; no socket opened.

**ACs**: AC-005 (token and messages) · AC-031 · AC-032 · FR-009 · FR-013

**Files**: new `services/ai_memory.py`, `exceptions.py`, `tests/ai_fakes.py`, `tests/test_ai_memory.py`

**Done when**: `tests/test_ai_memory.py` passes, `git diff --name-only` does not list `ff_tracker/services/ai_client.py`, and the PR body carries both `curl` responses.

---

### Task T204: `MemorySession` and FR-014's status map

**Deliverable**: one object per run that performs the read and the write, maps every outcome to a status, and never raises.

- [ ] `services/ai_memory.py`: `MEMORY_READ_OK/NONE/FAILED`, `MEMORY_WRITE_OK/FAILED/SKIPPED`; `MemorySession(memory_config, season, week, store=None)` with `open()`, `commit(summary)`, `read_status`, `write_status`, `entries`, `weeks`, `warnings`
- [ ] `open()`: at most one `load()`; bytes → `parse_archive` → `"ok"` with entries and weeks, or `"none"` plus **one** warning when the file will not parse (and `parsed` stays false, so `commit` will not write); `None` → `"none"` with no warning; `auth` → `"failed"` with one warning naming authentication; a read `not_found` → `"none"`, which is not a failure and does not suppress the write; `server`/`transport`/`timeout` → `"failed"` with **no** warning. Every `"failed"` read is what suppresses the write in `commit`
- [ ] `commit(summary)`: **`read_status == "failed"` → `"skipped"` with no store call and the store untouched** (the merge cannot preserve what it never read); `_can_key_entry(season, week)` (`2000–9999`, `1–18`) false → `"skipped"` with no store call; no entry to write (narrative unavailable) → `"skipped"`; the file failed to parse → `"skipped"` with no store call and the bytes untouched; `save()` success → `"ok"`; any store failure → `"failed"` with exactly one warning naming scope or authentication where identifiable. Order the checks so the failed-read case is the first one and cannot be reached with a stale archive
- [ ] It catches `AIMemoryStoreError` and nothing else, so a programming error escapes and fails the run loudly (Article III, and the same rule Decision 1 applies to the narrative)
- [ ] Entries and weeks are ordered by week; `weeks` is what will be reported as `memory_weeks`
- [ ] Tests, one case per cell of the plan's "Phase 2 failure policy" table: statuses, warning counts (exactly one, or zero), the pre-kickoff `week=0` and `week=None` cases with **zero** store calls, **a failed read of each kind (auth, 5xx, transport, timeout) asserting `write_status: "skipped"`, zero `save()` calls and the store bytes unchanged**, and one test that a store raising `AttributeError` propagates

**Validation**: `uv run pytest tests/test_ai_memory.py -q`.

**ACs**: AC-031 (every read failure records `"skipped"` and warns once for authentication or not at all) · AC-032 (write failures after a readable archive) · AC-033 (warn once, file untouched) · FR-014

**Files**: `services/ai_memory.py`, `tests/test_ai_memory.py`

**Done when**: `tests/test_ai_memory.py` passes and every row of the plan's failure-policy table has a named test that fails if its status or warning count changes — including one test per read-failure kind asserting zero saves.

---

### Task T205: The memory block, and the DEBUG line that redacts it

**Deliverable**: the archive in the prompt under two rules, with `prompt_sha` unmoved.

- [ ] `services/ai_summary_service.py`: `MEMORY_HEADING = "### MEMORY"`, `MEMORY_INTRO` (the archive is what you published in earlier weeks), `MEMORY_RULES: tuple[str, str]` — quotation (a record of its own reports, never a source of league fact; this week's data wins on any disagreement) and continuation (a running bit escalates or retires; repeating it in the same words is the failure)
- [ ] `build_memory_block(entries)` renders every entry in week order, each under its week tag, then the two rules; `render_memory_block(entries, redact=True)` replaces each entry's prose with its week tag
- [ ] Composition per plan Decision 15: `instructions = build_system_prompt(...)`, `system_prompt = instructions + "\n\n" + block`, `prompt_sha = prompt_sha(instructions)`; `AIRequest.system_prompt` is the composed string
- [ ] The DEBUG line logs `instructions` plus the **redacted** block, so the archive's shape is visible and its prose is not (FR-009)
- [ ] Tests: with six stored weeks, the block carries all six under their tags in week order and both rule constants appear (asserted on the constants, never on a copied sentence); **a stored paragraph longer than any cap appears verbatim in the composed block** — no truncation, no ellipsis, no reflow — which is AC-033's "sent into the prompt as written" and fails if anything ever starts trimming the archive; `prompt_sha` equals the hash of the instructions alone, with and without a block, so memory cannot move it; no block and no rule text when memory is off or the read was `"none"`; `caplog` at DEBUG contains the week tags and none of the stored prose, at any level

**Validation**: `uv run pytest tests/test_ai_summary_service.py -q`.

**ACs**: AC-028 (no block when off, prompt unchanged) · AC-030 (every entry, order, intro) · AC-033 (an over-long stored paragraph reaches the prompt as written) · AC-006 (redacted DEBUG line) · FR-003 · FR-004 · FR-008 · FR-009

**Files**: `services/ai_summary_service.py`, `tests/test_ai_summary_service.py`

**Done when**: the service tests pass, the over-long-paragraph assertion compares the stored text itself against the composed block, and the DEBUG-line test fails if the redaction is removed (spot-check by making `redact=False` locally, then revert).

---

### Task T206: Service lifecycle and the three provenance fields

**Deliverable**: read before generation, write after an accepted narrative, and memory's statuses in the JSON — absent when memory is off.

- [ ] `AISummaryService.__init__(config, client, memory: MemorySession | None = None)`
- [ ] `_generate`: `memory.open()` first, then the block, then the client call. **`memory.commit(summary)` runs only after `_normalise` has returned an `AISummary`** — the entry's `generated_at` must equal the rendered `provenance.generated_at`, so `_normalise` computes the instant once and `commit` copies it from the summary; nothing re-reads the clock
- [ ] `models/ai_summary.py`: `memory_read: str | None`, `memory_write: str | None`, `memory_weeks: list[int] | None`, validated all-`None` or all-set against `ai_memory`'s vocabularies; all four provenance fields exist only on the narrative path
- [ ] `display/json.py`: each memory key emitted only when it is not `None`
- [ ] Tests: an absent file and an empty gist each give `"none"`, `[]`, one read and one write, and a written entry whose `week`, `generated_at`, `headline`, `season_note` and every league's paragraphs and bullets match the rendered narrative — with `generated_at` asserted **equal to** `provenance.generated_at`, which is the regression B2 was about (AC-029); six prior weeks give `"ok"`, `[1,2,3,4,5,6]`, one provider call, no memory field in the response, and a section identical to the no-archive run (AC-030); a failed narrative performs **no write** and records `write_status: "skipped"` on the session, asserted as the store's call count with no assertion on JSON (the notice object carries no provenance)
- [ ] **Backfill proof in a fresh subprocess**, because `ff_tracker/__init__.py` imports `.main` and every services import loads it — so "main was never imported" is not assertable and not the constraint. The test writes a small entry-point script into `tmp_path`, runs it with `sys.executable` and the repo root on `PYTHONPATH`, and the script: replaces `ff_tracker.main.main` with a raiser; builds `create_config(league_ids=…, year=…, week=<the week>)` and `load_ai_summary_config()`; drives `ESPNService` (or a stubbed loader for the fixture), `MemorySession(memory, season, week, store=<inline file-backed fake>)` and `AISummaryService(...).generate(...)` with an inline fake client; writes the resulting narrative and provenance to a JSON file. Assert: the run exits 0, **stdout is empty**, the store file holds exactly one entry for that week with a matching `generated_at`, the result file shows a produced summary, and the raiser was never hit. This is "callable outside the CLI" as behaviour — no CLI invocation and no printing — which is what the throwaway backfill script needs
- [ ] The same test runs the entry point twice, as two separate subprocesses (week 5, then week 6), and asserts the archive grew by exactly one entry each time — so the loop the backfill script will use is proven once

**Validation**: `uv run pytest tests/test_ai_summary_service.py -q`.

**ACs**: AC-028 (no memory keys when off) · AC-029 · AC-030 · AC-032 (`skipped`) · FR-005 · FR-014 · the "Not doing" build constraint

**Files**: `services/ai_summary_service.py`, `models/ai_summary.py`, `display/json.py`, `tests/test_ai_summary_service.py`

**Done when**: the service tests pass, the written archive is asserted against an authored document, and the subprocess test asserts `stdout == ""`, exactly one store write for the week, and exit 0 — the three things that make "callable outside the CLI" true rather than an import-shape claim.

---

### Task T207: `main.py` wiring, the warnings, and the call counts

**Deliverable**: memory on in the CLI, its warnings printed once each, exit 0 always.

- [ ] `main.py`: when `ai_config.memory is not None`, build `MemorySession(ai_config.memory, config.year, espn_service.current_week)` (store defaulting to `GistMemoryStore`) and pass it to `AISummaryService`
- [ ] After generation, print each entry of `session.warnings` as `::warning::{line}` when `os.environ.get("GITHUB_ACTIONS") == "true"`, and nothing otherwise; the existing narrative-warning path is unchanged and can co-exist (one line per cause)
- [ ] Both `format_output` call sites keep passing `ai_summary=ai_summary`; nothing else about the report path changes
- [ ] Tests in `tests/test_main_cli.py`. The **count** assertions run the real service with `ff_tracker.main.OpenAICompatibleClient` and `ff_tracker.main.GistMemoryStore` patched to a fake client and a fake store, so the numbers are the ones production would make: one provider call, exactly one store read and **at most** one store write for 1/3/10 leagues and in `--output-dir` mode — at most one because a failed read suppresses the write; memory off → zero store calls; exit 0 in every failure case. The existing `AISummaryService`-patched tests keep asserting one `generate` call per run (AC-003's "one logical call")
- [ ] **Warning counts, exact and per cause**: a 401/403 read → `out.count("::warning::") == 1` and **zero `save()` calls**, because the failed read suppresses the write and there is no second cause to report; a 5xx, transport error or timeout on the read → `== 0` and zero saves; a failed write after a readable archive → `== 1`; a file that will not parse → `== 1` and zero saves; memory off → `== 0`. The same fixtures with `GITHUB_ACTIONS` unset print no `::warning::` at all
- [ ] A `ConfigurationError` from the loader → exit 1, no report, zero provider calls, zero store calls

**Validation**: `uv run pytest tests/test_main_cli.py -q`.

**ACs**: AC-003 (memory counts) · AC-004 (exit 0 preserved) · AC-009 (unchanged) · AC-031 (read failures and the suppressed write) · AC-032 (write failures after a successful read) · AC-033 (warn once) · FR-006 · FR-014

**Files**: `main.py`, `tests/test_main_cli.py`, `tests/ai_fakes.py`

**Done when**: `tests/test_main_cli.py` passes, every warning assertion is an exact count rather than a substring check, and each read-failure fixture asserts zero saves as well as its line count.

---

### Task T208: AC-028 — memory off against the Phase-1 golden

**Deliverable**: the one test that proves Phase 2 changes nothing when it is off.

- [ ] In `tests/test_ai_summary_rendering.py`, run the T106 harness with `AI_MEMORY_ENABLED` unset and again with it explicitly `false`, `ff_tracker.main.GistMemoryStore` patched to a `FakeMemoryStore`: the store records **zero** calls, the prompt the fake client received contains no block heading, and the JSON document has no `memory_read`, `memory_write` or `memory_weeks` key
- [ ] The four text formats and the JSON document equal `tests/fixtures/ai_summary_phase1_golden.json` exactly, with `AI_SUMMARY_MODEL` set to the golden's model and `generated_at` frozen to the golden's instant
- [ ] A second, memory-on run over the same fixture renders the same section text as the golden's narrative (the archive changes the prompt, not the render)
- [ ] The test reads the fixture and never writes it

**Validation**: `uv run pytest tests/test_ai_summary_rendering.py -q`; `git diff --exit-code tests/fixtures/` after a full run.

**ACs**: AC-028 · AC-001 (re-asserted) · AC-030 (renders identically with an archive)

**Files**: `tests/test_ai_summary_rendering.py`, `tests/ai_fakes.py`

**Done when**: the test passes, `git status --porcelain tests/fixtures/` is empty after the run, and it fails if a memory key is emitted while memory is off (spot-check, then revert).

---

### Task T210: The memory guard in the workflow, and what an operator needs to know

**Deliverable**: a checkout without the gist settings ships a normal report, and the person who owns the gist knows what it holds, how to turn it on, and how to retire it. (Absorbs the former T209: the guard and the documentation exist for the same reader and fail the same way — an operator who cannot enable memory in CI without breaking the weekly report.)

- [ ] `.github/workflows/weekly-report.yml`, workflow-level `env:`: `AI_MEMORY_ENABLED: ${{ secrets.AI_MEMORY_GIST_TOKEN != '' && vars.AI_MEMORY_GIST_ID != '' }}` — the literal `true`/`false`, referenced by the loader and never by an `if:`
- [ ] On the "Generate fantasy football report" step's `env:` only: `AI_MEMORY_GIST_ID: ${{ vars.AI_MEMORY_GIST_ID }}` and `AI_MEMORY_GIST_TOKEN: ${{ secrets.AI_MEMORY_GIST_TOKEN }}` — the token must not reach checkout or the setup steps, and none of the three is written to `.env`
- [ ] Every explanatory comment sits on a `#` line above its key; no `if:` in the file references `AI_MEMORY_ENABLED`
- [ ] `tests/test_ai_summary_config_workflow.py`: static string assertions — the expression exists and names both contexts, the two settings are forwarded on the report step, the flag appears on no `if:` line, and no memory value is appended to `.env`
- [ ] `.env.example`: the memory settings commented, with `AI_MEMORY_GIST_ID` from a repository variable, `AI_MEMORY_GIST_TOKEN` from a secret, the token's scope (Gists read and write, or classic `gist`), and one line saying a secret gist is unlisted rather than private
- [ ] `README.md` → the AI Summary section: what memory is (a log of published summaries, one entry per week), what it never contains (standings, scores, the prompt, credentials), that off is the default, that the file is `memory.json`, that seeding past weeks is `--week N` runs rather than a feature (the throwaway script is the owner's, not the repo's), and — plainly — **that a season's file must be retired at a season boundary**: entries are keyed by week alone, so a Week 6 run in the next season would replace the previous season's Week 6 entry, a hand edit included
- [ ] `CHANGELOG.md`: `### Added` under `## [Unreleased]`
- [ ] No code change and no `--help` change in this task

**Validation**: `uv run pytest tests/test_ai_summary_config_workflow.py -q` and `uv run pytest -q` unchanged; every `AI_MEMORY_*` name in the docs exists in `config.py` and every one in `config.py` appears in the docs.

**ACs**: WC-002 · FR-007 · FR-013 (Configuration) — the docs half has no automated criterion; the reader is the operator who has to enable and retire it

**Files**: `.github/workflows/weekly-report.yml`, `tests/test_ai_summary_config_workflow.py`, `.env.example`, `README.md`, `CHANGELOG.md`

**Done when**: the workflow test passes, `grep -n "AI_MEMORY" .github/workflows/weekly-report.yml` prints the expression, two step-level forwards and no `if:` line, `grep -oh "AI_MEMORY_[A-Z_]*" README.md .env.example ff_tracker/config.py | sort -u | wc -l` is 4, and the README states the season-boundary retirement.

---

### Task T211: Read-only memory — `AI_MEMORY_WRITE`

**Deliverable**: a run that uses the archive and does not update it, so the owner's dispatch tests cannot advance it.

- [ ] `config.py`: `AIMemoryConfig.write: bool = True`, parsed from `AI_MEMORY_WRITE` inside `_parse_memory_config` with the same boolean routine; blank means the default, a malformed non-blank value is a `ConfigurationError` naming the variable (only reachable when memory is on)
- [ ] `services/ai_memory.py`: `commit` records `MEMORY_WRITE_SKIPPED` and returns before the season/week guard when `write` is false — no store call, no warning
- [ ] The read is untouched: `open()` runs, the block reaches the prompt, `memory_read` and `memory_weeks` are whatever the read produced
- [ ] `.github/workflows/weekly-report.yml`: a `workflow_dispatch` boolean `update_memory` (default `true`) forwarded to `AI_MEMORY_WRITE` on the report step through a plain expression — empty on a schedule renders blank, which the loader reads as the default; no `||` fallback, which would swallow a deliberate false
- [ ] `.env.example`: one commented line beside the memory variables; `README.md`: one short paragraph in the AI Memory section on test runs, why they matter and that scheduled runs always write
- [ ] Tests: config (default, explicit false, blank, malformed, ignored when memory is off); the session writes nothing and reports `skipped` with no warning while still reading the entries; the service's provenance (`memory_read: "ok"`, `memory_weeks` populated, `memory_write: "skipped"`); the CLI prints no `::warning::` with `GITHUB_ACTIONS` set or unset; the five formats match a writing run, the JSON apart from `provenance.memory_write`; a static workflow check that the input exists, is a boolean defaulting to true and reaches the env
- [ ] No change to backfill, to the prompt, or to how memory is read

**Validation**: `uv run pytest tests/test_config.py tests/test_ai_memory.py tests/test_ai_summary_service.py tests/test_ai_summary_rendering.py tests/test_main_cli.py tests/test_ai_summary_config_workflow.py -q`, `uv run mypy .`

**ACs**: AC-034 · FR-014 · FR-007

**Files**: `config.py`, `services/ai_memory.py`, `.github/workflows/weekly-report.yml`, `.env.example`, `README.md`, `tests/test_config.py`, `tests/test_ai_memory.py`, `tests/test_ai_summary_service.py`, `tests/test_ai_summary_rendering.py`, `tests/test_main_cli.py`, `tests/test_ai_summary_config_workflow.py`

**Done when**: the six test files pass, `grep -n "AI_MEMORY_WRITE" .github/workflows/weekly-report.yml` shows the one step-level forward and no `||`, and the README paragraph explains the dispatch test run.

---

## Traceability

Every criterion in spec v0.26 maps to at least one task, clause by clause — including the review's wordings (AC-027's single-division case, the four provenance fields on the narrative path only, FR-011's nulls, FR-014's read 404, season keying and archive-shape parse, AC-031's read-404 case, AC-033's write guard and its over-long-paragraph clause, AC-032's value-identity). "Shipped" tasks are 1–13 in this file; `T1xx`/`T2xx` are the amendment. **LV** rows and T203's gist premise are manual and cannot be covered by a task; they are listed so their absence from the suite is a decision, not an oversight.

| Criterion | Task(s) | Notes |
|---|---|---|
| AC-001 | 8, 9, 10, 11 · T102, T106, T208 | prefix/suffix per format; re-asserted at each phase boundary |
| AC-002 | 7, 8, 9, 10 | shipped |
| AC-003 | 11 · T207 | memory counts added in T207: 1 provider call, 1 read, ≤1 write, every league count and both output modes |
| AC-004 | 7, 11 | shipped; T207 re-asserts exit 0 with memory failing |
| AC-005 | 3, 6, 7, 11 · T203 | gist token added to the never-printed set in T203 |
| AC-006 | 6, 7 · T205 | archive block redacted to week tags in the DEBUG line |
| AC-007 | 6, 7 | shipped |
| AC-008 | 7 | shipped |
| AC-009 | 4, 11 | shipped; unchanged by both phases |
| AC-010 | 4, 6, 7 | shipped |
| AC-011 | 9, 10 | shipped |
| AC-012 | 5, 10, 11 | mode coverage re-asserted in AC-025 (T101, T103) |
| AC-013 | 7 | shipped |
| AC-014 | 7 | shipped |
| AC-015 | 7 | shipped |
| AC-016 | 7 | shipped |
| AC-017 | 4 | shipped |
| AC-018 | 9, 10 | shipped; neither phase moves it |
| AC-019 | 7 | shipped |
| AC-020 | 7 | shipped; T206 re-uses the failed narrative for `"skipped"` |
| AC-021 | 7 | shipped |
| AC-022 | 7 | shipped |
| AC-023 | 10 | shipped; email untouched by both phases |
| AC-024 | T101 | one fixture per `scoring_trend` value; second fixture proves the anchor |
| AC-025 | T101, T103 | no-games and one-week cases; present in all three modes; one provider call |
| AC-026 | T101, T102, T103, T105, T106 | three keys only, five formats byte-identical, JSON differs by `history_weeks`, feature-off re-asserted |
| AC-027 | T102, T103 | one comparator; the agreement case on a <20-team fixture and the first-20 comparison on a >20-team one; every team; three-division extremes; single division (same teams, order, `rank`/`record`/`points_for`); no games; the two prompt rules (T103) |
| AC-028 | T106 (capture) · T205, T206, T208 | memory off compared against the committed golden; a memory-caused failure is never reconciled by recapturing |
| AC-029 | T202, T206 | absent file and empty gist; entry contents, including `generated_at` equal to `provenance.generated_at` |
| AC-030 | T203, T205, T206, T208 | six prior weeks; prompt contents; no gist id, token or league id in the body |
| AC-031 | T203, T204, T207 | read outcomes and their warning counts, the read 404 → `"none"` case, and **`"skipped"` with an untouched store on every failed read** |
| AC-032 | T202, T203, T204, T206, T207 | write outcomes after a readable archive, the read-404's failed write (its read is `"none"`, not a failure), and same-week replacement |
| AC-033 | T201, T202, T204, **T205**, T207 | parse-as-the-archive-shape failure (T202), unknown keys and over-long text read unchanged (T202), the over-long paragraph reaching the composed prompt as written (T205), the `week`/`season` write guard (T204, T207), missing settings (T201) |
| AC-034 | T211 | read-only memory: one read, zero writes, `"skipped"`, no warning, formats unchanged; the static half covers the `update_memory` input |
| WC-001 | 12 | shipped |
| WC-002 | T210 | static YAML assertions (folded with the documentation) |
| LV-001 | manual | one live three-league run at defaults; **not a task** |
| LV-002 | manual | unavailable model id → notice names status; **not a task** |
| LV-003 | manual | `AI_SUMMARY_TIMEOUT=1` → timeout notice; **not a task** |
| LV-004 | manual | playoff week: no individual players named; **not a task** |
| LV-005 | manual | live gist: write, same-week re-run replaces, a hand edit survives both; **not a task** |
| LV-006 | manual | both phases on, full-season archive, one call; **not a task** |
| T203's gist premise | manual | one `curl` against a scratch gist, once; the two responses live in the PR description; **not a task, not in the suite** |

**Build constraint (not an AC)**: "generating a given week's summary and appending it to the archive must be callable outside the CLI" (spec, Not doing) is carried by T206's subprocess test — a process that calls `ESPNService`, `MemorySession` and `AISummaryService` with a `(season, week)` override, makes no CLI invocation and prints nothing. `ff_tracker/__init__.py` imports `.main`, so the assertion is behavioural by necessity. Rejected as a separate task: it would test the same path twice.

---

## Success Criteria Checklist

**Shipped feature (tasks 1–13)**

- [ ] All 17 ACs covered by an offline test (task list above), plus WC-001 statically
- [ ] Feature off: five formats byte-identical, zero calls, no notice, no warning (AC-001)
- [ ] Feature on: section in all five formats, after the weekly highlights and before the season challenges (AC-002/AC-018/FR-005); JSON keeps its top-level key
- [ ] One provider call per run across 1/3/10 leagues and `--output-dir` in the normal case, at most one contract retry (AC-003/AC-019)
- [ ] Every failure path: full report, exit 0, one notice, one `::warning::` under Actions (AC-004)
- [ ] No key, request body, response body or endpoint path in any artefact (AC-005)
- [ ] `test_generate_propagates_programming_errors` exists and passes; the provider client's production `_urlopen` path is covered by a patched-`urlopen` test
- [ ] The digest's recursive key set is asserted against a golden
- [ ] `ruff`, `mypy`, `pytest` clean after every task; zero new mypy errors (baseline is 0 on this branch)
- [ ] No new dependency; no network in the suite
- [ ] LV-001…LV-004 run manually once against the live provider before release

**Phase A (T101–T103, T105, T106)**

- [ ] The digest carries exactly three new keys and nothing else: `history` per league, `overall_standings`, `weekly_extremes` (AC-026)
- [ ] The newest `rank_by_week` column equals the digest's `standings[]`, proved on a fixture whose `games` is short a week (AC-024)
- [ ] `overall_standings` is every team in the console table's order; on a >20-team fixture the console's 20 rows match its first 20; `weekly_extremes` agrees with the per-division winners where they overlap (AC-027)
- [ ] One comparator: the weekly report's path has one `(wins, points_for)` sort, in `services/rankings.py` (Decision 10)
- [ ] Both league-wide prompt rules are constants inside the hashed instructions, and the tests assert the constants rather than a sentence (AC-027)
- [ ] JSON differs from a pre-Phase-1 run by `provenance.history_weeks` alone; all five formats byte-identical (AC-026)
- [ ] The golden is committed by T106, no test can regenerate it, and its recapture procedure is written down (AC-028's prerequisite)

**Phase B (T201–T208, T210)**

- [ ] Memory off: zero store calls, no block in the prompt, no memory key in JSON, five formats equal the Phase-1 golden (AC-028)
- [ ] A same-week re-run leaves one entry for that week; every other entry unchanged, including one carrying an unknown key (AC-032, LV-005)
- [ ] A pre-kickoff run (`week` 0/None) writes nothing and makes zero store calls (AC-033's write guard)
- [ ] `memory_read` / `memory_write` / `memory_weeks` exist only when a narrative renders (FR-005)
- [ ] A read 404 is `"none"`, so its write is attempted and fails per AC-032; **any other read failure records `"skipped"`, makes no store call and leaves the store unchanged**; a read failure never appears in any format; a 401/403 read warns once, a 5xx/transport/timeout read does not; a write failure after a readable archive warns once and ships; the authentication-read fixture emits exactly one line (AC-031, AC-032)
- [ ] The entry's `generated_at` equals the rendered `provenance.generated_at` because one instant is computed once (AC-029)
- [ ] The gist token and id appear in no output, message, log line or artefact (AC-005, FR-009)
- [ ] No memory outcome changes the exit code: every case exits 0 (FR-006)
- [ ] `prompt_sha` is byte-identical to Phase 1 for the same instructions (AC-028)
- [ ] Backfill path proved in a fresh subprocess: one write, `main()` never called, empty stdout (build constraint)
- [ ] The README says a season's `memory.json` is retired at a season boundary, and why (S3)
- [ ] `AI_MEMORY_WRITE` false reads the archive, writes nothing, records `"skipped"`, warns about nothing, and renders exactly as a writing run (AC-034)
- [ ] LV-005 and LV-006 run manually once against a real gist and the live provider before release

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
| A — History and league-wide view | T101–T103, T105, T106 | 6–8 h |
| B — Memory log | T201–T208, T210 | 8–11 h |

**Shipped total**: 15–20 h of implementation, plus one live-provider pass (LV-001…004) that cannot be automated in the suite.

**Amendment**: 14–19 h, plus LV-005/LV-006 once at Phase B's release. Each phase is one engineer pass: A is 5 tasks and B is 9, both under the ~15 ceiling. Three tasks were folded rather than added — T104 into T103 (same two files, one test run) and T209 into T210 (the guard and the docs exist for the same reader) — so the ids keep their old numbers and the gaps are deliberate.

Two candidates were considered and left out:

- **A `--help` paragraph for the memory settings** — no FR asks for it, the existing epilog already states the feature's egress, and a fourth copy of a variable list is the drift Gate 2 cut once already.
- **A separate "backfill works outside the CLI" task** — T206's subprocess test is that path, so a second test would exercise the same code with a different name.

If either phase had to shrink further, the cheapest single task is T105's `history_weeks` into T101 (same digest, one field) — but nothing needs to go today.

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-10-21 | AI Agent | Initial 14-task breakdown, one AC map per task, signature-ordering constraint recorded |
| 1.1 | 2026-10-21 | AI Agent | Gate 2 revisions: old Tasks 7 and 8 merged into one narrative task (13 total, renumbered); Task 7 gains `test_generate_propagates_programming_errors` and the `JSONDecodeError`-only parse rule; Task 5 adopts `TypedDict` plus a golden recursive key-set test; Task 6 corrects the transport to `_urlopen(request, timeout) -> bytes` and adds the `patch("urllib.request.urlopen")` test; Task 4 adds the `.env`-only ordering test; Task 1 uses `int \| None = None`; Task 11's `--help` reduces to the egress paragraph; Task 12 drops `AI_SUMMARY_MODEL`; Task 13 drops `AGENTS.md` |
| 1.2 | 2026-10-21 | AI Agent | Spec v0.12: Task 7 gains the league-scope prompt (count and names from the digest, hashed), the one-retry contract loop and `attempts`; Task 2 gains `provenance.attempts` (1 or 2); Task 8 records `attempts` in JSON; Tasks 9 and 10 move the section between the weekly highlights and the season challenges with the notice in the same slot, and claim AC-018; Task 7 claims AC-019…AC-022. |
| 1.3 | 2026-10-21 | AI Agent | Gate 3 delta: Task 7's `prompt_sha` line hashes the composed prompt only; Task 10's email placement says "before the season challenges" rather than "before the footer"; Task 9/10 tests claim the playoff, championship and no-weekly placement cases (AC-018) and the spec v0.13 logging boundary (league names in the DEBUG prompt line only). |
| 2.0 | 2026-10-27 | AI Agent | Spec v0.24: the two-phase amendment. Phase A (T101–T106) adds the history block and the league-wide view to the digest, one shared comparator, the two league-wide prompt rules, `provenance.history_weeks`, and the Phase-1 golden capture as its last task. Phase B (T201–T210) adds memory configuration, the archive and its structural read, the gist store, `MemorySession`, the redacted prompt block, the service lifecycle and provenance, the CLI wiring and warnings, the AC-028 golden comparison, the WC-002 workflow guard and the operator documentation. Tasks 1–13 keep their ids; the amendment is numbered `T1xx`/`T2xx` so nothing shipped is renumbered. New: a dependency map (which tasks are independent, which are strict prerequisites), a full traceability table for AC-001…AC-033, WC-001/WC-002 and LV-001…LV-006 with the manual rows marked, and the two tasks considered and left out (a `--help` paragraph, a separate backfill task — the constraint rides on T206). No task exceeded the single-pass ceiling: A is 6, B is 10. |
| 2.1 | 2026-10-27 | AI Agent | Plan review applied. **B1** — T206's backfill proof becomes a fresh-subprocess behaviour test (one store write, `main()` replaced by a raiser and never called, empty stdout), because `ff_tracker/__init__.py` imports `.main` and no import assertion can hold. **B2** — `commit(summary)` moves after `_normalise`, and the entry's `generated_at` is copied from `summary.provenance.generated_at`, so one instant is used twice; T206 asserts equality. **B3** — the "shipped state" block and Tasks 4, 6 and 12 are corrected to the shipped shape: the full `AI_SUMMARY_*` set including `MAX_TOKENS` and `REASONING_EFFORT`, `max_tokens`/`reasoning_effort` as configuration with no hard-coded budget, default model `deepseek-v4.1-flash`, and `AI_SUMMARY_MODEL` forwarded from `vars.*`. **B4** — T207 asserts `== 2` for the paired authentication-read-plus-failed-write fixture and `== 1` for each single cause. **S1** — the failure table and AC-031/AC-033 rows point at the criteria that now exist. **S2** — T202 writes "parses as the archive shape". **S3** — T210 and the README bullet carry the season-boundary retirement, with the consequence stated. **S4** — T202 adds the unknown-key-survives-merge case. **S5** — T106 names the full patch set (`sys.argv`, league ids, `ESPNService`, the provider client, the `datetime` attribute on `ff_tracker.services.ai_summary_service`) and carries a recapture procedure with what may and may not break the golden. **S6** — T102 splits its fixtures and states that the agreement case guards rendering order, not the comparator; the >20-team comparison moves to T103. **S7** — T203's `curl` is marked manual, once, in the PR description. **S10** — Tasks 1–13 are marked shipped-context, with the three stale lines named. Cuts: no committed `research.md`; no `ai_client.py` rename (the store gets its own wrapper); T104 folded into T103; T209 folded into T210. Counts: Phase A 5, Phase B 9. |
| 2.2 | 2026-10-27 | AI Agent | Gate 2 close. Dependency map: **T103 requires T102**; T101 independent. **T205 joins AC-033's row** and its six-week test asserts an over-long stored paragraph reaches the composed block verbatim, so the criterion's third clause now has an owner. Header points at **spec v0.26**. Artifacts frozen; Phase A may start. |
| 2.3 | 2026-10-27 | AI Agent | Matches code: **a failed read suppresses the write.** T204 orders `commit` so `read_status: "failed"` is the first check and returns `"skipped"` with no store call, and its tests assert zero saves and unchanged store bytes for auth, 5xx, transport and timeout. T207's warning counts follow: a 401/403 read is one line and zero saves, the paired two-warning fixture is gone because a suppressed write has no line of its own, and the read-404 case keeps its attempted write. Traceability and the Phase B checklist say the same. Correctness change, not a wording one. |
| 2.4 | 2026-10-28 | AI Agent | New task **T211**, read-only memory (spec v0.28, plan v2.4 Decision 18). The owner tests the production workflow by dispatching it with the recipients overridden to their own address, and those runs must not advance the archive, so `AI_MEMORY_WRITE` (default `true`) makes the run read the archive and skip the write: `provenance.memory_write: "skipped"`, no `::warning::`, read untouched, nothing else changed. T211 carries the config field, the session gate, the `update_memory` dispatch input forwarded through a plain expression (empty on a schedule is the default, never false), the `.env.example` line and README paragraph, and AC-034's tests including the format-equality case. Dependency map and traceability updated; nothing renumbered. |
| 2.5 | 2026-10-28 | AI Agent | Conformance wording, no behaviour. `AI_MEMORY_WRITE` is the fourth memory setting, so T210's done-when grep now requires **4** rather than 3 — the check is executable and keeps a count — and T210's `.env.example` bullet says "the memory settings" rather than "the three variables". Nothing else in the task list changes; T211 already owns the new setting. |
