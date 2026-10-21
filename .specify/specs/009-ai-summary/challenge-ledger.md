# Challenge Ledger — 009 AI Summary

> Gate 1 (spec) · `spec.md` v0.14 (this commit) · Constitution v1.0.0, no conflict.
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
| CI prompt source: the committed `AI_SUMMARY_USER_PROMPT: \|` block scalar is replaced by repository variables — `AI_SUMMARY_BASE_URL`, `AI_SUMMARY_MODEL`, `AI_SUMMARY_TIMEOUT`, `AI_SUMMARY_MAX_TOKENS`, `AI_SUMMARY_REASONING_EFFORT`, `AI_SUMMARY_MAX_PROMPT_CHARS` and `AI_SUMMARY_USER_PROMPT` — with the prompt taken from `vars.AI_SUMMARY_USER_PROMPT \|\| secrets.AI_SUMMARY_USER_PROMPT`. Nothing prompt-related is in git. | **OWNER CHANGE, spec closed** — FR-009's egress bullet and the CI-record sentence say variable-or-secret and note that variables are not masked in logs while secrets are; FR-008's caveat now says an archived report shows that the same instructions produced it but cannot reproduce them, and retention is the operator's; FR-007 records that a blank optional value means "use the default" while a malformed non-blank one is still an error; the Configuration note is corrected. Implementation follow-ups: the workflow forwarding and the `.env` write for these variables, and the doc lines that still describe a committed prompt. |
