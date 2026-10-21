# Implementation Plan: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: Draft — for plan review (Gate 2)
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-21
> **Version**: 1.0
> **Spec**: [spec.md](./spec.md) v0.7 (authority — this plan decides implementation only)
> **Gate rulings**: [challenge-ledger.md](./challenge-ledger.md) (settled rows are settled)

## Scope

Add one optional section to the weekly report (`ff-tracker`), in all five formats, generated once per run from the report's own domain models, rendered last, and never able to stop the report. Nothing else changes: no new CLI, no new format, no new dependency, no change to `ff-championship` or `ff-season-recap`.

**Out of scope** (spec "Not doing", unchanged): season recap and championship CLIs, other provider families, streaming/retries/caching, a user-authored system prompt, `weekly_games` in JSON, per-format opt-out, factual verification, format arguments for this feature.

---

## Technology Choices

### Primary Stack
- **Language**: Python 3.9+ (runtime floor: `requires-python = ">=3.9"`)
- **HTTP**: stdlib `urllib.request` / `urllib.error` / `urllib.parse` — no new dependency. The week-6 spike proved the endpoint works with a non-default `User-Agent` header (`Python-urllib/*` is rejected by Cloudflare in front of the default endpoint).
- **JSON**: stdlib `json`
- **Hash/timestamp**: `hashlib.sha256`, `datetime.datetime.now(datetime.timezone.utc)`
- **Configuration**: `os.getenv` + existing `load_environment()` / `python-dotenv`
- **Testing**: pytest + `unittest.mock.patch` (already the repo's pattern in `tests/test_main_cli.py`) + one in-repo fake client. **No network in the suite.**

### Rationale
The single HTTP call, one JSON body and one prompt are small enough that a dependency (httpx, openai SDK) buys nothing and costs a lockfile entry, a supply-chain surface and a second retry/timeout policy to reason about. `urllib` also makes the "no retries, no streaming" rule structural: there is no client library that might retry behind our back.

**Constitutional Compliance**:
- Article I: fully typed, no `Any` (digest is `dict[str, object]`, never `dict[str, Any]`)
- Article II: every new model is a frozen dataclass validated in `__post_init__`
- Article III: fail-fast everywhere **except** the declared narrative boundary (see Complexity Tracking)
- Article IV: services never import `ff_tracker.display`; formatters never compute
- Article VI: the new section reaches all five formatters through the one `format_output` protocol

---

## Architecture Pattern

**Pattern**: Service-side payload + narrative generation, delivered to the existing formatters through one new optional parameter.

```
main.py
  ├─ ESPNService ................. divisions (unchanged)
  ├─ ChallengeCalculator ......... season challenges (unchanged)
  ├─ WeeklyChallengeCalculator ... weekly challenges (unchanged)
  ├─ AISummaryService ............ AISummary | AISummaryUnavailable   ← NEW (once per run)
  │    ├─ ai_digest.build_digest(domain models) → dict[str, object]
  │    ├─ ai_client.AIClient.complete(AIRequest) → str      (HTTP)
  │    └─ parse → match → normalise → AISummary
  └─ FormatterClass.format_output(..., ai_summary=result)  ← 5 formats
```

**Constitutional Compliance**:
- Article IV: the digest reads models, the service reads the digest, the formatters only render. `services/*` imports nothing from `display/`.
- Article VI: one new keyword parameter on the shared protocol; no format gets more capability than another.

---

## Key Architectural Decisions

### Decision 1: The fail-open boundary is one `try` around `_generate`, catching only `AISummaryError`

`AISummaryService.generate` is the whole boundary:

```python
def generate(self, ...) -> AISummaryResult:
    try:
        return self._generate(...)
    except AISummaryError as e:
        return AISummaryUnavailable(reason=e.reason)
```

`_generate` runs digest → request → `client.complete` → parse → match → normalise. Every failure the spec degrades on is raised as a subclass of `AISummaryError` (our own taxonomy, derived from `Exception`, **not** from `FFTrackerError`); everything else — a `TypeError` from a programming mistake, an `AttributeError`, a bad model construction outside the parse boundary — propagates and fails the run, which is what Article III wants.

**Why not `except Exception`**: it would make the single declared deviation unbounded, and a green suite cannot tell the difference. The narrow catch is the guardrail; converting parser noise (`json.JSONDecodeError`, `KeyError`, `TypeError`, `DataValidationError`, missing keys) into `AIContractError` happens **inside `_parse_response`**, where the noise is expected and bounded — not by widening the outer catch.

**Why not a decorator/context manager**: one call site, one boundary; a decorator hides the only place a reviewer needs to see.

### Decision 2: "Narrative or notice" is a union of two frozen models, not two parameters

```python
AISummaryResult = Union[AISummary, AISummaryUnavailable]   # typing.Union: a runtime alias, `X | Y` needs 3.10
```

`AISummaryUnavailable` holds `reason: str` and exposes `notice` (a `@property` returning `AI summary unavailable: {reason}. The report is unaffected.`). `format_output(..., ai_summary: AISummaryResult | None = None)` then has exactly three states: `None` = feature off (no section, no notice), `AISummary` = section, `AISummaryUnavailable` = notice. Each formatter branches once.

**Simpler alternative, rejected**: pass `str` for the notice. It works, but a bare string as an error carrier means any string is a failure and the sentence gets rebuilt in five formatters. Cost of the model: one 8-line frozen dataclass plus its validation.

**Simpler alternative, rejected**: two parameters (`ai_summary`, `ai_summary_notice`). Two nullable parameters can express impossible combinations (both set), and it doubles the protocol change.

### Decision 3: AI configuration sits **beside** `FFTrackerConfig`, loaded by `main.py`

`config.py` gains `AISummaryConfig` (frozen, validated) and `load_ai_summary_config()`. `main.py` calls the loader inside its existing `try:` block; `FFTrackerConfig` is not modified.

**Why not a field on `FFTrackerConfig`**: `create_config()` is shared by `ff-tracker`, `ff-championship` and `ff-season-recap`. Putting the loader there would make a malformed `AI_SUMMARY_*` variable fail the championship and season-recap CLIs too, which FR-001 excludes ("covers the weekly report CLI only"). Sits beside it, validated once, wired once.
**Trade-off**: configuration validation is not reachable from `create_config()`; the compile-time story is unchanged but the plan must keep the loader next to the other loaders in `config.py` so the convention is obvious.

### Decision 4: The digest is a `dict[str, object]` built by typed helpers, not a model tree

The digest exists only to be `json.dumps`-ed into one chat message. A parallel set of frozen dataclasses (`AIDigest`, `AIDigestLeague`, `AIDigestTeam`, `AIDigestMatchup`…) would be six classes whose only method is "turn me into dicts", and they would need updating in lockstep with the prompt.

`dict[str, object]` keeps Article I satisfied (`object`, never `Any`; values are `str`/`int`/`float`/`bool`/`None`/nested dicts/lists) while the builder stays ~120 lines of named helpers. The narrative *response* is modelled properly, because it has five consumers.

### Decision 5: `DivisionData.reg_season_count` is defaulted, not required

`reg_season_count: int = 14` with validation `1 <= value <= 18`. There are **62** `DivisionData(...)` construction sites across `ff_tracker/` and `tests/`; a required field means touching all of them for no behavioural gain. The one production builder (`ESPNService.load_division_data`, `ff_tracker/services/espn_service.py:1288`) always passes the league's real `settings.reg_season_count`; the default only serves fixtures and `SeasonRecapService` (which has no league settings in scope — see "Constraints discovered in the existing code").

### Decision 6: The client takes an injectable transport, so the real client is testable without a network or a mock library

```python
class HTTPTransport(Protocol):
    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes: ...
```

`OpenAICompatibleClient(config, transport=urllib.request.urlopen)` (parameter defaulted). Client tests pass a fake transport that returns canned bytes or raises `HTTPError`/`URLError`/`TimeoutError`; the summary-service tests use `FakeAIClient` at the protocol level and never touch HTTP. Two seams, two levels of test, no `responses`/`httpretty` dependency and no local server.

### Decision 7: Where the section lands, and why the trailing "Game data" line counts as a footer

Per format, the section is inserted so that **no existing line moves**:

| Format | Insert before | Rationale |
|---|---|---|
| console | the trailing `📊 Game data: …` line when present (regular season), otherwise the end (playoff mode) | that line is the report's closing summary; the section is "after standings" and before it |
| sheets | the end — after the final `OVERALL TOP TEAMS` block | sheets emits its `Game data:` line *mid-report* (right after season challenges), so the last section is the overall table, not standings |
| markdown | the trailing `📊 **Game data:** …` line when present, otherwise the end | same as console |
| email | the `<div class="footer">` block | that block *is* the footer (game data + version + repo link) |
| json | nothing — new top-level `ai_summary` key appended last | JSON has no order-sensitive footer |

For console and markdown the trailing "Game data" line is the only content after standings, so treating it as the footer satisfies FR-005 ("after the existing deterministic sections and before any format footer") and gives AC-001 a non-empty post-section suffix. Sheets prints its `Game data:` line *before* the standings (right after the season challenges), so the section is appended at the very end there and AC-001's suffix is empty — "output equals its prefix" is the same assertion with a shorter suffix. In championship mode console ends on a player-highlight note line; the section still goes last.

**Not changed**: the markdown table of contents is a fixed list (`markdown.py:89-102`), so the new `##` heading does not enter it. Adding it would change an existing section's content; FR-005 forbids that.

### Decision 8: `prompt_sha` hashes the template and the raw user prompt, 12 hex chars

`sha256(SYSTEM_PROMPT + "\n\x00\n" + user_prompt).hexdigest()[:12]` — the fixed separator is `\n\x00\n`, the length matches the spec's example (`9f2c1ab4e7d0`). Hashing the *composed* prompt instead would count the instructions block twice and make the hash sensitive to the block's delimiters rather than to the instructions.

---

## Component Breakdown

### Component 1: `AISummary` models — **NEW** `ff_tracker/models/ai_summary.py`

Data only (Article II). Exported from `ff_tracker/models/__init__.py`.

```python
@dataclass(frozen=True)
class AISummaryLeague:
    league: str          # heading, always one of our league names
    paragraphs: list[str]
    bullets: list[str]
    # __post_init__: league non-empty; >= 1 paragraph; every paragraph
    #   contains >= 1 word after .strip(); every bullet non-empty after strip

@dataclass(frozen=True)
class AIProvenance:
    model: str           # reported verbatim
    prompt_sha: str      # 12 hex chars
    generated_at: str    # ISO 8601 UTC, e.g. 2026-10-14T05:03:11Z
    truncated: bool = False
    # __post_init__: all strings non-empty

@dataclass(frozen=True)
class AISummary:
    headline: str
    leagues: list[AISummaryLeague]   # >= 1 entry
    season_note: str
    provenance: AIProvenance
    # __post_init__: headline and season_note non-empty; >= 1 league

@dataclass(frozen=True)
class AISummaryUnavailable:
    reason: str
    # __post_init__: reason non-empty
    @property
    def notice(self) -> str: ...     # "AI summary unavailable: {reason}. The report is unaffected."

AISummaryResult = Union[AISummary, AISummaryUnavailable]
```

The spec's "at least one non-empty paragraph per league" is enforced on `AISummaryLeague`, which is where a league entry exists at all — `AISummary` cannot hold an empty-paragraph league.

### Component 2: `DivisionData.reg_season_count` — **MODIFIED** `models/division.py`, `services/espn_service.py`

- `models/division.py:46` — add `reg_season_count: int = 14` after `playoff_bracket`; validate `1 <= reg_season_count <= 18` (`DataValidationError`).
- `services/espn_service.py:1288` — pass `reg_season_count=league.settings.reg_season_count` in the `DivisionData(...)` return of `load_division_data`.
- Optional convenience property `weeks_remaining(current_week: int | None) -> int | None` — **not** added: the digest computes `max(0, reg_season_count - current_week)` in one place, and a model property would need the `None` case anyway.

### Component 3: Error taxonomy — **MODIFIED** `ff_tracker/exceptions.py`

```python
class AISummaryError(Exception):          # NOT FFTrackerError: these must never reach main's fail-fast handler
    reason: str                           # FR-006 text, built at the failure site

class AIHTTPError(AISummaryError):        # status, host, model
class AITransportError(AISummaryError):   # host
class AITimeoutError(AISummaryError):     # seconds
class AITruncationError(AISummaryError):  # finish_reason=length
class AIContractError(AISummaryError):    # shape, or league-count mismatch with the counts
```

Each subclass takes its fields and builds `reason` in `__init__`:

| Failure | Raised in | `reason` |
|---|---|---|
| HTTP 4xx/5xx | `OpenAICompatibleClient.complete` | `HTTP 410 (model glm-5.3-flash at opencode.ai)` |
| transport | `OpenAICompatibleClient.complete` | `connection failed (opencode.ai)` |
| timeout | `OpenAICompatibleClient.complete` | `timed out after 120s` |
| truncation | `OpenAICompatibleClient.complete` | `finish_reason=length` |
| response shape | `AISummaryService._parse_response` | `response did not match the summary contract` |
| league-count mismatch | `AISummaryService._match_leagues` | `league count mismatch (3 leagues, 2 sections)` |

Deriving from `Exception` rather than `FFTrackerError` is deliberate: if one ever escaped the boundary, `main()` must not print `Error:` and exit 1 for a cosmetic failure — an uncaught `AISummaryError` should surface as the unexpected-error path, i.e. loudly, but it cannot be mistaken for a configuration error.

### Component 4: Configuration — **MODIFIED** `ff_tracker/config.py`

```python
@dataclass(frozen=True)
class AISummaryConfig:
    enabled: bool
    api_key: str = field(default="", repr=False)   # never in a repr/traceback
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: int = 120
    max_prompt_chars: int = 8000
    user_prompt: str = ""
    # __post_init__: enabled -> api_key.strip() non-empty (ConfigurationError naming AI_SUMMARY_API_KEY)
    #                timeout > 0, max_prompt_chars > 0  (names itself)
    #                len(user_prompt) <= max_prompt_chars -> else ConfigurationError with
    #                variable, actual length, configured limit
```

`load_ai_summary_config() -> AISummaryConfig` reads the seven variables, following `load_espn_credentials()` / `parse_league_ids_from_env()`:

| Variable | Parse | Invalid |
|---|---|---|
| `AI_SUMMARY_ENABLED` | lowercase in `{true,1,yes,on,false,0,no,off}`, default false | `ConfigurationError("AI_SUMMARY_ENABLED must be one of true/1/yes/on/false/0/no/off, got: 'maybe'")` |
| `AI_SUMMARY_API_KEY` | verbatim (not stripped — a token may not survive stripping; whitespace-only counts as empty) | `ConfigurationError` naming it when `enabled` |
| `AI_SUMMARY_BASE_URL` | verbatim with trailing `/` stripped; empty/whitespace → default | never (falls back) |
| `AI_SUMMARY_MODEL` | verbatim, default `glm-5.3-flash` | never |
| `AI_SUMMARY_TIMEOUT` | `int()`, default 120 | `ConfigurationError` naming the variable and the value |
| `AI_SUMMARY_MAX_PROMPT_CHARS` | `int()`, default 8000 | `ConfigurationError` naming the variable |
| `AI_SUMMARY_USER_PROMPT` | `.replace("\r\n", "\n").strip()`; empty → no block | length checked against the configured limit |

`main.py` calls the loader inside its existing `try:`; `ConfigurationError` is an `FFTrackerError`, so `main()` prints and returns 1 with no report and no HTTP call (AC-009), without new plumbing.

### Component 5: Digest builder — **NEW** `ff_tracker/services/ai_digest.py`

```python
def build_digest(
    divisions: Sequence[DivisionData],
    challenges: Sequence[ChallengeResult],
    weekly_challenges: Sequence[WeeklyChallenge] | None,
    current_week: int | None,
    championship: ChampionshipLeaderboard | None,
) -> dict[str, object]
```

Payload (no league IDs, no credentials, no API key — FR-002):

```json
{
  "week": 6,
  "mode": "regular_season",
  "leagues": [
    {
      "league": "MM Driveway Surfers",
      "teams": 12,
      "week": 6,
      "weeks_remaining": 8,
      "standings": [
        {"rank": 1, "team": "Butt Fumble", "owner": "Shaun",
         "record": "6-0", "points_for": 812.34, "points_against": 700.12,
         "playoff_status": "qualified"}
      ],
      "matchups": [
        {"team": "Donut Lose", "score": 126.14, "projected_score": 120.0,
         "true_projection_diff": 6.14,
         "opponent": "In JJ We Trust", "opponent_score": 125.06,
         "opponent_projected_score": 130.0, "opponent_true_projection_diff": null,
         "margin": 1.08}
      ],
      "weekly_challenges": [
        {"challenge": "Closest Game This Week", "winner": "Donut Lose",
         "value": "126.14 - 125.06 (Δ1.08)"}
      ]
    }
  ],
  "season_challenges": [
    {"challenge": "Most Points Overall", "winner": "Butt Fumble",
     "league": "MM Driveway Surfers", "value": "1250.50", "historical": false}
  ],
  "playoffs": {"round": "Semifinals", "matchups": [ ... ]},
  "championship": {"leaderboard": [ ... ]}
}
```

Rules the builder implements, each traceable to FR-002:

- **Mode** (the sixth local copy): `championship is not None` → `"championship"`; else `any(d.is_playoff_mode for d in divisions)` → `"playoffs"`; else `"regular_season"`. The digest takes `championship` from the same variable the formatters receive, so agreement is structural, not asserted-and-hoped — AC-012's assertion is then about the *filtering*, not the predicate.
- **Standings**: present in regular and playoff modes (formatters show them both), absent in championship mode. `rank` = the formatters' order (`_get_sorted_teams_by_division`: wins desc, points_for desc); `playoff_status` = `"qualified"` / `"eliminated"` from `TeamStats.in_playoff_position` (the JSON formatter's wording, not a seed).
- **Weeks remaining**: `max(0, division.reg_season_count - current_week)` when `current_week` is not `None`; both keys omitted when it is (see Constraints).
- **Matchups**: one row per `WeeklyGameResult` of `division.weekly_games`; opponent true diff read from the mirror row via a per-division lookup keyed `(team_name, opponent_name)`; `None` when there is no mirror row (FR-002's omission rule). Empty list plus `"matchups_note": "No matchups this week"` when a league has none — the explicit sentence FR-002 requires.
- **Weekly challenges**: `[c for c in weekly_challenges if c.division == division.name]`, and in playoff/championship modes further filtered to `"position" in c.additional_info` (the formatters' own filter). This relies on `WeeklyChallenge.division` being the winner's league, which the merged spec-003 fix (`a78e6ba`) provides on this branch.
- **Season challenges**: global, with `"historical": true` in playoff and championship modes (formatters label them final at Week 14).
- **Playoffs**: `{"round": bracket.round, "matchups": [...]}` per division from `PlayoffBracket` (team names, owners, seeds, scores, winner, nulls preserved).
- **Championship**: `{"leaderboard": [{"rank", "team", "owner", "division", "score", "is_champion"}]}` from `ChampionshipLeaderboard.entries`.

### Component 6: Provider client — **NEW** `ff_tracker/services/ai_client.py`

```python
MAX_TOKENS = 8000
CONTRACT_REASON = "response did not match the summary contract"

@dataclass(frozen=True)
class AIRequest:                       # data the fake can record (AC-010)
    system_prompt: str
    user_message: str
    max_tokens: int = MAX_TOKENS
    # __post_init__: prompts non-empty, max_tokens > 0

class AIClient(Protocol):
    def complete(self, request: AIRequest) -> str: ...   # returns message.content

class OpenAICompatibleClient:
    def __init__(self, config: AISummaryConfig, transport: HTTPTransport | None = None) -> None: ...
    def complete(self, request: AIRequest) -> str: ...
```

`complete`:

1. URL `config.base_url.rstrip("/") + "/chat/completions"`.
2. `urllib.request.Request(url, data=body, method="POST")` with
   `Authorization: Bearer <key>`, `Content-Type: application/json`,
   `User-Agent: ff-awards/<version>` (non-default; `Python-urllib/*` is refused by the default endpoint's front door).
3. Body `{"model": config.model, "messages": [{"role":"system",...},{"role":"user",...}], "max_tokens": request.max_tokens}`. No `response_format`, no `temperature` — the spike validates the plain call, and inventing knobs the spec does not name is exactly the gold-plating this plan avoids.
4. `self._transport(request_obj, self._config.timeout)` inside `try/except`:
   - `urllib.error.HTTPError` → read **and discard** `e.read()` (never logged), close, `raise AIHTTPError(status=e.code, host=host, model=...)`.
   - `urllib.error.URLError` → if `e.reason` is a `TimeoutError`/`socket.timeout` → `AITimeoutError(timeout)`; else `AITransportError(host)`.
   - `TimeoutError` (incl. `socket.timeout`, same class on 3.10+) → `AITimeoutError(timeout)`.
5. Parse the envelope: `choices[0].message.content` (must be `str`), `choices[0].finish_reason`. `finish_reason == "length"` → `AITruncationError()` **even when the content parses** (AC-007). Anything missing or mistyped → `AIContractError(CONTRACT_REASON)`.
6. Return the content string; the service parses *that* as JSON.

Logging (FR-009): INFO — model, status, latency ms; DEBUG — token counts from `usage` when present. Never the key, the request body or the response body. `host` comes from `urllib.parse.urlsplit(base_url).hostname` — the **only** URL fragment that may appear in a reason (FR-006/AC-005). `HTTPError.filename` holds the full URL, so it is never read, logged or formatted; the reason is built from `e.code` alone.

**Known limitation** (spec vs stdlib): `urlopen(timeout=...)` is a per-socket-operation timeout, not a wall-clock budget, so a slow trickle can outlive `AI_SUMMARY_TIMEOUT`. Enforcing a true whole-call deadline needs a worker thread or `signal.alarm` (POSIX only, breaks in pytest's main thread assumptions). The plan accepts the socket timeout and keeps the notice text ("timed out after 120s") accurate for the case it covers.

### Component 7: Summary service — **NEW** `ff_tracker/services/ai_summary_service.py`

```python
SYSTEM_PROMPT = """..."""            # module constant, the contract in prose (FR-004/FR-010)
INSTRUCTIONS_HEADING = "### COMMISSIONER'S INSTRUCTIONS"

def build_system_prompt(user_prompt: str) -> str      # template, or template + heading + value
def prompt_sha(user_prompt: str) -> str               # sha256(template + "\n\x00\n" + prompt)[:12]

class AISummaryService:
    def __init__(self, config: AISummaryConfig, client: AIClient) -> None: ...
    def generate(self, divisions, challenges, weekly_challenges, current_week, championship) -> AISummaryResult
    def _generate(...) -> AISummary
    def _parse_response(self, content: str) -> _Narrative
    def _match_leagues(self, narrative, divisions) -> list[AISummaryLeague]
    def _normalise(self, ...) -> AISummary
```

- **Prompt**: the constant states the JSON contract, the caps, the no-invented-facts rule, the commissioner voice, and the 60-word guidance floor (explicitly guidance, not a validated requirement). `build_system_prompt` appends the block only for a non-empty user prompt.
- **Request**: `AIRequest(system_prompt=build_system_prompt(config.user_prompt), user_message=json.dumps(digest, ensure_ascii=False))`.
- **Parse** (`_parse_response`): `json.loads` → structural checks (headline `str` non-empty; `leagues` list of dicts; `league` `str`; `paragraphs` list of `str` with ≥1 having a word after strip; `bullets` list of `str`; `season_note` `str` non-empty). All parser noise (`JSONDecodeError`, `KeyError`, `TypeError`, `ValueError`, `DataValidationError`) is caught **here** and re-raised as `AIContractError(CONTRACT_REASON)`.
- **Match** (`_match_leagues`) — FR-004's total order, applied once:
  1. `by_name = {e["league"].strip().casefold(): e}`; if `len(by_name) == len(entries) == len(divisions)` and every league name is a key → map by name, emit in **digest order** (response order irrelevant).
  2. elif `len(entries) == len(divisions)` → `zip(divisions, entries)` by position; heading is `division.name`; response-supplied names are discarded.
  3. else → `AIContractError(f"league count mismatch ({len(divisions)} leagues, {len(entries)} sections)")`.
- **Normalise** — FR-004's four steps in order, pure and total: drop bullets beyond 3 → drop paragraphs beyond 3 → drop trailing paragraphs while the league total exceeds 120 words, truncating the first paragraph at the last word boundary ≤120 with `…` if it alone exceeds the budget (dropping the rest) → truncate headline at 15 words and `season_note` at 40 with `…`. Word counting is `len(text.split())`; truncation is `" ".join(words[:cap]) + "…"`. `truncated` is true when any bullets/paragraphs were dropped or any text shortened. No sentence detection anywhere.
- **Provenance**: `model=config.model`, `prompt_sha=prompt_sha(config.user_prompt)`, `generated_at=now(UTC)`, `truncated=…`.
- **Logging**: WARNING on degradation (reason only), DEBUG for the composed system prompt (FR-009). Never the digest, the request body, the response body or the key; never the team/owner names.

### Component 8: Protocol & base formatter — **MODIFIED** `ff_tracker/display/base.py`

`OutputFormatter.format_output` (`:88`) and `BaseFormatter.format_output` (`:239`) gain:

```python
ai_summary: AISummaryResult | None = None,
```

last, keyword-usable, defaulted. Article VI: one signature, five implementations, no format-specific channel. The import is from `..models` (`AISummary`, `AISummaryResult`, `AISummaryUnavailable`) — display → models, allowed.

### Component 9: Renderers — **MODIFIED** five formatters

Each gains one private method, `_format_ai_summary(ai_summary) -> str | list[str]`, called from `format_output` at the insertion point from Decision 7, and only when `ai_summary is not None`.

| Format | Section (narrative) | Notice |
|---|---|---|
| `console.py` | `🤖 COMMISSIONER'S TAKE (AI-GENERATED)` header with the usual `"=" * 80` rules, headline, per-league name line, paragraphs (one line each — no wrapping, AC-011), `• ` bullets, `Generated by <model> · AI-generated text` | one line, same position |
| `sheets.py` | blank row, `AI SUMMARY (AI-GENERATED)`, `HEADLINE: …`, `LEAGUE: …` per league, one row per paragraph, `- ` bullet rows, attribution row; every cell flattened (`\t`, `\r`, `\n` → space) | one flattened notice row |
| `email.py` | `<h2>🤖 Commissioner's Take (AI-generated)</h2>` + marker, `<p>` paragraphs (`_escape_html`), `<ul><li>`, attribution line; inserted before `<div class="footer">` | one `<p>` |
| `json.py` | `data["ai_summary"]` appended last: `headline`, `season_note`, `leagues`, `provenance` | `{"error": notice}` |
| `markdown.py` | `## 🤖 Commissioner's Take (AI-generated)`, `### <league>`, paragraphs, `- ` bullets, `_Generated by <model> · AI-generated text_` | one line (italic) |

The JSON `leagues` entries reuse our league names and the normalised paragraphs/bullets — no re-matching in the formatter (display never computes).

### Component 10: CLI wiring — **MODIFIED** `ff_tracker/main.py`

```python
ai_config = load_ai_summary_config()                     # inside the existing try:
...
ai_summary: AISummaryResult | None = None
if ai_config.enabled:
    client = OpenAICompatibleClient(ai_config)
    ai_summary = AISummaryService(ai_config, client).generate(
        divisions, challenges, weekly_challenges or None,
        espn_service.current_week, championship,
    )
    if isinstance(ai_summary, AISummaryUnavailable) and os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning::{ai_summary.notice}")
```

Placed after weekly challenges, before the `--output-dir` branch, so **one call per run** covers five formats and both output modes (AC-003). Both `format_output(...)` call sites (`main.py:301` and `main.py:315`) pass `ai_summary=ai_summary`.

**Why the `::warning::` lives here and not in the service**: a workflow command is process output, not a report section, and Article IV forbids the service layer from printing presentation. The service returns the result and logs at WARNING; `main.py` is the only process-level writer.

`create_parser()`'s epilog gains an **AI Summary (optional)** block: the seven variables, "off by default", and the egress sentence FR-009 requires (team names, owner names and scores are sent to `AI_SUMMARY_BASE_URL`; the user prompt is sent verbatim; the key is never printed; `-vv` logs the system prompt, so do not use it in CI).

### Component 11: Workflow — **MODIFIED** `.github/workflows/weekly-report.yml`

```yaml
env:
  PYTHONUNBUFFERED: 1
  AI_SUMMARY_ENABLED: ${{ secrets.AI_SUMMARY_API_KEY != '' }}
  AI_SUMMARY_MODEL: glm-5.3-flash
  AI_SUMMARY_USER_PROMPT: |
    <the commissioner's committed instructions; empty by default>
```

- `secrets` is legal in `env:`, illegal in `if:` — exactly the FR-007 trap. The expression renders the literal `true`/`false`.
- In the "Create .env file from secrets" step, append **only when the flag is `true`**:
  ```bash
  if [ "$AI_SUMMARY_ENABLED" = "true" ]; then
    echo "AI_SUMMARY_ENABLED=true" >> .env
    echo "AI_SUMMARY_API_KEY=${{ secrets.AI_SUMMARY_API_KEY }}" >> .env
  fi
  ```
  The non-secret values (`MODEL`, `USER_PROMPT`) stay in the job `env:`, where they are the reviewable record FR-008 asks for and where multiline `.env` quoting cannot break them; `load_dotenv` does not override an already-set environment variable, so `os.getenv` sees them either way.
- No `if:` anywhere in the file mentions `AI_SUMMARY_ENABLED` (WC-001).
- The `::warning::` needs no workflow change: the service's reason is printed to stdout by the step, and Actions surfaces it as an annotation.

### Component 12: Documentation — **MODIFIED**

- `.env.example`: the seven variables, commented, with the real defaults (`https://opencode.ai/inference/openai/v1`, `glm-5.3-flash`, `120`, `8000`), and the egress note.
- `README.md` → Configuration: a "AI Summary (optional)" subsection — what leaves the machine, how to enable with a key alone, why `--help` and `.env.example` carry the defaults, and that `ff-championship`/`ff-season-recap` ignore it.
- `CHANGELOG.md` → `## [Unreleased]` / `### Added - AI Summary (optional)`.
- `AGENTS.md`: one paragraph under "Core Functionality" (the repo's own summary of the tool) — no other change.

---

## File Inventory

**New (11)**
| File | Contents |
|---|---|
| `ff_tracker/models/ai_summary.py` | `AISummaryLeague`, `AIProvenance`, `AISummary`, `AISummaryUnavailable`, `AISummaryResult` |
| `ff_tracker/services/ai_digest.py` | `build_digest` + typed helpers |
| `ff_tracker/services/ai_client.py` | `AIRequest`, `AIClient`, `HTTPTransport`, `OpenAICompatibleClient`, `MAX_TOKENS` |
| `ff_tracker/services/ai_summary_service.py` | `SYSTEM_PROMPT`, `build_system_prompt`, `prompt_sha`, `AISummaryService` |
| `tests/ai_fakes.py` | `FakeAIClient`, `FakeTransport`, canned responses, digest/formatter fixtures |
| `tests/test_ai_summary_models.py` | Article II validation, exception reasons |
| `tests/test_ai_summary_digest.py` | FR-002 payload, AC-012 modes |
| `tests/test_ai_client.py` | FR-003 request shape, error taxonomy |
| `tests/test_ai_summary_service.py` | matching, normalisation, fail-open, logging |
| `tests/test_ai_summary_rendering.py` | five formats, AC-001/002/011 |
| `tests/test_ai_summary_config_workflow.py` | WC-001 static YAML assertions |

**Modified (17)**
| File | Change | Why |
|---|---|---|
| `ff_tracker/models/division.py` | `reg_season_count` field + validation | FR-002 |
| `ff_tracker/models/__init__.py` | exports | new models |
| `ff_tracker/services/espn_service.py` | one keyword in `load_division_data` | populate the field |
| `ff_tracker/exceptions.py` | `AISummaryError` hierarchy | FR-006 reasons |
| `ff_tracker/config.py` | `AISummaryConfig`, `load_ai_summary_config` | FR-007/FR-010 |
| `ff_tracker/display/base.py` | protocol + abstract signature | Article VI |
| `ff_tracker/display/console.py` | signature + `_format_ai_summary` | FR-005 |
| `ff_tracker/display/sheets.py` | signature + `_format_ai_summary` | FR-005 |
| `ff_tracker/display/email.py` | signature + `_format_ai_summary` | FR-005 |
| `ff_tracker/display/json.py` | signature + `ai_summary` key | FR-005/FR-008 |
| `ff_tracker/display/markdown.py` | signature + `_format_ai_summary` | FR-005 |
| `ff_tracker/main.py` | wiring, `::warning::`, `--help` | FR-001/FR-006/FR-009 |
| `.github/workflows/weekly-report.yml` | guard + `.env` appends | FR-007/WC-001 |
| `tests/test_model_properties.py` | `reg_season_count` cases | Task 1 |
| `tests/test_config.py` | AC-009/AC-017 cases | Task 4 |
| `tests/test_json_formatter.py` | `ai_summary` cases + AC-001 (JSON) | Task 9 |
| `tests/test_main_cli.py` | call count, warning, config-error cases | Task 12 |

**Also modified (4, docs)** `.env.example`, `README.md`, `CHANGELOG.md`, `AGENTS.md` (one paragraph).

**Deliberately untouched**: `ff_tracker/championship.py`, `ff_tracker/season_recap.py`, `display/season_recap_*.py`, `display/factory.py`, `services/season_recap_service.py`, `services/championship_service.py`, `.github/workflows/championship-report.yml`, `.github/workflows/season-recap.yml`, `.specify/specs/**` (the spec is the authority; the plan does not edit it).

---

## Data Flow

### Feature off (`AI_SUMMARY_ENABLED` unset/false)
`main` → `load_ai_summary_config()` returns `enabled=False` → no client, no call, `ai_summary=None` → every formatter's `_format_ai_summary` is never entered → **byte-identical output to today** (AC-001), no notice, no warning, no section.

### Feature on, narrative succeeds
digest → `AIRequest` → one POST → content → `json.loads` → contract checks → league matching → normalisation → `AISummary` → same object passed to every format.

### Feature on, narrative fails
Any `AISummaryError` → `AISummaryUnavailable(reason)` → notice in the section's position in all five formats (JSON `ai_summary.error`) → `main` prints `::warning::…` when `GITHUB_ACTIONS == "true"` → **exit 0**, deterministic sections untouched (AC-004).

### Feature on, misconfigured
`load_ai_summary_config()` raises `ConfigurationError` before any ESPN data is fetched → `main` returns 1, no report, zero provider calls (AC-009). This is the *only* new failure path that stops a run, and it is deliberate (FR-007).

---

## Implementation Phases

Fourteen tasks, detailed in [tasks.md](./tasks.md). Grouped so the suite is green after every one:

| Phase | Tasks | Outcome |
|---|---|---|
| 1 — Groundwork | 1–4 | model field, AI models, exception taxonomy, configuration — all unit-tested, nothing wired |
| 2 — Payload & provider | 5–6 | digest builder, HTTP client (both testable in isolation, still unused by `main`) |
| 3 — Narrative | 7–8 | prompt/request/fail-open boundary, then matching + normalisation |
| 4 — Rendering | 9–11 | protocol signature + JSON, then console/markdown, then sheets/email |
| 5 — Wiring | 12 | one call per run, `::warning::`, `--help` |
| 6 — Ops & docs | 13–14 | workflow guard, README/`.env.example`/CHANGELOG |

**Signature-ordering constraint**: mypy requires an override to accept every parameter of the abstract method, so task 9 changes `display/base.py` **and all five** concrete `format_output` signatures in one commit (only JSON renders). Tasks 10–11 then add rendering to the other four without touching any signature. Splitting them the other way round would leave a red `mypy ff_tracker`.

---

## Constraints Discovered in the Existing Code

Recorded because they shape the implementation and are not visible from the spec alone:

1. **`current_week` can be `None`.** `main.py:265` guards weekly challenges on `espn_service.current_week and > 0`; if detection failed, the formatters omit weekly sections too. The digest therefore omits `week`/`weeks_remaining` and reports "no matchups this week" rather than inventing a week. FR-002 does not say what happens here; this is the plan's decision.
2. **`SeasonRecapService` builds `DivisionData` without league settings** (`ff_tracker/services/season_recap_service.py:411`). That call site can only take the default `reg_season_count`; it is a season-recap data path, never the AI digest's, so the default is correct there and the field stays honest for `ff-tracker`.
3. **`HTTPError` carries the full URL in `.filename`** (path and query included) even though `str()`/`repr()` omit it. AC-005 forbids that path from ever appearing, so the client builds reasons from `e.code`, the parsed host and the model, and never logs `e.filename`, the exception object or its traceback.
4. **The 5 formatters each recompute the mode** from `any(d.is_playoff_mode …)` and `championship is not None`; `ReportContext` still exists in `display/base.py` but no formatter reads it (the merged typing commit removed the `context` parameter). The digest's local copy is the sixth, as the spec states — not an extraction opportunity.
5. **`WeeklyChallenge.division` is the winner's league only because of the merged spec-003 fix** (`a78e6ba`). This branch is based on it; had it not merged, FR-002's per-league weekly challenges would be unattributable.
6. **Baseline mypy is clean on this branch** (`Success: no issues found in 41 source files`) — the 27 pre-existing errors the Gate 2 brief refers to were fixed in `a78e6ba`. The bar is therefore zero new errors, not "the same 27".

---

## Testing Strategy

No network: `FakeAIClient` implements `AIClient`; `FakeTransport` implements `HTTPTransport`; `unittest.mock.patch` for `ESPNService`/`create_config` at the CLI boundary, as `tests/test_main_cli.py` already does. Fixture data lives in `tests/ai_fakes.py` (canned responses + builders), not on disk.

| AC | Where |
|---|---|
| AC-001 feature off, five formats byte-identical | `test_ai_summary_rendering.py` (prefix/suffix; JSON parsed minus `ai_summary`) |
| AC-002 valid response renders in five formats | rendering + service tests |
| AC-003 one call, 1/3/10 leagues, `--output-dir` | `test_main_cli` additions (patched service counts calls) |
| AC-004 every failure path, exit 0, notice, warning | service tests (reason + result) + main test (`GITHUB_ACTIONS` set/unset, stdout captured) |
| AC-005 no error body/key/path in any output | service + main + rendering assertion over the five artefacts |
| AC-006 logging tiers | service test with `caplog`: DEBUG shows the system prompt, never the digest marker/team names/key |
| AC-007 `finish_reason=length` with parseable content | client test + service test |
| AC-008 league matching total order | service test (reorder, case/space, stray, duplicate, count mismatch) |
| AC-009 config errors exit 1, no report, zero calls | `tests/test_config.py` + main test |
| AC-010 request shape from configuration | `test_ai_client.py` (fake transport) + fake-client recording |
| AC-011 tabs/newlines/quotes/HTML in one cell | rendering test per format |
| AC-012 edge inputs, mode agreement | digest test + main test |
| AC-013/014/015 caps, first-paragraph truncation, `truncated` | service normalisation tests |
| AC-016 user prompt reaches the block, changes `prompt_sha`, cannot break the shape | service test |
| AC-017 prompt cap + non-default limit | config test |
| WC-001 static workflow check | `tests/test_ai_summary_config_workflow.py` (string assertions on the YAML, no YAML dependency) |
| LV-001…004 | manual, once, against the live provider (not in the suite) |

---

## Risk Assessment

### Risk 1: The fail-open boundary is too wide (or too narrow)
**Likelihood**: Medium · **Impact**: High
**Mitigation**: catch exactly `AISummaryError`; convert parser noise inside `_parse_response`; a test asserts an unexpected `RuntimeError` from the client is **not** swallowed (it propagates). **Fallback**: none needed — this is the design.

### Risk 2: Normalisation is subtly non-deterministic or contradicts the caps
**Likelihood**: Medium · **Impact**: Medium
**Mitigation**: `split()` word counting, no regex, no sentence detection, pure functions; AC-013 asserts two runs are byte-identical.

### Risk 3: A formatter silently changes existing output
**Likelihood**: Low · **Impact**: High
**Mitigation**: AC-001's prefix/suffix test for all five, run before wiring (task 9–11) and after (task 12). The insertion point never moves an existing line (Decision 7).

### Risk 4: The workflow guard is bypassed or the secret leaks into logs
**Likelihood**: Low · **Impact**: High
**Mitigation**: WC-001 test reads the YAML; `AI_SUMMARY_API_KEY` is only ever an `env:` value and a `.env` line; the client never logs requests; AC-005 greps every artefact.

---

## Performance Considerations

With the feature off, `load_ai_summary_config()` is one dict read and an `os.getenv` loop; the run budget is unchanged (Article X, as qualified in Complexity Tracking).

With it on, the run gains one provider call: 7.7–34.4 s in the spike, bounded by `AI_SUMMARY_TIMEOUT` (default 120 s). Nothing is retried and nothing is cached; one call per run regardless of league or format count, which is the only performance requirement this feature can enforce.

Digest size is bounded by the data: 3–4 leagues × (≤16 standings rows + ≤8 matchup rows + ≤7 challenges) — a few KB of JSON, far inside any model's context.

---

## Security Considerations

- The key exists only as an environment value, a `.env` line and `AISummaryConfig.api_key` (`field(repr=False)`). It is never a CLI flag, never a format argument, never logged, never rendered.
- Request and response bodies are never logged at any level (they carry team/owner names, PF/PA and — in principle — anything the model echoes). Only model id, status, latency and token counts are logged.
- The system prompt is logged at DEBUG only, because a public repo's Actions logs are world-readable; the committed `env:` block scalar is the CI record (FR-008/FR-009).
- Reasons name the endpoint **host only** — a custom base URL may carry a credential in its path.
- The digest carries no league IDs, no credentials and no API key (FR-002), and the prompt tells the model not to invent facts; no verification of prose claims is claimed or implied anywhere in the output.

---

## Complexity Tracking

> Two declared deviations, both from the spec's Constitution Deviations section. Each is approved there; recorded here as the constitution requires.

### Article III — Fail-Fast Error Handling (narrative failures degrade the report)

**Deviation**: `AISummaryService` does not fail the run when the narrative cannot be obtained, matched, validated or normalised. The report renders without the section and says so.

**Spec reasoning (quoted in substance)**: the narrative is cosmetic; the report carries the league's weekly facts and runs on a weekly schedule, where a failed proxy, a retired model or an HTTP 410 would otherwise deny the league its report entirely.

**Boundary this plan implements**:
- Applies **only** to obtaining, matching, validating and normalising the narrative — one `try/except AISummaryError` in `generate`.
- ESPN failures, `ConfigurationError` (missing key, bad `AI_SUMMARY_ENABLED`, bad timeout, oversized prompt), data-validation failures outside the parse boundary and every other `FFTrackerError` still fail fast and stop the run.
- Never silent: notice in the section's position in all five formats **plus** a `::warning::` under Actions.
- Normalisation cannot fail: the contract already guarantees ≥1 non-empty paragraph per league and normalisation only drops or shortens, so `AISummary` always constructs once matching succeeded.

### Article X — Performance Requirements (provider latency)

**Deviation**: the 5-second typical run no longer holds with the feature enabled.

**Spec reasoning**: 7.7–34.4 s per call in the spike, bounded by `AI_SUMMARY_TIMEOUT`. The 5-second budget applies to the deterministic report with the feature off.

**Boundary this plan implements**: off by default; zero added network I/O when off; one call per run when on; no retries, no streaming, no per-format second call. A caller that cares about schedule duration leaves the feature off, which is the default.

### Not deviated
Articles I (no `Any`, no suppressions), II (frozen validated models), IV (services never import display; the `::warning::` is emitted in `main.py`, not the service), V (no extra ESPN calls), VI (one protocol, five formats), VII (docstrings/names, comments only for the non-obvious), IX (no new flags; `--help` states the egress).

---

## Open Technical Questions

None open. Decisions the spec leaves to the plan, recorded here so Gate 2 can object to them specifically:

1. Digest shape is an internal `dict[str, object]` (Decision 4) — not a public schema, not the JSON formatter's output.
2. AI configuration sits beside `FFTrackerConfig` (Decision 3), so the other two CLIs never validate `AI_SUMMARY_*`.
3. `reg_season_count` defaults to 14 (Decision 5).
4. The trailing "Game data" lines are treated as the console/sheets/markdown footer for FR-005's placement rule (Decision 7).
5. `current_week is None` omits week/weeks-remaining from the digest (Constraints 1).
6. `provenance.truncated` is always emitted in JSON (`false` when nothing was cut); the spec allows absent-or-false.
7. The markdown TOC does not gain an entry for the new heading (Decision 7).

---

## Related Documentation

- **Feature Spec**: [spec.md](./spec.md)
- **Gate rulings**: [challenge-ledger.md](./challenge-ledger.md)
- **Tasks**: [tasks.md](./tasks.md)
- **Constitution**: [../../memory/constitution.md](../../memory/constitution.md)
- **Related specs**: [002 Weekly Highlights](../002-weekly-highlights/spec.md) · [003 Output Formatters](../003-output-formatters/spec.md) · [005 Format Arguments](../005-format-arguments/spec.md) · [006 Playoff Mode](../006-playoff-mode/spec.md)

---

## Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-10-21 | AI Agent | Initial implementation plan: 14 tasks, 11 new files, 21 modified files, two declared deviations, seven plan-level decisions recorded for Gate 2 |
