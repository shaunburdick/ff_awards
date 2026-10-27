# Implementation Plan: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: Frozen at v2.2 — Gate 2 closed; Phase A may start
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-27
> **Version**: 2.2
> **Spec**: [spec.md](./spec.md) v0.26 (authority — this plan decides implementation only)
> **Gate rulings**: [challenge-ledger.md](./challenge-ledger.md) (settled rows are settled; Gate 2 closed at v2.2)
>
> Sections 1–12 and Decisions 1–8 describe the **shipped** feature and are unchanged except where
> this amendment touches them. The amendment lives in "Amendment Architecture" (Decisions 9–17),
> Components 13–16, and the Phase 1 / Phase 2 rows added throughout.

## Scope

Add one optional section to the weekly report (`ff-tracker`), in all five formats, generated once per run from the report's own domain models, rendered between the weekly highlights and the season-long challenges, and never able to stop the report. Nothing else changes: no new CLI, no new format, no new dependency, no change to `ff-championship` or `ff-season-recap`.

**Out of scope** (spec "Not doing", unchanged): season recap and championship CLIs, other provider families, streaming/caching, retries beyond the single contract retry FR-003 allows, a user-authored system prompt, `weekly_games` in JSON, per-format opt-out, factual verification, format arguments for this feature.

### The amendment this plan now also covers (spec v0.17–v0.26)

Two phases, specced and approved together, delivered and reverted separately. **Phase 1 ships first**; Phase 2 is built against a merged Phase 1 and never against an unmerged one.

- **Phase 1 — prompt input only (FR-011, FR-012).** A per-league `history` block and one league-wide block (`overall_standings`, `weekly_extremes`), both derived from data the report already loads, plus `provenance.history_weeks`. No new variable, no new call, no storage. Shipped alone it is today's run with a larger prompt; one `git revert` removes it.
- **Phase 2 — the memory log (FR-013, FR-014).** Off by default. On: one gist, one `memory.json`, one read before generation and one write after, append-only, the whole archive in the prompt under two rules. Off means zero store calls and output identical to a Phase-1 run. One `git revert` removes it.

Neither phase renders anything: no format gains a section, line or field, and the notice path is untouched.

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

### The amendment adds no dependency either
Phase 1 makes no network call at all. Phase 2's store is GitHub's gist API over the same stdlib `urllib`/`json`, with the same injectable transport the provider client has, so `pyproject.toml` is untouched by both phases and the suite still needs no network: a fake client, a fake store and checked-in fixtures. `tests/fixtures/` gains the Phase-1 golden (see Decision 17); nothing else is read from disk at run time.

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

## Amendment Architecture (spec v0.26)

Phases 4–6 for the amendment. Decisions 1–8 stand untouched: the fail-open boundary is still one `try` around `_generate`, the digest is still a `TypedDict` document, the client is still one-shot, and no formatter learns anything new.

### Decision 9: History is its own module; the league-wide view stays in the digest builder

`ff_tracker/services/ai_history.py` (new) holds FR-011's block and its `TypedDict`s: `build_history(games, teams, anchor) -> AILeagueHistory | None`. It is the compromise between two bad shapes — ~130 lines of game arithmetic is more than a payload assembler should carry, and a second module for the league-wide view would be two small functions that need the same ranking helper and the same weekly rows the digest already unpacks. So:

- `ai_history.py` — FR-011 only: rank by week, head-to-head, streak, trend, best/worst, margins.
- `ai_digest.py` — `history` per league (one line, delegating) plus `overall_standings` and `weekly_extremes`.
- `services/rankings.py` — one comparator, shared with the formatters (Decision 10).

Rejected: everything in `ai_digest.py`, which turns one payload module into a 500-line mix of computation and assembly; and a new module per block, which is three modules for three keys.

### Decision 10: One comparator in `services/rankings.py`, called by the digest and by the formatters

FR-012 requires `overall_standings` to be in exactly the order the console's overall table produces, and the ledger forbids a second comparator "even when it looks equivalent". `rank_overall_teams(divisions, limit=None) -> list[TeamStats]` is `sorted(all_teams, key=lambda t: (t.wins, t.points_for), reverse=True)` with today's `limit` semantics (`None` or `<= 0` means every team). Both of `BaseFormatter`'s sorters become delegates — `_get_overall_top_teams` and `_get_sorted_teams_by_division` (which is the same comparator over one division's teams) — so the four `limit=20`/`max_teams` call sites (`console.py:442`, `markdown.py:433`, `sheets.py:212`, `email.py:481`), the per-division tables' order and their byte output are untouched; the digest calls it with no limit, because FR-012 carries every team where the console stops at 20, and `_standings_rows` calls it with one division so the per-league standings use the same rule.

Rejected: duplicating the sort in the digest and relying on AC-027's agreement assertion — the assertion is still worth having, but as the only guard it lets two comparators ship and drift between releases. **What AC-027's agreement case can and cannot prove**: once both sides call `rank_overall_teams`, the rendered table and `overall_standings` are the same list, so the assertion guards the *rendering* order (that the console has not re-sorted, truncated differently, or read another collection) and not the comparator's correctness — the comparator is guarded by its own `limit` fixtures. The >20-team fixture is where the two sides differ on purpose (the console stops at 20, the digest does not), so the comparison there is the rendered 20 rows against the first 20 of `overall_standings`, and "every team appears" is a separate fixture with its own count.

Rejected: putting the function in `models/` (Article II forbids business logic there) and importing `display` from a service (Article IV forbids it, and no service does today). Display importing a service is the downward direction Article IV permits; `services/__init__.py` imports nothing from `display`, so the import is acyclic. The season-recap formatters keep their own copies of this sort; that path is outside spec 009 and is deliberately not touched.

### Decision 11: History's newest rankings are the per-league standings list itself

`_league_digest` builds `rows = _standings_rows(division)` once. Its `standings` key is `rows` in regular and playoff modes and `[]` in championship mode (the formatters show none there); `build_history(..., anchor=rows)` receives the same list. In regular and playoff modes the anchor therefore *is* the digest's `standings[]`, so FR-011's "the latest week present is taken from `standings[].rank` verbatim" holds by construction rather than by agreement, and AC-024's second fixture — a `DivisionData.games` collection missing a week `TeamStats` counts — cannot move the newest column. In championship mode the digest shows no standings, so the anchor is the report's own ranking rather than nothing: still not a second comparator, and the block stays present, which AC-025 requires.

Earlier weeks are recomputed from `games` with `week <= N` under the same wins-then-points-for order; ties keep the anchor's relative order, so every week in the block is a total order.

### Decision 12: History's null cases and orderings, where FR-011 is silent

- `teams[]` follows the anchor's order, so the block reads in the same order as the standings beside it.
- `head_to_head[]` is sorted by opponent name: the spec fixes the row's keys, not its order, and the prompt reads better in a stable order than in game order.
- `streak`, `best_week`, `worst_week` and `average_margin` are `null` for a team with no game in the collection (adopted into FR-011 by the review): a real division plays every week, but a tolerant `games` collection can still miss a team, and omitting the team instead would contradict "for every team".
- A tie is a loss in `GameResult`'s own terms (`won` is `score > opponent_score`), so a tie extends a loss streak. The block invents no third `kind`.

### Decision 13: The store is a `MemoryStore` protocol; one `MemorySession` per run owns the lifecycle and never raises

- **`MemoryStore` (Protocol)**: `load() -> bytes | None` (`None` when the gist or `memory.json` is absent) and `save(data: bytes) -> None`. `GistMemoryStore(memory_config, transport=None)` is the production implementation with the same *shape* of injectable seam as the provider client, but its own small `(Request, timeout) -> bytes` wrapper inside `ai_memory.py`: `ai_client.py` is shipped and correct, and a rename there to share four lines would edit a file neither phase otherwise needs to touch. `FakeMemoryStore` lives in `tests/ai_fakes.py`: it records calls and can be told to fail per call.
- **`MemorySession(memory_config, season, week, store=None)`** owns one run: `open()` performs the single read and sets `read_status`, `entries`, `weeks` and a `parsed` flag; `commit(summary)` performs at most one write and sets `write_status`. Each call appends at most one warning string.
- **It never raises.** `GistMemoryStore` maps transport outcomes onto `AIMemoryStoreError(kind: auth | not_found | server | transport | timeout)`; `MemorySession` maps the kind onto FR-014's status map and decides whether that outcome warns. This is what keeps Decision 1's `try/except AISummaryError` exactly as wide as it is today: memory never enters that boundary, so no memory outcome can become a notice, and the taxonomy gains no new member that a narrative failure could be confused with.
- **The write happens after the narrative exists.** `_generate` calls `memory.open()` first, builds the block from what it read, calls the client, and only once `_normalise` has returned an `AISummary` does it call `memory.commit(summary)` — because the entry's `generated_at` is `summary.provenance.generated_at`. One instant is computed once, inside `_normalise`, and the entry copies it, so the file and the report cannot disagree; a rejected narrative never reaches `commit`, which is FR-014's `"skipped"` without a branch of its own.
- `AISummaryService.__init__(config, client, memory: MemorySession | None = None)`.
- **Read 404 is `"none"`** (FR-014 now says so): a deleted or mistyped gist id reads as "nothing published yet", and the write that follows is AC-032's 404 failure with its warning — which is the signal an operator can act on.

Rejected: the service constructing the store from config — a fake, a test and the throwaway backfill script could then not substitute one, and the backfill would have to reach into config for a seam. Rejected: `main.py` performing the read and the write around `generate` — the write lands after `provenance` is built, so `memory_write` would have to be patched into a frozen model from the CLI, and FR-014's lifecycle would live in the CLI.

### Decision 14: Provenance carries the tri-state, and `None` is how "memory off" stays absent

`AIProvenance` gains `history_weeks: int = 0`, `memory_read: str | None = None`, `memory_write: str | None = None` and `memory_weeks: list[int] | None = None`, validated as all-off or all-on, with FR-014's two vocabularies and `history_weeks >= 0`. `json.py` emits `history_weeks` on every narrative and each memory key only when it is not `None` — which is the mechanism AC-028 checks: with memory off no memory key exists, so the document matches the Phase-1 golden.

`history_weeks` is defaulted rather than required because twenty-odd fixtures construct `AIProvenance` directly; its value is asserted on real fixtures (T101, T106) rather than trusted. The service passes `history_week_count(digest)`, a helper in `ai_digest.py` that counts the union of `weeks_included` across leagues, so the count and the block cannot disagree.

All four fields exist only when a narrative renders, which is now FR-005's wording: the notice path is `{"error": …}` with no `provenance` at all, so a failed narrative records its `"skipped"` on the session where a test can see it and not in the report. `None`-means-absent is therefore the whole rule: `None` for a field is what keeps it out of JSON, and the three memory fields are all set or all absent.

### Decision 15: Three prompt pieces; `prompt_sha` hashes the first, and the DEBUG line reuses the block renderer in redacted mode

```
instructions  = build_system_prompt(user_prompt, league_names)   # template + league-wide rules + scope + instructions block
block         = build_memory_block(entries) if entries else None  # memory on, and something stored
system_prompt = instructions + ("\n\n" + block if block else "")
prompt_sha    = prompt_sha(instructions)
```

- `prompt_sha` keeps hashing the bytes it hashed before this amendment, so archived reports stay comparable and AC-028's memory-off comparison is possible at all. The memory block sits outside it, as FR-008 requires; the league-wide rules sit inside it, because they are instructions and a change to them must move the hash.
- Every piece of prompt prose is a module constant in `ai_summary_service.py`: `SYSTEM_PROMPT` (bytes unchanged), `LEAGUE_WIDE_RULES` (Phase 1, two strings), `MEMORY_HEADING`, `MEMORY_INTRO`, `MEMORY_RULES` (Phase 2). One file to review for a prompt edit.
- `build_memory_block(entries)` renders the archive in week order, each entry under its week tag, introduced as *what you published in earlier weeks*, then the two rules. `render_memory_block(entries, redact=True)` is the same function with each entry's prose replaced by its week tag, and that rendering is what the DEBUG line appends (FR-009): the block's shape is visible, its paragraphs are not. One function, two renderings, so the log cannot describe a block the model did not receive.
- **How the rules are tested without asserting prose**: they are constants, and each test asserts every constant appears verbatim in the composed prompt (and that no block appears with memory off). Rewording a rule keeps the test green; deleting one fails it. No test contains a sentence of prompt text.

### Decision 16: One predicate suppresses a write; one key replaces an entry

- `_can_key_entry(season, week) -> bool`: `2000 <= season <= 9999` and `1 <= week <= 18`, checked once inside `commit` before any store call. False is `"skipped"` with no store call, so a pre-kickoff `current_week` of 0 or negative writes nothing — FR-014's only suppressed write (AC-033). The narrative-failure case reaches the same status by never calling `commit`.
- `merge_entry(archive, entry)` replaces the entry whose `week` equals the run's week in place, and appends otherwise, then writes the list in week order. That is the only mutation and the only removal, so a dispatch re-run cannot stack a second take (AC-032) and every other entry's value is unchanged — including any key the tool does not know, which is carried through a successful merge untouched.
- The current week is **not** filtered out of the block. On a same-week re-run the read has already happened, so the previous take for that week is in the archive and is sent, and `memory_weeks` includes it. FR-014 forbids selection, windows and dropping, so excluding it would be the compaction rule the spec deletes; a re-run simply sees what it last said and is told to escalate or retire it.
- **Entries are keyed by week inside a file whose `season` is fixed at creation, and that has one consequence worth stating plainly**: a Week 6 run in 2027 against a 2026 file replaces the 2026 Week 6 entry — hand edits included — because the key is the week and the tool does not compare the file's season to the run's. The file is retired by the operator at a season boundary; starting a new one is a hand action (`memory.json` renamed or emptied in the gist), and FR-014's header rule means the tool never does it. The plan does not add a season check to the write: that would be the rollover rule the spec deletes, and it would make a legitimate mid-season correction impossible.

### Decision 17: The Phase-1 golden is captured in Phase 1, and recapturing it is a reviewed decision

AC-028 compares memory-off output against a golden captured at the Phase-1 commit. The capture is therefore **the last Phase-1 task** (T106), so the artifact exists, committed, before any Phase-2 test can read it. The fixture pins:

| Pinned | How | Why |
|---|---|---|
| model | `AI_SUMMARY_MODEL` set to the golden's id | a default-model bump must not fail a memory criterion |
| `generated_at` | the `datetime` **attribute on `ff_tracker.services.ai_summary_service`** replaced with a frozen class | the module imports the class, so patching `datetime.datetime` globally would leak; the module attribute is the only seam |
| prompt | `AI_SUMMARY_USER_PROMPT` empty | `prompt_sha` is in the golden and moves with the prompt |
| report data | the AC-027 three-division fixture built in `ai_fakes`, `year=2026`, week 6 | a small, stable, fully-synthetic report that already exists for another criterion |
| narrative | one canned response | the section's text is part of the compared bytes |
| format args | none | they change bytes in three formats |
| CLI inputs | `sys.argv` and the league ids patched, `ESPNService` patched, `--output-dir` into a temporary directory | `main()` parses args and would otherwise read the real environment |
| provider | `ff_tracker.main.OpenAICompatibleClient` replaced by a fake | one canned response, no network |

That is the full patch set: `sys.argv`, the league ids, `ESPNService`, the provider client, and `ff_tracker.services.ai_summary_service.datetime`. T106 and T208 use the same harness, so the two phases compare identical paths rather than two re-implementations of one.

The golden is one JSON file, `tests/fixtures/ai_summary_phase1_golden.json`, holding the console, sheets, email and markdown output as exact strings and the JSON format's document as a parsed object (dict equality, not string equality, so indentation cannot fake a pass). **No helper regenerates it at test time**, and the capture entry point is not importable from the test module.

**Recapture procedure** (in T106's done-when, and the only accepted way to change the file):

1. Run the harness from a clean tree at the commit whose output is being captured, with the pins above, and commit the result in its own commit with the reason in the message.
2. A recapture must still prove what the criterion is for: the five formats render the same *narrative and the same deterministic sections* as the golden's own copy of them, so the diff is reviewed line by line as output, not accepted as a blob.
3. **What may break it**: a deliberate change to a rendered format, to the digest-backed data the report shows, or to `SYSTEM_PROMPT`/`LEAGUE_WIDE_RULES` (which moves `prompt_sha`). **What may not**: anything memory-related. A Phase-2 change that fails AC-028 and is "fixed" by recapturing the golden is exactly the regression the criterion exists to catch, and a recapture in the same commit as a memory change is a review reject.

### Phase 2 failure policy, mapped

| Situation | `memory_read` | `memory_write` | Warnings under `GITHUB_ACTIONS` | Proved by |
|---|---|---|---|---|
| memory off | absent | absent | none | AC-028 |
| absent file, or an empty gist | `"none"` | `"ok"` (a file is created) | none | AC-029 |
| read 404 (gist gone or id mistyped) | `"none"` | `"failed"` (the write 404s too) | one, for the write | AC-031 (read case), AC-032 (its write) |
| read 401/403 | `"failed"` | attempted; `"failed"` when it 401s too | one for the read, and one for the write when it fails — never more than one per cause | AC-031, AC-032 |
| read 5xx / transport / timeout | `"failed"` | attempted; `"ok"` if the store recovers | none for the read | AC-031 |
| write 404 / 401/403 / 5xx / transport / timeout | as read | `"failed"` | one, naming scope or authentication | AC-032 |
| file will not parse as the archive shape | `"none"` | `"skipped"` — the file is not overwritten | one | AC-033 |
| narrative unavailable | as read | `"skipped"` — the session's status; the notice object carries no provenance, so nothing prints it | none for memory | AC-020, AC-032 |
| week not 1–18, or season not a 4-digit year | as read | `"skipped"`, no store call | none | AC-033 (write guard) |

Every row ships the report, exits 0, and puts nothing in any format's notice slot: the section was produced, so the notice is not the channel (FR-006). "One per cause" is the rule a test asserts — `out.count("::warning::")` is exact in each fixture, so a duplicated line fails, and the paired authentication-read-plus-failed-write fixture counts **two**: one line for each cause.

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

**As shipped** (the amendment adds one field; nothing below is a change to correct):

```python
@dataclass(frozen=True)
class AISummaryConfig:
    enabled: bool = False
    api_key: str = field(default="", repr=False)      # never in a repr/traceback
    base_url: str = DEFAULT_AI_BASE_URL               # https://opencode.ai/inference/openai/v1
    model: str = DEFAULT_AI_MODEL                     # deepseek-v4.1-flash
    timeout: int = DEFAULT_AI_TIMEOUT                 # 120
    max_tokens: int = DEFAULT_AI_MAX_TOKENS           # 8000, sent as the request's max_tokens
    reasoning_effort: str | None = None               # None omits the key entirely
    max_prompt_chars: int = DEFAULT_AI_MAX_PROMPT_CHARS   # 8000
    user_prompt: str = ""
```

`load_ai_summary_config()` calls `load_environment()` first, then reads the shipped settings, following `load_espn_credentials()` / `parse_league_ids_from_env()`:

| Variable | Parse | Invalid |
|---|---|---|
| `AI_SUMMARY_ENABLED` | lowercase in `{true,1,yes,on,false,0,no,off}`, default false | `ConfigurationError("AI_SUMMARY_ENABLED must be one of true/1/yes/on/false/0/no/off, got: 'maybe'")` |
| `AI_SUMMARY_API_KEY` | verbatim (not stripped — a token may not survive stripping; whitespace-only counts as empty) | `ConfigurationError` naming it when `enabled` |
| `AI_SUMMARY_BASE_URL` | verbatim with trailing `/` stripped; empty/whitespace → default | `ConfigurationError` when not an `http(s)` URL with a host |
| `AI_SUMMARY_MODEL` | `.strip()`, default `deepseek-v4.1-flash` | `ConfigurationError` when empty after strip |
| `AI_SUMMARY_TIMEOUT` | `int()`, default 120 | `ConfigurationError` naming the variable and the value |
| `AI_SUMMARY_MAX_TOKENS` | `int()`, default 8000 | `ConfigurationError` naming the variable and the value |
| `AI_SUMMARY_REASONING_EFFORT` | `.strip().lower()`, `low\|medium\|high`, empty → `None` | `ConfigurationError` naming the variable and the allowed values |
| `AI_SUMMARY_MAX_PROMPT_CHARS` | `int()`, default 8000 | `ConfigurationError` naming the variable |
| `AI_SUMMARY_USER_PROMPT` | `.replace("\r\n", "\n").strip()`; empty → no block | length checked against the configured limit |

While the feature is off the loader returns `AISummaryConfig()` after reading *only* the flag, so no other variable — including the memory group Phase B adds — can deny a report. `max_tokens` and `reasoning_effort` are configuration, not constants: FR-003 forbids a hard-coded budget and AC-010 proves both are read (the request double sees `max_tokens` and `reasoning_effort`, the construction double sees model, base URL, timeout and bearer token).

**Phase B adds** `memory: AIMemoryConfig | None = None` and reads `AI_MEMORY_ENABLED`, `AI_MEMORY_GIST_ID` and `AI_MEMORY_GIST_TOKEN` inside the enabled branch only.

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

### Component 6: Provider client — **as shipped** `ff_tracker/services/ai_client.py`

The amendment does not touch this file (the store gets its own wrapper — Decision 13). Recorded so no task re-derives it wrong:

```python
CONTRACT_REASON = "response did not match the summary contract"
USER_AGENT = f"ff-awards/{version('ff-awards')}"

@dataclass(frozen=True)
class AIRequest:                       # data the fake can record (AC-010)
    system_prompt: str
    user_message: str
    max_tokens: int                    # NO default: the configured budget is the only source
    reasoning_effort: str | None = None  # None omits the key; never sent as null or ""
    # __post_init__: prompts non-empty, max_tokens > 0, effort in low|medium|high

class AIClient(Protocol):
    def complete(self, request: AIRequest) -> str: ...   # returns message.content

class HTTPTransport(Protocol):
    def __call__(self, request: urllib.request.Request, timeout: int) -> bytes: ...

def _urlopen(request: urllib.request.Request, timeout: int) -> bytes: ...

class OpenAICompatibleClient:
    def __init__(self, config: AISummaryConfig, transport: HTTPTransport | None = None) -> None: ...
    def complete(self, request: AIRequest) -> str: ...
```

There is no `MAX_TOKENS` module constant: `max_tokens` comes from `config.max_tokens` on every call, which is what FR-003 requires and AC-010 proves. `complete`:

1. URL `config.base_url.rstrip("/") + "/chat/completions"`.
2. `urllib.request.Request(url, data=body, method="POST")` with
   `Authorization: Bearer <key>`, `Content-Type: application/json`,
   `User-Agent: ff-awards/<version>` (non-default; `Python-urllib/*` is refused by the default endpoint's front door).
3. Body `{"model": config.model, "messages": [{"role":"system",...},{"role":"user",...}], "max_tokens": request.max_tokens}`, plus `"reasoning_effort": request.reasoning_effort` only when it is not `None`. No `response_format`, no `temperature`, no streaming.
4. `self._transport(request_obj, self._config.timeout)` inside `try/except` (the transport is `_urlopen` unless one is injected — Decision 6):
   - `urllib.error.HTTPError` → read **and discard** `e.read()` (never logged), close, `raise AIHTTPError(status=e.code, host=host, model=...)`.
   - `urllib.error.URLError` → if `e.reason` is a `TimeoutError`/`socket.timeout` → `AITimeoutError(timeout)`; else `AITransportError(host)`.
   - `TimeoutError` (incl. `socket.timeout`, same class on 3.10+) → `AITimeoutError(timeout)`.
   - `(OSError, http.client.HTTPException)` around the body read → `AITransportError(host)`; a mid-body reset is the failure that would otherwise deny a report.
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

- `.env.example`: the shipped settings, commented, with the real defaults (`https://opencode.ai/inference/openai/v1`, `deepseek-v4.1-flash`, `120`, `8000`, empty `AI_SUMMARY_REASONING_EFFORT`), and the egress note.
- `README.md` → Configuration: an "AI Summary (optional)" subsection — what leaves the machine, how to enable with a key alone, that `.env.example` carries the defaults, and that `ff-championship`/`ff-season-recap` ignore it.
- `CHANGELOG.md` → `## [Unreleased]` / `### Added - AI Summary (optional)`.
- **No `AGENTS.md` change** (Gate 2 cut): no FR requires it, and a fourth copy of the feature description in the file every agent reads is exactly the drift this plan avoids elsewhere.

### Component 13: Season history builder — **NEW** `ff_tracker/services/ai_history.py`

FR-011 only, pure functions over `GameResult` rows plus the anchor (Decision 11).

```python
class AIRankByWeek(TypedDict):
    week: int
    rank: int

class AIHeadToHead(TypedDict):
    opponent: str
    wins: int
    losses: int

class AIStreak(TypedDict):
    kind: str          # "win" | "loss"
    length: int

class AIWeekScore(TypedDict):
    week: int
    score: float

class AITeamHistory(TypedDict):
    team: str
    rank_by_week: list[AIRankByWeek]
    head_to_head: list[AIHeadToHead]
    streak: AIStreak | None            # None only for a team with no game (Decision 12)
    scoring_trend: str | None          # "up" | "down" | "flat" | None
    best_week: AIWeekScore | None
    worst_week: AIWeekScore | None
    average_margin: float | None       # signed mean of score - opponent_score
    largest_win: float | None          # magnitude, like GameResult.margin
    largest_loss: float | None

class AILeagueHistory(TypedDict):
    weeks_included: list[int]
    teams: list[AITeamHistory]

def build_history(
    games: Sequence[GameResult],
    teams: Sequence[TeamStats],
    anchor: Sequence[AIStandingsRow],
) -> AILeagueHistory | None
```

Rules, each one line from FR-011: `weeks_included` is the distinct `week` values ascending; `None` when `games` is empty. Rank at week `N` is wins descending then points for descending over that team's games with `week <= N`, except the latest week present, which takes the anchor's rank verbatim. `scoring_trend` compares the latest week's score with the mean of that team's earlier weeks: `up` above +1.0, `down` below −1.0, `flat` inside the band, `None` under two weeks. `streak` counts back from the latest game. `largest_win`/`largest_loss` are magnitudes and `None` when the team has not won or not lost.

### Component 14: Overall ranking — **NEW** `ff_tracker/services/rankings.py`

```python
def rank_overall_teams(
    divisions: Sequence[DivisionData], limit: int | None = None
) -> list[TeamStats]
```

The single comparator (Decision 10). `display/base.py`'s two sorters — `_get_overall_top_teams` and `_get_sorted_teams_by_division` — keep their signatures, docstrings and `limit` semantics and become `return rank_overall_teams(divisions, limit)` and `return rank_overall_teams([division])`; the digest calls the first with no limit and `_standings_rows` calls the second's equivalent.

### Component 15: Memory store, archive and session — **NEW** `ff_tracker/services/ai_memory.py`

Payload types (a persisted document, shaped with `TypedDict` for the reason Decision 4 gives — it is serialised and read back, never held as application state, and FR-014's "the archive needs no model" settles it):

```python
class MemoryLeague(TypedDict):
    league: str
    paragraphs: list[str]
    bullets: list[str]

class MemoryEntry(TypedDict):
    week: int
    generated_at: str
    headline: str
    season_note: str
    leagues: list[MemoryLeague]

class MemoryFile(TypedDict):
    schema: int        # always 1
    season: int
    entries: list[MemoryEntry]
```

Functions and types:

| Name | Contract |
|---|---|
| `parse_archive(raw: bytes) -> MemoryFile | None` | `None` when the bytes do not parse **as the archive shape**: JSON, an object, `schema == 1`, a four-digit `season`, `entries` a list of objects with the required keys and types, `week` an int in 1–18. Structure only, as FR-014 now states — content, entry or summary counts and any text length are never reasons to reject a file, and a file that fails is reported as no memory and never overwritten (AC-033). An unknown key inside an entry is carried through untouched. |
| `merge_entry(archive: MemoryFile | None, entry: MemoryEntry, season: int) -> MemoryFile` | `None` creates the file with `schema: 1, season`; otherwise the same-week entry is replaced in place and the list is ordered by `week`, so an entry keyed by a week the file already holds replaces it. |
| `MEMORY_READ_OK/NONE/FAILED`, `MEMORY_WRITE_OK/FAILED/SKIPPED` | FR-014's two vocabularies, in one place, imported by the model's validator and the session. |
| `MemoryStore` (Protocol) | `load() -> bytes | None`; `save(data: bytes) -> None`. |
| `GistMemoryStore(memory_config, transport=None)` | `GET https://api.github.com/gists/{id}` and `PATCH` the same URL with `{"files": {"memory.json": {"content": …}}}`; `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, non-default `User-Agent`; timeout from `AI_SUMMARY_TIMEOUT` (no new setting); failures mapped to `AIMemoryStoreError(kind)`. The transport seam is this module's own `(Request, timeout) -> bytes` wrapper — `ai_client.py` is shipped and is not edited. The token and gist id never appear in a message, a log line or a reason (FR-009). |
| `MemorySession(memory_config, season, week, store=None)` | `open()`, `commit(summary)`, `read_status`, `write_status`, `entries`, `weeks`, `warnings` — Decision 13's lifecycle, never raising, and `commit` runs only after the narrative exists so the entry's `generated_at` is the report's. |

**Premise to confirm, not assume, and not a committed file**: the gist API's read/write shape — `files["memory.json"].content` on `GET`, `PATCH` with a `files` object to create or replace a file, `truncated: true` above 1 MB. T203's first step is one `curl` against a scratch gist, **run manually once; the two responses go in the PR description**, not in the repo: they are evidence for a reviewer, not an artifact the code or the suite reads. The application's ~56 KB by Week 17 is two orders of magnitude below the truncation limit, so the truncation case is recorded in the PR and not handled in code.

`ff_tracker/exceptions.py` gains `AIMemoryStoreError(Exception)` with `kind: str` and a `reason` that names the host and status only. It derives from `Exception`, not `FFTrackerError`, for Decision 1's reason: if one ever escaped the session it must surface as an unexpected error, never as a configuration failure that denies a report.

### Component 16: Modifications for the two phases

| File | Phase | Change |
|---|---|---|
| `services/ai_digest.py` | 1 | `history` per league; `overall_standings`; `weekly_extremes`; `history_week_count(digest)` |
| `display/base.py` | 1 | both sorters (`_get_overall_top_teams`, `_get_sorted_teams_by_division`) delegate to `rank_overall_teams` |
| `models/ai_summary.py` | 1, 2 | `history_weeks` (P1); `memory_read`/`memory_write`/`memory_weeks` (P2) |
| `services/ai_summary_service.py` | 1, 2 | `LEAGUE_WIDE_RULES` in the hashed prompt (P1); `MemorySession` parameter, block composition, redacted DEBUG line (P2) |
| `display/json.py` | 1, 2 | `history_weeks` always (P1); memory keys only when set (P2) |
| `config.py` | 2 | `AIMemoryConfig` inside `AISummaryConfig`, validated only in the enabled branch |
| `services/ai_memory.py` | 2 | new — Component 15, including its own transport wrapper |
| `exceptions.py` | 2 | `AIMemoryStoreError` |
| `main.py` | 2 | build the session when memory is on; print its warnings under Actions; call count assertions |
| `.github/workflows/weekly-report.yml` | 2 | `AI_MEMORY_ENABLED` guard + the two settings on the report step |
| `.env.example`, `README.md`, `CHANGELOG.md` | 2 | the three memory variables, the gist exposure, the token's scope, retiring the file at a season boundary |

`display/console.py`, `markdown.py`, `sheets.py`, `email.py` and `services/ai_client.py` are **untouched by both phases**: nothing new is rendered, and the provider client is shipped and correct.

---

## File Inventory

**New (11)**
| File | Contents |
|---|---|
| `ff_tracker/models/ai_summary.py` | `AISummaryLeague`, `AIProvenance` (incl. `attempts: 1\|2`), `AISummary`, `AISummaryUnavailable`, `AISummaryResult` |
| `ff_tracker/services/ai_digest.py` | `build_digest` + typed helpers |
| `ff_tracker/services/ai_client.py` | `AIRequest`, `AIClient`, `HTTPTransport`, `OpenAICompatibleClient`, `USER_AGENT` |
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

### Phase 1 files (spec Phase 1 — season history, league-wide view)

**New (4)**
| File | Contents |
|---|---|
| `ff_tracker/services/ai_history.py` | FR-011 block builder + its `TypedDict`s |
| `ff_tracker/services/rankings.py` | `rank_overall_teams` — the one comparator |
| `tests/test_ai_summary_history.py` | AC-024, AC-025 |
| `tests/fixtures/ai_summary_phase1_golden.json` | the five-format golden (T106) |

**Modified (7)** `ff_tracker/services/ai_digest.py` (three keys + `history_week_count`), `ff_tracker/display/base.py` (two delegates), `ff_tracker/models/ai_summary.py` (`history_weeks`), `ff_tracker/services/ai_summary_service.py` (league-wide rules in the hashed prompt), `ff_tracker/display/json.py` (`history_weeks`), `tests/test_ai_summary_digest.py` (key-set golden + league-wide cases), `tests/ai_fakes.py` (multi-week game fixtures). No formatter outside `json`'s provenance block.

### Phase 2 files (spec Phase 2 — the memory log)

**New (2)**
| File | Contents |
|---|---|
| `ff_tracker/services/ai_memory.py` | archive types, `parse_archive`, `merge_entry`, `MemoryStore`, `GistMemoryStore` (with its own transport wrapper), `MemorySession` |
| `tests/test_ai_memory.py` | store, archive, session, status map (fake store + fake transport) |

**Modified (8)** `ff_tracker/config.py`, `ff_tracker/exceptions.py`, `ff_tracker/models/ai_summary.py`, `ff_tracker/services/ai_summary_service.py`, `ff_tracker/display/json.py`, `ff_tracker/main.py`, `.github/workflows/weekly-report.yml`, `tests/ai_fakes.py` (`FakeMemoryStore`). Plus `tests/test_ai_summary_service.py`, `tests/test_ai_summary_rendering.py` (the AC-028 golden comparison), `tests/test_main_cli.py` (warning lines, call counts), `tests/test_ai_summary_config_workflow.py` (WC-002), `.env.example`, `README.md`, `CHANGELOG.md`. **No committed research note**: the gist API evidence lives in the PR description (T203).

**Deliberately untouched by both phases**: `display/console.py`, `display/markdown.py`, `display/sheets.py`, `display/email.py`, `display/factory.py`, `services/ai_client.py`, `championship.py`, `season_recap.py`, `services/championship_service.py`, `services/season_recap_service.py`, the two non-weekly workflows, `AGENTS.md`, `.specify/specs/**`.

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

### Phase 1 (feature on, either mode)
`build_digest` → per league: `_standings_rows` once → `standings` (mode-filtered) *and* `build_history(games, teams, anchor=rows)` → `history`; across divisions: `rank_overall_teams` → `overall_standings`, and the weekly rows → `weekly_extremes` → `history_week_count(digest)` → `AIProvenance.history_weeks` → `json.dumps(digest)` into the same one request. No store, no extra call, nothing rendered.

### Phase 2 (memory on, narrative accepted)
`MemorySession.open()` → one `GET` → `parse_archive` → `read_status`, `entries`, `weeks` → `build_memory_block(entries)` appended to the instructions → one provider call → parse, match, normalise → `AISummary` (its `provenance.generated_at` is the run's one instant) → `MemorySession.commit(summary)` → `_can_key_entry` → `merge_entry` (the entry copies `generated_at` from the summary) → one `PATCH` → `write_status` → `provenance` carries all three fields → `main` prints the session's warnings under Actions. A read or write failure changes no format and no exit code.

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

Phases 1–6 above are **shipped**; their task numbers 1–13 keep their ids. The amendment adds two
phases of its own, numbered `T1xx` and `T2xx` so nothing shipped is renumbered:

| Phase | Tasks | Outcome | Revertable alone |
|---|---|---|---|
| A — Season history and league-wide view (spec Phase 1) | T101–T103, T105, T106 (**5**) | three digest keys, one provenance field, the two league-wide prompt rules (in T103), the golden | yes: one `git revert`, nothing Phase-2-only touched |
| B — The memory log (spec Phase 2) | T201–T208, T210 (**9**) | config, archive, store, session, prompt block, service lifecycle, wiring, AC-028, workflow and docs (in T210) | yes: one `git revert` over B's commits |

**One engineer pass per phase.** Phase A is 5 tasks and Phase B is 9, both inside the ~15 a single
pass allows. Three tasks were folded rather than added: T104's prompt rules join T103 (same two
files, one test), and T209's workflow guard joins T210 with the operator documentation (both exist
to let an operator enable memory in CI without a report failing). Two more were considered and left
out: a `--help` paragraph for the memory settings (no FR asks, and it would be a fourth copy of a
variable list), and a separate "backfill works outside the CLI" task — the constraint rides on
T206's subprocess proof instead.

**Boundary rule**: Phase B is planned and delivered against a **merged** Phase A. Every Phase B
task that touches a Phase A file (`ai_summary_service.py`, `models/ai_summary.py`, `json.py`)
extends it; no Phase B task edits a Phase A *behaviour*, and reverting B leaves the Phase A golden
and its digest untouched. Reverting A alone is only meaningful before B merges, which the
sequencing guarantees.

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

Found while planning the amendment:

9. **`DivisionData.games` is the whole season up to the week processed, and it can be short.** `extract_games` builds both rows of every box score, so it carries `team_name`, `score`, `opponent_name`, `opponent_score`, `won`, `week`, `margin`, `division` — everything FR-011 needs — but a box score it failed to parse is silently skipped (`espn_service.py:453`, a `logger.warning` and `continue`). That is why FR-011 anchors the newest week on the standings rather than on the recomputation, and why AC-024's second fixture is not hypothetical.
10. **The overall ranking lives in exactly four formatter call sites.** `console.py:442`, `markdown.py:433`, `sheets.py:212` pass `limit=20`; `email.py:481` passes `format_args`' `max_teams` (0 = all). Delegating the method (Decision 10) is therefore a change to one body with four unchanged callers; changing any call site would change output under AC-001.
11. **Weekly challenges are computed once, across all divisions.** `main.py:296-312` concatenates every division's `weekly_games` before `calculate_all_weekly_challenges`, so "Highest Score This Week" is already league-wide. That is what makes AC-027's agreement clause cheap to test — the extremes and the challenge winner read the same rows — and it means the digest must not recompute a *per-division* winner for that comparison.
12. **`--week N` sets `espn_service.current_week = N`**, and the ESPN path then processes only weeks up to `N` (`_determine_max_week`). So the throwaway backfill script is the ordinary report path with a week override, applied in a loop; it needs no new API, only that `create_config(week=…)`, `load_ai_summary_config()`, `ESPNService`, `MemorySession` and `AISummaryService` stay callable and that `generate` never prints.
13. **`ff_tracker/__init__.py` imports `.main`**, so every `ff_tracker.services.*` import loads the CLI module. "Callable outside the CLI" therefore cannot be asserted as "main is not imported" — it has to be asserted as behaviour: a process that calls the services, makes no CLI invocation, and prints nothing. T206 proves it in a fresh subprocess.
14. **`config.year` is always a four-digit year** (`FFTrackerConfig` rejects `< 2000` and `detect_fantasy_year` returns a calendar year), so FR-014's season check is defensive rather than reachable through the CLI; it stays because a backfill script or a future caller can pass anything, and because `current_week` genuinely can be 0 or negative.
15. **`json.loads` returns `Any`, and the archive parser is new surface.** `parse_archive` binds to `object` first and narrows with `isinstance`, exactly as `_parse_response` and `_parse_envelope` do, so Article I holds with no suppression anywhere in the new file.

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

The amendment's criteria:

| AC | Where |
|---|---|
| AC-024 history block from games, anchored latest week, second fixture where `games` is short a week | `tests/test_ai_summary_history.py` (one fixture per `scoring_trend` value; magnitudes and nulls asserted as values) |
| AC-025 no games → `null`; one week → one entry, streak 1, trend `None`; present in all three modes; one provider call, no other outbound call | `test_ai_summary_history.py` + `test_ai_summary_digest.py` (mode fixtures), call count via `FakeAIClient.requests` |
| AC-026 exactly three digest keys; five formats byte-identical; only `history_weeks` differs in JSON; feature-off still today's output | `test_ai_summary_digest.py` (replaced `EXPECTED_KEYS`), the T106 golden, existing AC-001 test re-run |
| AC-027 overall standings order and completeness, division per row, extremes across three divisions, agreement with the per-division winners, single division, no games, prompt rules present | `test_ai_summary_digest.py` (order and completeness on their own fixtures; the >20-team fixture compares the rendered 20 console rows against the first 20 of `overall_standings`, which guards rendering order) + `test_ai_summary_service.py` (rule constants in the composed prompt) |
| AC-028 memory off: zero store calls, no block, no memory keys, five formats equal the Phase-1 golden | `test_ai_summary_rendering.py` (the golden comparison) + `test_ai_memory.py` (zero calls) |
| AC-029 absent file and empty gist: `"none"`, `[]`, one read, one write, the entry's contents | `test_ai_memory.py` + `test_ai_summary_service.py` |
| AC-030 six prior weeks: one read, every entry under its tag in week order, no gist id/token/league id in the body, `"ok"`, `[1…6]`, one provider call, response carries no memory field | `test_ai_summary_service.py` + `test_ai_memory.py` |
| AC-031 read failures: a 404 is `"none"` and its write fails per AC-032; 401/403 vs 5xx/transport/timeout, one warning and none, deterministic sections byte-identical, one provider call, `memory_weeks: []` | `test_ai_memory.py` (session) + `test_main_cli.py` (the printed line) |
| AC-032 write failures: 404/401/403/5xx/transport/timeout, exit 0, one warning and none, token absent; same-week re-run replaces in place | `test_ai_memory.py` (merge + session) + `test_main_cli.py` |
| AC-033 a file that will not parse as the archive shape warns once and is left unchanged; unknown keys and over-long text are read and never rewritten; a `week` outside 1–18 or a season that is not a four-digit year skips the write with no store call; missing gist id/token → `ConfigurationError`, exit 1, zero provider and zero store calls | `test_ai_memory.py` + `tests/test_config.py` + `test_main_cli.py` |
| WC-002 static workflow check | `tests/test_ai_summary_config_workflow.py` |
| LV-005 (live gist: write, re-run replaces, hand edit survives) and LV-006 (both phases, full archive, one call) | manual, once, at each phase's release — not in the suite |
| Gist API premise for T203 | **manual, once, against a scratch gist; not in the suite** — the two `curl` responses go in the PR description |

**No network, both phases**: `FakeAIClient` for the provider, `FakeMemoryStore` for the store (`tests/ai_fakes.py`), `FakeTransport` for both HTTP seams (the provider client's and the store's own wrapper), and `tests/fixtures/` for the golden. One test patches `urllib.request.urlopen` and drives the provider's production `_urlopen`, so that path is exercised once and only once; the store's wrapper gets its own small equivalent.

**Golden discipline**: T106 writes `tests/fixtures/ai_summary_phase1_golden.json` from Phase-1 code and commits it; AC-028's test only reads it. A capture helper that a test can call would make the golden a snapshot of the code under test, which is the failure mode AC-028 names. Decision 17 carries the recapture procedure and the rule that decides when a recapture is legitimate.

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

### Risk 5: Two overall rankings ship and drift (Phase 1)
**Likelihood**: Medium · **Impact**: Medium
**Mitigation**: one comparator in `services/rankings.py`, called by `_get_overall_top_teams` and by the digest (Decision 10), so there is nothing to drift; AC-027 additionally asserts the digest's order against the console's rendered table, which is the check that catches a future third copy. **Fallback**: none needed — the design removes the second copy rather than reconciling two.

### Risk 6: The golden rots, or blesses a bug (Phase 1 → 2)
**Likelihood**: Medium · **Impact**: High
**Mitigation**: the fixture pins model, clock, prompt, report data, CLI inputs and format args (Decision 17); the capture is a separate task whose output is reviewed as a diff and committed; no test can regenerate it; and a recapture in the same commit as a memory change is a review reject, because reconciling AC-028 that way is exactly the regression the criterion exists to catch. **Fallback**: if the golden fails for a reason unrelated to memory, the failure names the format and the first differing byte, so the cause is visible before anyone reaches for the recapture procedure.

---

## Performance Considerations

With the feature off, `load_ai_summary_config()` is one dict read and an `os.getenv` loop; the run budget is unchanged (Article X, as scoped in Complexity Tracking).

With it on, the run gains one provider call: 7.7–34.4 s in the spike, bounded by `AI_SUMMARY_TIMEOUT` (default 120 s). A contract failure adds exactly one identical retry (two calls, roughly two socket-read timeouts worst case); nothing else is retried and nothing is cached. One call per run in the normal case regardless of league or format count, which is the only performance requirement this feature can enforce.

Digest size is bounded by the data: 3–4 leagues × (≤16 standings rows + ≤8 matchup rows + ≤7 challenges) — a few KB of JSON, far inside any model's context.

**Phase 1** adds no request and no round trip: history is a pass over `DivisionData.games`, and the league-wide view a sort plus a pass over the weekly rows already in memory. Its cost is prompt size — one more block per league and one cross-division block, a few KB.

**Phase 2** adds at most two store round trips, each bounded by `AI_SUMMARY_TIMEOUT` (120 s default), and a prompt that grows to roughly 10,000 tokens by Week 17 (~56 KB of archive). The reply budget is `AI_SUMMARY_MAX_TOKENS` and is unrelated to the prompt's size; the spec refuses to shorten the archive, so there is no knob here and no tuning task.

---

## Security Considerations

- The key exists only as an environment value, a `.env` line and `AISummaryConfig.api_key` (`field(repr=False)`). It is never a CLI flag, never a format argument, never logged, never rendered.
- Request and response bodies are never logged at any level (they carry team/owner names, PF/PA and — in principle — anything the model echoes). Only model id, status, latency and token counts are logged.
- The system prompt is logged at DEBUG only, because a public repo's Actions logs are world-readable. FR-008's CI record is the `AI_SUMMARY_USER_PROMPT` value behind the workflow's `vars`/`secrets` expression — a repository variable or a secret, not a file in git (FR-008/FR-009).
- Reasons name the endpoint **host only** — a custom base URL may carry a credential in its path.
- The digest carries no league IDs, no credentials and no API key (FR-002), and the prompt tells the model not to invent facts; no verification of prose claims is claimed or implied anywhere in the output.

---

## Complexity Tracking

> **Two articles are violated**, counted by the clause each breaks, not by the sections below:
> **Article III** — fail-fast ("no partial data tolerance", "no retry logic"), broken by the narrative
> fail-open, by the two memory fail-open cases, and by the single contract retry (which also touches
> Article V's "no retry logic" sentence); and **Article X** — the five-second typical run, which no
> longer holds with the feature on. Below them are two **scope notes**, not violations: the second
> external API, and Phase 1's zero-added-I/O claim. Every item is approved in the spec's Constitution
> Deviations section; recorded here because the constitution requires it.

### Article III — Fail-Fast Error Handling, violation 1: the narrative degrades the report

**Deviation**: `AISummaryService` does not fail the run when the narrative cannot be obtained, matched, validated or normalised. The report renders without the section and says so.

**Spec reasoning (quoted in substance)**: the narrative is cosmetic; the report carries the league's weekly facts and runs on a weekly schedule, where a failed proxy, a retired model or an HTTP 410 would otherwise deny the league its report entirely.

**Boundary this plan implements**:
- Applies **only** to obtaining, matching, validating and normalising the narrative — one `try/except AISummaryError` in `generate`.
- ESPN failures, `ConfigurationError` (missing key, bad `AI_SUMMARY_ENABLED`, bad timeout, oversized prompt, missing gist id or token), data-validation failures outside the parse boundary and every other `FFTrackerError` still fail fast and stop the run.
- Never silent: notice in the section's position in all five formats **plus** a `::warning::` under Actions.
- Normalisation cannot fail: the contract already guarantees ≥1 non-empty paragraph per league and normalisation only drops or shortens, so `AISummary` always constructs once matching succeeded.
- **The exception hierarchy is part of the boundary**: `AISummaryError` and its five subclasses derive from `Exception`, not from `FFTrackerError`. That is deliberate and load-bearing — if a narrative failure ever escaped the boundary, `main()` must not render it as `Error: ...` with exit 1, which is exactly what an `FFTrackerError` subclass would do. Deriving from the project's own base class would convert a cosmetic failure into a denied report by inheritance alone.
- **Transport failures map inside the client, not outside it**: `HTTPError`, `URLError`, timeouts, and the mid-body `OSError`/`http.client.HTTPException` raised by `response.read()` all become `AISummaryError` subclasses before they leave `complete()`. A `ConnectionResetError` escaping as an `OSError` would be caught by `main()`'s unexpected-error branch and deny the report, so this mapping is a fail-open requirement, not error-polish.

### Article III — Fail-Fast Error Handling, violation 2 (Phase 2): the memory log degrades silently and warns

**Deviation**: a failed memory read never appears in the report at all, and a failed memory write ships the report and warns. Neither is a failure of the run.

**Spec reasoning (FR-014, FR-006)**: the archive is context for prose that has already been produced without it; a read failure changes no output, so a notice would advertise a section that is not missing. A write failure is different — the log is what the next week depends on, so it must be visible — but it still cannot cost the league its report.

**Boundary this plan implements**:
- `MemorySession` **never raises** (Decision 13), so neither case can enter Decision 1's boundary and neither can acquire a notice. The two Article III cases share one structural guarantee instead of two catch clauses.
- A read failure is recorded in `provenance.memory_read` and is silent except for a 401/403, which warns once under Actions — the one failure an operator can fix.
- A write failure is recorded in `provenance.memory_write` and warns once under Actions, naming scope or authentication where identifiable. Outside Actions, nothing is printed.
- Everything around memory still fails fast: a missing gist id or token with memory on is a `ConfigurationError` (exit 1, no report, no provider call, no store call), and a programming error inside the session propagates as an unexpected error.

### Articles III and V — one bounded retry, contract failures only (existing behaviour, recorded as a violation of both)

**Deviation**: `_generate` retries once. Article III says "no retry logic"; Article V says "no retry logic (fail clearly)". This is the third Article III violation and the only Article V sentence this amendment touches.

**Spec reasoning (FR-003)**: the retried class — malformed JSON, a wrong shape, a league-count or name mismatch, an empty required field — is sampling noise rather than a statement about the provider, so a second identical attempt is cheap and often sufficient. It is never HTTP 4xx/5xx, a transport error, a timeout or `finish_reason == "length"`, each of which would fail identically at the same cost; the retry reuses the same request object, so prompt, model and budget are unchanged; a second contract failure is the ordinary notice.

**Boundary this plan implements**: `except AIContractError` only, `attempts` capped at 2, `provenance.attempts` recording which happened, and no retry of any kind in `AIClient` or `MemoryStore`. Phase 2 adds no retry: a store failure is mapped to a status, never re-attempted.

### Article V — scope note (Phase 2): a second external API, one read and one write per run

**Not a violation.** Article V's clauses are about ESPN call discipline — context managers, a single call for many items, one fetch feeding every format, no retries, rate-limit awareness — and a one-shot gist call that is timed out per socket read and never retried meets every one of them. This section records the *scope* change, which is that a run with memory on now talks to two external services rather than one.

**Spec reasoning (FR-013)**: one gist read before generation and at most one write after, regardless of league count, with no retries of its own and a one-shot client — the same discipline FR-001 applies to the provider call and Article V applies to ESPN.

**What the plan does with it**:
- `MemorySession.open()` and `.commit()` are each called at most once per run; the write is skipped when there is nothing to key (Decision 16), so a pre-kickoff run makes one call, not two.
- No ESPN traffic changes: history and the league-wide view are computed in-process from `DivisionData.games`, `TeamStats` and `weekly_games`. **Phase 1 adds no network call at all**, which is why it has no Article V entry of its own.
- The store's socket read is bounded by `AI_SUMMARY_TIMEOUT`; no new timeout setting is added.
- The `User-Agent` on both clients is non-default for the same reason: the default `Python-urllib/*` is refused at the edge.

### Article X — Performance Requirements (violation): provider and store latency

**Deviation**: the 5-second typical run no longer holds with the feature enabled.

**Spec reasoning (v0.8, v0.23)**: 7.7–34.4 s per provider call in the spike, bounded by `AI_SUMMARY_TIMEOUT` **on each socket read**; there is no wall-clock deadline, so a pathologically slow provider can exceed the configured value. The 5-second budget applies to the deterministic report with the feature off. Phase 2 adds at most two store round trips, each bounded by the same per-socket-read timeout, and a ~10,000-token prompt by Week 17 — a cost the spec states and explicitly refuses to trade against the archive's length.

**Boundary this plan implements**: off by default; zero added network I/O when off; one call per run when on, plus at most one identical retry after a contract failure; no other retries, no streaming, no per-format second call; no thread or signal wrapper (a timed-out `urlopen` cannot be cancelled, so a worker thread would hang shutdown for the same duration it was meant to bound); Phase 1 adds no request at all. A caller that cares about schedule duration leaves the feature off, which is the default.

### Held without a governing FR

- **The non-default `User-Agent` is a hard requirement** on both clients. No FR names it, but the default endpoint sits behind Cloudflare, which rejects `Python-urllib/*`; without an identifying header every call fails at the edge. It is recorded here because a future "remove the unused header" cleanup would silently break the default endpoint, and no acceptance criterion would go red.

### Not deviated
Articles I (no `Any`, no suppressions — the new archive parser narrows from `object` like the existing two), II (frozen validated models; the archive is a `TypedDict` payload, not state), IV (services never import display; the one new edge is display → services for the shared comparator, which is the direction the article permits; every `::warning::` is still emitted in `main.py`), VI (one protocol, five formats, and neither phase touches four of them), VII (docstrings/names, comments only for the non-obvious), IX (no new flags; `--help` unchanged by Phase 1, and Phase 2's three variables are documented where the existing ones are).

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

Decisions this amendment leaves to the plan, recorded so Gate 3 can object to them specifically:

9. History is its own module, the league-wide view stays in the digest, and one comparator lives in `services/rankings.py` shared with the formatters (Decisions 9, 10). `display → services` is the one new import edge.
10. History's newest rankings are the per-league standings list object, unfiltered by mode, so the anchor is the report's own ranking in every mode (Decision 11).
11. Four history fields are `null` for a team with no game, and `head_to_head` is ordered by opponent name (Decision 12).
12. The store is a `MemoryStore` protocol plus one `MemorySession` per run that never raises; the service takes the session, `main.py` prints its warnings (Decision 13).
13. `provenance.history_weeks` is a defaulted int; the three memory fields are all-set or all-`None`, and `None` is what keeps them out of JSON (Decision 14).
14. `prompt_sha` hashes the instructions only; the memory block is appended after it, and the DEBUG line is the block renderer in redacted mode (Decision 15).
15. A same-week re-run's own previous take **is** sent in the block, because excluding it would be the selection rule FR-014 deletes (Decision 16).
16. The file's `season` is fixed at creation and the entry key is the week alone, so a later season's Week-N run replaces the earlier season's Week-N entry, hand edits included; retiring `memory.json` at a season boundary is the operator's action, documented in T210 (Decision 16).
17. The Phase-1 golden is one JSON fixture holding four strings and one parsed document, captured by T106 and never regenerated by a test (Decision 17), with a written recapture procedure and the rule that a memory change may never be reconciled by recapturing it.

### Spec nits for the next spec edit (not edited here)

None. The review's wordings are in the spec, and the current version fixed the one unsatisfiable phrase this plan had already read as value-identity (AC-032's "byte-identical" for entries the tool re-serialises), so nothing here asks for a further spec edit.

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
| 2.0 | 2026-10-27 | AI Agent | Spec v0.24: the two-phase amendment. New Amendment Architecture section (Decisions 9–17): history is its own module while the league-wide view stays in the digest; one comparator in `services/rankings.py` called by `_get_overall_top_teams` and the digest, so no second ordering can exist; history's newest rankings are the per-league standings list itself; the store is a `MemoryStore` protocol plus a per-run `MemorySession` that never raises, so Decision 1's boundary is unchanged; provenance carries `history_weeks` always and the three memory fields only when set; `prompt_sha` hashes the instructions with the memory block appended after it, and the DEBUG line is the block renderer redacted; one predicate suppresses a write and one key replaces an entry; the Phase-1 golden and exactly what it pins. Components 13–16, the Phase 1/Phase 2 file inventory, the two delivery phases, the AC-024…AC-033 / WC-002 / LV-005–006 test map, the Phase-2 failure-policy table, two new risks, six new constraints and the four-deviation Complexity Tracking were added. Five spec nits recorded and not edited. |
| 2.1 | 2026-10-27 | AI Agent | Review findings applied. **B1** — the backfill constraint is proved by behaviour in a fresh subprocess (no CLI invocation, one store write, `main()` never called, empty stdout), because `ff_tracker/__init__.py` imports `.main` and an import assertion could never pass; new Constraint 13 records that. **B2** — `commit(summary)` runs after `_normalise`, and the entry copies `generated_at` from the summary's provenance so one instant is computed once. **B3** — Components 4 and 6 restated to the shipped configuration (the full `AI_SUMMARY_*` set including `MAX_TOKENS` and `REASONING_EFFORT`, default model `deepseek-v4.1-flash`, no hard-coded budget, `reasoning_effort` omitted when unset). **B4** — the paired authentication-read-plus-failed-write fixture counts two warnings, one per cause. **S1** — the failure table points the read-404 row at AC-031/AC-032 and the write guard at AC-033; **S2** — `parse_archive` is described as "parses as the archive shape", with content, counts and text length never read-only causes; **S3** — the season consequence is stated plainly and documented in T210; **S4** — an unknown key inside a prior entry survives a merge. **S5** — T106 names the full patch set and Decision 17 carries the recapture procedure and what may and may not break the golden; **S6** — AC-027's >20-team comparison is the rendered 20 rows against the first 20, and states that it guards rendering order rather than the comparator; **S7** — the gist `curl` is marked manual, once, in the PR description. **S9** — Complexity Tracking counts two violated articles (III, X) with Article V relabelled a scope note. **S10** — see tasks.md. Cuts: no committed `research.md`, no `ai_client.py` rename (the store gets its own transport wrapper), and T104 folded into T103. |
| 2.2 | 2026-10-27 | AI Agent | Gate 2 close, five corrections and no design change. The dependency map restored **T103 requires T102** (it calls the comparator T102 creates). **AC-033's over-long-paragraph clause gained its owner**: T205 joins the traceability row and its six-week test asserts that a stored paragraph longer than any cap reaches the composed block verbatim. Version pointers retargeted from spec v0.24 to **v0.26**; the phantom Configuration-table nit deleted, because the row already reads "Per-socket-read timeout in seconds"; the spec-nits section now reads "None". Artifacts frozen. |
