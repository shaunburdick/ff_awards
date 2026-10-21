# Feature: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: Draft — revised after Gate 1
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-21
> **Version**: 0.3

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
- League matching is a **total order**, applied once per response:
  1. If every league name matches exactly one entry and every entry matches exactly one league (after `strip().casefold()` equality), map by name. Response order is irrelevant.
  2. Otherwise, if the entry count equals the league count, map by position in digest order, and render every heading from our own league names — never from the response. A stray, renamed or duplicated entry at equal counts lands here and renders.
  3. Otherwise — the counts differ and (1) did not resolve — the response is a contract failure: the section is not rendered, wholly or partially.
- Response order is expected to follow the digest order: (1) does not depend on it, and (2) is defined by it.
- Voice: a commissioner addressing the league — direct, dry, allowed to be wry, no invented statistics and no claims about players or teams absent from the digest.
- Length expectation: roughly 60–120 words per league (150–400 words for a three-league report), 1–3 paragraphs and at most 3 bullets per league, `headline` at most 15 words, `season_note` 1–2 sentences. Length is a prompt instruction, not a validation gate: an over-long response renders as delivered and is not truncated or rejected.
- The section is labelled in every format as AI-generated. It is never presented as fact-checked or as a league record. No requirement verifies that its claims are true; only the shape and league matching are validated.
- The narrative may not be used to compute, alter or replace any deterministic value.

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
    "generated_at": "2026-10-14T05:03:11Z"
  }
}
```

- `ai_summary` is absent when the feature is off; present (narrative or error) when it is on.
- Cell values in sheets and console must not contain tabs or newlines; paragraph text is flattened, not reflowed or summarised.

### FR-006 — Failure policy: the report always ships

Any failure while obtaining or validating the narrative produces the same result: the deterministic report is rendered and written as normal, the section is omitted, the run exits 0, and the failure is visible in two places:

1. a one-line notice in the output, in the section's position at the bottom, in the format's own style: `AI summary unavailable: <reason>. The report is unaffected.` In JSON the notice is the value of `ai_summary.error`. The notice stays where the section would have been — it is not hoisted into the header, because nothing about the deterministic report changed.
2. when `GITHUB_ACTIONS` is `true`, a workflow command on stdout: `::warning::AI summary unavailable: <reason>.` — outside Actions no workflow command is emitted, so console output stays clean. This warning is the visibility backstop that a bottom-of-report notice needs.

`<reason>` names what failed and never includes the API key or the response body: for HTTP errors `HTTP 410 (model glm-5.3-flash)`; for timeouts `timed out after 120s`; for transport errors `connection failed`; for truncation `finish_reason=length`; for shape problems `response did not match the summary contract`; for a league-count mismatch `league count mismatch (3 leagues, 2 sections)`.

This is a deliberate, documented exception to Article III (see Constitution Deviations).

### FR-007 — Enabled but not configured

Configuration errors are not narrative failures and are not degraded:

- `AI_SUMMARY_ENABLED` true with `AI_SUMMARY_API_KEY` missing or empty → `ConfigurationError` naming `AI_SUMMARY_API_KEY`, exit 1, no report, no HTTP call.
- The same for a missing or empty `AI_SUMMARY_BASE_URL`.
- `AI_SUMMARY_ENABLED` set to any value not in `true|1|yes|on|false|0|no|off` (case-insensitive) → `ConfigurationError`.
- `AI_SUMMARY_TIMEOUT` not a positive integer → `ConfigurationError`.
- Misspelled or missing provider settings therefore fail loudly once, instead of quietly degrading every scheduled run.
- Because that failure produces no report, the weekly workflow sets `AI_SUMMARY_ENABLED=true` only when **both** `secrets.AI_SUMMARY_API_KEY` and `vars.AI_SUMMARY_BASE_URL` are non-empty, and omits it otherwise. Guarding the key alone is not enough: the base URL has no default, so a key with no base URL reaches the missing-base-URL branch above and is the same CI trap one variable over. `AI_SUMMARY_BASE_URL` is a repository **variable**, not a secret — a URL is not a credential, an operator must be able to verify it in the repository settings, and hiding it buys nothing. The guard is an `env:` expression yielding the literal `true`/`false` (e.g. `AI_SUMMARY_ENABLED: ${{ secrets.AI_SUMMARY_API_KEY != '' && vars.AI_SUMMARY_BASE_URL != '' }}`) consumed by the step that writes `.env`. It cannot be an `if:` condition: `secrets` is not available in `jobs.<job_id>.if` or `steps.<job_id>.if`, so such a condition evaluates without the secret and silently disables the feature. No workflow sets the flag unconditionally.

**Tradeoff, stated plainly:** a fork or a rotated credential leaves the flag on with no key or no base URL, and with the flag on that means no report at all — not a report without a narrative. Without the workflow guard, a missing secret would silently stop the weekly report, which is the one outcome this feature must not cause. With the guard, a checkout missing either value produces a normal report with the feature off, and gets no AI section until an operator supplies both. The guard is therefore a requirement, not workflow polish.

### FR-008 — Provenance and determinism

- JSON records `provenance.model`, `provenance.prompt_sha` and `provenance.generated_at` (ISO 8601 UTC). `prompt_sha` is a hash of the prompt text, computed from the prompt at generation time, so it cannot drift from the prompt by hand-editing; an archived report can be traced to the model and prompt that produced it.
- console, sheets, email and markdown carry the model id in the attribution line. They do not carry `prompt_sha`.
- The narrative is not deterministic: two runs over identical data may differ in wording and emphasis, and no requirement compares two live generations.
- For identical inputs and identical narrative outcome, every deterministic section is byte-identical, and is identical to a run with the feature off. The report's facts never depend on the narrative.

### FR-009 — Secrets and privacy

- The API key never appears in any output, artifact, error message, notice, warning command or log line, including when the provider echoes it back in an error body or header.
- The key is supplied only through `AI_SUMMARY_API_KEY` (environment or `.env`, same loading as `ESPN_S2`/`SWID`). There is no CLI flag and no `--format-arg` for it — format arguments are for presentation and must not carry credentials.
- The digest, the request body and the response body are never logged at any level, including `-vv`. Only the model, HTTP status, latency and token counts may be logged.
- Team names, owner names and scores leave the machine and are sent to `AI_SUMMARY_BASE_URL`. `ff-tracker --help` states this under the feature's configuration section.

---

## Configuration

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `AI_SUMMARY_ENABLED` | no | `false` | Opt-in switch. Off means no call, no section, no notice. |
| `AI_SUMMARY_API_KEY` | when enabled | none | Bearer token; never printed. |
| `AI_SUMMARY_BASE_URL` | when enabled | none | OpenAI-compatible endpoint root; `/chat/completions` is appended. No default in code: the endpoint used in the spike goes in `.env.example` and the README's configuration section. |
| `AI_SUMMARY_MODEL` | no | `glm-5.3-flash` | Model id, reported verbatim in errors and provenance. |
| `AI_SUMMARY_TIMEOUT` | no | `120` | Whole-call timeout in seconds. |

These are loaded the same way as existing settings (`load_environment` / `.env`).

---

## Data Requirements

### Input

- The weekly report's existing data: `list[DivisionData]`, `list[ChallengeResult]`, `list[WeeklyChallenge] | None`, `current_week`, optional `ChampionshipLeaderboard`, as already assembled in `main.py`.
- Feature configuration from the table above.

### Model additions this feature requires

- `DivisionData.reg_season_count` (or an equivalent field on the same model), populated from the ESPN `League` settings. It does not exist today — `DivisionData` carries `league_id`, `name`, `teams`, `games`, `weekly_games`, `weekly_players` and `playoff_bracket` — so FR-002's "weeks remaining" is a model change the plan must carry, not existing data.

### Prompt

- The prompt text is a module-level constant in the summary service under `ff_tracker/services/`, so a prompt edit is a single reviewable diff and `prompt_sha` is computed from that constant.

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
- **AC-005** A fake error body containing the API key and the base URL never appears in stdout, stderr, the notice, the warning, or any file written to `--output-dir`.
- **AC-006** No log line emitted by the summary service or by any other code this feature adds contains a team name, owner name, league ID, API key, prompt text or response body; a unique marker planted in the digest never appears in a `-vv` run over three leagues. Existing logging in modules this feature does not touch is out of scope for this criterion.
- **AC-007** `finish_reason: "length"` with complete, parseable content is still treated as FR-006's truncation failure — the content is not rendered.
- **AC-008** League matching follows FR-004's total order: (i) entries reordered, or differing only in case and surrounding whitespace, map by name; (ii) with equal counts and no full name match — including one stray entry or one duplicated entry — every section renders by position under our own league names, and no response-supplied league name appears as a heading; (iii) with differing counts and no full name match, the FR-006 contract failure is reported with the count-mismatch reason and nothing is rendered.
- **AC-009** Missing key, missing base URL, bad `AI_SUMMARY_ENABLED` value, and non-numeric or zero `AI_SUMMARY_TIMEOUT` each raise `ConfigurationError` naming the variable, exit 1, record zero calls, and write no report.
- **AC-010** The fake client records the model, base URL, timeout, `max_tokens: 8000` and bearer token from each configuration; changing `AI_SUMMARY_MODEL` changes the value sent and the value in provenance and the attribution line.
- **AC-011** A paragraph containing a tab, newline, `"`, `<`, `&` and emoji renders as one sheet row and one console line, is HTML-escaped in email, and does not break TSV column counts.
- **AC-012** Edge-case inputs — single league, a league with no matchups this week, Week 15 playoff mode, Week 17 championship mode, and a digest with no player data — each produce a valid request and a rendered section; the digest sent in Weeks 15–16 carries bracket matchups and the 7 player highlights, and in Week 17 the championship leaderboard, matching what the formatters display; the mode the digest derives agrees with the mode each of the five formatters renders for the same inputs.

### Workflow configuration check (static; inspects the YAML, not runtime behaviour)

- **WC-001** `.github/workflows/weekly-report.yml` sets `AI_SUMMARY_ENABLED` through an `env:` expression that references both `secrets.AI_SUMMARY_API_KEY` and `vars.AI_SUMMARY_BASE_URL`; the step that writes `.env` appends the three `AI_SUMMARY_*` values only when that value is `true`; and no `if:` condition in the file references `AI_SUMMARY_ENABLED`.

Verified manually against a live provider, once, with a real three-league week:

- **LV-001** Response validates against FR-004 in one call; prose references figures that appear in the deterministic report (spot-check two quoted numbers); length falls in the expected range.
- **LV-002** Setting `AI_SUMMARY_MODEL` to a model id known to be unavailable (e.g. `kimi-k2.6`) yields the FR-006 HTTP failure: report present, notice names the model and status, exit 0.
- **LV-003** Set `AI_SUMMARY_TIMEOUT=1` to force the FR-006 timeout against the live provider; report present, notice names the timeout, exit 0.
- **LV-004** On a week with player highlights suppressed (playoff week or no player data), the returned narrative names no individual players.

---

## Edge Cases

1. **Provider returns well-formed JSON for the wrong week or season** — shape and league matching pass; there is no further verification (see Not doing). The report's deterministic sections remain the source of truth.
2. **Very long prose** — rendered as delivered, flattened in TSV, truncated only if a format already truncates (e.g. table cell widths).

---

## Constitution Deviations

**Article III (Fail-Fast Error Handling).** This feature violates the "no partial data tolerance" clause on purpose: an AI narrative failure degrades the report instead of failing it. Reasoning: the narrative is cosmetic, the report carries the league's weekly facts, and the report runs on a weekly schedule where a failed proxy, model retirement or HTTP 410 would otherwise deny the league its report entirely. The exception is bounded — it applies only to obtaining and validating the narrative; ESPN data failures, configuration errors and every other failure path still fail fast, and the omission is never silent (notice plus Actions warning). This exemption must be recorded in the plan's Complexity Tracking.

**Article X (Performance).** The 5-second typical run applies to the deterministic report with the feature off. With the feature on, the run additionally waits for provider latency (7.7–34.4 s per call in the spike), bounded by `AI_SUMMARY_TIMEOUT`. Callers that care about schedule duration leave the feature off.

---

## Out of Scope (Not doing)

- The season recap (`ff-season-recap`) and championship (`ff-championship`) CLIs.
- Anthropic, Gemini or any provider API family other than OpenAI-compatible Chat Completions; provider SDKs.
- Streaming, retries, caching, or a second attempt with a fallback model.
- A user-authored prompt, tone or league-lore file.
- Adding `weekly_games` to the JSON formatter (the digest is the AI payload, not a new public shape).
- Changing, reordering or reformatting any existing deterministic section.
- Per-format or per-league opt-out: when the feature is on, all five formats get the section.
- Fact-checking the prose beyond the contract in FR-004 and league matching.
- Any `--format-arg` for this feature; credentials and provider settings are environment only.

---

## Open Questions

None open. The earlier question about an `AI_SUMMARY_BASE_URL` default is resolved: no default in code, and the spike's endpoint is documented in `.env.example` and the README's configuration section instead.

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
