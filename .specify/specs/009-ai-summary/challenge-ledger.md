# Challenge Ledger — 009 AI Summary

> Gate 1 (spec) · `spec.md` v0.5 (this commit) · Constitution v1.0.0, no conflict.
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
| v0.5 clauses: host in the reason, fallback test, AC strength, traceability, floor, exclusions, lore header | OWNER CHANGE — FR-006 names the endpoint host only (a custom base URL may embed a token in its path); AC-005 matches; AC-010 covers unset/empty/whitespace fallback and override; AC-013 adds surviving first paragraph and first three bullets plus repeat-run identity, and the old AC-014 is deleted with AC-015…AC-017 renumbered; AC-017 adds the packaged-default path; FR-008 states that a custom lore file is untracked and a combined hash cannot separate prompt from lore edits; the 60-word floor is declared prompt guidance that is deliberately not validated; a narrow "user-authored system prompt" exclusion returns; the shipped lore template opens with a committed-and-sent header. | — | — |

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
