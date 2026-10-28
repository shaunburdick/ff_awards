# Challenge Ledger — 009 AI Summary

> Gate 1 (spec) · `spec.md` v0.15 (this commit) · Constitution v1.0.0, no conflict.
> Owner decisions of 2026-10-21 are precedent: fail-fast when enabled-but-unconfigured with a
> workflow guard; league matching by name with positional fallback; failure notice at the bottom.
> They are not reopened. The v0.4 owner changes (endpoint default, enforced length, committed lore
> file) are recorded below as owner changes, not as challenges to earlier rulings.

## Rulings (v2 — after the owner's decisions)

| Decision | Ruling | Carried to |
|---|---|---|
| FR-007: missing key/base URL → `ConfigurationError`, exit 1, no report, with a workflow guard | DEFENDED — owner's decision; spec states the fork/rotated-secret tradeoff plainly (FR-007 §Tradeoff). Closed in v0.3: the guard requires key **and** base URL (`vars` for the URL, with the reason), is an `env:` expression yielding literal `true`/`false`, and FR-007 states that `if:` cannot express it because `secrets` is unavailable in `jobs.<job_id>.if`/`steps.<job_id>.if`. | — |
| Failure notice at the bottom, in the section's position | DEFENDED — owner's decision; FR-005 and FR-006 are consistent and the `::warning::` is named as the backstop. | — |
| League matching: name (`strip().casefold()`) with positional fallback, headings from our data | DEFENDED in policy — owner's decision. Closed in v0.3: FR-004 states the total order (all names match once → name map; else equal counts → position; else fail), so a stray or duplicated entry at equal counts renders and only a count mismatch fails; AC-008 and FR-006's reason list (`league count mismatch`) are aligned. | — |
| `AI_SUMMARY_ENABLED` as a separate switch | DEFENDED — a stray key must not by itself send team/owner names to a third party. | — |
| Article III deviation (report ships on narrative failure) | DEFENDED — bounded, declared, never silent; owner's decision. | — |
| FR-002 digest vs models | CLOSED — `reg_season_count` named as a model addition; opponent true diff read from the mirror row with an explicit omission rule; playoff position worded as the `in_playoff_position` boolean. The cut of Edge Case 2 cost the no-matchups instruction; restored in v0.3 — FR-002 states explicitly when a league had no matchups this week. | — |
| Mode rule (Weeks 15–17) | CLOSED — one rule stated, AC-012 aligned. The "existing mode predicate" claim was inaccurate; v0.3 now says the digest applies the same two-line rule locally as a deliberate sixth copy (not an extraction — `ReportContext._build_context_from_params` is unreachable from a service) and must agree with the formatters, which AC-012 asserts. | — |
| `prompt_sha` replaces `prompt_version`; prompt is a module constant under `ff_tracker/services/` | CLOSED — hash cannot drift; prompt edits are one reviewable diff. | — |
| Digest / request / response never logged | CLOSED — FR-009 clause plus AC-006. AC-006 now asserts only code this feature owns (summary service and any new code: no team name, owner name, league ID, key, prompt text or response body) plus a digest-marker check; existing logging in untouched modules (`espn_service.py`) is explicitly out of scope. | — |
| AC-001 testability; AC-010 | CLOSED — AC-001 is a same-test prefix/suffix comparison with JSON parsed minus `ai_summary`; AC-010 deleted and ACs renumbered with no stale references. | — |
| Spike numbers doing requirement work | CLOSED — word counts, "roughly 7 KB" and the reasoning-token ranges are gone; `max_tokens: 8000` keeps one line of justification as a request parameter. | — |
| Open Question 1: base URL default | REVERSED in v0.4 by the owner: `AI_SUMMARY_BASE_URL` now defaults to `https://opencode.ai/inference/openai/v1` with the uncontrolled-endpoint tradeoff stated; the missing-base-URL branch is gone and the workflow guard is key-only. | — |
| Open Question 2: placement | DELETED — not a question; already decided in FR-005. |
| v0.4 owner change: endpoint default, key-only enablement | OWNER CHANGE — reverses the earlier no-default ruling. Empty or whitespace falls back to the default; FR-007 keeps fail-fast for a missing key and for malformed `AI_SUMMARY_ENABLED`/`AI_SUMMARY_TIMEOUT`; WC-001 and the guard reference only `secrets.AI_SUMMARY_API_KEY`; `vars` is no longer used; the default and model id are a `.env.example`/README plan requirement. | — |
| v0.4 owner change: length enforced by normalisation | OWNER CHANGE — reverses "a prompt instruction, not a validation gate". Fixed order: contract shape → league matching → normalisation → render. Caps: headline ≤ 15 words; ≤ 3 paragraphs, ≤ 3 bullets, ≤ 120 words per league; `season_note` ≤ 2 sentences/≤ 40 words. The 120-word paragraph reading was internally inconsistent with the 120-word league cap, so the word cap is the league total and paragraphs truncate against the remaining budget; sentence boundaries per the stated rule; `…` for word-boundary cuts; `provenance.truncated`. | — |
| v0.4 owner change: committed lore file (FR-010) | OWNER CHANGE — reverses the "user-authored prompt, tone or league-lore file" exclusion. `AI_SUMMARY_LORE_FILE` (default packaged `ff_tracker/prompts/ai_summary_lore.md`), 4000-character cap, neutral shipped template with no real names, appended to the system prompt and never overriding the contract/caps/no-invented-facts rule, lore egress declared in FR-009, `prompt_sha` covers prompt plus lore, wheel inclusion to be verified by the plan. | — |
| v0.5 change: normalisation is structure-first | OWNER CHANGE — the sentence-boundary detector with its abbreviation list is deleted: initials (`J.J. Smith`, `A.J. Brown`) cannot be enumerated as abbreviations, so it split inside names. Order is now drop bullets → drop paragraphs → drop whole trailing paragraphs to fit 120 words, truncating only a first paragraph that alone exceeds the budget at a word boundary with `…` → headline and `season_note` at word boundaries. The `season_note` two-sentence rule and all sentence/URL/number/emoji clauses go with it; caps and `provenance.truncated` are unchanged. | — |
| v0.5 change: the contract requires prose | OWNER CHANGE — each league entry has ≥ 1 paragraph and every paragraph has ≥ 1 word after trimming, so `"paragraphs": []` is a contract failure; the "normalises to nothing" failure clause is deleted as unreachable, and Article III's note updated to say normalisation can only drop or shorten. | — |
| v0.5 clauses: host in the reason, fallback test, AC strength, traceability, floor, exclusions, lore header | OWNER CHANGE — FR-006 names the endpoint host only (a custom base URL may embed a token in its path); AC-005 matches; AC-010 covers unset/empty/whitespace fallback and override; AC-013 adds surviving first paragraph and first three bullets plus repeat-run identity, and the old AC-014 is deleted with AC-015…AC-017 renumbered; AC-017 adds the packaged-default path; FR-008 states that a custom lore file is untracked and a combined hash cannot separate prompt from lore edits; the 60-word floor is declared prompt guidance that is deliberately not validated; a narrow "user-authored system prompt" exclusion returns; the shipped lore template opens with a committed-and-sent header. | — |
| v0.6 owner change: lore file replaced by `AI_SUMMARY_USER_PROMPT` | OWNER CHANGE — the file is the wrong shape because automation must be able to set it through the environment. Removed: `AI_SUMMARY_LORE_FILE`, the packaged `ff_tracker/prompts/ai_summary_lore.md` default, the wheel-inclusion data requirement, the missing-path `ConfigurationError`, the neutral-template rule, the template header, and every read from disk. Added: an optional env string appended as a `### COMMISSIONER'S INSTRUCTIONS` block, sent verbatim; strip/CRLF-to-LF rules with empty/whitespace as a no-op; an 8000-character cap whose error names the variable, length and limit (the limit bounds prompt size and cost, not a platform); the precedence sentence kept; the trusted-but-unsanitised note; non-verification of factual claims extended to anything the prompt asks for; FR-008 records that the prompt is not archived and recommends a committed `env:` block scalar; FR-009 covers user-prompt egress and variable visibility; AC-016/AC-017 restated in place (no id removed or renamed); the exclusion now covers the system prompt template only. Residual for the owner: nothing in the repository guarantees the prompt text is reviewable, and a secret-held prompt is never reviewed. | — |
| v0.7 owner change: the system prompt may be logged at DEBUG only | OWNER CHANGE — logging is tiered. Never logged at any level: the key, the request body (the digest, carrying team names, owner names, PF/PA and league IDs) and the response body. DEBUG only: the system prompt, template plus the resolved instructions block, never at INFO/WARNING/ERROR or in notices, error messages or warning commands. FR-009 states the hazard — this repository is public and Actions logs are world-readable, so the DEBUG line is for a local `-vv` run, and for CI the committed `env:` block scalar is the record; logging is not a substitute. FR-008 and AC-006 match. Residual: nothing in the spec can stop someone enabling `-vv` in CI, so the warning is the only control. | — |
| v0.7 owner change: `AI_SUMMARY_MAX_PROMPT_CHARS` | OWNER CHANGE — the user-prompt cap is configurable, optional, default 8000, positive integer. The oversize error names the variable, the actual length and the configured limit, not a hard-coded 8000; a non-integer or non-positive limit is itself a `ConfigurationError` naming the variable. FR-007 lists it, the Configuration table notes the default is a cost guard rather than a platform limit, and AC-017 exercises a limit other than 8000 so the test proves the value is read. | — | — |

## Cuts confirmed

- Failure Modes table — no loss: AC-004 enumerates the paths, and a 2xx empty body is covered by "must parse directly as JSON".
- Edge Cases 1–5 — one loss: the no-matchups digest instruction (restored in v0.3, see FR-002).
- AC-010 (old byte-identical criterion) — no loss: AC-001 and AC-004 cover both directions.
- Open Question 2 — no loss.

## Re-review findings — closed in v0.3

1. Workflow guard was incomplete and named no mechanism → FR-007 now guards key **and** base URL through an `env:` expression and states that `if:` cannot express it; the workflow assertion moved to WC-001 (static YAML check), and AC-009 keeps only what a fake client observes.
2. League rule was not total → FR-004 states the total order; AC-008 and FR-006's reasons aligned; a duplicate or stray entry at equal counts renders, only a count mismatch fails.
3. AC-006 asserted a property of untouched code → scoped to the summary service and new code, with a digest marker and existing logging declared out of scope.

Minor: FR-002's no-matchups sentence restored; the "existing mode predicate" wording replaced with an explicit local sixth copy plus an agreement assertion in AC-012.

---

## Gate 2 — plan and tasks (plan v1.0, tasks v1.0)

> Rulings of 2026-10-21. DEFERRED and CONCEDED rows are precedent for Gate 3.
> Verdict: HOLD — six material findings, all cheap; nothing here reopens a Gate 1 ruling.

| Decision | Ruling | Carries to |
|---|---|---|
| Fail-open boundary catches only `AISummaryError` (Decision 1) | DEFENDED in shape (one boundary, one call site, `Exception` not `FFTrackerError` so a cosmetic failure cannot render `Error:` exit 1); CONCEDED in breadth — `_parse_response` catching `TypeError`/`ValueError` makes the effective boundary wider than the declared one and mislabels a coding error as a provider fault. | The propagation test (`test_generate_propagates_programming_errors`) must exist before Task 7 is done; Gate 3 rejects a parse helper whose only failure mode is `AIContractError`. |
| Digest is `dict[str, object]` (Decision 4) | DEFERRED — nothing reads the digest back, so a key typo degrades the prompt silently rather than raising `KeyError`; the 5-class objection is fair against dataclasses but `TypedDict` was never considered (~25 lines, no conversion layer, key typos become mypy errors). Verification: adopt TypedDict, or Task 5's test must compare the digest's exact recursive key set. | Task 5 and Gate 3: a builder helper whose keys no test asserts is a cut. |
| Two test seams: `FakeAIClient` + injectable `HTTPTransport` (Decision 6) | DEFENDED as policy (network-free, no dependency, no fixture server); detail CONCEDED — `urlopen` returns `HTTPResponse`, so it cannot satisfy `-> bytes`, and `urlopen(request, timeout)` passes the timeout as `data`. Verification: `_urlopen(request, timeout) -> bytes` wrapper plus one `unittest.mock.patch("urllib.request.urlopen")` test. | Gate 3: the default (production) transport path must have a test; every task test injects a fake and would not catch it. |
| AI configuration beside `FFTrackerConfig` (Decision 3) | DEFENDED — `create_config()` serves three CLIs and FR-001 scopes the feature to `ff-tracker`; a malformed `AI_SUMMARY_*` must not break the other two. Ordering CONCEDED: `load_environment()` runs only inside `create_config()`, so the loader must run after it or call it itself; Task 12's "first" contradicts the Configuration section's "loaded the same way as existing settings". | Gate 3: a test that a `.env`-only configuration enables the feature, with `create_config` unpatched. |
| `DivisionData.reg_season_count: int = 14` (Decision 5) | DEFERRED — correct for the 62 fixture sites, but a silently-defaulted 14 is a false statement in any second production builder and the digest quotes it into the prompt as fact. Verification: consider `int \| None = None` with the digest omitting `weeks_remaining` (same number of touched sites, one extra branch). | Gate 3: any new production `DivisionData(...)` builder. |
| `::warning::` printed by `main.py` (Component 10) | DEFENDED — a workflow command is process output; services must not print and formatters have no process-level channel; `main.py` already owns `print()` for both report paths. | — |
| Per-socket timeout vs FR-003's "call abandoned at `AI_SUMMARY_TIMEOUT`" | DEFERRED to the owner — the plan is right that stdlib offers no wall-clock deadline, and right to reject a thread wrapper (a timed-out future does not cancel its worker and shutdown hangs the process); its claim that `signal.alarm` breaks under pytest is inaccurate but the conclusion stands. FR-003's sentence is what must change, not the plan. Verification: LV-003 proves the notice path; no unit test can prove wall-clock. | Spec wording (owner); Gate 3 must not read the current FR-003 sentence as met. |
| Console/championship insertion rationale (Decision 7) | CONCEDED (minor) — console emits season challenges after weekly highlights (`console.py:126-136`), so championship mode ends on the challenge table, not a player-highlight note line. Append-at-end is still the correct behaviour; the stated reason is not. | — |

**Cut list of this gate**: the seven-variable `--help` table (FR-009 needs the egress sentence, not a third copy of the config table); `AI_SUMMARY_MODEL` in the workflow `env:` (duplicates the code default and lets the two diverge); the `AGENTS.md` paragraph (no FR, fourth copy of the same description, in the file every agent reads).

**Closed by spec v0.8**: the per-socket-timeout row is not carried to Gate 3 — FR-003 now says the socket read is bounded by `AI_SUMMARY_TIMEOUT` with no wall-clock deadline, and Article X matches, so the plan is the record of what the code does rather than an exception to the spec.

**Task shape**: no task is unnecessary — all 14 trace to an FR or AC. Tasks 7 and 8 merge (Task 7's happy-path test cannot pass while its matching/normalisation stubs raise contract errors, which breaks the plan's green-suite-per-task invariant). Task 9 stays whole: adding a keyword parameter to the `@abstractmethod` makes every override incompatible unless all six signatures move together, and `championship.py:193/494` passes keyword arguments, so the two excluded CLIs are unaffected.

### Re-review — plan v1.1, tasks v1.1, spec v0.8 (2026-10-21)

| Gate 2 row | Status |
|---|---|
| Fail-open breadth (`_parse_response`) | **CLOSED as a rule** — only `JSONDecodeError` is converted; every other rejection is an explicit `isinstance`/`len`/`strip` check. **Test CARRIED**: `test_generate_propagates_programming_errors` stubs the digest builder, which raised `AttributeError` under the v1.0 design too, so it proves the outer catch and not that the inner one is gone. It must also raise `TypeError` from inside the parse (`json.loads` patched) and assert `generate` raises. |
| Digest typing | **CLOSED** — `TypedDict` adopted, every key total, `null` for unknown, golden recursive key-set test in Task 5. Carry to Gate 3: the golden must be authored from FR-002, not snapshotted from the builder (a snapshot blesses a wrong key), and the v1.0 rule bullets that say "seeds … preserved" and describe one `{"round", "matchups"}` block *per division* contradict the flat `AIPlayoffRound` and must be rewritten. |
| Transport | **CLOSED** — `_urlopen(request, timeout) -> bytes` is the default, `HTTPTransport` matches that signature, and a `patch("urllib.request.urlopen")` test drives the production path. |
| Config ordering | **CLOSED** — the loader calls `load_environment()` itself; `main.py` calls it after `create_config` and before any ESPN call; Task 4 proves a `.env`-only setup with `create_config` unpatched. |
| `reg_season_count` | **CLOSED** — `int \| None = None`; unknown serialises as `null` rather than quoting a fabricated 14 into the prompt. |
| Per-socket timeout | **CLOSED by spec v0.8, description nit closed in v0.9** — FR-003 states the per-operation bound and that no wall-clock budget is guaranteed; Article X matches; the Configuration table now reads "Per-socket-read timeout in seconds" instead of "Whole-call timeout". |
| `AI_SUMMARY_MAX_TOKENS` (spec v0.9) | MEASUREMENT-DRIVEN — the hard-coded 8000 truncated `glm-5.3-flash` on the real 5,158-token digest (8000/8000 reasoning, `content: null`). FR-003 sends the configured value, FR-007 rejects a non-positive or non-integer one, AC-010 proves it is read rather than assumed. | — |
| `AI_SUMMARY_REASONING_EFFORT` (spec v0.9) | MEASUREMENT-DRIVEN — optional `low\|medium\|high`, sent as `reasoning_effort` only when set and omitted entirely when unset; FR-007 rejects other values naming the allowed set; the spec states it is a non-standard extension an endpoint may ignore, and that ignoring it is not a failure. | — |
| Default model → `deepseek-v4.1-flash` (spec v0.9) | MEASUREMENT-DRIVEN — the previous default exhausted its budget on reasoning for the grown digest (8000/8000, `content: null`, 50 s); the new default completes the same payload in about 2,057 reasoning tokens and 9 s. `glm-5.3-flash` stays supported via `AI_SUMMARY_MODEL`, with the larger-budget or honoured-`reasoning_effort` trade-off stated. | — |
| `::warning::` in `main.py` | DEFENDED — unchanged, no reason to revisit. |
| Console/championship placement rationale | **CLOSED** — Decision 7 now says the report ends on the season-challenge table. |
| Cut list | **APPLIED** — `--help` reduced to the egress paragraph (Task 11 + Component 10, test updated to assert the wording rather than a variable list); `AI_SUMMARY_MODEL` removed from the workflow with a static assertion that it stays out; `AGENTS.md` dropped and moved to "deliberately untouched". Keeping `AI_SUMMARY_USER_PROMPT: |` was **right**, not an unfinished cut: FR-008 makes the committed block scalar the only record an archived CI report can be reproduced from, it is content rather than a pinned setting, and it is empty by default. Caveat: anything inside the block is literal prompt text, so the explanatory comment belongs above the key. |
| Tasks 7+8 merge | **ACCEPTED** — restores the green-suite-per-task invariant at task boundaries; the internal order (parse → match → normalise) is a task's own business, and no further split. |

**CARRIED (blocking)**: AC-006's client half still has no test (Task 6 gains the logging rule, not the assertion); AC-012's mode-agreement clause is still argued structurally instead of tested.

**Verdict**: HOLD — three edits (two bullets in `tasks.md`, one prose fix in plan Component 5). No re-planning required.

---

## Gate 3 — implementation review (spec v0.10)

> Three places where spec 009 contradicted the code or itself. All three are text edits; no requirement, cap, criterion or settled row was reopened. Verdict: the spec side is closed here; the code-side items below are the implementer's.

| Finding | Status |
|---|---|
| FR-007 validated `AI_SUMMARY_TIMEOUT`, `AI_SUMMARY_MAX_TOKENS` and `AI_SUMMARY_MAX_PROMPT_CHARS` unconditionally, contradicting FR-001 (off means unchanged output) — one stale `.env` value exited 1 with no report | **CLOSED by spec v0.10** — every FR-007 bullet is scoped to `AI_SUMMARY_ENABLED` true, and any other malformed `AI_SUMMARY_*` value is ignored while the feature is off; a malformed value of the flag itself stays an error, since an unreadable flag cannot be read as off. Code side (implementer): parse and validate the AI configuration behind the enable check. |
| FR-009 said the request body carries league IDs, which FR-002, the digest builder and the README all deny | **CLOSED by spec v0.10** — the phrase is deleted; the request body now reads team names, owner names, and points for and against. No code change implied. |
| AC-010 implied one test double observes every value | **CLOSED by spec v0.10** — the criterion names the test doubles and the layer each value belongs to: construction sees model, base URL, timeout and bearer token; the request sees `max_tokens` and `reasoning_effort`. Every assertion is unchanged; the existing two-seam tests already satisfy it. |

### Re-review — remediation @ 116d460 (2026-10-21)

**Closed, verified against the code and the tests:**

| Gate 3 finding | Outcome |
|---|---|
| 1. Mid-body transport failure | CLOSED — `except (OSError, http.client.HTTPException)` after the timeout handlers, mapping to `AITransportError`; unit, service-level and end-to-end tests. `test_mid_body_failure_still_ships_the_report_and_exits_zero` patches `urllib.request.urlopen` and makes `response.read()` raise, so the real `_urlopen`, client, service and console run; it fails against the pre-fix code (exit 1, “Unexpected error”). |
| 2. Console flattening | CLOSED — `BaseFormatter._flatten_text` (display-layer string handling) used by console and by sheets' `_ai_cell`; the rewritten AC-011 test asserts no tab, one line, one bullet line, and fails against the old `lines.extend(paragraphs)` implementation. |
| 3. Malformed base URL | CLOSED — scheme/host check in `AISummaryConfig.__post_init__`, two tests; the loader only validates when enabled. |
| 4. Feature-off validation | CLOSED in code — the loader reads only the flag and returns the disabled default. Test-strength note: the junk-variable test asserts timeout/budget/effort/base-URL/prompt-cap defaults but not `model`, `user_prompt` or `api_key`; the guarantee is structural (early return), not fully observed. |
| 5. Workflow prompt test | CLOSED — emptiness assertion removed, comment-inside-block check kept. |
| 6. AC-012 five outputs | CLOSED — four formatters parametrised plus exact JSON `report_type`, both modes. |
| 7. Untested branches | CLOSED — trailing-paragraph drop (3×60 words) and opponent true diff (3.14) both discriminate. |
| 8. Self-asserting test | CLOSED — deleted; no coverage lost. |
| 9. `finish_reason` at INFO | CLOSED — removed from the log line; still used for the truncation decision. |
| 10. FR-009 league IDs | CLOSED by spec v0.10. |
| 11. Playoff-mode matchups | CLOSED — suppressed in playoff and championship; digest test asserts it. |
| 12. `AIRequest.max_tokens` default | CLOSED — removed; callers pass the configured value. |
| 13. Plan bookkeeping | CLOSED — exception hierarchy and `User-Agent` recorded. |
| 14. README stale sentence | CLOSED — corrected. |

**Closed by spec v0.11 — the one open text item:** FR-002's standings bullet now names the digest's own values (`in_playoff_position` / `outside_playoff_position`, current position against the top-four cutoff) and requires the `standings_note` that the status is not a final outcome, beside the existing no-matchups sentence, so the golden key-set test is again authored from FR-002. FR-009 now describes the prompt as a committed workflow `env:` block scalar, and AC-009 states its enable precondition. Remaining for the implementer: `plan.md:119/362/390` and `tasks.md:110` still list the old `qualified|eliminated` values — those files are untouched by this spec edit, and the plan/tasks value lists must follow FR-002 before Gate 3 closes.

**Merge order:** PR #7 first (it renames the JSON formatter's values), then rebase this branch. If this branch lands first, FR-002's clause is false for the interval; the reviewer must re-verify that `json.py` and `ai_digest.py` word `playoff_status` identically once #7 merges.

### Owner changes — spec v0.12

| Owner change | Status |
|---|---|
| The section moves up: after the weekly highlights, before the season-long challenges, with the failure notice in the same position; JSON's top-level key unchanged | **OWNER CHANGE, spec closed** — FR-005's intro, table, FR-006's notice position and AC-002/AC-018 now say so, and the report order chain is stated. Code and plan follow: the four positioned formatters move the insertion point, and the plan/tasks text that describes a trailing section must be corrected with it. |
| One retry, only for contract failures, plus the prompt naming the league count and names | **OWNER CHANGE, spec closed** — FR-003 scopes the retry (contract violations only; never HTTP 4xx/5xx, transport, timeout or `finish_reason == "length"`; same prompt and payload; second failure is the ordinary FR-006 outcome; worst case two attempts and roughly two socket-read timeouts) and requires the prompt to list the league count and names verbatim. FR-008 adds `provenance.attempts`; AC-019…AC-022 cover the retry and AC-018 the placement. Implementation follow-ups: the retry loop, the provenance field, the prompt clause and the placement move. |

**Verdict:** HOLD — one spec/plan/tasks edit; the fourteen findings and the digest code fix are closed. No requirement, cap, criterion or settled row reopened.

### Delta — spec v0.12 implementation @ 8fcc942 (2026-10-21)

| Delta item | Outcome |
|---|---|
| Placement moved to between the weekly highlights and the season challenges (console, markdown, email, sheets); JSON unchanged; notice in the same slot | **CLOSED** in code and spec. The placement tests fail on the old trailing position (`weekly < season < ai`); the notice test fails on the old slot; the email test now asserts challenges before footer. Code inspected in regular, playoff and championship: the insertion sits outside the weekly guard and before the season block in all four formats, and no deterministic section is suppressed. AC-001's difflib check is a mid-document insert. |
| One retry, contract failures only, identical request, `provenance.attempts` | **CLOSED.** Only `AIContractError` is caught; the second attempt reuses the same `AIRequest`; a second failure re-raises into the ordinary FR-006 boundary (no third call); HTTP/transport/timeout/truncation make exactly one call and the tests fail if they are retried; `attempts` is 1 or 2 in the model, the loop and the serializer. Digest built once, request built once; only the client's per-call INFO line and one DEBUG retry line repeat. |
| Prompt anchor: league count and names from the digest; `prompt_sha` over the composed prompt | **CLOSED** — the scope follows the digest, the hash is stable for identical inputs and changes with the league set. The FR-009 side closes with spec v0.13: the DEBUG bullet now names the league scope and permits league names only in that line. The logging test's WARNING-level assertion that no league name appears outside DEBUG is an implementer follow-up, not a spec item. |
| A failed generation records no `attempts` | **DEFENDED** — the failure contract is a single error string; a contract-failure notice implies two attempts (the first always retries), and a mixed contract-then-HTTP failure names the final failure. No change. |

**Closed by spec v0.13 — the one spec sentence:** FR-009's DEBUG bullet now names the league scope (count and names) and permits league names only in that line, so it no longer forbids what the code does; the WARNING-level assertion that no league name appears outside DEBUG remains an implementer follow-up, as do the doc rewording items below (README:422, CHANGELOG:11, plan.md:13) and the low-severity AC-018 and `prompt_sha` notes.

**Open — docs:** README:422, CHANGELOG:11 and plan.md:13 still say the section is the report's last / rendered last. Reword to “between the weekly highlights and the season challenges”.

**Low — AC-018 coverage:** placement is tested in regular season only. Add one playoff and one championship case per format (their markers differ) and a `weekly=None` case, so a block moved inside the weekly guard would fail.

**Low — `prompt_sha` material includes the user prompt twice** (the composed prompt already contains the block, then the user prompt follows the separator). Deterministic and harmless; `prompt_sha(composed_prompt)` would remove the redundancy and the stale Decision 8 rationale.

**Verdict:** HOLD — the delta's code is correct; one spec sentence and three doc lines must follow it.

---

## v0.14 — prompt source moves to repository variables (spec v0.14)

| Change | Status |
|---|---|
| CI prompt source: the committed `AI_SUMMARY_USER_PROMPT: \|` block scalar is replaced by repository variables — `AI_SUMMARY_BASE_URL`, `AI_SUMMARY_MODEL`, `AI_SUMMARY_TIMEOUT`, `AI_SUMMARY_MAX_TOKENS`, `AI_SUMMARY_REASONING_EFFORT`, `AI_SUMMARY_MAX_PROMPT_CHARS` and `AI_SUMMARY_USER_PROMPT` — with the prompt taken from `vars.AI_SUMMARY_USER_PROMPT \|\| secrets.AI_SUMMARY_USER_PROMPT`. The user prompt is not in git; the system prompt template stays a module constant. | **OWNER CHANGE, spec closed** — FR-009's egress bullet and the CI-record sentence say variable-or-secret and note that variables are not masked in logs while secrets are; FR-008's caveat now says an archived report shows that the same instructions produced it but cannot reproduce them, and retention is the operator's; FR-007 records that a blank optional value means "use the default" while a malformed non-blank one is still an error; the Configuration note is corrected. Implementation follow-ups: the workflow `env:` forwarding — these settings are inherited from the workflow env and are never written to `.env`, where the writer only handles `LEAGUE_IDS`, the ESPN cookies and `AI_SUMMARY_ENABLED`/`AI_SUMMARY_API_KEY` — and the doc lines that still describe a committed prompt. |

### Gate 3 — v0.14 prompt source (branch `feature/ai-summary-vars` @ `e873e45`)

| Point | Outcome |
|---|---|
| Expression semantics | **CORRECT** — `secrets` is permitted in the workflow-level `env:` (GitHub's context table lists `github, secrets, inputs, vars` for `env`), `\|\|` returns the first truthy operand and an unset `vars.*` evaluates to `""` (falsy), and masking rewrites log output only, not the rendered env. Variables win when both are set; a whitespace-only variable is truthy, shadows a secret, and the loader then strips it to no instructions. |
| Empty-string forwarding | **CORRECT** — an unset workflow variable renders `""`; the optional settings are inherited from the workflow env and are not written to `.env`; `load_dotenv` does not override an existing env var; the loader treats empty and absent alike. No shell step interpolates them, so no `''` or dropped-variable path exists. |
| Prompt-in-secret path | **WORKS** — masked in logs, still hashed by `prompt_sha`, no FR-009 conflict (the prompt is not report data). Hardening open: the secret sits at workflow-level `env:`, so every step, including the pinned setup actions, receives it; move it to the report step's `env:`. |
| Tests | Exact expressions per key fail on a rename, a drop or a wrong context. `test_no_optional_value_is_wrapped_in_a_shell_guard` and `test_no_duplicate_env_keys` are redundant (the loader rejects duplicates in every test; shell guards cannot live in YAML). The block-scalar mistake is caught by `test_no_block_scalar_remains_for_the_prompt`, not by the comments test. |
| `pyyaml` | **ACCEPTED** — the `dev` group is already unpinned (`ruff`, `mypy`, `pytest`); a hand-rolled YAML parser is worse. Runtime dependencies stay pinned. |
| Stale docs | **OPEN** — `plan.md:532/536/544/723` and `tasks.md:268/287` still describe the removed committed `AI_SUMMARY_USER_PROMPT: \|` block scalar, and this v0.14 row's "`.env` write for these variables" is wrong: the optional settings are inherited from the workflow env and never written to `.env`. `README.md`'s example sets the variable and the secret one after the other, so the variable wins and the unmasked store is used — present them as alternatives. |

**Verdict:** HOLD — the CI change works; the plan/tasks references and the README example must follow, and the prompt secret should move to the report step's `env:`.

---

## v0.15 — email name highlighting and a one-run prompt override (spec v0.15)

| Change | Status |
|---|---|
| Email names: team names inside the AI text wrapped in `<span class="ai-team">`, bold and coloured by the new `email.ai_team_color` format argument (default `#0b57d0`), plus a one-run `ai_summary_prompt` `workflow_dispatch` input with precedence input → `vars.AI_SUMMARY_USER_PROMPT` → `secrets.AI_SUMMARY_USER_PROMPT` → empty | **OWNER CHANGE, spec closed** — FR-005's email row and its five highlighting bullets state the matching (case-insensitive, original casing kept, longest name first, whole names), the escaping rule (segment by segment, so apostrophes and `<`, `>`, `&` stay text), the class-plus-inline-style split so stylesheets can override, and that the notice path and the other four formats are untouched; AC-023 covers it. FR-010 states the input precedence, that the input is non-persistent, that an empty input falls through rather than clearing the variable or secret, that dispatch strings are single-line, and that a dispatch input is visible in the run's inputs so it must not carry a secret; FR-009 and the Configuration note list the new source. Implementation follow-ups: the email wrapper and format argument, the dispatch input, and the workflow step env that forwards `inputs.ai_summary_prompt || vars.AI_SUMMARY_USER_PROMPT || secrets.AI_SUMMARY_USER_PROMPT`. |

### Gate 3 — v0.15 delta @ ff6369d (2026-10-21)

| Point | Outcome |
|---|---|
| Email highlighting | Matching handles the asked cases: a prefix name loses to the longer one (longest-first); straight apostrophes, a trailing space in the data, possessives (the name is wrapped, `'s` stays outside), repeated occurrences and case-only matches. Escaping is per segment — the raw match never reaches the HTML, and the colour is HTML-escaped. **Known trade-offs:** case-insensitive whole-word matching wraps ordinary prose when a team name is a common word (`Win`, `Big`, `The`) or a player's surname (`Brown` in "A.J. Brown"); it misses curly-apostrophe variants (`Drew’s`), punctuation changes the model makes (`St.` → `St`), and paraphrases. The spec says "every occurrence", so these are accepted, not defects. **Defect:** the `.ai-team` stylesheet rule is built from a plain string with doubled braces (`ff_tracker/display/email.py:88-92`), so the email emits `.ai-team {{ … }}` — invalid CSS; the inline style still applies, and no test asserts the rule's presence or content. |
| AC-001 helper | **Not weakened.** It asserts every non-equal SequenceMatcher opcode is an `insert` and reconstructs the off string exactly from the on string minus the inserted ranges, so a replace/delete (a moved or reworded line) fails; the multi-insert tolerance is what the email's two blocks need. It still uses the off output as the reference, so an addition present in both off and on is invisible to it; the absolute guarantee remains the worktree `diff -r`, and a targeted off-state assertion would close the CSS-rule case. |
| Conditional rule | `isinstance(ai_summary, AISummary)` — narrative only; the notice path is tested; the off path is not tested in the suite (external diff only). |
| Workflow input | `inputs` is permitted in step-level `env:`. On `schedule` the context is unavailable and evaluates to an empty string, so the `\|\|` chain falls through correctly (community caveat: using it as a boolean `if` without a type guard errors; here it is a string). Empty input falls through; a whitespace-only input is truthy and then stripped to no instructions. |
| Help/doc | `--help`'s "Email-Specific" list (`ff_tracker/main.py:151-153`) omits `email.ai_team_color` although README and `get_supported_args` have it. FR-005's "stylesheet rule can override it" is inaccurate: the inline style wins unless the rule uses `!important`. Plan/tasks carry no AC-023 or dispatch-input entry (low). |

**Closed by spec v0.15 wording correction:** FR-005's stylesheet sentence now reads that the class is for targeting and for clients that strip `<style>`, the inline style applies unless a rule uses `!important`, and the shipped `.ai-team` rule is weight-only. The doubled-brace CSS defect and the missing `--help` line remain implementer items.

**Verdict:** HOLD — fix the doubled braces, add a test for the rule's presence with a narrative and absence when off, and add the help line. The matching limitations are accepted trade-offs, not defects.

---

## v0.16 — team-name span is class-only (spec v0.16)

| Change | Status |
|---|---|
| Email team-name highlight: the span becomes `<span class="ai-team">` with no `style` attribute, and `.ai-team { color: <email.ai_team_color, default #0b57d0>; font-weight: 700; }` in the email's stylesheet carries the appearance, emitted only when a narrative renders | **OWNER CHANGE, spec closed** — FR-005's email row, its span bullet and the two style bullets state the class-only span, the stylesheet rule and its emission condition; AC-023 asserts the colour lands in the rule and the rule is absent for the notice. Reason recorded: the template is already stylesheet-driven — `.winner`, `.challenge-name`, `.playoff-team` and `.container` all declare on the class — so an inline span was inconsistent with the rest of the message, and leaving only the weight on the class made `email.ai_team_color` unstyleable by class. Trade-off accepted rather than hidden: a client that strips `<style>` loses the highlight, exactly as it already loses those other classes. Matching and escaping rules are unchanged. Supersedes the v0.15 row's "class-plus-inline-style split so stylesheets can override", which was also factually wrong — an inline style wins unless a rule uses `!important`. |

### Gate 3 — v0.16 class-only span @ c385e9c (2026-10-21)

| Point | Outcome |
|---|---|
| Defect this switch exposes | The doubled-brace rule recorded in the v0.15 Gate 3 row is now the only carrier of the appearance, so `ff_tracker/display/email.py` must emit single-braced, valid CSS; an invalid rule now loses the highlight instead of the inline style covering for it. Implementer item, with a test asserting the rule's presence and its colour. |
| Not emitted when off, not for the notice | The rule belongs in the same conditional as the section, so no `.ai-team` selector appears when `ai_summary` is absent or is the `AISummaryUnavailable` notice. Implementer item: assert the rule's absence in both. |
| Clauses this edit does not touch | Longest-first ordering, whole-name matching, the model's original casing, segment-by-segment escaping and the report-data-only name list are unchanged; AC-023's clauses for them stand. |
| `--help` | The `email.ai_team_color` line missing from `--help` stays an implementer item from the v0.15 row; the argument's name and default do not change here, so the spec needs no new wording for it. |

**Verdict:** HOLD — the spec, AC and ledger agree; the implementer must drop the inline style, emit a valid single-brace `.ai-team` rule, assert its presence with a narrative and its absence for the notice and when off, and add the `--help` line.

---

## Gate 1 — v0.19 memory amendment

> Rulings of 2026-10-27 on spec v0.18. Nothing here reopens an earlier gate: the store,
> the model-appended memory and the fail-open asymmetry stand as decided.
> Verdict: HOLD lifted — all **seven** blockers (B1–B7) and all six should-fixes accepted,
> three requirements cut.

| Finding | Ruling | Carries to |
|---|---|---|
| B1 — a revoked gist token was described as behaving like a missing key, i.e. no report at all; the boolean `memory_read` could not separate "never configured" from "dead token for sixteen weeks" | ACCEPTED — one explicit status map in FR-014: `memory_read` is `"ok" \| "none" \| "failed"`, `memory_write` is `"ok" \| "failed" \| "skipped"`. Absent file / no file for a league / 404 on the gist is `"none"` — no memory yet, no warning, the write still attempted. Read 401/403 is `"failed"` with **exactly one** `::warning::` under Actions naming authentication; read 5xx/transport/timeout is `"failed"` and silent. Every write failure ships the report, warns once, exit 0. No read failure appears in the report in any format. FR-007's revoked-token sentence deleted; a present-but-dead token is a read/write failure, not a configuration error. AC-031/AC-032 restated. | FR-005, FR-006, FR-007, FR-014, AC-031, AC-032 |
| B2 — `prompt_sha` had absorbed the memory block, breaking comparability with every archived report, and FR-005 claimed provenance fields were the only output-visible effect without naming them | ACCEPTED — `prompt_sha` hashes the **instructions only** (template, FR-003 league scope, `### COMMISSIONER'S INSTRUCTIONS` block), byte-equal to the archived definition. New `provenance.memory_sha` hashes the memory block text alone, present only when memory is on. FR-005 names all four: `history_weeks`, `memory_read`, `memory_write`, `memory_sha`. | FR-005, FR-008, Data Requirements |
| B3 — the prompt never asked for a `memory` array, so Phase 2 could never write | ACCEPTED — FR-012 states the `### MEMORY` block's exact contents (alias-to-league-name mapping, stored season, up to six entries with season and week tags, up to three prior-season summaries); FR-003 requires the prompt to state the `memory` array's shape and its rules; AC-028 asserts both. | FR-003, FR-004, FR-012, AC-028 |
| B4 — `scoring_trend` was not executable | ACCEPTED — `up` above the earlier-week mean by more than 1.0 point, `down` below by more than 1.0, otherwise `flat`, and `null` under two weeks. AC-024 carries one fixture per value; AC-025's one-week fixture asserts the `null`. | FR-011, AC-024, AC-025 |
| B5 — caps and replacement contradicted the hand-edit rule | ACCEPTED — truncation and dropping bind only text the model supplied in this run; a human-written entry is written back byte-identical even over a cap and is never dropped; a hand-added entry keyed to the run's own `(season, week)` is replaced like any other. AC-029 and LV-005 restated to match FR-013. | FR-013, FR-014, AC-029, LV-005 |
| B6 — an off-season run could write a schema-invalid file and, being then read-only forever, kill that league's memory | ACCEPTED — the write is skipped (`"skipped"`, file untouched) unless the report's season is a four-digit year and its week is an integer in 1–18. Reason stated in one clause: `espn_service.current_week` can be 0 or negative pre-kickoff and FR-014 treats a shape-mismatched file as permanently read-only. AC-030 extended to assert it. | FR-013, FR-014, AC-030 |
| B7 — `rank_by_week` had no anchor against the standings the digest already carries | ACCEPTED — the latest week present takes `standings[].rank` verbatim; earlier weeks are recomputed from `DivisionData.games`. AC-024 adds a fixture whose `DivisionData.games` is missing a week the standings still count, proving the anchor where the tolerant collection and `TeamStats` disagree. | FR-011, AC-024 |
| Should-fixes 1–6 | ACCEPTED — `average_margin` is the signed mean of `score - opponent_score`; `reg_season_count` (`int \| None`) and `weeks_remaining` (`int \| None`) are described as they exist, `None` case stated, "does not yet carry" claims deleted; Phase 1 ships first and AC-027 compares against a checked-in golden captured at the Phase-1 commit with `generated_at` pinned; FR-009 requires the DEBUG line to emit the system prompt with the memory block's text replaced by its per-alias season and week tags; memory truncation never sets `provenance.truncated`; the single contract-only retry is recorded against Articles III and V, with new **LV-006** re-measuring the 8000-token budget with both phases on and the expectation stated that it still completes in one call. | FR-005, FR-008, FR-009, FR-011, AC-024, AC-027, LV-005, LV-006, Constitution Deviations, Data Requirements |
| Cut 1 — the model-written `season_summary` field | ACCEPTED — cut from the response contract; rollover uses the deterministic fallback only (that season's stored takes joined in order, truncated to 160 characters with `…`). AC-034 softened to the fallback alone; prior-season summaries stay in the `### MEMORY` block, which is what carries a finished season forward. | FR-004, FR-013, FR-014, FR-012, AC-034, Out of Scope |
| Cut 2 — `head_to_head[].points_for` / `points_against` | ACCEPTED — the row is `{opponent, wins, losses}`. FR-011 and AC-024 updated; spec.md carries no derived-block size estimate, so no number to revise (the only token budget here is the memory record's and it does not touch these fields). | FR-011, AC-024 |
| Cut 3 — FR-012 (backward references) as a requirement of its own | ACCEPTED — merged into FR-004 as the third bounded exception beside the 60-word floor and the no-invention rule, content intact in substance. Memory store/record/lifecycle renumber old FR-013…FR-015 → FR-012…FR-014, with every cross-reference in the requirements, ACs, Configuration table, Data Requirements and Out of Scope following. | FR-004, FR-012…FR-014, AC-036 |

**Verdict:** HOLD lifted. Seven blockers and six should-fixes accepted, three requirements cut, `spec.md` at v0.19. Three changes an implementer must not silently reverse: **`prompt_sha` semantics** (instructions only; the memory block is `memory_sha`), **the store status map** (`"none"` is not `"failed"`, and only a 401/403 or a write failure warns), and **the newest-rank anchor** (the latest week's ranks are the digest's standings, never recomputed from a possibly incomplete game list).

---

## Gate 1 re-check — v0.20

> Rulings of 2026-10-27 on spec v0.19. The seven original blockers and six should-fixes
> of the previous gate are verified closed; this pass closes the two shapes they left behind.

| Finding | Ruling | Carries to |
|---|---|---|
| 1 — the read gate rejected the file the spec permits: FR-013 allowed an over-cap hand-written entry, FR-014 called a shape mismatch read-only forever, so that league's memory died (the B6 shape again) | ACCEPTED — the read gate validates **structure only**: required keys, value types, `week` 1–18, a four-digit `season`, list counts. A `take`, `joke` or `summary` over its cap is **not** a shape mismatch and never makes a file read-only. An over-cap hand-written entry is truncated **for the prompt only** (word boundary, `…`) and stored byte-identical — one clause in FR-012's block contents, one in FR-014 — so the LV-006 budget stays bounded. AC-028, AC-029 and AC-033 assert it. | FR-012, FR-013, FR-014, AC-028, AC-029, AC-033 |
| 2 — AC-031 asserted a gist-404 write succeeds while AC-032 asserted a write 404 fails | ACCEPTED — AC-031's gist-404 fixture only **attempts** the write; success stays with the absent-file and no-file fixtures and failure with AC-032's write-404 → `"failed"`. | AC-031, AC-032 |
| 3 — "a run whose read and write both fail emits one line for each" contradicted FR-014's silent 5xx read | ACCEPTED — both sentences scoped to an **authentication** read failure: a 401/403 read plus a failed write emit one line each, and AC-032 names that fixture and pairs it with a silent-read case that emits only the write's line. | FR-014, AC-032 |
| 4 — `memory_sha` had no algorithm, length or presence rule worth the name | ACCEPTED — sha256 over the block text, first 12 hex characters, exactly as `prompt_sha`; **absent whenever no block was sent**, i.e. on a `"none"` or `"failed"` read. FR-005, FR-008 and FR-014 say which memory field is present in which case; AC-028 asserts different blocks differ, the same block repeats, and a `"none"` read carries no key. | FR-005, FR-008, FR-014, AC-028 |
| 5 — FR-004 miscounted its exceptions | ACCEPTED — "the third bounded exception" becomes "the bounded exception", since the 60-word floor excepts nothing and FR-004 calls it guidance elsewhere. | FR-004 |
| 6 — AC-027 pinned `generated_at` but not `model` | ACCEPTED — the fixture pins both and configures the golden's model through `AI_SUMMARY_MODEL`, so a default-model bump cannot fail the Phase-1 golden for a reason unrelated to memory. | AC-027 |
| 7 — FR-014's per-league triggers read as run-level outcomes | ACCEPTED — the read bullets are reworded per league ("for a league whose file is absent, …"), leaving the union rule as the only run-level sentence about the field. | FR-014 |

**Verdict:** HOLD lifted — the seven original blockers and six should-fixes verified closed, and this pass closed the read-gate structure, the 404 contradiction, the warning scoping and `memory_sha`'s presence and algorithm. One residual for the owner, carried not decided: entry **count** is in the structural gate as ruled, and a file whose hand-written entries fill all six slots cannot take a new model-written entry without exceeding that count — the same read-only trap, one level up, if it ever happens.

---

## Gate 1 residual — v0.21

> Ruling of 2026-10-27 on the entry-count trap left open by v0.20. This is the one
> place the spec's **design** changed after the re-check rather than a wording fix:
> without an authorship marker the service could not tell its own entries from a
> human's, so "never drop a hand entry" was unimplementable, not merely awkward at
> the count.

| Point | Ruling | Carries to |
|---|---|---|
| The trap — entry count sat inside the structural gate while manual entries could never be dropped, so a file with six hand entries plus one model entry became read-only, and the service had no way to know which was which | ACCEPTED as a design change — an authorship marker is added rather than the count removed alone. | FR-013, FR-014 |
| A — `entries[].source` | ACCEPTED — `"model"` or `"manual"`; the service tags what it writes, and an entry without the field reads as `"manual"`, so hand editing needs no ceremony. FR-013 states why in one clause: the file is co-authored and the tool must distinguish its own prose from an edit without guessing. | FR-013 (schema, table, JSON example) |
| B — the gate checks no count | ACCEPTED — keys, value types, `week` 1–18, four-digit `season` values with the file's `season` equal to its newest entry's, `source` one of the two values or absent. Entry **and** summary counts never make a file read-only, joining over-cap text in that rule. | FR-013, FR-014, AC-033 |
| C — the write drops only what it wrote | ACCEPTED — oldest `"model"` entries beyond six and oldest service-written summaries beyond three; a `"manual"` entry or summary is never dropped, reordered or rewritten except by the same-week replacement, which applies to any `source`. A file whose six slots are manual still accepts this week's entry. Rollover empties the model entries in the window and leaves manual ones alone. | FR-013, FR-014 |
| D — the prompt takes the newest six | ACCEPTED — at most six entries, newest by `(season, week)`, no source preferred, because a joke from Week 3 is context rather than instruction; over the block's budget they are dropped oldest-first **for the prompt only**, file untouched. The size-budget bullet now says the figure bounds the prompt, not the file. | FR-012, FR-013, AC-028 |
| E — `season_summaries` courtesy | ACCEPTED — unbounded by the gate, never dropped if hand-written, at most three in the block, truncated for the prompt only. One clause, not a second rule set. | FR-012, FR-013, AC-028 |

**Verdict:** HOLD lifted — the trap is closed at its root, not at the count. The prompt's size is now bounded by rule (newest six by chronology, prompt-only truncation) rather than by the assumption that the file stays small, and `source` is the marker that makes C implementable at all.

---

## Owner redesign — v0.23: memory is the published summary

> Owner decision of 2026-10-27, given in conversation. Phase 2 shrank from a second
> artifact with its own schema, witnesses and compaction rules to a log of what the
> tool already publishes.

| Change | Ruling | Carries to |
|---|---|---|
| What memory is | The owner's reasoning, recorded: generating a second artifact per week invented a second voice and a second schema to keep honest. The published summary already exists, already passed the contract, and already carries the week it belongs to — so the log is the summary plus a week tag, and nothing is asked of the model for it. | FR-013 |
| One gist, one file | `memory.json`, not one file per league id. The gist is the key: one gist is one commissioner setup however many divisions it spans, so league ids stay out of filenames and the `league_1`… alias layer has no job left. | FR-012 |
| Hand edits without machinery | Append-only at the run level — earlier entries are never modified, reordered or dropped — so a hand edit inside an earlier entry is safe by construction and `entries[].source` is unnecessary. | FR-013 |
| The only mutation | A re-run of the same week replaces that entry, so a dispatch re-run cannot stack a second take. Still the only mutation and the only removal. | FR-013 |
| The whole archive in the prompt | No selection, window, truncation, dropping or caps. Trimming would be a compaction rule by another name, and the season is bounded anyway. | FR-012, FR-013 |
| Two prompt rules replace a contract | Quotation — the archive is *what you published*, a record, never a source of league fact, and this week's data wins on any disagreement — and continuation: a running bit escalates or retires, because repeating a joke in the same words is the failure memory exists to prevent. | FR-004 |
| `memory_weeks` replaces `memory_sha` | A list of the weeks that were in the prompt answers "what was in context"; a hash does not. All three memory provenance fields are absent when memory is off. | FR-005, FR-008 |
| Cost | Stated once and plainly: ~500 words per entry, ~56 KB and ~10,000 prompt tokens by Week 17; a whole season of archive costs a few cents. Cost is not a reason to shorten anything, and `AI_SUMMARY_MAX_TOKENS` bounds the reply, not the prompt. Every sentence that treated token count or a prompt budget as governing memory size is gone. | FR-013, Configuration |
| Deleted outright | Per-league files and league-id keying; the alias mapping; `entries[].source`; `take`/`joke` and their 200/120 caps; the truncation order; the six-entry window; the size-budget reasoning; `season_summaries`; rollover; the older-season rule; the structural read gate and the never-overwrite-a-bad-shape rule; the `memory` array in FR-004 with its retry interaction, per-entry validation and duplicate-alias rule; `provenance.memory_sha`. What survives from the old design is the store's status map, its one-read-one-write discipline and its two warning cases. | FR-002…FR-005, FR-008, FR-009, FR-012, FR-013, Configuration, Data Requirements, AC-006, AC-027…AC-032 |
| Scope statements | Backfill is not a product feature — the owner will run a throwaway local script, so generating a week's summary and appending it must be callable outside the CLI. Out of Scope also names all prompt-side pruning, compaction, rollover and cross-season carry-over. | Out of Scope |
| Raised, not decided | A cross-division consolidated view (all teams ranked across divisions, highest score and biggest beatdown across divisions) would give the shared headline something to be about for a 24-plus-person group. Derived from data already held. Recommended as a Phase 1 companion; **not approved**, so not in the requirements. | Open Questions |

**Verdict:** ACCEPTED as the owner's design. Three things an implementer must not silently restore: **the quotation rule** (the archive is never a source of league fact), **append-only** (a write never touches an earlier entry — the only exception is the same-week replacement), and **`memory_weeks` instead of a hash** (the archive's presence is a list of weeks, not a checksum). Anything that reintroduces a cap, a window, a rollover or a model-authored memory field is a new owner decision, not an implementation detail.

---

## Owner addition — v0.24: the league-wide view

> Owner decision of 2026-10-27. The item previously recorded as raised-but-not-decided
> is now approved and becomes Phase 1's second block.

| Change | Ruling | Carries to |
|---|---|---|
| Why it exists | One 24-plus-person league was split across divisions for platform limits. The shared headline is the only section addressed to everyone at once, and the per-division digest gave it nothing cross-division to be about — the narrative could only eyeball separate tables. | FR-012, Problem Statement |
| `overall_standings` | Every team across every division in one ranking, `{rank, team, division, record, points_for}`. The ordering is **passed through, not newly computed**: the report already ranks all teams by wins then points for in `base.py:_get_overall_top_teams`, and the digest states that rule instead of inventing a second one and requires agreement with the console's overall table for the same inputs. Where the console table caps at 20, the digest carries every team — the jokes land at the bottom too. | FR-012, AC-027, AC-026 |
| `weekly_extremes` | Highest and lowest score, biggest winning margin and closest game measured **across divisions**, from the weekly matchups already loaded. This one **is** new computation, unlike the ranking; where a value coincides with a per-division challenge winner the two must agree because both read the same rows. `null` when the run has no weekly matchups. | FR-012, AC-027 |
| Prompt rules | Two, and only two: an overall claim may come only from this block (a division `rank: 1` is not the best record in the setup), and this block is the source for cross-division statements without changing a per-division value. | FR-012 |
| Absence | One division: the block still exists, and `overall_standings` equals that division's standings. No completed games: both `null`, prompt says so. | FR-012, AC-027 |
| No rendering | No section, line, field or provenance key: the block is prompt input only, so FR-005's "only output-visible effect" sentence stays true. | FR-005, FR-012 |
| Renumbering | The memory requirements move to FR-013 and FR-014, and their acceptance criteria to AC-028…AC-033, with the new block taking AC-027 and AC-026's golden replaced (not doubled) to carry the three Phase-1 keys. Revision-history rows and the earlier sections of this ledger keep their original numbers — **in everything written before this section, FR-012 is today's FR-013 and FR-013 is today's FR-014**; the pointers here use the current ones. | FR-002…FR-014, AC-026, AC-027, Delivery Phases, Configuration, Data Requirements |

**Verdict:** ACCEPTED. Two things an implementer must not silently change: **the ranking is a pass-through of the report's existing overall order** (a second comparator is a bug even when it looks equivalent), and **the per-division rank rule stays in the prompt** (without it the model reads a division's rank 1 as the best record in the whole setup, which is exactly the confusion this block exists to remove).

---

## Gate 2 — v0.25 wording fixes

> Plan review of 2026-10-27. No design change was found — seven ambiguities, two of
> which left criteria unowned.

| Fix | Ruling | Carries to |
|---|---|---|
| AC-027, single division | ACCEPTED — "identical" was unsatisfiable: a league-wide row is `{rank, team, division, record, points_for}` and a per-league standings row also carries `owner`, `points_against` and `playoff_status`. The criterion now asserts the same teams in the same order with `rank`, `record` and `points_for` matching. | AC-027 |
| Provenance on the notice path | ACCEPTED — `history_weeks` was promised "whenever the feature is on" and the memory fields "whenever memory is on", but a failed narrative renders `{"error": …}` with no provenance object at all, which is today's behaviour and the intended one. All four fields are now present only when a narrative renders. | FR-005, FR-008 |
| FR-011 null types | ACCEPTED — the `games` collection is built tolerantly, so a team can have no game; `streak`, `best_week`, `worst_week` and `average_margin` are `null` for it, stated in the table and in a bullet. | FR-011 |
| FR-014 read 404 | ACCEPTED — a 404 on read is `"none"`, and the write that follows 404s in turn and is AC-032's write failure. | FR-014 |
| Season keying | ACCEPTED — entries are keyed by week inside a file whose `season` is fixed when the file is created, so a later-season run would replace the same week's entry; the operator retires `memory.json` at a season boundary. Documentation of the single-season assumption, not new behaviour. | FR-014 |
| "No structural gate" | ACCEPTED — the two sentences contradicted each other and the plan does reject a wrong `schema`, a missing key and an out-of-range `week`. Reworded to *parses as the archive shape*: schema, required keys and week range are checked; content, counts, text length and season agreement never make a file read-only. | FR-014 |
| Two unowned criteria | ACCEPTED — AC-031 gains the read-404-then-attempted-write case (it asserts the attempt, not the outcome, so it cannot contradict AC-032), and AC-033 gains the season/week guard: writes nothing, leaves the file byte-identical, records `"skipped"`. | AC-031, AC-033 |

**Verdict:** ACCEPTED — the plan review found no design change, only these ambiguities and two unowned criteria. AC-027's wording was the one that could never have passed as written: it demanded byte-equality between two row shapes that differ by design. Nothing here reopens a design decision.

---

## Gate 2 closed — v2.2

> Verification of 2026-10-27 on plan v2.1 / tasks v2.1 / spec v0.25. Two must-fixes, both
> cross-reference defects rather than design; three notes. Nothing here reopens a ruling.

| Finding | Ruling | Carries to |
|---|---|---|
| **M1 — the dependency map contradicted the design.** Tasks v2.1 said T101, T102 and T103 were independent, but T103's `overall_standings` calls `rank_overall_teams`, which T102 creates; followed literally, the phase's fourth task cannot start in either order. | ACCEPTED — restored: **T103 requires T102**; T101 is independent of both. The strict prerequisites now read T103 ← T102, T105 ← T101, T106 ← all four. | tasks.md, dependency map |
| **M2 — AC-033's third clause had no owner.** "an over-long stored paragraph is read, sent into the prompt as written" was asserted nowhere: the traceability row listed T201, T202, T204 and T207, none of which composes the prompt, so the clause held only because nothing truncates. | ACCEPTED — **T205 joins AC-033's row**, and its six-week test asserts that a stored paragraph longer than any cap appears verbatim in the composed memory block. The criterion now fails if anything ever starts trimming the archive. | tasks.md, T205 and the AC-033 row |
| Note — stale version pointers | CLOSED — plan 8/21/243 and tasks 9/642 still read "spec v0.24, plus the review wordings a parallel dispatch applies". All five now point at **spec v0.26**, the version that carries those wordings plus the AC-032 fix. The version rows in each Revision History keep their original dates as history, not pointers. | plan.md, tasks.md |
| Note — a spec nit that did not exist | CLOSED — the plan recorded that the Configuration table still called `AI_SUMMARY_TIMEOUT` a whole-call timeout. It does not: the row already reads "Per-socket-read timeout in seconds". The nit is deleted so nobody opens a spec edit for a correct line. The section now reads "None". | plan.md, Spec nits |
| Note — AC-032's "byte-identical" | CLOSED — the same-week replacement clause required every other entry to be byte-identical, which no parse-and-rewrite can satisfy: re-serialising changes whitespace and key order with nothing edited. Spec v0.26 changes it to **"unchanged in value"**, matching AC-033 and the plan's existing reading. One row records it and nothing else. | spec.md v0.26, AC-032 |

**Verdict:** GATE 2 CLOSED. The two must-fixes are applied, all three notes are closed with no requirement changed beyond AC-032's one word, and every criterion clause now names a task that asserts it — the traceability table covers AC-001…AC-033, WC-001/WC-002, LV-001…LV-006 and T203's manual premise, with the manual rows marked as manual. **Artifacts frozen at plan v2.2, tasks v2.2 and spec v0.26**: no further edits to these three without a new gate. **Phase A (T101, T102, T103, T105, T106) may start**, delivered as one engineer pass against the merged task list.

---

## Quality review — v0.27: a failed read must not overwrite

| Item | Ruling | Carries to |
|---|---|---|
| What was found | A read failure suppressed nothing but the unparseable-file case: a 5xx, transport error, timeout or auth rejection left the archive empty in memory, and the write that followed replaced a whole season's entries with the one new week. Read failures are the silent kind, so the loss would not have announced itself. | FR-014 |
| Why it was a defect and not a preference | Append-only is the promise that makes a hand edit safe by construction. A path that silently rewrites the whole file in one write is an exception to that promise in the same sentence that advertises it — so this is a contradiction inside the requirement, not a tuning choice. | FR-014 |
| The ruling | The write is skipped when the read failed for any reason — auth, server, transport, timeout, unparseable file — in addition to the season/week guard, because the merge cannot preserve what it never read. During a failed read the store is left exactly as it was, and `memory_write` is `"skipped"`, never a later `"ok"` or `"failed"` for that run. | FR-014, FR-013, AC-032 |
| Criterion it changes | AC-032's paired clause (an auth read failure plus a failed write emitting two lines) was unreachable once a failed read suppresses the write. It now asserts the failed-read case: one `::warning::` when the failure was a 401/403 and none otherwise, `"skipped"` for the write, and the fake store byte-identical afterwards. Write failures stay reachable through a store that reads cleanly and fails on write; a 404 read is still `"none"` and still attempts the write. | AC-032, AC-031 |
| Traffic wording | FR-013 said "one read and one write per run", which no longer describes a run whose read failed. It now says one read, and one write only when that read succeeded. | FR-013 |

**Verdict:** ACCEPTED, and implemented in code before the wording landed. The spec's own append-only promise is what made this a defect rather than a preference: a transient error must cost one week of memory, never the season.
