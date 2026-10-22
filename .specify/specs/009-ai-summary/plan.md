# Implementation Plan: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: Draft — revised after Gate 2 (plan HOLD)
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-21
> **Version**: 1.3
> **Spec**: [spec.md](./spec.md) v0.13 (authority — this plan decides implementation only)
> **Gate rulings**: [challenge-ledger.md](./challenge-ledger.md) (settled rows are settled; Gate 2 rows are precedent for Gate 3)

## Scope

Add one optional section to the weekly report (`ff-tracker`), in all five formats, generated once per run from the report's own domain models, rendered between the weekly highlights and the season-long challenges, and never able to stop the report. Nothing else changes: no new CLI, no new format, no new dependency, no change to `ff-championship` or `ff-season-recap`.

**Out of scope** (spec "Not doing", unchanged): season recap and championship CLIs, other provider families, streaming/caching, retries beyond the single contract retry FR-003 allows, a user-authored system prompt, `weekly_games` in JSON, per-format opt-out, factual verification, format arguments for this feature.

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
The single HTTP call, one JSON body and one prompt are small enough that a dependency (httpx, openai SDK) buys nothing and costs a lockfile entry, a supply-chain surface and a second retry/timeout policy to reason about. `urllib` also keeps retry policy structural: the client is one-shot, and the single contract retry lives in the summary service, so no library retries behind our back.

**Constitutional Compliance**:
- Article I: fully typed, no `Any` (the digest is a `TypedDict`, parsed JSON is narrowed from `object`)
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
  │    ├─ ai_digest.build_digest(domain models) → AIDigest (TypedDict)
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

**Why not `except Exception`**: it would make the single declared deviation unbounded, and a green suite cannot tell the difference. The narrow catch is the guardrail.

**How the parse stays inside the boundary without widening it** (Gate 2): `_parse_response` converts exactly one exception class — `json.JSONDecodeError`, raised by `json.loads` on content that is not JSON (fenced, prefixed, empty). Every other rejection is a check **we write**, raising `AIContractError` directly from a failing `isinstance`/`len`/`strip` test; there is no `except TypeError`, `except ValueError`, `except KeyError`, and no `except Exception` anywhere in the parse. A structure we did not anticipate therefore crashes the run instead of masquerading as a provider fault, which is the behaviour the ledger requires.

**Narrowing without `Any`**: `json.loads` returns `Any`; the result is bound to `object` immediately (`raw: object = json.loads(content)`) and every level is narrowed with `isinstance` plus small helpers typed `dict[str, object]` / `list[object]`. No `Any` appears in a signature.

**Propagation is tested, not assumed**: `test_generate_propagates_programming_errors` stubs the digest builder to raise `AttributeError` and asserts `generate` raises rather than returning `AISummaryUnavailable` — the test the ledger names for this row.

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

**Load ordering (Gate 2)**: `load_environment()` runs only inside `create_config()`, so `load_ai_summary_config()` calls `load_environment()` itself at the top before reading anything. `load_dotenv` does not override variables already in the process environment, so the call is idempotent and a value set by a workflow `env:` wins over `.env` either way. `main.py` calls the loader **after** `create_config(...)` and before any ESPN call — not "first", which would have read `.env` before it existed. Configuration is therefore "loaded the same way as existing settings" (spec, Configuration section) and `.env`-only setups work; Task 4 carries the test that proves it with `create_config` unpatched.

### Decision 4: The digest is a `TypedDict` document built by typed helpers

The digest exists only to be `json.dumps`-ed into one chat message, and nothing reads it back — which is exactly why it must not be an untyped dict (Gate 2, DEFERRED): with `dict[str, object]`, a key typo (`"weeks_remaing"`) degrades the prompt silently and no test fails.

`TypedDict` gives the enforcement with none of the cost the dataclass tree would carry — no conversion layer, no `asdict`, and a wrong key or value type is a mypy error at the builder:

```python
class AIStandingsRow(TypedDict):
    rank: int; team: str; owner: str; record: str
    points_for: float; points_against: float
    playoff_status: str          # "in_playoff_position" | "outside_playoff_position"

class AIMatchupRow(TypedDict):
    team: str; score: float; projected_score: float
    true_projection_diff: float | None
    opponent: str; opponent_score: float; opponent_projected_score: float
    opponent_true_projection_diff: float | None
    margin: float

class AIWeeklyChallenge(TypedDict):
    challenge: str; winner: str; value: str

class AISeasonChallenge(TypedDict):
    challenge: str; winner: str; league: str; value: str; historical: bool

class AIPlayoffMatchup(TypedDict):
    round_name: str; team1: str; owner1: str; score1: float | None
    team2: str; owner2: str; score2: float | None
    winner: str | None; division: str

class AIPlayoffRound(TypedDict):
    round: str
    matchups: list[AIPlayoffMatchup]

class AIChampionshipEntry(TypedDict):
    rank: int; team: str; owner: str; division: str
    score: float; is_champion: bool

class AIChampionship(TypedDict):
    leaderboard: list[AIChampionshipEntry]

class AILeagueDigest(TypedDict):
    league: str; teams: int
    week: int | None; weeks_remaining: int | None
    standings: list[AIStandingsRow]
    standings_note: str | None   # the status is a position, not a final outcome
    matchups: list[AIMatchupRow]
    matchups_note: str | None
    weekly_challenges: list[AIWeeklyChallenge]

class AIDigest(TypedDict):
    week: int | None
    mode: str                    # "regular_season" | "playoffs" | "championship"
    leagues: list[AILeagueDigest]
    season_challenges: list[AISeasonChallenge]
    playoffs: AIPlayoffRound | None
    championship: AIChampionship | None
```

Every key is **total** (no `NotRequired`, which is 3.11+ and this project supports 3.9), so unknown values are `None` and serialize as `null` rather than being omitted: one shape for every mode, one set of assertions, and no optional-key machinery. `mode` stays a `str` rather than a `Literal` so the value is easy to log and compare without narrowing gymnastics; the three values are documented on the key.

The `TypedDict`s live in `services/ai_digest.py` and are **payload types, not Article II models**: they describe a JSON document built once per run and immediately serialised, never held as application state, so immutability is not in question (a `TypedDict` is a shape for a mutable dict, which is why it does not belong in `models/`). Task 5 also asserts the digest's exact recursive key set against a golden, so a future key rename cannot pass silently even with the type checker green. That golden is authored from **FR-002's field list**, not captured from the builder: a snapshot would bless whatever the builder happens to emit, including a key the spec never asked for.

### Decision 5: `DivisionData.reg_season_count` is `int | None = None`

Gate 2 was right: a defaulted `14` is a false statement in any second production builder, and the digest quotes it into the prompt as fact.

`reg_season_count: int | None = None`, validated `None or 1 <= value <= 18`. The one production builder for the weekly path (`ESPNService.load_division_data`, `ff_tracker/services/espn_service.py:1288`) always passes the league's real `settings.reg_season_count`; fixtures and `SeasonRecapService` (no league settings in scope) pass nothing and the model records "unknown" honestly. The digest then emits `"weeks_remaining": null` when either `reg_season_count` or `current_week` is unknown, and the prompt is told the value is unknown rather than fed a fabricated 8.

Same number of touched sites as the defaulted version (zero — the 62 existing `DivisionData(...)` constructions keep compiling), plus one branch in the digest builder.

### Decision 6: The client takes an injectable transport, defaulting to a `_urlopen` wrapper

Gate 2 caught a real defect in the v1.0 seam: `urllib.request.urlopen` returns an `HTTPResponse`, not `bytes`, and its second positional parameter is `data`, not the timeout — so `transport(urlopen)` could not be the injectable boundary as written. The transport is a function of `(Request, timeout) -> bytes`, and the production implementation is a module-level wrapper:

```python
def _urlopen(request: urllib.request.Request, timeout: int) -> bytes:
    """Default transport: one request, one read, no retries."""
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body: bytes = response.read()
    return body

class HTTPTransport(Protocol):
    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes: ...

class OpenAICompatibleClient:
    def __init__(self, config: AISummaryConfig, transport: HTTPTransport | None = None) -> None:
        self._transport: HTTPTransport = transport or _urlopen
```

Two test levels, both network-free:
- **Service level**: `FakeAIClient` implements `AIClient`.
- **Client level**: `FakeTransport` implements `HTTPTransport` for the request/error matrix, **plus** one test that patches `urllib.request.urlopen` and drives `_urlopen` itself — the default (production) path, which every injected-fake test would otherwise never execute.

### Decision 7: Where the section lands — after the weekly highlights

FR-005 v0.12 fixes the order: `header → weekly highlights → Commissioner's Take → season-long challenges → per-league standings → overall top teams → game data`. The section is inserted between the highlights and the season challenges, so no existing line moves and the failure notice takes the same slot.

| Format | Insert after | Before | Notes |
|---|---|---|---|
| console | the weekly highlights table (and its championship note) | the `💰 SEASON-LONG CHALLENGES` / `📊 REGULAR SEASON FINAL RESULTS` block | the blank-line + banner pattern is unchanged |
| sheets | the weekly challenge rows | the `OVERALL SEASON CHALLENGES` rows | the AI block keeps its blank row |
| markdown | the weekly highlight sections | the `## 💰 OVERALL SEASON CHALLENGES` / `# 📊 …` block | the TOC is a fixed list and still omits the new heading |
| email | the weekly-highlight `<div>` | the season-challenge section | the footer stays last |
| json | — | — | top-level `ai_summary`, unchanged |

The AC-001 prefix/suffix assertion is now a **pure insertion in the middle**: `off` equals the on-output with the section removed, which the difflib opcode test proves (exactly one `insert` op, everything else equal). Repositioning is what changed; the bytes outside the block did not.

**Championship mode**: the same slot — after the weekly highlights (which run there too) and before the season-challenge table, which is then the last deterministic block.

**Not changed**: the markdown table of contents is a fixed list (`markdown.py:89-102`), so the new `##` heading does not enter it. Adding it would change an existing section's content; FR-005 forbids that.

### Decision 8: `prompt_sha` hashes the composed system prompt, 12 hex chars

`sha256(system_prompt).hexdigest()[:12]` — the length matches the spec's example (`9f2c1ab4e7d0`), and `system_prompt` is the **composed** prompt from `build_system_prompt(user_prompt, league_names)`: the template, the league scope and, when set, the `### COMMISSIONER'S INSTRUCTIONS` block. Hashing the composed prompt once is the whole rule; appending `user_prompt` a second time (as an earlier draft did) is redundant because the block already contains it, and a second moving part with no information is a liability. The hash is stable for identical inputs and moves when the template, the league set or the user prompt changes, so an archived report's prompt and scope are identifiable from the hash alone.

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
    attempts: int = 1    # 1, or 2 when the contract retry was spent
    # __post_init__: all strings non-empty; attempts in {1, 2}

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

- `models/division.py:46` — add `reg_season_count: int | None = None` after `playoff_bracket`; validate `None` or `1 <= reg_season_count <= 18` (`DataValidationError`).
- `services/espn_service.py:1288` — pass `reg_season_count=league.settings.reg_season_count` in the `DivisionData(...)` return of `load_division_data`.
- `None` means "unknown", not "ESPN's standard 14": the digest emits `weeks_remaining: null` rather than quoting a fabricated number into the prompt. `SeasonRecapService`'s builder (`season_recap_service.py:411`) passes nothing and stays honest.

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

`load_ai_summary_config() -> AISummaryConfig` calls `load_environment()` first, then reads the seven variables, following `load_espn_credentials()` / `parse_league_ids_from_env()`:

| Variable | Parse | Invalid |
|---|---|---|
| `AI_SUMMARY_ENABLED` | lowercase in `{true,1,yes,on,false,0,no,off}`, default false | `ConfigurationError("AI_SUMMARY_ENABLED must be one of true/1/yes/on/false/0/no/off, got: 'maybe'")` |
| `AI_SUMMARY_API_KEY` | verbatim (not stripped — a token may not survive stripping; whitespace-only counts as empty) | `ConfigurationError` naming it when `enabled` |
| `AI_SUMMARY_BASE_URL` | verbatim with trailing `/` stripped; empty/whitespace → default | never (falls back) |
| `AI_SUMMARY_MODEL` | verbatim, default `glm-5.3-flash` | never |
| `AI_SUMMARY_TIMEOUT` | `int()`, default 120 | `ConfigurationError` naming the variable and the value |
| `AI_SUMMARY_MAX_PROMPT_CHARS` | `int()`, default 8000 | `ConfigurationError` naming the variable |
| `AI_SUMMARY_USER_PROMPT` | `.replace("\r\n", "\n").strip()`; empty → no block | length checked against the configured limit |

`main.py` calls the loader **after** `create_config(...)` and before any ESPN call, inside its existing `try:` block; `ConfigurationError` is an `FFTrackerError`, so `main()` prints and returns 1 with no report and no HTTP call (AC-009), without new plumbing. `load_environment()` has already run inside `create_config`, and the loader calls it again defensively (idempotent), so a `.env`-only configuration enables the feature — proved by a test that leaves `create_config` unpatched.

### Component 5: Digest builder — **NEW** `ff_tracker/services/ai_digest.py`

```python
def build_digest(
    divisions: Sequence[DivisionData],
    challenges: Sequence[ChallengeResult],
    weekly_challenges: Sequence[WeeklyChallenge] | None,
    current_week: int | None,
    championship: ChampionshipLeaderboard | None,
) -> AIDigest
```

`AIDigest` and its nested `TypedDict`s are defined in this module (Decision 4). Every key is total; unknown values are `null`, so one shape covers all three modes.

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
         "playoff_status": "in_playoff_position"}
      ],
      "standings_note": "playoff_status is the current position against the top-four cutoff only; it is not a final outcome.",
      "matchups": [
        {"team": "Donut Lose", "score": 126.14, "projected_score": 120.0,
         "true_projection_diff": 6.14,
         "opponent": "In JJ We Trust", "opponent_score": 125.06,
         "opponent_projected_score": 130.0, "opponent_true_projection_diff": null,
         "margin": 1.08}
      ],
      "matchups_note": null,
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
- **Standings**: present in regular and playoff modes (formatters show them both), an empty list in championship mode (the formatters render no standings there). `rank` = the formatters' order (`_get_sorted_teams_by_division`: wins desc, points_for desc); `playoff_status` = `"in_playoff_position"` / `"outside_playoff_position"` from `TeamStats.in_playoff_position` — the current top-four cutoff position, not a seed and not a fate. `standings_note` carries that requirement in the payload (FR-002): *"playoff_status is the current position against the top-four cutoff only; it is not a final outcome."* — present whenever `standings` is non-empty and `null` in championship mode, in the same style as `matchups_note`.
- **Weeks remaining**: `max(0, reg_season_count - current_week)` when both are known, `null` when either is `None` (unknown regular-season length, or no detected week). Never a fabricated number.
- **Matchups**: one row per `WeeklyGameResult` of `division.weekly_games`; opponent true diff read from the mirror row via a per-division lookup keyed `(team_name, opponent_name)`; `None` when there is no mirror row (FR-002's omission rule). Empty list plus `"matchups_note": "No matchups this week"` when a league has none — the explicit sentence FR-002 requires; `null` otherwise.
- **Weekly challenges**: `[c for c in weekly_challenges if c.division == division.name]`, and in playoff/championship modes further filtered to `"position" in c.additional_info` (the formatters' own filter). This relies on `WeeklyChallenge.division` being the winner's league, which the merged spec-003 fix (`a78e6ba`) provides on this branch.
- **Season challenges**: global, with `"historical": true` in playoff and championship modes (formatters label them final at Week 14).
- **Playoffs**: `AIDigest["playoffs"]` is **one** `AIPlayoffRound` — `{"round": <semifinals|finals>, "matchups": [...]}` — with a **flat** matchup list spanning every division's matchups for that round, and **no seed key** (the formatters take the round from `divisions[0].playoff_bracket.round`, and `PlayoffMatchup` carries no seed field on the digest shape). Each row is the `AIPlayoffMatchup` TypedDict: round name, both team names and owners, both scores (`None` when a game has not started), winner (`None` when incomplete), and the division name. `null` outside playoff mode.
- **Championship**: `{"leaderboard": [{"rank", "team", "owner", "division", "score", "is_champion"}]}` from `ChampionshipLeaderboard.entries`; `null` outside championship mode.

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

class HTTPTransport(Protocol):
    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes: ...

def _urlopen(request: urllib.request.Request, timeout: int) -> bytes:
    """Default transport: one request, one read, no retries."""
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body: bytes = response.read()
    return body

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
4. `self._transport(request_obj, self._config.timeout)` inside `try/except` (the transport is `_urlopen` unless one is injected — Decision 6):
   - `urllib.error.HTTPError` → read **and discard** `e.read()` (never logged), close, `raise AIHTTPError(status=e.code, host=host, model=...)`.
   - `urllib.error.URLError` → if `e.reason` is a `TimeoutError`/`socket.timeout` → `AITimeoutError(timeout)`; else `AITransportError(host)`.
   - `TimeoutError` (incl. `socket.timeout`, same class on 3.10+) → `AITimeoutError(timeout)`.
5. Parse the envelope: `choices[0].message.content` (must be `str`), `choices[0].finish_reason`. `finish_reason == "length"` → `AITruncationError()` **even when the content parses** (AC-007). Anything missing or mistyped → `AIContractError(CONTRACT_REASON)` (an explicit check, not a caught `TypeError`).
6. Return the content string; the service parses *that* as JSON.

Logging (FR-009): INFO — model, status, latency ms; DEBUG — token counts from `usage` when present. Never the key, the request body or the response body. `host` comes from `urllib.parse.urlsplit(base_url).hostname` — the **only** URL fragment that may appear in a reason (FR-006/AC-005). `HTTPError.filename` holds the full URL, so it is never read, logged or formatted; the reason is built from `e.code` alone.

**Timeout bound** (spec v0.8): `urlopen(timeout=...)` bounds each socket operation, not the whole call, so a provider that trickles bytes can outlive `AI_SUMMARY_TIMEOUT`. That is now what FR-003 and Article X state, so this is no longer a deviation the plan must justify; the notice (`timed out after 120s`) is raised only when the socket operation itself times out, and LV-003 is the manual proof that the notice renders. No thread or `signal.alarm` wrapper is attempted: a timed-out `urlopen` cannot be cancelled, so a worker thread would hang process shutdown for the same duration it was meant to bound.

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

- **Prompt**: the constant states the JSON contract, the caps, the no-invented-facts rule, the commissioner voice, and the 60-word guidance floor (explicitly guidance, not a validated requirement). `build_system_prompt(config.user_prompt, league_names)` then appends two things: the **league scope** — the exact count and the names verbatim, built from the digest at request time (`League scope: this report covers exactly 3 leagues: "A", "B", "C". Return exactly 3 entries in "leagues" - one for each name above, using those names verbatim and in that order. Do not add, duplicate, split or rename a league.`), and the commissioner block only for a non-empty user prompt. The anchor exists because a live run returned four sections for three leagues; no matching rule can repair an extra section.
- **Request**: `AIRequest(system_prompt=build_system_prompt(config.user_prompt, [league["league"] for league in digest["leagues"]]), user_message=json.dumps(digest, ensure_ascii=False), max_tokens=config.max_tokens, reasoning_effort=config.reasoning_effort)`.
- **Retry (FR-003)**: `_generate` loops at most twice around *client call + parse + match*, catching only `AIContractError`. A contract failure on attempt 1 sets `attempts = 2` and re-sends the **same `AIRequest` object** — same prompt, payload, model and budget, no mutation. A second contract failure re-raises into the ordinary fail-open boundary. `AIHTTPError`, `AITransportError`, `AITimeoutError` and `AITruncationError` are not caught, so they surface after exactly one call. The retry lives here, not in the client, because the client must stay one-shot and honest about what happened; `_normalise` receives `attempts` and writes it into provenance.
- **Parse** (`_parse_response`): `json.loads` → structural checks (headline `str` non-empty; `leagues` list of dicts; `league` `str`; `paragraphs` list of `str` with ≥1 having a word after strip; `bullets` list of `str`; `season_note` `str` non-empty). Exactly one exception is converted — `json.JSONDecodeError` → `AIContractError(CONTRACT_REASON)`; every other rejection is an explicit `isinstance`/`len`/`strip` check that raises `AIContractError` itself. No `except TypeError`/`ValueError`/`KeyError`, and no `except Exception` (Decision 1). The parsed value is bound to `object` and narrowed level by level, so nothing returns `Any`.
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
| `email.py` | `<h2>🤖 Commissioner's Take (AI-generated)</h2>` + marker, `<p>` paragraphs (`_escape_html`), `<ul><li>`, attribution line; inserted after the weekly highlights, before the season challenges | one `<p>` |
| `json.py` | top-level `ai_summary` key (not positional): `headline`, `season_note`, `leagues`, `provenance` (incl. `attempts`) | `{"error": notice}` |
| `markdown.py` | `## 🤖 Commissioner's Take (AI-generated)`, `### <league>`, paragraphs, `- ` bullets, `_Generated by <model> · AI-generated text_` | one line (italic) |

The JSON `leagues` entries reuse our league names and the normalised paragraphs/bullets — no re-matching in the formatter (display never computes).

### Component 10: CLI wiring — **MODIFIED** `ff_tracker/main.py`

```python
ai_config = load_ai_summary_config()      # after create_config(), inside the existing try:
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

The loader runs **after** `create_config(...)` (which is what loads `.env`) and before any ESPN call — see Decision 3. The generation sits after weekly challenges and before the `--output-dir` branch, so **one call per run** covers five formats and both output modes (AC-003). Both `format_output(...)` call sites (`main.py:301` and `main.py:315`) pass `ai_summary=ai_summary`.

**Why the `::warning::` lives here and not in the service**: a workflow command is process output, not a report section, and Article IV forbids the service layer from printing presentation. The service returns the result and logs at WARNING; `main.py` is the only process-level writer.

`create_parser()`'s epilog gains an **AI Summary (optional)** paragraph, deliberately short (Gate 2 cut): that the feature is off by default, enabled only by `AI_SUMMARY_API_KEY` plus `AI_SUMMARY_ENABLED`, and the egress sentence FR-009 requires — team names, owner names and scores are sent to `AI_SUMMARY_BASE_URL`, the user prompt is sent verbatim, the key is never printed, and `-vv` logs the system prompt so it must not be used in CI. The variable list and defaults are **not** repeated here: they live in `.env.example` and the README, and a third copy is a third thing to drift.

### Component 11: Workflow — **MODIFIED** `.github/workflows/weekly-report.yml`

```yaml
env:                                   # workflow level: harmless everywhere
  PYTHONUNBUFFERED: 1
  AI_SUMMARY_ENABLED: ${{ secrets.AI_SUMMARY_API_KEY != '' }}
  AI_SUMMARY_BASE_URL: ${{ vars.AI_SUMMARY_BASE_URL }}
  AI_SUMMARY_MODEL: ${{ vars.AI_SUMMARY_MODEL }}
  AI_SUMMARY_TIMEOUT: ${{ vars.AI_SUMMARY_TIMEOUT }}
  AI_SUMMARY_MAX_TOKENS: ${{ vars.AI_SUMMARY_MAX_TOKENS }}
  AI_SUMMARY_REASONING_EFFORT: ${{ vars.AI_SUMMARY_REASONING_EFFORT }}
  AI_SUMMARY_MAX_PROMPT_CHARS: ${{ vars.AI_SUMMARY_MAX_PROMPT_CHARS }}

# and, on the "Generate fantasy football report" step only:
env:
  AI_SUMMARY_USER_PROMPT: ${{ vars.AI_SUMMARY_USER_PROMPT || secrets.AI_SUMMARY_USER_PROMPT }}
```

- `secrets` is legal in `env:`, illegal in `if:` — exactly the FR-007 trap. The expression renders the literal `true`/`false`.
- **The optional settings are repository variables**, so they are changed in settings rather than YAML: an unset variable renders empty, which the loader already reads as the code default. `AI_SUMMARY_USER_PROMPT` may be a variable or a secret (`vars` wins); it sits on the report step alone, its only consumer, because a secret prompt must not reach `actions/checkout`, `setup-python`, `setup-uv` or the `.env` writer. A prompt that must not be published belongs in the secret: variables are unmasked in logs.
- In the "Create .env file from secrets" step, append **only when the flag is `true`**:
  ```bash
  if [ "$AI_SUMMARY_ENABLED" = "true" ]; then
    echo "AI_SUMMARY_ENABLED=true" >> .env
    echo "AI_SUMMARY_API_KEY=${{ secrets.AI_SUMMARY_API_KEY }}" >> .env
  fi
  ```
  These settings are **inherited from the step's `env:` and never written to `.env`**: the writer handles `LEAGUE_IDS`, the ESPN cookies and `AI_SUMMARY_ENABLED`/`AI_SUMMARY_API_KEY` only. The report process sees the variables directly (and `load_dotenv` does not override an already-set variable), so no multiline quoting problem arises.
- No `if:` anywhere in the file mentions `AI_SUMMARY_ENABLED` (WC-001).
- The `::warning::` needs no workflow change: the service's reason is printed to stdout by the step, and Actions surfaces it as an annotation.

### Component 12: Documentation — **MODIFIED**

- `.env.example`: the seven variables, commented, with the real defaults (`https://opencode.ai/inference/openai/v1`, `glm-5.3-flash`, `120`, `8000`), and the egress note.
- `README.md` → Configuration: an "AI Summary (optional)" subsection — what leaves the machine, how to enable with a key alone, that `.env.example` carries the defaults, and that `ff-championship`/`ff-season-recap` ignore it.
- `CHANGELOG.md` → `## [Unreleased]` / `### Added - AI Summary (optional)`.
- **No `AGENTS.md` change** (Gate 2 cut): no FR requires it, and a fourth copy of the feature description in the file every agent reads is exactly the drift this plan avoids elsewhere.

---

## File Inventory

**New (11)**
| File | Contents |
|---|---|
| `ff_tracker/models/ai_summary.py` | `AISummaryLeague`, `AIProvenance` (incl. `attempts: 1\|2`), `AISummary`, `AISummaryUnavailable`, `AISummaryResult` |
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
| `ff_tracker/models/division.py` | `reg_season_count: int \| None` + validation | FR-002 |
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
| `tests/test_json_formatter.py` | `ai_summary` cases + AC-001 (JSON) | Task 8 |
| `tests/test_main_cli.py` | call count, warning, config-error cases | Task 11 |

**Also modified (3, docs)** `.env.example`, `README.md`, `CHANGELOG.md`.

**Deliberately untouched**: `ff_tracker/championship.py`, `ff_tracker/season_recap.py`, `display/season_recap_*.py`, `display/factory.py`, `services/season_recap_service.py`, `services/championship_service.py`, `.github/workflows/championship-report.yml`, `.github/workflows/season-recap.yml`, `AGENTS.md` (Gate 2 cut — no FR requires it), `.specify/specs/**` (the spec is the authority; the plan does not edit it).

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

Thirteen tasks, detailed in [tasks.md](./tasks.md). Grouped so the suite is green after every one:

| Phase | Tasks | Outcome |
|---|---|---|
| 1 — Groundwork | 1–4 | model field, AI models, exception taxonomy, configuration — all unit-tested, nothing wired |
| 2 — Payload & provider | 5–6 | digest builder, HTTP client (both testable in isolation, still unused by `main`) |
| 3 — Narrative | 7 | prompt, request, parse, league matching, normalisation, fail-open boundary — one task, because the happy path cannot pass while any of them is a stub (Gate 2) |
| 4 — Rendering | 8–10 | protocol signature + JSON, then console/markdown, then sheets/email |
| 5 — Wiring | 11 | one call per run, `::warning::`, `--help` egress paragraph |
| 6 — Ops & docs | 12–13 | workflow guard, README/`.env.example`/CHANGELOG |

**Signature-ordering constraint**: mypy requires an override to accept every parameter of the abstract method, so task 8 changes `display/base.py` **and all five** concrete `format_output` signatures in one commit (only JSON renders). Tasks 9–10 then add rendering to the other four without touching any signature. Splitting them the other way round would leave a red `mypy ff_tracker`.

---

## Constraints Discovered in the Existing Code

Recorded because they shape the implementation and are not visible from the spec alone:

1. **`current_week` can be `None`.** `main.py:265` guards weekly challenges on `espn_service.current_week and > 0`; if detection failed, the formatters omit weekly sections too. The digest emits `"week": null` / `"weeks_remaining": null` rather than inventing a week, and `matchups_note` follows the matchups list (empty → "No matchups this week"), not the week. FR-002 does not say what happens here; this is the plan's decision, and `null` (rather than an omitted key) keeps the `TypedDict` total.
2. **`SeasonRecapService` builds `DivisionData` without league settings** (`ff_tracker/services/season_recap_service.py:411`). That call site passes no `reg_season_count`, and with `int | None` the model records "unknown" instead of asserting `14`; it is a season-recap data path, never the AI digest's.
3. **`HTTPError` carries the full URL in `.filename`** (path and query included) even though `str()`/`repr()` omit it. AC-005 forbids that path from ever appearing, so the client builds reasons from `e.code`, the parsed host and the model, and never logs `e.filename`, the exception object or its traceback.
4. **The 5 formatters each recompute the mode** from `any(d.is_playoff_mode …)` and `championship is not None`; `ReportContext` still exists in `display/base.py` but no formatter reads it (the merged typing commit removed the `context` parameter). The digest's local copy is the sixth, as the spec states — not an extraction opportunity.
5. **`WeeklyChallenge.division` is the winner's league only because of the merged spec-003 fix** (`a78e6ba`). This branch is based on it; had it not merged, FR-002's per-league weekly challenges would be unattributable.
6. **Baseline mypy is clean on this branch** (`Success: no issues found in 41 source files`) — the 27 pre-existing errors the Gate 2 brief refers to were fixed in `a78e6ba`. The bar is therefore zero new errors, not "the same 27".
7. **`urlopen` returns `HTTPResponse` and its second positional argument is `data`.** The transport seam therefore cannot be `urlopen` itself; it is the `_urlopen(request, timeout) -> bytes` wrapper (Decision 6), and one test must patch `urllib.request.urlopen` to exercise that wrapper — every other client test injects a fake and would never run the production path.
8. **`load_environment()` runs only inside `create_config()`.** A loader that reads `AI_SUMMARY_*` must call it itself or run after `create_config`; the plan does both (Decision 3), and Task 4 proves a `.env`-only setup with `create_config` unpatched.

---

## Testing Strategy

No network: `FakeAIClient` implements `AIClient`; `FakeTransport` implements `HTTPTransport`; `unittest.mock.patch` for `ESPNService`/`create_config` at the CLI boundary, as `tests/test_main_cli.py` already does. One test patches `urllib.request.urlopen` to drive the production `_urlopen` wrapper. Fixture data lives in `tests/ai_fakes.py` (canned responses + builders), not on disk.

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
| AC-018 placement in console/markdown/email/sheets, notice in the same slot, JSON unchanged | `test_ai_summary_rendering.py` — per-format marker order (`weekly < ai < season`), notice order, JSON key |
| AC-019 contract-failure retry then success: 2 calls, `attempts: 2`, identical request | `TestRetry::test_contract_failure_then_success_retries_once`, `test_retry_reuses_the_identical_request` |
| AC-020 two contract failures: 2 calls, notice, exit 0 | `TestRetry::test_two_contract_failures_stop_after_two_calls` |
| AC-021 no retry on HTTP 500 / transport / timeout / truncation | `TestRetry::test_non_contract_failures_are_not_retried` (4 ids) |
| AC-022 first-attempt success records `attempts: 1` | `TestRetry::test_first_attempt_success_records_one_attempt` |
| WC-001 static workflow check | `tests/test_ai_summary_config_workflow.py` (string assertions on the YAML, no YAML dependency) |
| LV-001…004 | manual, once, against the live provider (not in the suite) |

Guards the ACs do not name but Gate 2 required:

| Guard | Where |
|---|---|
| `test_generate_propagates_programming_errors` — `AttributeError` from the digest builder escapes `generate` | `test_ai_summary_service.py` |
| `_urlopen` (production transport) reads the response body and passes `timeout=` | `test_ai_client.py` via `patch("urllib.request.urlopen")` |
| Digest key set compared against a golden, recursively | `test_ai_summary_digest.py` |
| `.env`-only configuration enables the feature with `create_config` unpatched | `tests/test_config.py` |

---

## Risk Assessment

### Risk 1: The fail-open boundary is too wide (or too narrow)
**Likelihood**: Medium · **Impact**: High
**Mitigation**: catch exactly `AISummaryError`; convert only `JSONDecodeError` in `_parse_response`; `test_generate_propagates_programming_errors` asserts a stubbed digest builder raising `AttributeError` crashes the run instead of degrading to "AI summary unavailable". **Fallback**: none needed — this is the design.

### Risk 2: Normalisation is subtly non-deterministic or contradicts the caps
**Likelihood**: Medium · **Impact**: Medium
**Mitigation**: `split()` word counting, no regex, no sentence detection, pure functions; AC-013 asserts two runs are byte-identical.

### Risk 3: A formatter silently changes existing output
**Likelihood**: Low · **Impact**: High
**Mitigation**: AC-001's prefix/suffix test for all five, run before wiring (tasks 8–10) and after (task 11). The insertion point never moves an existing line (Decision 7).

### Risk 4: The workflow guard is bypassed or the secret leaks into logs
**Likelihood**: Low · **Impact**: High
**Mitigation**: WC-001 test reads the YAML; `AI_SUMMARY_API_KEY` is only ever an `env:` value and a `.env` line; the client never logs requests; AC-005 greps every artefact.

---

## Performance Considerations

With the feature off, `load_ai_summary_config()` is one dict read and an `os.getenv` loop; the run budget is unchanged (Article X, as scoped in Complexity Tracking).

With it on, the run gains one provider call: 7.7–34.4 s in the spike, bounded by `AI_SUMMARY_TIMEOUT` (default 120 s). A contract failure adds exactly one identical retry (two calls, roughly two socket-read timeouts worst case); nothing else is retried and nothing is cached. One call per run in the normal case regardless of league or format count, which is the only performance requirement this feature can enforce.

Digest size is bounded by the data: 3–4 leagues × (≤16 standings rows + ≤8 matchup rows + ≤7 challenges) — a few KB of JSON, far inside any model's context.

---

## Security Considerations

- The key exists only as an environment value, a `.env` line and `AISummaryConfig.api_key` (`field(repr=False)`). It is never a CLI flag, never a format argument, never logged, never rendered.
- Request and response bodies are never logged at any level (they carry team/owner names, PF/PA and — in principle — anything the model echoes). Only model id, status, latency and token counts are logged.
- The system prompt is logged at DEBUG only, because a public repo's Actions logs are world-readable. FR-008's CI record is the `AI_SUMMARY_USER_PROMPT` value behind the workflow's `vars`/`secrets` expression — a repository variable or a secret, not a file in git (FR-008/FR-009).
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
- **The exception hierarchy is part of the boundary**: `AISummaryError` and its five subclasses derive from `Exception`, not from `FFTrackerError`. That is deliberate and load-bearing — if a narrative failure ever escaped the boundary, `main()` must not render it as `Error: ...` with exit 1, which is exactly what an `FFTrackerError` subclass would do. Deriving from the project's own base class would convert a cosmetic failure into a denied report by inheritance alone.
- **Transport failures map inside the client, not outside it**: `HTTPError`, `URLError`, timeouts, and the mid-body `OSError`/`http.client.HTTPException` raised by `response.read()` all become `AISummaryError` subclasses before they leave `complete()`. A `ConnectionResetError` escaping as an `OSError` would be caught by `main()`'s unexpected-error branch and deny the report, so this mapping is a fail-open requirement, not error-polish.

### Article X — Performance Requirements (provider latency)

**Deviation**: the 5-second typical run no longer holds with the feature enabled.

**Spec reasoning (v0.8)**: 7.7–34.4 s per call in the spike, bounded by `AI_SUMMARY_TIMEOUT` **on each socket read**. There is no wall-clock deadline, so a pathologically slow provider can exceed the configured value. The 5-second budget applies to the deterministic report with the feature off.

**Boundary this plan implements**: off by default; zero added network I/O when off; one call per run when on, plus at most one identical retry after a contract failure; no other retries, no streaming, no per-format second call; no thread or signal wrapper (a timed-out `urlopen` cannot be cancelled, so a worker thread would hang shutdown for the same duration it was meant to bound). A caller that cares about schedule duration leaves the feature off, which is the default.

### Held without a governing FR

- **The non-default `User-Agent` is a hard requirement.** No FR names it, but the default endpoint sits behind Cloudflare, which rejects `Python-urllib/*`; without an identifying header every call fails at the edge. It is recorded here because a future "remove the unused header" cleanup would silently break the default endpoint, and no acceptance criterion would go red.

### Not deviated
Articles I (no `Any`, no suppressions), II (frozen validated models), IV (services never import display; the `::warning::` is emitted in `main.py`, not the service), V (no extra ESPN calls), VI (one protocol, five formats), VII (docstrings/names, comments only for the non-obvious), IX (no new flags; `--help` states the egress).

---

## Open Technical Questions

None open. Decisions the spec leaves to the plan, recorded here so Gate 3 can object to them specifically:

1. Digest shape is a `TypedDict` document in `services/ai_digest.py` (Decision 4) — not a public schema, not the JSON formatter's output, and not an Article II model.
2. AI configuration sits beside `FFTrackerConfig` (Decision 3), so the other two CLIs never validate `AI_SUMMARY_*`; the loader calls `load_environment()` itself and `main.py` invokes it after `create_config`.
3. `reg_season_count` is `int | None = None`; unknown means `"weeks_remaining": null` rather than a fabricated `14` (Decision 5).
4. The trailing "Game data" line is the console/markdown footer for FR-005's placement rule; sheets appends at the end because its game-data line is mid-report (Decision 7).
5. `current_week is None` emits `"week": null` / `"weeks_remaining": null` (Constraints 1).
6. `provenance.truncated` is always emitted in JSON (`false` when nothing was cut); the spec allows absent-or-false.
7. The markdown TOC does not gain an entry for the new heading (Decision 7).
8. The transport is `_urlopen(request, timeout) -> bytes`; `urlopen` itself cannot be the seam because it returns `HTTPResponse` and takes `data` as its second argument (Decision 6).

### Spec nits for the next spec edit (not edited here)

- **Configuration table**: `AI_SUMMARY_TIMEOUT` is still described as "Whole-call timeout in seconds". FR-003 (v0.8) and Article X now say the bound is per socket operation with no wall-clock deadline, so the table row should say "Per-socket-read timeout in seconds". One line; belongs to the owner's next spec commit, not to this plan.

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
| 1.1 | 2026-10-21 | AI Agent | Gate 2 revisions. Fail-open breadth narrowed: only `JSONDecodeError` is converted in `_parse_response`, every other rejection is an explicit check, and `test_generate_propagates_programming_errors` is a done-criterion. Digest adopted as a `TypedDict` document (total keys, `null` for unknown) with a golden recursive key-set test. Transport corrected to the `_urlopen(request, timeout) -> bytes` wrapper plus a `patch("urllib.request.urlopen")` test, because `urlopen` returns `HTTPResponse` and takes `data` second. Config load ordering stated: the loader calls `load_environment()` and runs after `create_config`, with a `.env`-only test. `reg_season_count` changed to `int \| None = None` so "unknown" is not a fabricated 14. Tasks 7 and 8 merged into one narrative task (13 total, renumbered) so the green-suite-per-task invariant holds. Cuts applied: the `--help` variable table reduces to the egress paragraph, `AI_SUMMARY_MODEL` leaves the workflow `env:`, the `AGENTS.md` paragraph is dropped. Console/championship placement rationale corrected (the report ends on the season-challenge table). Spec nit recorded: the configuration table still calls `AI_SUMMARY_TIMEOUT` a whole-call timeout |
| 1.2 | 2026-10-21 | AI Agent | Gate 3 bookkeeping: the Article III boundary now records why the AI exception hierarchy derives from `Exception` rather than `FFTrackerError` (so a narrative failure cannot be rendered as a report error) and why transport failures, including mid-body `OSError`/`HTTPException`, are mapped inside the client; a new "Held without a governing FR" note records the non-default `User-Agent` as a hard requirement of the default endpoint, which no criterion covers. |
| 1.3 | 2026-10-21 | AI Agent | Spec v0.12: the section moves from the report's end to between the weekly highlights and the season challenges in console, markdown, email and sheets (JSON unchanged), so Decision 7's placement table and Component 9 are restated and AC-001 becomes a mid-document insertion; `_generate` retries once for `AIContractError` only, reusing the same request, with `provenance.attempts` (1 or 2) recording it; the system prompt names the exact league count and the names, built from the digest at request time, so `prompt_sha` now hashes the composed prompt; AC-018…AC-022 added to the mapping and the performance note moved from "no retries" to "one identical retry". |
| 1.4 | 2026-10-21 | AI Agent | Gate 3 delta: Decision 8 now hashes the composed prompt only (the commissioner block is already inside it, so appending the user prompt hashed it twice); the Scope line and the spec reference were corrected to v0.13 and the new placement; AC-018's mapping now covers playoff and championship modes plus the no-weekly-challenges case; the logging boundary is recorded as league names only, in the DEBUG prompt line, per FR-009 v0.13. |
