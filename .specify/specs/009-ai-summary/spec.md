# Feature: AI Summary (Commissioner's Take)

> **Spec ID**: 009
> **Status**: Draft — for owner review
> **Created**: 2026-10-21
> **Last Updated**: 2026-10-21
> **Version**: 0.1

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

- league name, team count, current week, weeks remaining in the regular season;
- standings: rank, team name, owner name, record, points for, points against, current playoff position;
- the week's matchups: both team names, both scores, margin, both projected scores and both true projection differences;
- the weekly challenges that league won.

Globally it carries the 13 weekly challenge winners (with position and points for player challenges) and the 5 season-challenge leaders, and marks the season challenges as historical in playoff and championship modes (they are final at the end of Week 14).

The digest contains no league IDs, no ESPN credentials and no API key. It is roughly 7 KB for 3 leagues / 24 teams.

### FR-003 — Request

- One OpenAI-compatible Chat Completions call to `<AI_SUMMARY_BASE_URL>/chat/completions` with `Authorization: Bearer <AI_SUMMARY_API_KEY>`.
- `max_tokens` is 8000. The spike's models are reasoning models: at 3000 all four cells returned `finish_reason: length` with empty or truncated content; at 8000, 8/8 returned clean JSON, with reasoning consuming 2.3k–7.1k tokens for 200–400 tokens of prose.
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
- `leagues` contains exactly one entry per league present in the report data, matched by league name after stripping whitespace. A missing league, a duplicated league, or a league name that is not in the data is a contract failure — the section is not rendered partially.
- `leagues` order follows the digest order.
- Voice: a commissioner addressing the league — direct, dry, allowed to be wry, no invented statistics and no claims about players or teams absent from the digest.
- Length expectation: roughly 60–120 words per league (150–400 words for a three-league report, matching the spike's 214/244/322), 1–3 paragraphs and at most 3 bullets per league, `headline` at most 15 words, `season_note` 1–2 sentences. Length is a prompt instruction, not a validation gate: an over-long response renders as delivered and is not truncated or rejected.
- The section is labelled in every format as AI-generated. It is never presented as fact-checked or as a league record. No requirement verifies that its claims are true; only the shape and league membership are validated.
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
    "prompt_version": "1",
    "generated_at": "2026-10-14T05:03:11Z"
  }
}
```

- `ai_summary` is absent when the feature is off; present (narrative or error) when it is on.
- Cell values in sheets and console must not contain tabs or newlines; paragraph text is flattened, not reflowed or summarised.

### FR-006 — Failure policy: the report always ships

Any failure while obtaining or validating the narrative produces the same result: the deterministic report is rendered and written as normal, the section is omitted, the run exits 0, and the failure is visible in two places:

1. a one-line notice in the output, in the section's position and in the format's own style: `AI summary unavailable: <reason>. The report is unaffected.` In JSON the notice is the value of `ai_summary.error`.
2. when `GITHUB_ACTIONS` is `true`, a workflow command on stdout: `::warning::AI summary unavailable: <reason>.` — outside Actions no workflow command is emitted, so console output stays clean.

`<reason>` names what failed and never includes the API key or the response body: for HTTP errors `HTTP 410 (model glm-5.3-flash)`; for timeouts `timed out after 120s`; for truncation `finish_reason=length`; for shape problems `response did not match the summary contract`; for a stray league `unknown league "X"` / for a missing one `missing league "X"`.

This is a deliberate, documented exception to Article III (see Constitution Deviations).

### FR-007 — Enabled but not configured

Configuration errors are not narrative failures and are not degraded:

- `AI_SUMMARY_ENABLED` true with `AI_SUMMARY_API_KEY` missing or empty → `ConfigurationError` naming `AI_SUMMARY_API_KEY`, exit 1, no report, no HTTP call.
- The same for a missing or empty `AI_SUMMARY_BASE_URL`.
- `AI_SUMMARY_ENABLED` set to any value not in `true|1|yes|on|false|0|no|off` (case-insensitive) → `ConfigurationError`.
- `AI_SUMMARY_TIMEOUT` not a positive integer → `ConfigurationError`.
- Misspelled or missing provider settings therefore fail loudly once, instead of quietly degrading every scheduled run.

### FR-008 — Provenance and determinism

- JSON records `provenance.model`, `provenance.prompt_version` and `provenance.generated_at` (ISO 8601 UTC). `prompt_version` changes whenever the prompt text changes, so an archived report can be traced to the model and prompt that produced it.
- console, sheets, email and markdown carry the model id in the attribution line. They do not carry the prompt version.
- The narrative is not deterministic: two runs over identical data may differ in wording and emphasis, and no requirement compares two live generations.
- For identical inputs and identical narrative outcome, every deterministic section is byte-identical, and is identical to a run with the feature off. The report's facts never depend on the narrative.

### FR-009 — Secrets and privacy

- The API key never appears in any output, artifact, error message, notice, warning command or log line, including when the provider echoes it back in an error body or header.
- The key is supplied only through `AI_SUMMARY_API_KEY` (environment or `.env`, same loading as `ESPN_S2`/`SWID`). There is no CLI flag and no `--format-arg` for it — format arguments are for presentation and must not carry credentials.
- Team names, owner names and scores leave the machine and are sent to `AI_SUMMARY_BASE_URL`. `ff-tracker --help` states this under the feature's configuration section.

---

## Configuration

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `AI_SUMMARY_ENABLED` | no | `false` | Opt-in switch. Off means no call, no section, no notice. |
| `AI_SUMMARY_API_KEY` | when enabled | none | Bearer token; never printed. |
| `AI_SUMMARY_BASE_URL` | when enabled | none | OpenAI-compatible endpoint root; `/chat/completions` is appended. No default is assumed. |
| `AI_SUMMARY_MODEL` | no | `glm-5.3-flash` | Model id, reported verbatim in errors and provenance (`kimi-k2.6` returned HTTP 410 on every attempt in the spike, which is why this is configurable). |
| `AI_SUMMARY_TIMEOUT` | no | `120` | Whole-call timeout in seconds; the spike saw 7.7–34.4 s per call. |

These are loaded the same way as existing settings (`load_environment` / `.env`).

---

## Data Requirements

### Input

- The weekly report's existing data: `list[DivisionData]`, `list[ChallengeResult]`, `list[WeeklyChallenge] | None`, `current_week`, optional `ChampionshipLeaderboard`, as already assembled in `main.py`.
- Feature configuration from the table above.

### Output

- `AI summary` value embedded in the report: headline, per-league paragraphs and bullets, season note, provenance (FR-004, FR-005, FR-008).
- On failure: a notice string rendered in the report and, in JSON, `ai_summary.error`.

---

## Failure Modes

| # | Trigger | Behaviour |
|---|---|---|
| F-01 | Feature off (default) | No call, no section, no notice, no warning; output unchanged. |
| F-02 | Enabled, key or base URL missing/invalid | `ConfigurationError`, exit 1, no report, no call. |
| F-03 | HTTP 4xx, including 410 model unavailable | Report ships; notice names status and model; `::warning::` under Actions; exit 0. |
| F-04 | HTTP 5xx | As F-03. |
| F-05 | Timeout | Report ships; notice names the timeout; `::warning::`; exit 0. |
| F-06 | Transport/DNS/TLS error | As F-03, reason `connection failed`. |
| F-07 | `finish_reason == "length"` | Treated as a failure even if the arriving content happens to parse; reason `finish_reason=length`. |
| F-08 | Not JSON, or JSON not matching the contract (missing/extra keys, wrong types, empty headline/paragraph/season_note, empty `leagues`) | Failure; reason `response did not match the summary contract`. |
| F-09 | `leagues` names a league not in the data | Failure; notice names that league. |
| F-10 | `leagues` omits a league that is in the data, or repeats one | Failure; no partial render; notice names the league. |
| F-11 | Provider returns 2xx with an empty body | Failure as F-08. |

---

## Acceptance Criteria

Tested offline with a fake client that records requests and returns canned responses.

- **AC-001** Feature off: zero calls recorded; console, sheets, email, markdown and JSON outputs are byte-identical to the same run on `main`.
- **AC-002** Feature on with a valid fake response: the section appears in all five formats, after the existing sections and before the footer, labelled AI-generated; JSON `ai_summary` contains headline, one entry per league in digest order, and provenance.
- **AC-003** Multi-league run: exactly one call, regardless of 1, 3 or 10 leagues, and exactly one call in `--output-dir` mode with five formats; the same narrative appears in all five files.
- **AC-004** Each of F-03 … F-11 produces: the complete deterministic section set, exit code 0, one notice line in the section's position, no empty heading, no `::warning::` when `GITHUB_ACTIONS` is unset, and exactly one `::warning::` line when it is `true`.
- **AC-005** A fake error body containing the API key and the base URL never appears in stdout, stderr, the notice, the warning, or any file written to `--output-dir`.
- **AC-006** `finish_reason: "length"` with complete, parseable content is still treated as F-07 — the content is not rendered.
- **AC-007** Extra league in the response, missing league, duplicated league, and a league name differing only in surrounding whitespace: first three are F-09/F-10, the last matches. None render a partial section.
- **AC-008** F-02 cases (missing key, missing base URL, bad `AI_SUMMARY_ENABLED` value, non-numeric or zero timeout) raise `ConfigurationError` with the variable named, exit 1, and record zero calls.
- **AC-009** The fake client records the model, base URL, timeout, `max_tokens: 8000` and bearer token from each configuration; changing `AI_SUMMARY_MODEL` changes the value sent and the value in provenance and the attribution line.
- **AC-010** Deterministic sections are byte-identical between a run with a valid narrative, a run with the feature off, and a run where the narrative failed (ignoring the section's own lines and the format's trailing separator).
- **AC-011** A paragraph containing a tab, newline, `"`, `<`, `&` and emoji renders as one sheet row and one console line, is HTML-escaped in email, and does not break TSV column counts.
- **AC-012** Edge-case inputs — single league, a league with no matchups this week, Week 15 playoff mode, Week 17 championship mode, and a digest with no player data — each produce a valid request and a rendered section; the digest sent in Week 15–16 carries bracket matchups rather than weekly team challenges, and in Week 17 carries the championship leaderboard.

Verified manually against a live provider, once, with a real three-league week:

- **LV-001** Response validates against FR-004 in one call; prose references figures that appear in the deterministic report (spot-check two quoted numbers); length falls in the expected range.
- **LV-002** Setting `AI_SUMMARY_MODEL` to a model id known to be unavailable (e.g. `kimi-k2.6`) yields F-03: report present, notice names the model and status, exit 0.
- **LV-003** Set `AI_SUMMARY_TIMEOUT=1` to force F-05 against the live provider; report present, notice names the timeout, exit 0.
- **LV-004** On a week with player highlights suppressed (playoff week or no player data), the returned narrative names no individual players.

---

## Edge Cases

1. **Single-league run** — one league section; the section is per league present in the data, so nothing is special-cased.
2. **League with no games this week** — the digest still carries that league's standings and states that it has no matchups; the league still gets a section, and the prose is not required to describe a game.
3. **Weeks 15–16 playoff mode** — the digest mirrors what the report shows: bracket matchups instead of weekly team challenges, the 7 player highlights, season challenges marked historical. The section still appears.
4. **Week 17 championship mode** — the digest carries the championship leaderboard (division winners ranked by championship score) and the section still appears. `ff-championship` itself is unaffected.
5. **Digest with no player data** — no player highlights are available; the narrative must not name players (LV-004). Data absence is not a failure.
6. **Provider returns well-formed JSON for the wrong week or season** — shape and league names pass; there is no further verification (see Not doing). The report's deterministic sections remain the source of truth.
7. **Very long prose** — rendered as delivered, flattened in TSV, truncated only if a format already truncates (e.g. table cell widths).

---

## Constitution Deviations

**Article III (Fail-Fast Error Handling).** This feature violates the "no partial data tolerance" clause on purpose: an AI narrative failure degrades the report instead of failing it. Reasoning: the narrative is cosmetic, the report carries the league's weekly facts, and the report runs on a weekly schedule where a failed proxy, model retirement or HTTP 410 would otherwise deny the league its report entirely. The exception is bounded — it applies only to obtaining and validating the narrative; ESPN data failures, configuration errors and every other failure path still fail fast, and the omission is never silent (notice plus Actions warning). This exemption must be recorded in the plan's Complexity Tracking.

**Article X (Performance).** The 5-second typical run applies to the deterministic report with the feature off. With the feature on, the run additionally waits for provider latency (7.7–34.4 s in the spike), bounded by `AI_SUMMARY_TIMEOUT`. Callers that care about schedule duration leave the feature off.

---

## Out of Scope (Not doing)

- The season recap (`ff-season-recap`) and championship (`ff-championship`) CLIs.
- Anthropic, Gemini or any provider API family other than OpenAI-compatible Chat Completions; provider SDKs.
- Streaming, retries, caching, or a second attempt with a fallback model.
- A user-authored prompt, tone or league-lore file.
- Adding `weekly_games` to the JSON formatter (the digest is the AI payload, not a new public shape).
- Changing, reordering or reformatting any existing deterministic section.
- Per-format or per-league opt-out: when the feature is on, all five formats get the section.
- Fact-checking the prose beyond the contract in FR-004 and league membership.
- Any `--format-arg` for this feature; credentials and provider settings are environment only.

---

## Open Questions

1. `AI_SUMMARY_BASE_URL` has no default. Confirm the spike's endpoint if a default is wanted; otherwise it stays required when the feature is enabled.
2. The section is placed last, after the deterministic sections. Confirmed as the least disruptive choice; if the commissioner's take should read as an opening instead, that is a placement change, not a contract change.

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
