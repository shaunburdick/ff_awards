# Feature: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: Draft — revised after Gate 1
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-21
> **Version**: 0.6

## Overview

The weekly report (`ff-tracker`) currently renders deterministic facts only. This feature adds an optional, AI-written narrative — a "commissioner's take" — as an additional section inside the existing weekly report, in all five output formats. It is not a new CLI and not a new format.

The narrative is generated text and is labelled as such everywhere it appears. If it cannot be generated, the report ships without it and says so. Nothing in the existing deterministic sections changes.

---

## Problem Statement

The weekly report tells a commissioner what happened but not how to talk about it. Writing the weekly blurb by hand is the last manual step before the report goes out, and it is skipped when the week is busy. A generated narrative is worth having even though it is imperfect: the alternatives are a hand-written paragraph or no paragraph at all. The narrative must never be able to stop the report.

---

## Done when

`ff-tracker` with the feature enabled renders a labelled AI section containing one subsection per league, and a run where the provider fails still produces the full deterministic report plus a visible notice, exit code 0, and a GitHub Actions warning.

---

## Functional Requirements

### FR-001 — Opt-in generation

- The feature is off unless `AI_SUMMARY_ENABLED` is true. With the feature off there is no HTTP call, no section, no notice, no warning, and the output is unchanged from the current report.
- A configured API key does not turn the feature on.
- The feature covers the weekly report CLI only (`ff-tracker`), in regular, playoff (Weeks 15–16) and championship (Week 17) modes. It does not cover `ff-championship` or `ff-season-recap`.
- When on, the narrative is generated once per report execution, before rendering, and the same narrative is embedded in every format the run produces (single format or `--output-dir`). One run = one provider call, regardless of league count and format count.

### FR-002 — Payload

The digest sent to the provider is built from the domain models (`DivisionData`, weekly challenges, season challenges, championship leaderboard where present), not from the JSON formatter's output. It carries, per league:

- league name, team count, current week, and weeks remaining in the regular season (`reg_season_count - current_week`, never below zero — this reads a field the models do not yet carry; see Data Requirements);
- standings: rank, team name, owner name, record, points for, points against, and whether the team is currently **inside or outside the top four by record** — the `in_playoff_position` boolean, worded as the JSON's `playoff_status` values, not a seed, playoff rank or prediction;
- the week's matchups: both team names, both scores, margin, both projected scores, and each team's `true_projection_diff`. A `WeeklyGameResult` row carries only its own `starter_projected_score` and `true_projection_diff`; the opponent's true diff is read from the mirror row, pairing rows by `team_name`/`opponent_name`, and left out when no mirror row exists. There is no opponent true-diff field to read. The digest states explicitly when a league had no matchups this week;
- the weekly challenges that league won, under the mode rule below.

**Mode rule (one rule).** The digest derives the mode locally with the same two expressions the formatters use — `any(d.is_playoff_mode for d in divisions)` and `championship is not None` — and the digest must agree with what the formatters render for the same inputs; AC-012 asserts that agreement. It is a deliberate sixth copy of those two lines, not an extraction: each of the five formatters already computes them independently, and `ReportContext._build_context_from_params` is not reachable from a service. In each mode the digest carries:

- regular season: standings and the 13 weekly challenges, with their winners globally;
- Weeks 15–16 and Week 17: bracket matchups or the championship leaderboard instead of weekly team challenges, the 7 player highlights only, standings where the formatters show them, and the 5 season-challenge leaders marked historical (final at the end of Week 14).

The digest contains no league IDs, no ESPN credentials and no API key.

### FR-003 — Request

- One OpenAI-compatible Chat Completions call to `<AI_SUMMARY_BASE_URL>/chat/completions` with `Authorization: Bearer <AI_SUMMARY_API_KEY>`.
- `max_tokens` is 8000. At 3000 the spike's reasoning models returned `finish_reason: length` with empty or truncated content in all four cells; at 8000, 8/8 returned clean JSON.
- The call is abandoned at `AI_SUMMARY_TIMEOUT` seconds. No retries, no streaming.
- The response must parse directly as JSON matching the contract in FR-004. Fenced, prefixed or otherwise non-JSON responses are contract failures, not parsed leniently.

### FR-004 — Narrative contract

Response shape:

```json
{
  "headline": "string",
  "leagues": [
    { "league": "string", "paragraphs": ["string"], "bullets": ["string"] }
  ],
  "season_note": "string"
}
```

- `headline`, every `paragraphs` entry and `season_note` are non-empty strings; `bullets` may be empty.
- Each league entry has at least one paragraph, and every paragraph contains at least one word after trimming — a whitespace-only paragraph is invalid. `"paragraphs": []` is a contract failure.
- League matching is a **total order**, applied once per response:
  1. If every league name matches exactly one entry and every entry matches exactly one league (after `strip().casefold()` equality), map by name. Response order is irrelevant.
  2. Otherwise, if the entry count equals the league count, map by position in digest order, and render every heading from our own league names — never from the response. A stray, renamed or duplicated entry at equal counts lands here and renders. Response order is expected to follow the digest order: (1) does not depend on it and (2) is defined by it.
  3. Otherwise — the counts differ and (1) did not resolve — the response is a contract failure: the section is not rendered, wholly or partially.
- Voice: a commissioner addressing the league — direct, dry, allowed to be wry, no invented statistics and no claims about players or teams absent from the digest.
- The section is labelled in every format as AI-generated. It is never presented as fact-checked or as a league record. No requirement verifies that its claims are true; only the shape and league matching are validated.
- The narrative may not be used to compute, alter or replace any deterministic value.

**Length caps, enforced after the contract checks:** `headline` ≤ 15 words; per league ≤ 3 paragraphs, ≤ 3 bullets, and ≤ 120 words across its paragraphs (bullets count only against the ≤ 3 bullet cap, not against the 120 words); `season_note` ≤ 40 words.

**Validation order, fixed:** contract shape → league matching (the total order above) → length normalisation → render. Normalisation is deterministic and total — the same response normalises to the same output every time — and it never turns a valid response into a contract failure.

**Normalisation, in this order:**

1. Drop bullets after the third, in response order.
2. Drop paragraphs after the third, in response order.
3. If a league's paragraphs still exceed 120 words, drop whole trailing paragraphs until they fit. If the **first** paragraph alone exceeds 120 words, truncate it at the last word boundary at or before 120 and append `…`, dropping every other paragraph.
4. Truncate `headline` beyond 15 words at a word boundary with `…`. Truncate `season_note` beyond 40 words at a word boundary with `…`.

There is no sentence detection anywhere in this path: initials in names (`J.J. Smith`, `A.J. Brown`) are indistinguishable from sentence ends, so the rule is structural — whole bullets, whole paragraphs, then whole words. `…` is appended only where step 3 or 4 cut a first paragraph, the headline or the season note.

120 is a cap, not a target: the 60-word floor is prompt guidance only, deliberately not validated, because enforcing it would mean padding the prose — inventing facts — or dropping a short section, both worse than a short take.

`provenance.truncated` is `true` when normalisation dropped or shortened anything for this report, and absent or `false` otherwise.

### FR-005 — Rendering

The section appears as the last section of the report, after the existing deterministic sections and before any format footer, in all five formats. No existing section changes position, content or order.

| Format | Placement | Shape | Absent |
|---|---|---|---|
| console | after standings | `🤖 COMMISSIONER'S TAKE (AI-GENERATED)` header, headline, per-league subsection, paragraphs, `•` bullets, `Generated by <model> · AI-generated text` line | one-line notice in the same position |
| sheets | after standings, blank row | `AI SUMMARY (AI-GENERATED)` row, `HEADLINE:` row, `LEAGUE:` row per league, paragraphs flattened to one row each, bullets as `- ` rows, attribution row | one-line notice row |
| email | after standings, before footer | section with heading, AI-generated marker, `<p>` paragraphs, `<ul>` bullets, attribution line; HTML-escaped | one-line notice |
| json | top-level `ai_summary` key | object described below | `"ai_summary": {"error": "<notice text>"}` |
| markdown | after standings | `## 🤖 Commissioner's Take (AI-generated)`, `### <league>`, paragraphs, `- ` bullets, italic attribution line | one-line notice |

JSON `ai_summary` object:

```json
{
  "headline": "string",
  "season_note": "string",
  "leagues": [{ "league": "string", "paragraphs": ["string"], "bullets": ["string"] }],
  "provenance": {
    "model": "glm-5.3-flash",
    "prompt_sha": "9f2c1ab4e7d0",
    "generated_at": "2026-10-14T05:03:11Z",
    "truncated": false
  }
}
```

- `ai_summary` is absent when the feature is off; present (narrative or error) when it is on.
- Cell values in sheets and console must not contain tabs or newlines; paragraph text is flattened, not reflowed or summarised.

### FR-006 — Failure policy: the report always ships

Any failure while obtaining, matching, validating or normalising the narrative produces the same result: the deterministic report is rendered and written as normal, the section is omitted, the run exits 0, and the failure is visible in two places:

1. a one-line notice in the output, in the section's position at the bottom, in the format's own style: `AI summary unavailable: <reason>. The report is unaffected.` In JSON the notice is the value of `ai_summary.error`. The notice stays where the section would have been — it is not hoisted into the header, because nothing about the deterministic report changed.
2. when `GITHUB_ACTIONS` is `true`, a workflow command on stdout: `::warning::AI summary unavailable: <reason>.` — outside Actions no workflow command is emitted, so console output stays clean. This warning is the visibility backstop that a bottom-of-report notice needs.

`<reason>` names what failed and never includes the API key or the response body: for HTTP errors `HTTP 410 (model glm-5.3-flash at opencode.ai)`; for transport errors `connection failed (opencode.ai)`; for timeouts `timed out after 120s`; for truncation `finish_reason=length`; for shape problems `response did not match the summary contract`; for a league-count mismatch `league count mismatch (3 leagues, 2 sections)`. The endpoint appears as its **host only**, never its path or query, because a custom base URL may embed a credential there — with a defaulted endpoint, the host is also what tells a commissioner whether the default or their override failed.

This is a deliberate, documented exception to Article III (see Constitution Deviations).

### FR-007 — Enabled but not configured

Configuration errors are not narrative failures and are not degraded:

- `AI_SUMMARY_ENABLED` true with `AI_SUMMARY_API_KEY` missing or empty → `ConfigurationError` naming `AI_SUMMARY_API_KEY`, exit 1, no report, no HTTP call.
- `AI_SUMMARY_ENABLED` set to any value not in `true|1|yes|on|false|0|no|off` (case-insensitive) → `ConfigurationError`.
- `AI_SUMMARY_TIMEOUT` not a positive integer → `ConfigurationError`.
- `AI_SUMMARY_USER_PROMPT` longer than 8000 characters → `ConfigurationError` naming the variable, its actual length and the limit.
- Misspelled or missing provider settings therefore fail loudly once, instead of quietly degrading every scheduled run.
- Because that failure produces no report, the weekly workflow sets `AI_SUMMARY_ENABLED=true` only when `secrets.AI_SUMMARY_API_KEY` is non-empty, and omits it otherwise. The base URL needs no guard because it has a default. The guard is an `env:` expression yielding the literal `true`/`false` (e.g. `AI_SUMMARY_ENABLED: ${{ secrets.AI_SUMMARY_API_KEY != '' }}`) consumed by the step that writes `.env`. It cannot be an `if:` condition: `secrets` is not available in `jobs.<job_id>.if` or `steps.<job_id>.if`, so such a condition evaluates without the secret and silently disables the feature. No workflow sets the flag unconditionally.

**Tradeoff, stated plainly:** a fork or a rotated credential leaves the flag on with no key, and with the flag on that means no report at all — not a report without a narrative. Without the workflow guard, a missing secret would silently stop the weekly report, which is the one outcome this feature must not cause. With the guard, a checkout without the key produces a normal report with the feature off, and gets no AI section until an operator supplies the key. The guard is therefore a requirement, not workflow polish.

### FR-008 — Provenance and determinism

- JSON records `provenance.model`, `provenance.prompt_sha`, `provenance.generated_at` (ISO 8601 UTC) and `provenance.truncated`. `prompt_sha` is a hash over the system prompt text **and** `AI_SUMMARY_USER_PROMPT` (FR-010), in that order with a fixed separator, computed at generation time — so editing the user prompt changes it. The limitation stated plainly: the user prompt itself is not archived, so an archived report can be reproduced only if that value was retained; committing it as a workflow `env:` block scalar is the recommended way to keep it reviewable.
- console, sheets, email and markdown carry the model id in the attribution line. They do not carry `prompt_sha`.
- The narrative is not deterministic: two runs over identical data may differ in wording and emphasis, and no requirement compares two live generations.
- For identical inputs and identical narrative outcome, every deterministic section is byte-identical, and is identical to a run with the feature off. The report's facts never depend on the narrative.

### FR-009 — Secrets and privacy

- The API key never appears in any output, artifact, error message, notice, warning command or log line, including when the provider echoes it back in an error body or header.
- The key is supplied only through `AI_SUMMARY_API_KEY` (environment or `.env`, same loading as `ESPN_S2`/`SWID`). There is no CLI flag and no `--format-arg` for it — format arguments are for presentation and must not carry credentials.
- The digest, the request body and the response body are never logged at any level, including `-vv`. Only the model, HTTP status, latency and token counts may be logged.
- Team names, owner names and scores leave the machine and are sent to `AI_SUMMARY_BASE_URL`. `AI_SUMMARY_USER_PROMPT` (FR-010) is sent verbatim to the provider, so it must never contain credentials; and because a repository *variable* is visible in repository settings, anything the league would not publish belongs in a secret. `ff-tracker --help` states this under the feature's configuration section.

### FR-010 — User prompt

- `AI_SUMMARY_USER_PROMPT` is optional and defaults to empty. It is free-form — tone, nicknames, running jokes, facts to mention, things never to say — with no required structure. It is appended to the system prompt as a clearly delimited block: `### COMMISSIONER'S INSTRUCTIONS` on its own line, then the value, sent verbatim inside that block.
- Reading rules: the value is used exactly as supplied; leading and trailing whitespace is stripped and internal newlines are preserved; CRLF is normalised to LF. An empty or whitespace-only value means "no extra instructions" and is not an error — the block is then omitted rather than sent empty.
- Size cap: 8000 characters, measured after the whitespace strip. Linux permits roughly 128 KB per environment variable and GitHub caps a secret at 48 KB, so this limit exists to keep prompt size and cost bounded, not to respect a platform limit. Exceeding it is a `ConfigurationError` naming the variable, the actual length and the limit.
- **Precedence:** the user prompt shapes tone and content only, and is ignored wherever it would contradict the JSON contract, the caps and normalisation (FR-004), or the "no invented facts" rule (FR-004).
- The user prompt is trusted input authored by the commissioner and is not sanitised: the JSON contract and normalisation run after generation and are the actual guardrail. Nothing in this feature validates the factual accuracy of the prose, including anything the user prompt asks it to say.
- It is never echoed into the report; `prompt_sha` (FR-008) is the only trace of it.

---

## Configuration

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `AI_SUMMARY_ENABLED` | no | `false` | Opt-in switch. Off means no call, no section, no notice. |
| `AI_SUMMARY_API_KEY` | when enabled | none | Bearer token; never printed. |
| `AI_SUMMARY_BASE_URL` | no | `https://opencode.ai/inference/openai/v1` | OpenAI-compatible endpoint root; `/chat/completions` is appended. An empty or whitespace-only value falls back to the default rather than erroring. |
| `AI_SUMMARY_MODEL` | no | `glm-5.3-flash` | Model id, reported verbatim in errors and provenance. |
| `AI_SUMMARY_TIMEOUT` | no | `120` | Whole-call timeout in seconds. |
| `AI_SUMMARY_USER_PROMPT` | no | empty | Free-form commissioner instructions appended to the system prompt (FR-010); stripped, CRLF-normalised, maximum 8000 characters. |

These are loaded the same way as existing settings (`load_environment` / `.env`); `AI_SUMMARY_USER_PROMPT` can be set as a GitHub Actions `env:` block scalar, so it is committed and reviewable without any runtime file, and `.env` accepts a quoted multi-line value. Enabling the feature needs only a key: the endpoint default matches the model default. A default endpoint we do not control can change upstream, and the failure is visible — notice plus `::warning::` — rather than silent, which is why the default is acceptable now. The default base URL and the model id belong in `.env.example` and the README's configuration section: a plan requirement, not a code comment.

---

## Data Requirements

### Input

- The weekly report's existing data: `list[DivisionData]`, `list[ChallengeResult]`, `list[WeeklyChallenge] | None`, `current_week`, optional `ChampionshipLeaderboard`, as already assembled in `main.py`.
- The value of `AI_SUMMARY_USER_PROMPT`, if any (FR-010).
- Feature configuration from the table above.

### Model additions this feature requires

- `DivisionData.reg_season_count` (or an equivalent field on the same model), populated from the ESPN `League` settings. It does not exist today — `DivisionData` carries `league_id`, `name`, `teams`, `games`, `weekly_games`, `weekly_players` and `playoff_bracket` — so FR-002's "weeks remaining" is a model change the plan must carry, not existing data.

### Prompt

- The system prompt is a module-level constant in the summary service under `ff_tracker/services/`, so a prompt edit is a single reviewable diff; `prompt_sha` is computed from that constant plus `AI_SUMMARY_USER_PROMPT`. Nothing is read from disk.

### Output

- `AI summary` value embedded in the report: headline, per-league paragraphs and bullets, season note, provenance (FR-004, FR-005, FR-008).
- On failure: a notice string rendered in the report and, in JSON, `ai_summary.error`.

---

## Acceptance Criteria

Tested offline with a fake client that records requests and returns canned responses.

- **AC-001** Feature off: zero calls recorded. Each of the five formats is compared against the feature-on output produced in the same test: JSON documents are parsed and compared after removing the `ai_summary` key; console, sheets, email and markdown are compared on everything outside the new block, by asserting the output equals its pre-section prefix followed by its post-section suffix.
- **AC-002** Feature on with a valid fake response: the section appears in all five formats, after the existing sections and before the footer, labelled AI-generated; JSON `ai_summary` contains headline, one entry per league in digest order, and provenance.
- **AC-003** Multi-league run: exactly one call, regardless of 1, 3 or 10 leagues, and exactly one call in `--output-dir` mode with five formats; the same narrative appears in all five files.
- **AC-004** Each failure path in FR-006 — HTTP 4xx/5xx, transport error, timeout, `finish_reason=length`, contract mismatch, league-count mismatch — produces: the complete deterministic section set, exit code 0, one notice line in the section's position, no empty heading, no `::warning::` when `GITHUB_ACTIONS` is unset, and exactly one `::warning::` line when it is `true`.
- **AC-005** A fake error body never appears in stdout, stderr, the notice, the warning, or any file written to `--output-dir`; the API key appears nowhere; and the configured endpoint appears, if at all, as its host only — never its path or query.
- **AC-006** No log line emitted by the summary service or by any other code this feature adds contains a team name, owner name, league ID, API key, prompt text or response body; a unique marker planted in the digest never appears in a `-vv` run over three leagues. Existing logging in modules this feature does not touch is out of scope for this criterion.
- **AC-007** `finish_reason: "length"` with complete, parseable content is still treated as FR-006's truncation failure — the content is not rendered.
- **AC-008** League matching follows FR-004's total order: (i) entries reordered, or differing only in case and surrounding whitespace, map by name; (ii) with equal counts and no full name match — including one stray entry or one duplicated entry — every section renders by position under our own league names, and no response-supplied league name appears as a heading; (iii) with differing counts and no full name match, the FR-006 contract failure is reported with the count-mismatch reason and nothing is rendered.
- **AC-009** Missing key, bad `AI_SUMMARY_ENABLED` value, and non-numeric or zero `AI_SUMMARY_TIMEOUT` each raise `ConfigurationError` naming the variable, exit 1, record zero calls, and write no report.
- **AC-010** The fake client records the model, base URL, timeout, `max_tokens: 8000` and bearer token from each configuration; changing `AI_SUMMARY_MODEL` changes the value sent and the value in provenance and the attribution line; unset, empty and whitespace-only `AI_SUMMARY_BASE_URL` all send the default `https://opencode.ai/inference/openai/v1`, and an explicit value overrides it.
- **AC-011** A paragraph containing a tab, newline, `"`, `<`, `&` and emoji renders as one sheet row and one console line, is HTML-escaped in email, and does not break TSV column counts.
- **AC-012** Edge-case inputs — single league, a league with no matchups this week, Week 15 playoff mode, Week 17 championship mode, and a digest with no player data — each produce a valid request and a rendered section; the digest sent in Weeks 15–16 carries bracket matchups and the 7 player highlights, and in Week 17 the championship leaderboard, matching what the formatters display; the mode the digest derives agrees with the mode each of the five formatters renders for the same inputs.
- **AC-013** An overlong fake response — four paragraphs, one of 200 words, four bullets, a 20-word headline and a 60-word `season_note` — normalises to the caps: headline ≤ 15 words, ≤ 3 paragraphs, ≤ 3 bullets, ≤ 120 words per league, `season_note` ≤ 40 words; the first paragraph and the first three bullets survive unchanged; and two runs over the same fixture produce byte-identical output with the same `provenance.truncated` value.
- **AC-014** When the first paragraph alone exceeds 120 words it truncates at the last word boundary at or before 120 with `…` appended, and every other paragraph is dropped.
- **AC-015** Bullets beyond the third are dropped rather than merged into a paragraph, paragraphs beyond the third are dropped, and `provenance.truncated` is `true` when anything was dropped or shortened and absent or `false` when nothing was.
- **AC-016** The user prompt reaches the request body inside the `### COMMISSIONER'S INSTRUCTIONS` block; changing it changes `prompt_sha`; and a user prompt instructing the model to add fields, exceed the caps, return non-JSON or invent a fact does not alter the output shape after normalisation.
- **AC-017** A value over 8000 characters raises `ConfigurationError` naming the variable, the actual length and the limit, records zero calls and writes no report; an unset, empty or whitespace-only value is accepted and sends no instructions block.

### Workflow configuration check (static; inspects the YAML, not runtime behaviour)

- **WC-001** `.github/workflows/weekly-report.yml` sets `AI_SUMMARY_ENABLED` through an `env:` expression that references `secrets.AI_SUMMARY_API_KEY`; the step that writes `.env` appends the `AI_SUMMARY_*` values only when that value is `true`; and no `if:` condition in the file references `AI_SUMMARY_ENABLED`.

Verified manually against a live provider, once, with a real three-league week:

- **LV-001** Response validates against FR-004 in one call; prose references figures that appear in the deterministic report (spot-check two quoted numbers); length falls in the expected range.
- **LV-002** Setting `AI_SUMMARY_MODEL` to a model id known to be unavailable (e.g. `kimi-k2.6`) yields the FR-006 HTTP failure: report present, notice names the model and status, exit 0.
- **LV-003** Set `AI_SUMMARY_TIMEOUT=1` to force the FR-006 timeout against the live provider; report present, notice names the timeout, exit 0.
- **LV-004** On a week with player highlights suppressed (playoff week or no player data), the returned narrative names no individual players.

---

## Edge Cases

1. **Provider returns well-formed JSON for the wrong week or season** — shape and league matching pass; there is no further verification (see Not doing). The report's deterministic sections remain the source of truth.
2. **Very long prose** — normalised to the FR-004 caps before render, then flattened to one TSV row; a single unbroken token wider than a table cell is still truncated by that format, as it is for any cell.

---

## Constitution Deviations

**Article III (Fail-Fast Error Handling).** This feature violates the "no partial data tolerance" clause on purpose: an AI narrative failure degrades the report instead of failing it. Reasoning: the narrative is cosmetic, the report carries the league's weekly facts, and the report runs on a weekly schedule where a failed proxy, model retirement or HTTP 410 would otherwise deny the league its report entirely. The exception is bounded — it applies only to obtaining, matching and normalising the narrative; ESPN data failures, configuration errors (including an oversized `AI_SUMMARY_USER_PROMPT`) and every other failure path still fail fast, and the omission is never silent (notice plus Actions warning). Length normalisation never fails the run: the contract already requires at least one non-empty paragraph per league, and normalisation only drops or shortens content, so the report always ships. This exemption must be recorded in the plan's Complexity Tracking.

**Article X (Performance).** The 5-second typical run applies to the deterministic report with the feature off. With the feature on, the run additionally waits for provider latency (7.7–34.4 s per call in the spike), bounded by `AI_SUMMARY_TIMEOUT`. Callers that care about schedule duration leave the feature off.

---

## Out of Scope (Not doing)

- The season recap (`ff-season-recap`) and championship (`ff-championship`) CLIs.
- Anthropic, Gemini or any provider API family other than OpenAI-compatible Chat Completions; provider SDKs.
- Streaming, retries, caching, or a second attempt with a fallback model.
- A user-authored system prompt: the template itself is a module constant, and only the `AI_SUMMARY_USER_PROMPT` suffix is configurable. Configuration cannot override the contract or the caps.
- Adding `weekly_games` to the JSON formatter (the digest is the AI payload, not a new public shape).
- Changing, reordering or reformatting any existing deterministic section.
- Per-format or per-league opt-out: when the feature is on, all five formats get the section.
- Fact-checking the prose beyond the contract, league matching and caps in FR-004, and beyond the user-prompt precedence rule in FR-010 — including anything the user prompt asks it to say.
- Any `--format-arg` for this feature; credentials and provider settings are environment only.

---

## Open Questions

None open.

---

## Related Specifications

- **002: Weekly Highlights** — supplies the weekly challenges the digest carries.
- **003: Output Formatters** — all five formats gain the section; no existing field changes.
- **005: Format Arguments** — this feature adds no format arguments, because credentials must not travel through them.
- **006: Playoff Mode** — defines the Weeks 15–17 modes the digest must mirror.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-10-21 | AI Agent | Initial draft from the product owner's decisions and the week-6 spike evidence |
| 0.2 | 2026-10-21 | AI Agent | Gate 1 revisions: digest fields matched to model reality (playoff-position boolean, mirror-row true diff, `reg_season_count` as a model addition); one mode rule replaces the playoff contradiction; no digest/body logging plus a `-vv` criterion; `prompt_version` replaced by `prompt_sha` with the prompt located in the service; league matching gains a positional fallback; workflow conditionally sets the enable flag with the tradeoff stated; unexecutable byte-identical criteria replaced; failure-mode table, edge cases 1–5, the old byte-identical AC and Open Question 2 cut (ACs renumbered); duplicated spike numbers reduced to where they drive requirements |
| 0.3 | 2026-10-21 | AI Agent | Re-review revisions: the workflow guard covers key **and** base URL, names the `env:` expression and states that `if:` cannot express it (`vars` chosen for the URL with the reason); the workflow assertion moved out of AC-009 into a static WC-001; league matching stated as a total order with AC-008 and FR-006's reasons aligned (duplicates and strays at equal counts render; only count mismatches fail); the no-matchups digest sentence restored; the mode rule now says the digest carries a local sixth copy and must agree with the formatters; AC-006 scoped to this feature's own logging with a digest marker |
| 0.4 | 2026-10-21 | AI Agent | Owner changes: `AI_SUMMARY_BASE_URL` gains the `https://opencode.ai/inference/openai/v1` default (empty/whitespace falls back), the missing-base-URL branch and its guard half are gone, and key-only enablement is stated with the uncontrolled-endpoint tradeoff; length caps are enforced by deterministic normalisation after league matching, with `provenance.truncated` and the sentence-boundary rule; new FR-010 adds a committed lore file with a 4000-character cap, a neutral packaged default, contract-over-lore precedence, lore egress in FR-009, `prompt_sha` covering prompt plus lore, and wheel-inclusion verification; AC-013…AC-018 added; the lore exclusion is removed from Out of Scope; Edge Case 2 restated because capped prose is no longer "rendered as delivered" |
| 0.5 | 2026-10-21 | AI Agent | Normalisation replaced with structure-first rules that need no sentence detection (initials such as `J.J. Smith` broke the abbreviation list): drop bullets, drop paragraphs, drop trailing paragraphs to fit 120 words, truncate only a first paragraph that alone exceeds it, then headline and `season_note` at word boundaries; the `season_note` two-sentence rule and the abbreviation/URL/number/emoji clauses are gone. The contract now requires at least one non-empty paragraph per league, so `"paragraphs": []` fails and the "normalises to nothing" failure clause is deleted. Failure reasons name the endpoint host only; AC-005, AC-010 (base-URL fallback) and AC-013 (survivors plus determinism) strengthened; the old AC-014 deleted and AC-015…AC-017 renumbered; AC-017 gains the packaged-default path; FR-008 states the two traceability limits; the floor is stated as prompt guidance that is deliberately not validated; a narrow user-authored-system-prompt exclusion returns; the lore template opens with a header saying it is committed and sent to the provider |
| 0.6 | 2026-10-21 | AI Agent | The lore file is replaced by `AI_SUMMARY_USER_PROMPT`, an optional free-form env-var string appended as a `### COMMISSIONER'S INSTRUCTIONS` block; `AI_SUMMARY_LORE_FILE`, the packaged default, the wheel-inclusion requirement, the missing-path error and the neutral-template rule are removed and nothing is read from disk. Cap is 8000 characters with the variable, length and limit in the error; strip/CRLF rules and the empty-value no-op are stated; precedence, the trusted-input note and the non-verification statement sit in FR-010. FR-008 records that the user prompt is not archived and recommends a committed `env:` block scalar; FR-009 covers user-prompt egress and variable visibility; AC-016/AC-017 are restated for the variable; the exclusion now covers the system prompt template only |
